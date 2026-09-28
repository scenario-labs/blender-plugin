# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Render Image and Render Video lanes: capture first, precise prompts, Prompt Spark when the look is empty."""

import json
import unittest
from unittest.mock import MagicMock, patch

import bpy
from helpers import FIXTURES, isolated_manager, reset_scene, submodule


def rec(name):
    catalog = submodule("core.api.catalog")
    return catalog.ModelRecord.from_api(
        json.loads((FIXTURES / "models" / f"{name}.json").read_text())["model"]
    )


class RenderLanesTests(unittest.TestCase):
    def setUp(self):
        reset_scene()
        self.generation = submodule("blender.generation")
        self.render_lanes = submodule("blender.render_lanes")
        self.runtime = submodule("blender.runtime")
        handlers = submodule("blender.handlers")
        self.runtime.state.reset()
        self.enterContext(isolated_manager())
        records = [
            rec("model_google-gemini-3-1-flash"),
            rec("model_openai-gpt-image-2"),
            rec("model_bytedance-seedance-2-0"),
            rec("model_minimax-h3"),
        ]
        handlers.dispatch(
            ("catalog", {"privacy": "public", "records": records, "detailed": records})
        )
        self.scene = bpy.context.scene
        self.image_lane = self.scene.scenario.lane_state("render_image")
        self.video_lane = self.scene.scenario.lane_state("render_video")

    def uploaded(self, lane_name, role="scene", asset="uploaded-scene"):
        prepared = submodule("blender.render_references")
        lane = self.scene.scenario.lane_state(lane_name)
        spec = prepared.target(lane_name, self.generation.schema_for(lane.model_id), role)
        ref = lane.references.add()
        ref.param_name, ref.source, ref.asset_id = spec.name, "ASSET", asset
        ref[prepared.ROLE] = role
        if role == prepared.FIRST_FRAME:
            ref.filepath = lane.first_frame_path
        return ref

    def test_lane_tabs_have_no_generations_or_mcp(self):
        props = submodule("blender.props")
        ids = [item[0] for item in props.LANE_ITEMS]
        self.assertEqual(
            ids,
            [
                "image",
                "video",
                "3d",
                "material",
                "audio",
                "render_image",
                "render_video",
                "blockout",
            ],
        )
        self.assertIsNotNone(self.scene.scenario.lane_state("render_image"))
        self.assertIsNotNone(self.scene.scenario.lane_state("edit3d"))

    def test_render_image_request_puts_the_capture_first_and_writes_the_scene_prompt(self):
        self.image_lane.model_id = "model_google-gemini-3-1-flash"
        self.image_lane.prompt = "weathered steampunk copper"
        style = self.image_lane.references.add()
        style.param_name, style.source, style.asset_id = (
            "referenceImages",
            "ASSET",
            "uploaded-style",
        )
        self.uploaded("render_image")
        request = self.generation.build_request(self.scene, "render_image")
        self.assertEqual(request.errors, [])
        self.assertEqual(request.kind, "image")
        self.assertEqual(request.captures, [])
        self.assertEqual(request.body["referenceImages"], ["uploaded-scene", "uploaded-style"])
        prompt = request.body["prompt"]
        self.assertTrue(prompt.startswith("Image 1 is a screenshot of a 3D viewport"))
        self.assertIn("weathered steampunk copper", prompt)
        self.assertIn("Image 2 is a style reference only", prompt)
        self.assertIsNone(request.spark)
        self.assertEqual(request.meta["render_lane"], "render_image")

    def test_empty_look_asks_prompt_spark_and_uses_the_default_look_meanwhile(self):
        self.image_lane.model_id = "model_google-gemini-3-1-flash"
        self.image_lane.prompt = ""
        self.image_lane.capture_source = "VIEWPORT"
        self.uploaded("render_image")
        request = self.generation.build_request(self.scene, "render_image")
        self.assertIn("Prompt Spark", request.errors[0])
        self.assertEqual(request.spark, {"kind": "image", "style_count": 0})
        self.assertEqual(request.captures, [])
        self.assertIn("photorealistic", request.body["prompt"])
        self.image_lane.spark_enabled = False
        request = self.generation.build_request(self.scene, "render_image")
        self.assertIsNone(request.spark)

    def test_render_video_seedance_request_tags_inputs_and_uses_the_first_frame(self):
        self.video_lane.model_id = "model_bytedance-seedance-2-0"
        self.video_lane.prompt = "claymation"
        self.video_lane.first_frame_path = str(FIXTURES / "patina-copper-512" / "albedo.png")
        self.scene.frame_start, self.scene.frame_end = 1, 48
        self.uploaded("render_video")
        self.uploaded("render_video", "first_frame", "uploaded-first")
        request = self.generation.build_request(self.scene, "render_video")
        self.assertEqual(request.errors, [])
        self.assertEqual(request.kind, "video")
        self.assertEqual(request.captures, [])
        self.assertEqual(request.body["referenceVideos"], ["uploaded-scene"])
        self.assertEqual(request.body["image"], "uploaded-first")
        self.assertEqual(request.files, {})
        prompt = request.body["prompt"]
        self.assertIn("@video1 is a playblast", prompt)
        self.assertIn("@image1 shows how the finished first frame must look", prompt)
        self.assertIn("claymation", prompt)
        # Render Video: the model's own duration is the source (Seedance default -1 = Auto), not the clip length
        self.assertEqual(request.body["duration"], -1)

    def test_render_video_without_tags_for_minimax(self):
        self.video_lane.model_id = "model_minimax-h3"
        self.video_lane.prompt = "oil painting"
        self.video_lane.first_frame_path = ""
        self.uploaded("render_video")
        request = self.generation.build_request(self.scene, "render_video")
        self.assertEqual(request.body["referenceVideos"], ["uploaded-scene"])
        prompt = request.body["prompt"]
        self.assertTrue(prompt.startswith("The reference video is a playblast"))
        self.assertNotIn("@video1", prompt)
        self.assertIsNone(request.spark)

    def test_empty_video_look_blocks_until_spark_has_separate_approval(self):
        self.video_lane.model_id = "model_bytedance-seedance-2-0"
        self.video_lane.prompt = ""
        self.uploaded("render_video")
        request = self.generation.build_request(self.scene, "render_video")
        self.assertEqual(request.captures, [])
        self.assertIn("Prompt Spark", request.errors[0])
        self.assertEqual(request.spark["kind"], "video")

    def test_first_frame_picker_is_drawn_when_empty(self):
        self.video_lane.model_id = "model_bytedance-seedance-2-0"
        layout = MagicMock()
        self.assertEqual(self.video_lane.first_frame_path, "")
        self.render_lanes._draw_first_frame(
            layout, self.video_lane, self.generation.schema_for(self.video_lane.model_id)
        )
        layout.row.return_value.prop.assert_any_call(self.video_lane, "first_frame_path", text="")
        self.assertEqual(self.video_lane.bl_rna.properties["first_frame_path"].subtype, "FILE_PATH")
        self.assertEqual(self.video_lane.first_frame_path, "")

    def test_result_reference_action_preserves_prepared_single_file_render_slots(self):
        catalog = submodule("core.api.catalog")
        form = submodule("blender.reference_form")
        for lane_name, role in (("render_image", "scene"), ("render_video", "first_frame")):
            with self.subTest(lane=lane_name):
                lane = self.scene.scenario.lane_state(lane_name)
                model = catalog.ModelRecord.from_api(
                    {
                        "id": "fixture-single-render-" + lane_name,
                        "name": "Single render input",
                        "type": "custom",
                        "capabilities": [
                            "img2img" if lane_name == "render_image" else "video2video"
                        ],
                        "inputs": [{"name": "image", "type": "file", "kind": "image"}]
                        + (
                            [{"name": "video", "type": "file", "kind": "video"}]
                            if lane_name == "render_video"
                            else []
                        ),
                    }
                )
                self.generation.set_catalog([model], [model])
                lane.model_id = model.id
                ref = lane.references.add()
                ref.param_name, ref.source, ref.asset_id = "image", "ASSET", "prepared-asset"
                ref[form.RENDER_ROLE] = role
                lane.estimate_key, lane.estimate_state = "approved-quote", "READY"
                with self.assertRaisesRegex(RuntimeError, "prepared render reference"):
                    bpy.ops.scenario.use_as_reference(
                        filepath=str(FIXTURES / "patina-copper-512" / "albedo.png"),
                        target=lane_name,
                    )
                self.assertEqual(len(lane.references), 1)
                self.assertEqual(ref.asset_id, "prepared-asset")
                self.assertEqual(ref.get(form.RENDER_ROLE), role)
                self.assertEqual(lane.estimate_key, "approved-quote")
                self.assertEqual(lane.estimate_state, "READY")

    def test_render_image_result_preserves_the_video_first_frame_and_quote(self):
        records = submodule("core.jobs.records")
        job = records.JobRecord.new(
            lane="render_image",
            kind="image",
            model_id="model_google-gemini-3-1-flash",
            body={},
            meta={"render_lane": "render_image", "spark_look": "warm brass"},
        )
        job.files = [str(FIXTURES / "patina-copper-512" / "albedo.png")]
        job.status = "success"
        self.video_lane.first_frame_path = "chosen-first-frame.png"
        self.video_lane.estimate_key = "approved-video-quote"
        self.video_lane.estimate_state = "READY"
        self.video_lane.estimate_dirty_at = 0
        self.render_lanes.on_result(job)
        self.assertEqual(self.video_lane.first_frame_path, "chosen-first-frame.png")
        self.assertEqual(self.video_lane.estimate_key, "approved-video-quote")
        self.assertEqual(self.video_lane.estimate_state, "READY")
        self.assertEqual(self.video_lane.estimate_dirty_at, 0)
        self.assertEqual(self.image_lane.spark_look, "warm brass")

    def test_prepare_writes_the_spark_look_into_the_body(self):
        class FakeClient:
            def post(self, path, json_body=None, query=None):
                assert path == "/generate/prompt"
                assert json_body["images"][0].startswith("data:image/png;base64,")
                return {"prompts": ["brushed brass under studio light"]}

        records = submodule("core.jobs.records")
        job = records.JobRecord.new(
            lane="render_image", kind="image", model_id="m", body={"prompt": "placeholder"}, meta={}
        )
        prepare = self.render_lanes.make_prepare(
            {"kind": "image", "style_count": 1},
            str(FIXTURES / "patina-copper-512" / "albedo.png"),
            "prompt",
        )
        prepare(FakeClient(), job)
        self.assertIn("brushed brass under studio light", job.body["prompt"])
        self.assertIn("Image 2 is a style reference only", job.body["prompt"])
        self.assertEqual(job.meta["spark_look"], "brushed brass under studio light")

    def test_panels_are_registered_as_four_sections(self):
        for name in (
            "SCENARIO_PT_main",
            "SCENARIO_PT_jobs",
            "SCENARIO_PT_generations",
            "SCENARIO_PT_agents",
        ):
            self.assertTrue(hasattr(bpy.types, name), name)
        self.assertFalse(hasattr(bpy.types, "SCENARIO_PT_results"))


