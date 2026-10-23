# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Edit 3D lane: the selected mesh is exported at generate time, the result lands next to it."""

import json
import os
import unittest
from unittest.mock import MagicMock

import bpy
from helpers import FIXTURES, drawn_texts, reset_scene, submodule


def rec(name):
    catalog = submodule("core.api.catalog")
    return catalog.ModelRecord.from_api(
        json.loads((FIXTURES / "models" / f"{name}.json").read_text())["model"]
    )


class Edit3DLaneTests(unittest.TestCase):
    def setUp(self):
        reset_scene()
        self.generation = submodule("blender.generation")
        self.runtime = submodule("blender.runtime")
        handlers = submodule("blender.handlers")
        self.runtime.state.reset()
        records = [
            rec("model_scenario-claude-opus-5-5-3d"),
            rec("model_meshy-7-retexture"),
            rec("model_tripo-retopology"),
            rec("model_meshy-rigging"),
            rec("model_meshy-7-txt23d"),
        ]
        handlers.dispatch(
            ("catalog", {"privacy": "public", "records": records, "detailed": records})
        )
        self.scene = bpy.context.scene
        bpy.ops.mesh.primitive_cube_add(size=2.0, location=(0, 0, 1))
        self.cube = bpy.context.active_object
        self.cube.name = "Hero"

    def test_task_tabs_filter_the_models(self):
        self.scene.scenario.edit3d_task = "RETEXTURE"
        self.assertEqual(
            [i[0] for i in self.runtime.enum_items(("models", "edit3d"))],
            ["model_meshy-7-retexture", "model_scenario-claude-opus-5-5-3d"],
        )
        self.scene.scenario.edit3d_task = "REMESH"
        self.assertEqual(
            [i[0] for i in self.runtime.enum_items(("models", "edit3d"))],
            ["model_tripo-retopology"],
        )
        self.scene.scenario.edit3d_task = "ALL"
        self.assertEqual(len(self.runtime.enum_items(("models", "edit3d"))), 4)

    def test_retexture_starts_on_meshy_7_on_the_source_uvs_with_pbr_maps(self):
        # About a minute; Replace textures then paints the source's head back in place.
        self.scene.scenario.edit3d_task = "REMESH"
        self.scene.scenario.edit3d_task = "RETEXTURE"
        lane = self.scene.scenario.lane_state("edit3d")
        self.assertEqual(lane.model_id, "model_meshy-7-retexture")
        lane.prompt = "red and gold royal guard uniform"
        self.generation.on_model_changed(bpy.context, lane)
        request = self.generation.build_request(self.scene, "edit3d")
        self.assertEqual(request.errors, [])
        self.assertIs(request.body.get("enableOriginalUv"), True)
        self.assertIs(request.body.get("enablePbr"), True)
        policy = submodule("core.scene.mesh_edit_policy")
        self.assertEqual(policy.default_policy(lane.model_id).policy, "RETEXTURE")

    def test_claude_opus_5_5_3d_takes_the_mesh_as_its_scene_file(self):
        # It repaints what the prompt names and keeps the rest, a character's face included.
        self.scene.scenario.edit3d_task = "RETEXTURE"
        lane = self.scene.scenario.lane_state("edit3d")
        lane.model_id = "model_scenario-claude-opus-5-5-3d"
        lane.prompt = "red and gold royal guard uniform"
        request = self.generation.build_request(self.scene, "edit3d")
        self.assertEqual(request.errors, [])
        self.assertEqual(
            request.captures[0],
            {"param": "sceneFile", "source": "MESH", "camera": None, "first": True},
        )
        self.assertEqual(request.body.get("prompt"), "red and gold royal guard uniform")
        # The schema's own High effort: Standard can add parts that Replace textures refuses.
        self.assertEqual(request.body.get("buildEffort"), "high")
        policy = submodule("core.scene.mesh_edit_policy")
        self.assertEqual(policy.default_policy(lane.model_id).policy, "RETEXTURE")

    def test_request_sends_the_selected_mesh_as_the_model_input(self):
        self.scene.scenario.edit3d_task = "RETEXTURE"
        lane = self.scene.scenario.lane_state("edit3d")
        lane.model_id = "model_meshy-7-retexture"
        lane.prompt = "rusty iron plates"
        request = self.generation.build_request(self.scene, "edit3d")
        self.assertEqual(request.errors, [])
        self.assertEqual(request.kind, "3d")
        self.assertEqual(
            request.captures[0], {"param": "model", "source": "MESH", "camera": None, "first": True}
        )
        self.assertEqual(request.body.get("textStylePrompt"), "rusty iron plates")

    def test_request_without_a_mesh_selected_is_refused(self):
        self.scene.scenario.edit3d_task = "REMESH"
        lane = self.scene.scenario.lane_state("edit3d")
        lane.model_id = "model_tripo-retopology"
        self.cube.select_set(False)
        bpy.context.view_layer.objects.active = None
        request = self.generation.build_request(self.scene, "edit3d")
        self.assertIn("Select the mesh to edit", request.errors)

    def test_dense_mesh_hint_suggests_remesh_and_keeps_generate(self):
        panels = submodule("blender.panels")

        def hints(task):
            self.scene.scenario.edit3d_task = task
            layout = MagicMock()
            panels.draw_edit3d_lane(layout, bpy.context)
            box = layout.box.return_value
            return " ".join(call.kwargs["text"] for call in box.label.call_args_list)

        self.assertNotIn("Dense mesh", hints("RIG"))
        # Over the plugin's in-place application work cap, like many generated meshes.
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=7)
        drawn = hints("RIG")
        self.assertIn("Dense mesh: 81,920 triangles.", drawn)
        self.assertIn("can't be applied to it in place", drawn)
        self.assertIn("remeshing it first, for example with Tripo Retopology,", drawn)
        drawn = hints("REMESH")
        self.assertIn("Dense mesh: 81,920 triangles.", drawn)
        self.assertNotIn("remeshing", drawn)
        # Apply animation changes only the rig: a rigged dense mesh still takes it.
        self.assertIn("Dense mesh", hints("ANIMATE"))
        rig = bpy.data.objects.new("Dense rig", bpy.data.armatures.new("Dense rig"))
        self.scene.collection.objects.link(rig)
        bpy.context.active_object.modifiers.new("Skin", "ARMATURE").object = rig
        self.assertNotIn("Dense mesh", hints("ANIMATE"))
        self.assertIn("Dense mesh", hints("RIG"))
        # A hint only: the Edit form still builds its request.
        self.scene.scenario.edit3d_task = "RETEXTURE"
        lane = self.scene.scenario.lane_state("edit3d")
        lane.model_id = "model_meshy-7-retexture"
        lane.prompt = "rusty iron plates"
        self.assertEqual(self.generation.build_request(self.scene, "edit3d").errors, [])

    def test_retexture_form_says_what_keeps_its_texture_and_how_long_slow_models_take(self):
        panels = submodule("blender.panels")
        self.scene.scenario.edit3d_task = "RETEXTURE"
        lane = self.scene.scenario.lane_state("edit3d")

        def drawn():
            layout = MagicMock()
            panels.draw_edit3d_lane(layout, bpy.context)
            props = [call.args[1] for call in layout.prop.call_args_list if len(call.args) > 1]
            return " ".join(drawn_texts(layout)), props

        # A 2 m cube is no standing character, and Meshy 7 needs no wait warning.
        text, shown = drawn()
        self.assertIn("Select faces in Edit Mode to keep their texture.", text)
        self.assertNotIn("retexture_keep_head", shown)
        self.assertNotIn("Slow:", text)
        # Stood up like a person, it offers to keep the head, on by default.
        self.cube.scale = (0.3, 0.2, 0.9)
        bpy.context.view_layer.update()
        text, shown = drawn()
        self.assertIn("retexture_keep_head", shown)
        self.assertIn("The head keeps its texture.", text)
        self.scene.scenario.retexture_keep_head = False
        self.assertNotIn("The head keeps its texture.", drawn()[0])
        # Faces selected in Edit Mode win.
        for polygon in self.cube.data.polygons:
            polygon.select = polygon.index == 0
        self.assertIn("Faces selected in Edit Mode keep their texture (1);", drawn()[0])
        lane.model_id = "model_scenario-claude-opus-5-5-3d"
        self.assertIn("Slow: about 12 to 16 minutes", drawn()[0])

    def test_export_and_result_placed_next_to_the_source(self):
        mesh_export = submodule("blender.mesh_export")
        apply_3d = submodule("blender.apply_3d")
        records = submodule("core.jobs.records")
        path = mesh_export.export_glb(bpy.context, [self.cube])
        self.assertTrue(os.path.exists(path) and os.path.getsize(path) > 0)
        self.assertTrue(self.cube.select_set)  # selection restored, the cube is still there
        job = records.JobRecord.new(
            lane="edit3d",
            kind="3d",
            model_id="model_meshy-7-retexture",
            body={},
            meta={"source_object": "Hero", "model_name": "Meshy 7 - Retexture", "prompt": "rusty"},
        )
        job.files = [path]
        job.status = "success"
        objects = apply_3d.on_3d_result(job)
        meshes = [o for o in objects if o.type == "MESH"]
        self.assertEqual(len(meshes), 1)
        self.assertIn("Hero", meshes[0].name)
        self.assertEqual(job.meta["objects"], [o.name for o in objects])
        # to the right of the source (its bbox spans x in [-1, 1]), bottoms aligned
        new_min_x = min((meshes[0].matrix_world @ v.co).x for v in meshes[0].data.vertices)
        new_min_z = min((meshes[0].matrix_world @ v.co).z for v in meshes[0].data.vertices)
        self.assertGreater(new_min_x, 1.0)
        self.assertAlmostEqual(new_min_z, 0.0, places=3)

    def test_export_writes_only_the_active_scene(self):
        mesh_export = submodule("blender.mesh_export")
        other = bpy.data.scenes.new("Other scene")
        try:
            # An object selected in another scene must not join the upload.
            elsewhere = bpy.data.objects.new("Elsewhere", self.cube.data.copy())
            other.collection.objects.link(elsewhere)
            elsewhere.select_set(True, view_layer=other.view_layers[0])
            path = mesh_export.export_glb(bpy.context, [self.cube])
            with open(path, "rb") as stream:
                stream.seek(12)
                size = int.from_bytes(stream.read(4), "little")
                stream.seek(20)
                document = json.loads(stream.read(size))
            self.assertEqual(len(document["scenes"]), 1)
            self.assertEqual([node["name"] for node in document["nodes"]], ["Hero"])
        finally:
            bpy.data.scenes.remove(other)

    def test_mesh_param_for_the_curated_models(self):
        catalog = submodule("core.api.catalog")
        self.assertEqual(catalog.mesh_param(rec("model_meshy-7-retexture")), "model")
        self.assertEqual(catalog.mesh_param(rec("model_scenario-claude-opus-5-5-3d")), "sceneFile")
        self.assertEqual(catalog.mesh_param(rec("model_tripo-retopology")), "model")
        self.assertIsNone(catalog.mesh_param(rec("model_meshy-7-txt23d")))


