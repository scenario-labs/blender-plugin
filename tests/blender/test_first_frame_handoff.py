# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Saved image results handed to the Render Video first frame through the shared runtime,
local MCP and the native saved-job controls.

Synthetic SDK transport and real job storage; no physical desktop interaction.
"""

import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import bpy
import test_model_generation as model_tests
from helpers import submodule

# A first-frame input the schema lets go with the clip (no declared exclusivity).
FRAME_AND_CLIP = [
    {"name": "prompt", "type": "string", "prompt": True},
    {"name": "image", "type": "file", "kind": "image", "label": "First Frame"},
    {"name": "referenceImages", "type": "file_array", "kind": "image", "maxLength": 9},
    {"name": "referenceVideos", "type": "file_array", "kind": "video", "maxLength": 3},
]
# Seedance 2.0 Fast's live wording (2026-10-10): its first frame cannot be sent
# with reference images or videos. A paid job with both was accepted, then failed.
SEEDANCE = [
    {"name": "prompt", "type": "string", "prompt": True},
    {
        "name": "image",
        "type": "file",
        "kind": "image",
        "label": "First Frame",
        "description": "First frame image (frame mode). "
        "Mutually exclusive with reference images/videos.",
        "required": {"ifDefined": {"lastFrameImage": {}}},
    },
    {
        "name": "lastFrameImage",
        "type": "file",
        "kind": "image",
        "label": "Last Frame",
        "description": "Last frame image. Only valid when a first frame image is provided.",
    },
    {
        "name": "referenceImages",
        "type": "file_array",
        "kind": "image",
        "label": "Reference Images",
        "maxLength": 9,
        "description": "Reference images for multimodal mode (up to 9). "
        "Mutually exclusive with first frame.",
    },
    {
        "name": "referenceVideos",
        "type": "file_array",
        "kind": "video",
        "label": "Reference Videos",
        "maxLength": 3,
        "description": "Reference videos for multimodal mode (up to 3). "
        "Mutually exclusive with first frame.",
    },
]
H3 = [
    {"name": "prompt", "type": "string", "required": True, "prompt": True},
    {"name": "firstFrameImage", "type": "file", "kind": "image", "label": "First Frame"},
    {"name": "lastFrameImage", "type": "file", "kind": "image", "label": "Last Frame"},
    {"name": "referenceVideos", "type": "file_array", "kind": "video", "maxLength": 3},
]
ARRAY_ONLY = [
    {"name": "prompt", "type": "string", "required": True, "prompt": True},
    {
        "name": "referenceImages",
        "type": "file_array",
        "kind": "image",
        "maxLength": 2,
        "label": "Reference Images",
    },
    {"name": "video", "type": "file", "kind": "video"},
]
NO_IMAGE = [
    {"name": "prompt", "type": "string", "required": True, "prompt": True},
    {"name": "video", "type": "file", "kind": "video"},
]
JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00" + bytes(64)
WEBP = b"RIFF\x48\x00\x00\x00WEBPVP8 " + bytes(64)


class FirstFrameHandoffTests(unittest.TestCase):
    cleanup_jobs = model_tests.ModelGenerationTests.cleanup_jobs
    result_fixture = model_tests.ModelGenerationTests.result_fixture
    settle = model_tests.ModelGenerationTests.settle
    deliver_results = model_tests.ModelGenerationTests.deliver_results
    configure_ui_lane = model_tests.ModelGenerationTests.configure_ui_lane
    mcp_quote = model_tests.ModelGenerationTests.mcp_quote
    mcp_submit = model_tests.ModelGenerationTests.mcp_submit
    recovery_args = model_tests.ModelGenerationTests.recovery_args

    def setUp(self):
        model_tests.ModelGenerationTests.setUp(self)
        self.handoff = submodule("blender.first_frame_handoff")
        self.references = submodule("blender.render_references")
        self.form = submodule("blender.reference_form")
        self.jobstate = self.storemod.JobState
        self.image_model = self.model
        saved = self.prefs.project_id
        self.addCleanup(setattr, self.prefs, "project_id", saved)

    # -- fixtures ---------------------------------------------------------

    def saved_image(self, data=None, media_type="image/png", metadata=None):
        """A downloaded image job saved READY without automatic import."""
        self.model = self.image_model
        record = submodule("core.api.catalog").ModelRecord.from_api(self.model)
        self.runtime.ensure_job_store()
        self.generation.set_catalog([record], [record])
        if data is None:
            self.result_fixture()
        else:
            self.result_bytes, self.remote_status = data, "success"
        self.result_media_type = media_type
        if metadata is not None:
            self.result_metadata = metadata
        result = self.mcp_submit(self.mcp_quote())
        owner = self.runtime.state.model_jobs
        owner.submissions[result["local_id"]].result(5)
        owner.session.invalidate_scene(bpy.context.scene)
        self.deliver_results()
        self.runtime.state.reset()
        self.runtime.inspect_model_jobs()
        self.assertEqual(self.store.get(result["local_id"]).state, self.jobstate.READY)
        return result["local_id"]

    def render_video(self, inputs, model_id="fixture-render-video"):
        """Select one Render Video model with an uploaded scene clip and a typed look."""
        model = {
            "id": model_id,
            "name": "Render video fixture",
            "type": "custom",
            "capabilities": ["video2video"],
            "inputs": inputs,
        }
        record = submodule("core.api.catalog").ModelRecord.from_api(model)
        self.runtime.state.records[record.id] = record
        self.generation._schemas.pop(record.id, None)
        self.runtime.set_enum_items(("models", "render_video"), [(record.id, record.name, "")])
        lane = bpy.context.scene.scenario.lane_state("render_video")
        lane.references.clear()
        lane.model_id = record.id
        self.generation.on_model_changed(bpy.context, lane)
        lane.prompt = "copper sculpture"
        video = next(item["name"] for item in inputs if item.get("kind") == "video")
        ref = lane.references.add()
        ref.param_name, ref.source, ref.asset_id = video, "ASSET", "scene-clip"
        ref[self.references.ROLE] = self.references.SCENE
        # Later quotes read this model's detail through the synthetic transport.
        self.model = model
        return lane

    def prepare(self, request_id, asset_id="result-image"):
        args = self.recovery_args(request_id, "use_first_frame")
        del args["action"]
        args.update(purpose="video_first_frame", asset_id=asset_id)
        return self.tools.prepare_result_application(args)

    def apply(self, approval):
        deferred = self.tools.apply_result_application(
            {key: approval[key] for key in ("context_id", "application_id")}
        )
        return deferred.finish(deferred.run())

    def estimate(self):
        deferred = self.tools.estimate_cost(
            {"model_id": self.model["id"], "parameters": {}, "lane": "render_video"}
        )
        return deferred.finish(deferred.run())

    def first_frames(self, lane):
        return self.references.slot(lane, self.references.FIRST_FRAME)

    def network(self):
        return len(self.calls), len(self.paid), len(self.downloads)

    def slot_values(self, lane):
        """Every first-frame slot's RNA fields and ID properties, for change checks."""
        return [
            (
                (ref.param_name, ref.source, ref.asset_id, ref.filepath, ref.label),
                {key: str(ref[key]) for key in ref.keys()},
            )
            for _, ref in self.first_frames(lane)
        ] + [(lane.first_frame_path, lane.use_first_frame, lane.estimate_state)]

    # -- tests ------------------------------------------------------------

    def test_saved_png_binds_its_asset_without_upload_path_spend_or_job_change(self):
        request_id = self.saved_image()
        lane = self.render_video(FRAME_AND_CLIP)
        lane.first_frame_path = "chosen-first-frame.png"
        record, before = self.store.get(request_id), self.network()
        owner = self.runtime.state.model_jobs
        self.assertIn("use_first_frame", owner.status(request_id)["actions"])
        # Native surfaces offer the same review for the projected still.
        recovery = submodule("blender.job_recovery")
        drawn = [
            (item.label, item.operator, dict(item.properties)["asset_id"])
            for item in recovery.result_actions(owner.views[request_id])
            if item.action == "use_first_frame"
        ]
        self.assertEqual(
            drawn,
            [("Use as video first frame (1)", "scenario.use_saved_first_frame", "result-image")],
        )
        approval = self.prepare(request_id)
        self.assertEqual(
            {
                key: approval[key]
                for key in (
                    "kind",
                    "purpose",
                    "lane",
                    "model_id",
                    "input",
                    "asset_id",
                    "mode",
                    "sent_as",
                    "replaces_first_frame_path",
                    "enables_first_frame",
                    "scene",
                )
            },
            {
                "kind": "video_first_frame",
                "purpose": "video_first_frame",
                "lane": "render_video",
                "model_id": "fixture-render-video",
                "input": "image",
                "asset_id": "result-image",
                "mode": "reuse_asset",
                "sent_as": "first_frame",
                "replaces_first_frame_path": True,
                "enables_first_frame": False,
                "scene": bpy.context.scene.name,
            },
        )
        self.assertNotIn("reuse", approval)
        # Preparation is inert: no request, read, form change or saved-job change.
        self.assertEqual(self.network(), before)
        self.assertEqual(self.first_frames(lane), [])
        self.assertEqual(lane.first_frame_path, "chosen-first-frame.png")
        self.assertEqual(self.store.get(request_id), record)
        lane.estimate_state = "READY"
        status = self.apply(approval)
        self.assertEqual(status["status"], "ready", status)
        self.assertIsNone(status["error"])
        self.assertEqual(status["local_applications"], [])
        self.assertEqual(
            status["first_frame"],
            {
                "state": "bound",
                "scene": bpy.context.scene.name,
                "lane": "render_video",
                "input": "image",
                "asset_id": "result-image",
                "undo_recorded": False,  # background sessions have no desktop history
                "error": None,
            },
        )
        self.assertEqual(self.store.get(request_id), record)
        self.assertEqual(self.network(), before)
        self.assertFalse(self.runtime.state.job_session.upload_recovery_plan())
        (_, ref), *others = self.first_frames(lane)
        self.assertEqual(others, [])
        self.assertEqual(
            (ref.param_name, ref.source, ref.asset_id, ref.filepath),
            ("image", "ASSET", "result-image", ""),
        )
        self.assertEqual(ref[self.form._ASSET], "result-image")
        self.assertEqual(ref[self.form._KIND], "image")
        self.assertEqual(
            ref[self.form._SCOPE], self.form.scope_key(self.runtime.state.job_session.scope)
        )
        self.assertNotIn(self.form._MARKER, ref)
        self.assertEqual(
            json.loads(ref[self.form._RESULT]),
            {
                "request_id": request_id,
                "asset_id": "result-image",
                "sha256": record.results[0].receipt.sha256,
            },
        )
        self.assertEqual((lane.first_frame_path, lane.use_first_frame), ("", True))
        self.assertEqual(lane.estimate_state, "PENDING")
        # No private result path reaches the form.
        state_dir = str(self.runtime.paths().state_dir)
        for value in (lane.first_frame_path, ref.filepath, ref.label, *ref.keys()):
            self.assertNotIn(state_dir, str(value))
        self.assertNotIn(state_dir, json.dumps({key: str(ref[key]) for key in ref.keys()}))
        self.assertIsNone(self.form.scope_error(lane))
        request = self.generation.build_request(bpy.context.scene, "render_video", True)
        self.assertEqual(request.errors, [])
        self.assertEqual(request.body["image"], "result-image")
        self.assertEqual(request.body["referenceVideos"], ["scene-clip"])
        self.assertIn("finished first frame must look", request.body["prompt"])
        inspection = self.tools.render_form({"lane": "render_video"})
        sources = [item["source_result"] for item in inspection["references"]]
        self.assertEqual(
            sources, [None, {"request_id": request_id, "asset_id": "result-image", "saved": True}]
        )
        self.assertTrue(inspection["ready_to_estimate"], inspection["errors"])
        self.assertEqual(inspection["first_frame_path"], "")
        # The free quote carries the saved asset ID in the first-frame input.
        quote = self.estimate()
        dry_run = [
            json.loads(call.content)
            for call in self.calls
            if call.url.params.get("dryRun") == "true"
        ][-1]
        self.assertEqual(dry_run["image"], "result-image")
        self.assertEqual(quote["lane"], "render_video")
        self.assertEqual(len(self.paid), 0 + before[1])
        # The approval is single-use and an occupied slot refuses another review.
        with self.assertRaises(self.request_error):
            self.apply(approval)
        with self.assertRaisesRegex(self.request_error, "Remove the current Render Video first"):
            self.prepare(request_id)

    def test_minimax_style_and_array_only_models_receive_the_first_frame(self):
        request_id = self.saved_image()
        lane = self.render_video(H3, "fixture-render-h3")
        self.apply(self.prepare(request_id))
        request = self.generation.build_request(bpy.context.scene, "render_video", True)
        self.assertEqual(request.errors, [])
        self.assertEqual(request.body["firstFrameImage"], "result-image")
        self.assertNotIn("lastFrameImage", request.body)
        lane = self.render_video(ARRAY_ONLY, "fixture-render-array")
        style = lane.references.add()
        style.param_name, style.source, style.asset_id = "referenceImages", "ASSET", "style-a"
        status = self.apply(self.prepare(request_id))
        self.assertEqual(status["first_frame"]["input"], "referenceImages")
        request = self.generation.build_request(bpy.context.scene, "render_video", True)
        self.assertEqual(request.errors, [])
        # The first frame orders before style references in the shared array.
        self.assertEqual(request.body["referenceImages"], ["result-image", "style-a"])

    def test_seedance_first_frame_is_sent_as_reference_image_1_with_the_scene_clip(self):
        request_id = self.saved_image()
        lane = self.render_video(SEEDANCE, "fixture-render-seedance")
        style = lane.references.add()
        style.param_name, style.source, style.asset_id = "referenceImages", "ASSET", "style-a"
        approval = self.prepare(request_id)
        # The review says what will be sent before anything changes.
        self.assertEqual(
            {key: approval[key] for key in ("input", "input_label", "sent_as", "reason")},
            {
                "input": "referenceImages",
                "input_label": "Reference Images",
                "sent_as": "reference_image",
                "reason": "exclusive",
            },
        )
        self.assertIn(
            "This model can't use an exact first frame with the scene clip, "
            "so the image is sent as image 1 of Reference Images.",
            approval["note"],
        )
        status = self.apply(approval)
        self.assertEqual(status["first_frame"]["state"], "bound", status)
        self.assertEqual(status["first_frame"]["input"], "referenceImages")
        request = self.generation.build_request(bpy.context.scene, "render_video", True)
        self.assertEqual(request.errors, [])
        self.assertNotIn("image", request.body)
        self.assertEqual(request.body["referenceImages"], ["result-image", "style-a"])
        self.assertEqual(request.body["referenceVideos"], ["scene-clip"])
        self.assertIn(
            "@image1 shows how the finished first frame must look", request.body["prompt"]
        )
        self.estimate()
        dry_run = [
            json.loads(call.content)
            for call in self.calls
            if call.url.params.get("dryRun") == "true"
        ][-1]
        self.assertNotIn("image", dry_run)
        self.assertEqual(dry_run["referenceImages"], ["result-image", "style-a"])
        self.assertEqual(dry_run["referenceVideos"], ["scene-clip"])

    def test_eligibility_offers_only_downloaded_colour_stills(self):
        for media_type, data in (("image/jpeg", JPEG), ("image/webp", WEBP)):
            with self.subTest(media_type=media_type):
                request_id = self.saved_image(data, media_type)
                owner = self.runtime.state.model_jobs
                record = self.store.get(request_id)
                self.assertIn("use_first_frame", owner.actions(record))
                self.render_video(FRAME_AND_CLIP)
                status = self.apply(self.prepare(request_id))
                self.assertEqual(status["first_frame"]["state"], "bound", status)
        item = record.results[0]
        variants = {
            "exr": replace(item, asset=replace(item.asset, media_type="image/x-exr")),
            "normal map": replace(item, asset=replace(item.asset, texture_role="normal")),
            "not downloaded": replace(item, receipt=None),
        }
        for name, result in variants.items():
            with self.subTest(variant=name):
                self.assertNotIn(
                    "use_first_frame", owner.actions(replace(record, results=(result,)))
                )
        base = replace(item, asset=replace(item.asset, texture_role="base"))
        self.assertIn("use_first_frame", owner.actions(replace(record, results=(base,))))
        prompt = replace(record, intent=replace(record.intent, operation="prompt"))
        self.assertEqual(self.handoff.eligible_assets(prompt), ())
        # Applied jobs keep offering it; the explicit control command refuses it.
        with self.assertRaises(self.request_error):
            owner.control(request_id, record.revision, "use_first_frame")

    def test_refusals_leave_the_form_and_saved_job_unchanged(self):
        request_id = self.saved_image()
        record = self.store.get(request_id)
        lane = self.render_video(FRAME_AND_CLIP)
        with self.assertRaisesRegex(self.request_error, "Choose one downloaded PNG"):
            self.prepare(request_id, "another-asset")
        with self.assertRaisesRegex(ValueError, "requires the saved image asset_id"):
            self.prepare(request_id, "")
        pending = lane.references.add()
        pending.param_name, pending.source, pending.filepath = "image", "FILE", "first.png"
        pending[self.references.ROLE] = self.references.FIRST_FRAME
        pending[self.form._MARKER] = "uncertain-upload"
        with self.assertRaisesRegex(self.request_error, "Remove the current Render Video first"):
            self.prepare(request_id)
        lane.references.remove(len(lane.references) - 1)
        library = lane.references.add()
        library.param_name, library.source, library.asset_id = "image", "ASSET", "library-asset"
        with self.assertRaisesRegex(self.request_error, "Remove a reference from First Frame"):
            self.prepare(request_id)
        lane = self.render_video(ARRAY_ONLY, "fixture-render-array")
        for name in ("style-a", "style-b"):
            style = lane.references.add()
            style.param_name, style.source, style.asset_id = "referenceImages", "ASSET", name
        with self.assertRaisesRegex(self.request_error, "Remove a reference from Reference"):
            self.prepare(request_id)
        self.render_video(NO_IMAGE, "fixture-render-no-image")
        with self.assertRaisesRegex(self.request_error, "with an image input"):
            self.prepare(request_id)
        lane = self.render_video(FRAME_AND_CLIP)
        reads = AssertionError("Reviewing started a model read")
        with (
            patch.object(self.generation, "schema_for", return_value=None),
            patch.object(self.generation, "ensure_record", side_effect=reads),
        ):
            with self.assertRaisesRegex(self.request_error, "Load the Render Video model"):
                self.prepare(request_id)
        self.assertEqual(len(lane.references), 1)
        self.assertEqual(self.store.get(request_id), record)
        self.assertEqual(self.runtime.state.model_jobs._application_approvals, {})
        other = bpy.data.scenes.new("Other destination")
        self.addCleanup(bpy.data.scenes.remove, other)
        owner = self.runtime.state.model_jobs
        with self.assertRaisesRegex(self.request_error, "Select the destination scene"):
            owner.prepare_first_frame_application(
                request_id, record.revision, other, "result-image"
            )

    def test_changed_form_or_context_before_apply_requires_a_fresh_review(self):
        request_id = self.saved_image()
        edits = {
            "model": lambda lane: self.render_video(H3, "fixture-render-h3"),
            "chosen file": lambda lane: setattr(lane, "first_frame_path", "other.png"),
            "enabled": lambda lane: setattr(lane, "use_first_frame", False),
            "references": lambda lane: lane.references.add(),
        }
        for name, edit in edits.items():
            with self.subTest(edit=name):
                lane = self.render_video(FRAME_AND_CLIP)
                lane.use_first_frame = True
                approval = self.prepare(request_id)
                edit(lane)
                with self.assertRaises((self.request_error, self.origin_error)):
                    self.apply(approval)
                lane = bpy.context.scene.scenario.lane_state("render_video")
                self.assertEqual(self.first_frames(lane), [])
        self.render_video(FRAME_AND_CLIP)
        approval = self.prepare(request_id)
        self.runtime.state.model_jobs.session.invalidate_all()  # undo, redo or file load
        with self.assertRaises(self.origin_error):
            self.apply(approval)
        approval = self.prepare(request_id)
        context_id = approval["context_id"]
        self.runtime.state.reset()  # a credential or project change retires the context
        self.runtime.inspect_model_jobs()
        with self.assertRaisesRegex(self.request_error, "context changed"):
            self.tools.apply_result_application(
                {"context_id": context_id, "application_id": approval["application_id"]}
            )
        self.assertEqual(self.first_frames(self.render_video(FRAME_AND_CLIP)), [])

    def test_changes_during_verification_stop_without_binding(self):
        request_id = self.saved_image()
        record = self.store.get(request_id)
        changes = {
            "scene": lambda lane: self.runtime.state.model_jobs.session.invalidate_scene(
                bpy.context.scene
            ),
            "form": lambda lane: setattr(lane, "use_first_frame", False),
            "slot": lambda lane: lane.references.add(),
        }
        for name, change in changes.items():
            with self.subTest(change=name):
                lane = self.render_video(FRAME_AND_CLIP)
                lane.use_first_frame = True
                approval = self.prepare(request_id)
                deferred = self.tools.apply_result_application(
                    {key: approval[key] for key in ("context_id", "application_id")}
                )
                result = deferred.run()
                change(lane)
                status = deferred.finish(result)
                self.assertEqual(status["status"], "ready", status)
                self.assertEqual(status["first_frame"]["state"], "failed")
                self.assertTrue(status["first_frame"]["error"])
                self.assertEqual(status["error"], self.handoff.STOPPED)
                self.assertTrue(status["delivery_paused"])
                self.assertIn("use_first_frame", status["actions"])
                self.assertEqual(self.first_frames(lane), [])
                self.assertEqual(self.store.get(request_id), record)

    def test_tampered_or_mislabelled_bytes_are_refused_at_binding(self):
        request_id = self.saved_image()
        record = self.store.get(request_id)
        receipt = record.results[0].receipt
        root = self.runtime.paths().state_dir / "shared-results"
        (path,) = [item for item in root.rglob(receipt.name) if item.is_file()]
        original = path.read_bytes()
        self.addCleanup(path.write_bytes, original)
        for moment in ("before verification", "after verification"):
            with self.subTest(moment=moment):
                lane = self.render_video(FRAME_AND_CLIP)
                approval = self.prepare(request_id)
                if moment == "before verification":
                    path.write_bytes(original[:-1] + b"\x00")
                    status = self.apply(approval)
                else:
                    deferred = self.tools.apply_result_application(
                        {key: approval[key] for key in ("context_id", "application_id")}
                    )
                    result = deferred.run()
                    path.write_bytes(original[:-1] + b"\x00")
                    status = deferred.finish(result)
                path.write_bytes(original)
                self.assertEqual(status["first_frame"]["state"], "failed", status)
                self.assertEqual(self.first_frames(lane), [])
        mislabelled = self.saved_image(b"GIF89a" + bytes(64), "image/png")
        lane = self.render_video(FRAME_AND_CLIP)
        status = self.apply(self.prepare(mislabelled))
        self.assertEqual(
            status["first_frame"]["error"], "Image contents do not match the saved media type"
        )
        self.assertEqual(self.first_frames(lane), [])

    def test_bound_frame_drives_spark_and_changes_follow_the_existing_slot_rules(self):
        request_id = self.saved_image()
        lane = self.render_video(FRAME_AND_CLIP)
        lane.prompt = ""
        spark = submodule("blender.render_prompt_jobs")
        with self.assertRaisesRegex(self.request_error, "first frame for video Prompt Spark"):
            spark.parameters(bpy.context.scene, "render_video")
        self.apply(self.prepare(request_id))
        payload, key = spark.parameters(bpy.context.scene, "render_video")
        self.assertEqual(payload["images"], ["result-image"])
        self.assertIn("result-image", key)
        # Choosing a local file afterwards needs the old slot removed first.
        lane.first_frame_path = "chosen.png"
        request = self.generation.build_request(bpy.context.scene, "render_video", True)
        self.assertTrue(any("remove its old reference" in error for error in request.errors))
        lane.first_frame_path = ""
        # Disabling omits it; removing the slot allows a fresh handoff.
        lane.use_first_frame = False
        self.assertFalse(self.references.first_frame_enabled(lane))
        request = self.generation.build_request(bpy.context.scene, "render_video", True)
        self.assertNotIn("image", request.body)
        lane.use_first_frame = True
        inspection = self.tools.render_form({"lane": "render_video"})
        key = inspection["references"][1]["reference_key"]
        self.tools.render_form({"lane": "render_video", "action": "remove", "reference_key": key})
        self.assertFalse(self.references.first_frame_enabled(lane))
        status = self.apply(self.prepare(request_id))
        self.assertEqual(status["first_frame"]["state"], "bound")

    def test_saved_blend_keeps_no_private_path_and_is_scoped_on_reopen(self):
        request_id = self.saved_image()
        lane = self.render_video(FRAME_AND_CLIP)
        self.apply(self.prepare(request_id))
        state_dir = str(self.runtime.paths().state_dir)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "first-frame.blend"
            bpy.ops.wm.save_as_mainfile(filepath=str(path), check_existing=False, compress=False)
            data = path.read_bytes()
            self.assertIn(b"result-image", data)  # the slot itself is saved uncompressed
            self.assertNotIn(state_dir.encode(), data)
            self.assertNotIn(b"shared-results", data)
            self.runtime.state.reset()
            bpy.ops.wm.open_mainfile(filepath=str(path))
        lane = bpy.context.scene.scenario.lane_state("render_video")
        (_, ref), *_ = self.first_frames(lane)
        self.assertEqual(self.handoff.provenance(ref)["request_id"], request_id)
        self.runtime.inspect_model_jobs()
        self.render_video_records(FRAME_AND_CLIP)
        self.assertIsNone(self.form.scope_error(lane))
        self.assertIsNotNone(self.handoff.saved_source(self.runtime.state.job_store, ref))
        request = self.generation.build_request(bpy.context.scene, "render_video", True)
        self.assertEqual(request.errors, [])
        self.assertEqual(request.body["image"], "result-image")
        self.prefs.project_id = "different-project"
        self.runtime.state.reset()
        self.runtime.ensure_job_session()
        self.assertIn("another connection", self.form.scope_error(lane))
        self.assertIsNone(self.handoff.saved_source(self.runtime.state.job_store, ref))

    # -- native controls --------------------------------------------------

    def native_operator(self, request_id, asset_id="result-image"):
        """The native review operator on a stand-in instance with a recording layout."""
        args = self.recovery_args(request_id, "use_first_frame")
        operator = submodule("blender.job_recovery").SCENARIO_OT_use_saved_first_frame
        fake = SimpleNamespace(
            context_id=args["context_id"],
            request_id=request_id,
            expected_revision=args["expected_revision"],
            asset_id=asset_id,
            layout=MagicMock(),
            report=MagicMock(),
        )
        manager = MagicMock()
        manager.invoke_props_dialog.return_value = {"RUNNING_MODAL"}
        return operator, fake, SimpleNamespace(scene=bpy.context.scene, window_manager=manager)

    def test_native_controls_offer_each_downloaded_colour_still_without_reading_jobs(self):
        self.result_assets = {
            "colour-a": {},
            "normal-map": {"type": "texture-normal"},
            "colour-b": {"type": "texture"},
        }
        request_id = self.saved_image()
        owner = self.runtime.state.model_jobs
        view = owner.views[request_id]
        self.assertEqual(view.meta["first_frame_assets"], ("colour-a", "colour-b"))
        recovery = submodule("blender.job_recovery")
        store = self.runtime.state.job_store
        before = (self.store.get(request_id), self.network(), dict(view.meta))
        layout = MagicMock()
        refuse = AssertionError("drawing read or started jobs")
        with (
            patch.object(self.runtime, "ensure_model_jobs", side_effect=refuse),
            patch.object(self.runtime, "ensure_job_session", side_effect=refuse),
            patch.object(self.runtime, "ensure_job_store", side_effect=refuse),
            patch.object(store, "get", side_effect=refuse),
            patch.object(store, "records", side_effect=refuse),
        ):
            recovery.draw_controls(layout, view)
        buttons = [
            (call.args[0], call.kwargs["text"])
            for call in layout.operator.call_args_list
            if call.args[0] == "scenario.use_saved_first_frame"
        ]
        # Numbering counts every saved asset; the normal map gets no button.
        self.assertEqual(
            buttons,
            [
                ("scenario.use_saved_first_frame", "Use as video first frame (1)"),
                ("scenario.use_saved_first_frame", "Use as video first frame (3)"),
            ],
        )
        drawn = [
            dict(item.properties)
            for item in recovery.result_actions(view)
            if item.action == "use_first_frame"
        ]
        self.assertEqual(
            [(item["request_id"], item["asset_id"]) for item in drawn],
            [(request_id, "colour-a"), (request_id, "colour-b")],
        )
        self.assertEqual(
            {(item["context_id"], item["expected_revision"]) for item in drawn},
            {(self.runtime.state.job_context_id, self.store.get(request_id).revision)},
        )
        self.assertEqual((self.store.get(request_id), self.network(), dict(view.meta)), before)
        lane = self.render_video(FRAME_AND_CLIP)
        with self.assertRaisesRegex(self.request_error, "Choose one downloaded PNG"):
            self.prepare(request_id, "normal-map")
        status = self.apply(self.prepare(request_id, "colour-b"))
        self.assertEqual(status["first_frame"]["asset_id"], "colour-b")
        self.assertEqual([ref.asset_id for _, ref in self.first_frames(lane)], ["colour-b"])

    def test_native_dialog_reviews_the_destination_and_cancel_discards_it(self):
        request_id = self.saved_image()
        record = self.store.get(request_id)
        lane = self.render_video(FRAME_AND_CLIP)
        lane.first_frame_path, lane.use_first_frame = "chosen-first-frame.png", False
        operator, fake, context = self.native_operator(request_id)
        before = self.network()
        self.assertEqual(operator.invoke(fake, context, None), {"RUNNING_MODAL"})
        context.window_manager.invoke_props_dialog.assert_called_once_with(
            fake, width=520, title="Use as video first frame", confirm_text="Use as first frame"
        )
        owner = self.runtime.state.model_jobs
        self.assertIn(fake.application_id, owner._application_approvals)
        snapshot = dict(vars(fake))
        operator.draw(fake, context)
        self.assertEqual(vars(fake), snapshot)  # Drawing only displays prepared text.
        labels = [call.kwargs.get("text") for call in fake.layout.label.call_args_list]
        self.assertEqual(
            labels,
            [
                f"Scene: {bpy.context.scene.name}",
                "Form: Render Video",
                "Model: Render video fixture",
                "Input: First Frame",
                f"Image: {record.results[0].asset.name} (saved result)",
                "Use the saved Scenario asset; nothing is uploaded.",
                "No new generation; the blend stores no file path.",
                "Replace the chosen first-frame file: chosen-first-frame.png",
                "Turn on the video first frame.",
                "Invalidate the Render Video and Prompt Spark prices.",
                "Remove the first-frame slot to undo this.",
            ],
        )
        # The 520 px dialog was verified on the desktop with 59-character lines.
        fixed = [label for label in labels if not label.startswith(("Scene:", "Image:"))]
        self.assertLessEqual(max(len(label) for label in fixed), 59)
        operator.cancel(fake, context)
        self.assertNotIn(fake.application_id, owner._application_approvals)
        # Review and cancel change nothing and contact nobody.
        self.assertEqual(self.first_frames(lane), [])
        self.assertEqual(
            (lane.first_frame_path, lane.use_first_frame), ("chosen-first-frame.png", False)
        )
        self.assertEqual(self.store.get(request_id), record)
        self.assertEqual(self.network(), before)
        # An enabled first frame without a chosen file states neither change.
        lane.first_frame_path, lane.use_first_frame = "", True
        operator, fake, context = self.native_operator(request_id)
        operator.invoke(fake, context, None)
        operator.draw(fake, context)
        labels = [call.kwargs.get("text") for call in fake.layout.label.call_args_list]
        self.assertFalse(any(label.startswith(("Replace", "Turn on")) for label in labels))
        operator.cancel(fake, context)
        self.assertEqual(owner._application_approvals, {})

    def test_native_review_reports_the_refusal_reason_without_an_approval(self):
        request_id = self.saved_image()
        self.render_video(NO_IMAGE, "fixture-render-no-image")
        owner = self.runtime.state.model_jobs
        operator, fake, context = self.native_operator(request_id)
        self.assertEqual(operator.invoke(fake, context, None), {"CANCELLED"})
        fake.report.assert_called_once_with(
            {"ERROR"}, "Choose a Render Video model with an image input"
        )
        lane = self.render_video(FRAME_AND_CLIP)
        self.apply(self.prepare(request_id))
        operator, fake, context = self.native_operator(request_id)
        self.assertEqual(operator.invoke(fake, context, None), {"CANCELLED"})
        fake.report.assert_called_once_with(
            {"ERROR"}, "Remove the current Render Video first frame first"
        )
        context.window_manager.invoke_props_dialog.assert_not_called()
        self.assertEqual(owner._application_approvals, {})
        self.assertEqual(len(self.first_frames(lane)), 1)
        # A button drawn for a retired connection names the native next step.
        lane.references.remove(self.first_frames(lane)[0][0])
        operator, fake, context = self.native_operator(request_id)
        fake.context_id = "retired-context"
        self.assertEqual(operator.invoke(fake, context, None), {"CANCELLED"})
        fake.report.assert_called_once_with(
            {"ERROR"}, "The connection changed; inspect saved jobs again"
        )
        self.assertEqual(owner._application_approvals, {})

    def test_native_operator_consumes_an_mcp_approval_once(self):
        request_id = self.saved_image()
        lane = self.render_video(FRAME_AND_CLIP)
        approval = self.prepare(request_id)
        args = {
            "context_id": approval["context_id"],
            "application_id": approval["application_id"],
            "request_id": request_id,
            "expected_revision": approval["revision"],
            "asset_id": approval["asset_id"],
        }
        record, before = self.store.get(request_id), self.network()
        self.assertEqual(bpy.ops.scenario.use_saved_first_frame(**args), {"FINISHED"})
        self.assertEqual(
            self.runtime.state.last_message,
            "Verifying the saved image for the Render Video first frame",
        )
        self.deliver_results()
        ((_, ref),) = self.first_frames(lane)
        self.assertEqual((ref.source, ref.asset_id), ("ASSET", "result-image"))
        self.assertEqual(
            self.tools.job_status({"job_id": request_id})["first_frame"]["state"], "bound"
        )
        with self.assertRaisesRegex(RuntimeError, "First frame was not set"):
            bpy.ops.scenario.use_saved_first_frame(**args)
        self.assertEqual(len(self.first_frames(lane)), 1)
        self.assertEqual(self.store.get(request_id), record)
        self.assertEqual(self.network(), before)
        # A fresh approval from a retired connection is refused in native words.
        lane.references.remove(self.first_frames(lane)[0][0])
        args.update(application_id=self.prepare(request_id)["application_id"])
        args.update(context_id="retired-context")
        with self.assertRaisesRegex(RuntimeError, "The connection changed; inspect saved jobs"):
            bpy.ops.scenario.use_saved_first_frame(**args)
        self.assertEqual(self.first_frames(lane), [])

    def test_render_lane_labels_a_saved_result_slot_read_only(self):
        request_id = self.saved_image()
        lane = self.render_video(FRAME_AND_CLIP)
        render_lanes = submodule("blender.render_lanes")
        schema = self.generation.schema_for(lane.model_id)
        saved = ("From a saved result",), {"icon": "FILE_REFRESH"}

        def drawn_labels():
            layout = MagicMock()
            values = self.slot_values(lane)
            store = self.runtime.state.job_store
            refuse = AssertionError("drawing read jobs")
            with (
                patch.object(store, "get", side_effect=refuse),
                patch.object(store, "records", side_effect=refuse),
            ):
                render_lanes._draw_first_frame(layout, lane, schema)
            self.assertEqual(self.slot_values(lane), values)  # Drawing changes no slot.
            return [
                ((call.kwargs.get("text"),), {"icon": call.kwargs.get("icon")})
                for call in layout.label.call_args_list
            ]

        self.assertNotIn(saved, drawn_labels())
        self.apply(self.prepare(request_id))
        self.assertIn(saved, drawn_labels())
        ((_, ref),) = self.first_frames(lane)
        provenance = ref[self.form._RESULT]
        # Edited or absent provenance is not presented as a saved result.
        ref[self.form._RESULT] = provenance.replace("result-image", "another-asset")
        self.assertNotIn(saved, drawn_labels())
        del ref[self.form._RESULT]
        self.assertNotIn(saved, drawn_labels())

    def test_bound_first_frame_records_one_native_undo_step(self):
        """Headless memfile history; the desktop timer context needs separate proof."""
        request_id = self.saved_image()
        lane = self.render_video(FRAME_AND_CLIP)
        lane.use_first_frame = False
        names = bpy.context.scene.name
        module = submodule("blender.mesh_result_application")
        preferences = bpy.context.preferences.edit
        settings = preferences.use_global_undo, preferences.undo_steps
        preferences.use_global_undo, preferences.undo_steps = True, 32

        def current_lane():
            scene = bpy.data.scenes[names]
            bpy.context.window.scene = scene
            return scene.scenario.lane_state("render_video")

        try:
            self.assertEqual(bpy.ops.ed.undo_push(message="Fixture before handoff"), {"FINISHED"})
            record, before = self.store.get(request_id), self.network()
            # The installed runner has a window; production records only on the desktop.
            with patch.object(module, "_undo_enabled", return_value=True):
                status = self.apply(self.prepare(request_id))
            self.assertEqual(status["first_frame"]["state"], "bound", status)
            self.assertTrue(status["first_frame"]["undo_recorded"])
            self.assertEqual(bpy.ops.ed.undo(), {"FINISHED"})
            lane = current_lane()
            self.assertEqual(self.first_frames(lane), [])
            self.assertFalse(lane.use_first_frame)
            self.assertEqual(bpy.ops.ed.redo(), {"FINISHED"})
            lane = current_lane()
            ((_, ref),) = self.first_frames(lane)
            self.assertEqual((ref.source, ref.asset_id), ("ASSET", "result-image"))
            self.assertIsNotNone(self.handoff.provenance(ref))
            self.assertTrue(lane.use_first_frame)
            # History restores the form only: no saved-job change, request or upload.
            self.assertEqual(self.store.get(request_id), record)
            self.assertEqual(self.network(), before)
            self.assertFalse(self.runtime.state.job_session.upload_recovery_plan())
        finally:
            preferences.use_global_undo, preferences.undo_steps = settings

    def render_video_records(self, inputs, model_id="fixture-render-video"):
        """Register the model again after a reset, keeping the reopened form."""
        model = {
            "id": model_id,
            "name": "Render video fixture",
            "type": "custom",
            "capabilities": ["video2video"],
            "inputs": inputs,
        }
        record = submodule("core.api.catalog").ModelRecord.from_api(model)
        self.runtime.state.records[record.id] = record
        self.generation._schemas.pop(record.id, None)
        self.runtime.set_enum_items(("models", "render_video"), [(record.id, record.name, "")])


if __name__ == "__main__":
    unittest.main()