class TimelineSyncTests(unittest.TestCase):
    def setUp(self):
        reset_scene()
        self.generation = submodule("blender.generation")
        self.runtime = submodule("blender.runtime")
        handlers = submodule("blender.handlers")
        self.runtime.state.reset()
        self.enterContext(isolated_manager())
        records = [rec("model_minimax-h3"), rec("model_bytedance-seedance-2-0")]
        handlers.dispatch(
            ("catalog", {"privacy": "public", "records": records, "detailed": records})
        )
        self.scene = bpy.context.scene
        self.lane = self.scene.scenario.lane_state("render_video")

    def test_render_video_duration_is_the_model_setting_not_the_clip(self):
        # Render Video flips the base Video direction (0.9.2): the model's duration in Settings is the source, the
        # scene frame range no longer drives it, and with Match timeline on the camera path follows the model duration.
        self.lane.model_id = "model_minimax-h3"
        self.scene.frame_start, self.scene.frame_end = (
            1,
            144,
        )  # 6 s: must NOT force duration to 6 any more
        self.lane.params["duration"].int_value = 8
        request = self.generation.build_request(self.scene, "render_video")
        self.assertEqual(request.body["duration"], 8)
        self.lane.match_timeline = True
        self.generation.sync_shot_duration(self.scene)
        self.assertAlmostEqual(
            self.scene.scenario_shot.duration, 8.0, places=3
        )  # the camera path follows the model
        # Seedance keeps its own Auto default, still independent of the clip length
        self.lane.model_id = "model_bytedance-seedance-2-0"
        request = self.generation.build_request(self.scene, "render_video")
        self.assertEqual(request.body["duration"], -1)

    def test_model_switch_rebuilds_every_parameter_without_callback_errors(self):
        params_ui = submodule("blender.params_ui")
        original_sync = params_ui.sync_params
        errors = []

        def sync(*args):
            try:
                return original_sync(*args)
            except Exception as error:
                # Blender catches property-update errors itself, so record them
                # explicitly instead of letting unittest report a false pass.
                errors.append(str(error))
                raise

        with patch.object(params_ui, "sync_params", side_effect=sync):
            for model_id in (
                "model_minimax-h3",
                "model_bytedance-seedance-2-0",
                "model_minimax-h3",
            ):
                self.lane.model_id = model_id
                self.assertEqual(errors, [], "Model-switch callback failed")
                schema = self.generation.schema_for(model_id)
                expected = {
                    spec.name for spec in schema.specs if not spec.is_prompt and not spec.is_file
                }
                self.assertEqual({item.name for item in self.lane.params}, expected)
                self.assertEqual(len(self.lane.params), len(expected))
                self.assertTrue(all(item.model_id == model_id for item in self.lane.params))
                for item in self.lane.params:
                    spec = schema.by_name(item.name)
                    if spec.allowed_values and spec.ptype != "string_array":
                        self.assertIn(
                            item.enum_value,
                            [str(value) for value in spec.allowed_values if str(value)],
                        )

    def test_messages_expire(self):
        self.runtime.set_message("Submitted to Meshy 7")
        self.assertEqual(self.runtime.message_visible(), "Submitted to Meshy 7")
        self.runtime.state.message_at -= 60
        self.assertEqual(self.runtime.message_visible(), "")