class AnimateTaskTests(unittest.TestCase):
    """Text-to-motion models and Meshy's named library motions in the Animate task."""

    def setUp(self):
        from helpers import chain_rig

        reset_scene()
        self.generation = submodule("blender.generation")
        self.runtime = submodule("blender.runtime")
        catalog = submodule("core.api.catalog")
        self.runtime.state.reset()
        records = [
            rec("model_uthana-text-to-motion-3.0"),
            catalog.ModelRecord.from_api(
                {
                    "id": "model_viggle-text-to-motion",
                    "name": "Viggle Text to Motion",
                    "capabilities": ["txt23d"],
                    "status": "trained",
                    "inputs": [
                        {
                            "name": "prompt",
                            "type": "string",
                            "prompt": True,
                            "required": {"always": True},
                        },
                        {"name": "duration", "type": "number", "default": 5, "min": 3, "max": 60},
                    ],
                }
            ),
            catalog.ModelRecord.from_api(
                {
                    "id": "model_meshy-animation",
                    "name": "Meshy Animation",
                    "capabilities": ["3d23d"],
                    "status": "trained",
                    "inputs": [
                        {"name": "model", "type": "file", "kind": "3d"},
                        {
                            "name": "actionId",
                            "type": "number",
                            "label": "Action ID",
                            "default": 0,
                            "min": 0,
                            "step": 1,
                            "required": {"always": True},
                        },
                    ],
                }
            ),
        ]
        handlers = submodule("blender.handlers")
        handlers.dispatch(
            ("catalog", {"privacy": "public", "records": records, "detailed": records})
        )
        self.scene = bpy.context.scene
        self.scene.scenario.edit3d_task = "ANIMATE"
        self.lane = self.scene.scenario.lane_state("edit3d")
        bpy.ops.mesh.primitive_cube_add(size=2.0, location=(0, 0, 1))
        self.cube = bpy.context.active_object
        self.rig = chain_rig(self.scene, "Character rig")

    def skin(self):
        self.cube.modifiers.new("Skin", "ARMATURE").object = self.rig

    def drawn(self):
        panels = submodule("blender.panels")
        layout = MagicMock()
        panels.draw_edit3d_lane(layout, bpy.context)
        return " ".join(
            call.kwargs["text"] for call in layout.box.return_value.label.call_args_list
        )

    def test_text_to_motion_comes_first_and_sends_no_mesh(self):
        self.assertEqual(
            [i[0] for i in self.runtime.enum_items(("models", "edit3d"))],
            [
                "model_uthana-text-to-motion-3.0",
                "model_viggle-text-to-motion",
                "model_meshy-animation",
            ],
        )
        self.skin()
        for model_id in ("model_viggle-text-to-motion", "model_uthana-text-to-motion-3.0"):
            with self.subTest(model=model_id):
                self.lane.model_id = model_id
                self.lane.prompt = "walks forward four steps then waves"
                request = self.generation.build_request(self.scene, "edit3d")
                self.assertEqual(request.errors, [])
                # Uthana's optional character input stays empty: nothing is uploaded.
                self.assertEqual((request.captures, request.files), ([], {}))
                self.assertEqual(request.body["prompt"], "walks forward four steps then waves")
                self.assertIn("Nothing is uploaded", self.drawn())

    def test_a_motion_form_hides_and_never_sends_a_character(self):
        self.skin()
        self.lane.model_id = "model_uthana-text-to-motion-3.0"
        self.lane.prompt = "waves"
        layout = MagicMock()
        submodule("blender.panels").draw_edit3d_lane(layout, bpy.context)
        self.assertNotIn("Character 3D model", str(layout.mock_calls))
        # A character an older form attached is not uploaded either.
        ref = self.lane.references.add()
        ref.param_name, ref.source, ref.filepath = "characterFile", "FILE", "//character.glb"
        request = self.generation.build_request(self.scene, "edit3d")
        self.assertEqual((request.errors, request.captures, request.files), ([], [], {}))

    def motion_form(self, model_id):
        self.scene.scenario.lane, self.scene.scenario.three_d_mode = "3d", "EDIT"
        self.lane.model_id = model_id
        self.lane.prompt = "walks forward four steps then waves"
        self.generation.on_model_changed(bpy.context, self.lane)
        return self.generation.build_request(self.scene, "edit3d", for_estimate=True).body

    def test_a_motion_starts_at_the_scenes_frame_rate_and_length(self):
        self.scene.render.fps, self.scene.render.fps_base = 24, 1.0
        self.scene.frame_start, self.scene.frame_end = 1, 120  # 5 s
        body = self.motion_form("model_uthana-text-to-motion-3.0")
        # Only the skeleton and its clip come back: Apply animation keeps no mannequin.
        self.assertEqual((body["fps"], body["length"], body["animationOnly"]), (24, 5, True), body)
        self.assertEqual(self.motion_form("model_viggle-text-to-motion")["duration"], 5)
        # Both follow the scene until edited, within each input's range.
        self.scene.frame_end = 240  # 10 s
        self.assertTrue(self.generation.sync_shown_forms())
        self.assertEqual(self.lane.params["duration"].int_value, 10)
        self.lane.params["duration"].int_value = 7
        self.scene.frame_end = 96
        self.assertFalse(self.generation.sync_shown_forms())
        self.assertEqual(self.lane.params["duration"].int_value, 7)
        self.lane.model_id = "model_uthana-text-to-motion-3.0"
        self.generation.on_model_changed(bpy.context, self.lane)
        self.assertEqual(self.lane.params["length"].int_value, 4)  # 4 s is the minimum

    def test_a_default_range_or_an_unoffered_frame_rate_keeps_the_models_own(self):
        self.scene.render.fps, self.scene.render.fps_base = 25, 1.0
        self.assertEqual((self.scene.frame_start, self.scene.frame_end), (1, 250))
        # A form made in this scene; one made earlier keeps the last rate it followed.
        self.lane.model_id = "model_meshy-animation"
        body = self.motion_form("model_uthana-text-to-motion-3.0")
        # Apply animation fits a default range to the clip, so the clip keeps its length.
        self.assertEqual((body["fps"], body["length"]), (30, 8), body)
        self.scene.frame_end = 125  # 5 s at 25 fps, a range the user set
        self.assertTrue(self.generation.sync_shown_forms())
        self.assertEqual(self.lane.params["length"].int_value, 5)
        self.assertEqual(self.lane.params["fps"].enum_value, "30")

    def test_text_to_motion_needs_a_rigged_selection(self):
        self.lane.model_id = "model_viggle-text-to-motion"
        self.lane.prompt = "waves"
        errors = self.generation.build_request(self.scene, "edit3d").errors
        self.assertEqual(errors, ["Rig the selected mesh first: the motion plays on its armature"])

    def test_meshy_library_motions_are_picked_by_name_or_by_any_id(self):
        self.lane.model_id = "model_meshy-animation"
        schema = self.generation.schema_for("model_meshy-animation")
        params_ui = submodule("blender.params_ui")
        params_ui.sync_params(self.lane, schema, "model_meshy-animation")
        item = self.lane.params["actionId"]
        labels = {i[0]: i[1] for i in self.runtime.enum_items(item_key(item))}
        self.assertEqual((item.enum_value, labels["30"], labels["28"]), ("0", "Walk", "Wave hello"))
        item.enum_value = "28"
        self.assertEqual(params_ui.collect_values(self.lane, schema)[0]["actionId"], 28)
        item.enum_value, item.int_value = "OTHER", 455
        self.assertEqual(params_ui.collect_values(self.lane, schema)[0]["actionId"], 455)
        # Other shows the number field beside the choice; a named motion hides it.
        layout = MagicMock()
        params_ui.draw_params(layout, self.lane, schema)
        row = layout.box.return_value.row.return_value.row.return_value
        self.assertEqual([c.args[1] for c in row.prop.call_args_list], ["enum_value", "int_value"])


def item_key(item):
    return ("param", item.model_id, item.name)


class ResultObjectTagTests(unittest.TestCase):
    def setUp(self):
        reset_scene()
        self.runtime = submodule("blender.runtime")
        self.runtime.state.reset()

    def test_imported_objects_carry_the_job_tag_and_can_be_selected_and_deleted(self):
        mesh_export = submodule("blender.mesh_export")
        apply_3d = submodule("blender.apply_3d")
        records = submodule("core.jobs.records")
        bpy.ops.mesh.primitive_cube_add(size=1.0)
        cube = bpy.context.active_object
        path = mesh_export.export_glb(bpy.context, [cube])
        job = records.JobRecord.new(
            lane="3d",
            kind="3d",
            model_id="model_meshy-7-txt23d",
            body={},
            meta={"prompt": "a crate"},
        )
        job.files = [path]
        job.status = "success"
        self.runtime.state.jobs_view.insert(0, job)
        objects = apply_3d.on_3d_result(job)
        self.assertTrue(objects)
        self.assertEqual(
            sorted(o.name for o in apply_3d.objects_of_job(job.local_id)),
            sorted(o.name for o in objects),
        )
        for obj in objects:
            obj.name = "renamed " + obj.name  # the tag survives renames
        bpy.ops.scenario.select_result_objects(names="", local_id=job.local_id)
        self.assertEqual(
            sorted(o.name for o in bpy.context.selected_objects), sorted(o.name for o in objects)
        )
        bpy.ops.scenario.delete_result_objects(names="", local_id=job.local_id)
        self.assertEqual(apply_3d.objects_of_job(job.local_id), [])
        self.assertIn(cube.name, bpy.data.objects)
