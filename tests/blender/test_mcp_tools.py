# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
import json
import os
import tempfile
import unittest

import bpy
import imbuf
from helpers import FIXTURES, reset_scene, submodule


class McpToolsTests(unittest.TestCase):
    def setUp(self):
        reset_scene()
        self.tb = submodule("mcp.tools_blender")
        self.ts = submodule("mcp.tools_scenario")
        self.sandbox = submodule("mcp.sandbox")
        bpy.ops.mesh.primitive_cube_add(location=(1, 2, 3))
        bpy.context.active_object.name = "Crate"

    def test_scene_summary_and_object_detail(self):
        summary = self.tb.scene_summary({})
        names = [o["name"] for o in summary["objects"]]
        self.assertIn("Crate", names)
        self.assertEqual(
            summary["frame_range"], [bpy.context.scene.frame_start, bpy.context.scene.frame_end]
        )
        detail = self.tb.object_detail({"name": "Crate"})
        self.assertEqual(detail["type"], "MESH")
        self.assertAlmostEqual(detail["location"][2], 3.0)
        self.assertIn("vertices", detail)
        with self.assertRaises(ValueError):
            self.tb.object_detail({"name": "Nope"})

    def test_scene_summary_pages_and_filters_large_scenes(self):
        stage = bpy.data.collections.new("Stage")
        bpy.context.scene.collection.children.link(stage)
        for index in range(120):
            stage.objects.link(bpy.data.objects.new(f"Marker {index:03}", None))
        first = self.tb.scene_summary({})
        self.assertEqual((first["scene_object_count"], first["total"]), (121, 121))
        self.assertEqual((len(first["objects"]), first["next_offset"]), (100, 100))
        self.assertIn("offset 100", first["note"])
        rest = self.tb.scene_summary({"offset": first["next_offset"]})
        self.assertEqual((len(rest["objects"]), rest["next_offset"]), (21, None))
        self.assertNotIn("note", rest)
        names = [o["name"] for o in first["objects"] + rest["objects"]]
        self.assertEqual(len(set(names)), 121)
        meshes = self.tb.scene_summary({"types": ["mesh"], "fields": ["dimensions"]})
        self.assertEqual(meshes["objects"], [{"name": "Crate", "dimensions": [2.0, 2.0, 2.0]}])
        staged = self.tb.scene_summary(
            {"collection": "Stage", "name_contains": "MARKER 11", "limit": 5}
        )
        self.assertEqual(
            [o["name"] for o in staged["objects"]], [f"Marker {i}" for i in range(110, 115)]
        )
        self.assertEqual((staged["total"], staged["next_offset"]), (10, 5))
        self.tb.select_objects({"names": ["Marker 007"]})
        picked = self.tb.scene_summary({"selected_only": True, "fields": []})
        self.assertEqual(picked["objects"], [{"name": "Marker 007"}])
        for bad in (
            {"limit": 0},
            {"limit": 501},
            {"limit": True},
            {"offset": -1},
            {"types": "MESH"},
            {"types": ["ROCKET"]},
            {"fields": ["vertices"]},
            {"collection": "Nope"},
            {"collection": 3},
            {"name_contains": 3},
            {"selected_only": "yes"},
        ):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.tb.scene_summary(bad)

    def test_scene_summary_collection_filter_ignores_a_linked_namesake(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "twin.blend")
            twin = bpy.data.objects.new("Twin", None)
            bpy.data.libraries.write(path, {twin})
            bpy.data.objects.remove(twin)
            with bpy.data.libraries.load(path, link=True) as (_, target):
                target.objects = ["Twin"]
            bpy.context.scene.collection.objects.link(target.objects[0])
            stage = bpy.data.collections.new("Stage")
            bpy.context.scene.collection.children.link(stage)
            stage.objects.link(bpy.data.objects.new("Twin", None))
            twins = self.tb.scene_summary({"name_contains": "Twin", "fields": []})
            self.assertEqual(twins["total"], 2)
            staged = self.tb.scene_summary({"collection": "Stage", "fields": []})
            self.assertEqual((staged["total"], staged["objects"]), (1, [{"name": "Twin"}]))

    def test_scene_summary_caps_selected_and_camera_names(self):
        for index in range(55):
            camera = bpy.data.objects.new(f"Shot {index:02}", bpy.data.cameras.new("Shot"))
            bpy.context.scene.collection.objects.link(camera)
            camera.select_set(True)
        summary = self.tb.scene_summary({"types": ["CAMERA"], "limit": 1})
        self.assertEqual((summary["camera_count"], len(summary["cameras"])), (55, 50))
        self.assertEqual((summary["selected_count"], len(summary["selected"])), (56, 50))
        self.assertEqual((summary["total"], summary["next_offset"]), (55, 1))

    def test_image_sizes_are_bounded_and_screenshots_scaled_down(self):
        for args in ({"width": 15}, {"width": 4097}, {"height": 0}, {"width": "1280"}):
            with self.subTest(args=args), self.assertRaises(ValueError):
                self.tb.render_still(args)
        with self.assertRaises(ValueError):
            self.tb._image_size({"max_size": 63}, "max_size", 1280, minimum=64)
        # Background Blender still loads the startup layout, so its areas can be compared.
        _, area = self.tb._largest_viewport()
        views = [
            a
            for window in bpy.context.window_manager.windows
            for a in window.screen.areas
            if a.type == "VIEW_3D"
        ]
        self.assertEqual(area.width * area.height, max(a.width * a.height for a in views))
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "wide.png")
            image = bpy.data.images.new("Wide", 2000, 1000)
            image.filepath_raw, image.file_format = path, "PNG"
            image.save()
            bpy.data.images.remove(image)
            for max_size, expected in ((1280, (1280, 640)), (2000, (1280, 640)), (500, (500, 250))):
                self.tb._fit_png(path, max_size)
                with open(path, "rb") as handle:
                    self.assertEqual(handle.read(8), b"\x89PNG\r\n\x1a\n")
                scaled = imbuf.load(path)
                try:
                    self.assertEqual(tuple(scaled.size), expected, max_size)
                finally:
                    scaled.free()

    def test_blender_api_help_returns_docs_and_properties(self):
        op = self.tb.blender_api_help({"path": "bpy.ops.mesh.primitive_cube_add"})
        self.assertEqual(op["path"], "bpy.ops.mesh.primitive_cube_add")
        self.assertIn("properties", op)
        self.assertIn("size", [p["name"] for p in op["properties"]])
        data = self.tb.blender_api_help({"path": "bpy.data.objects"})
        self.assertTrue(data.get("members") or data.get("properties"))
        self.assertIn("error", self.tb.blender_api_help({"path": "bpy.nope.nope"}))
        self.assertIn("error", self.tb.blender_api_help({"path": ""}))

    def test_datablocks_summary_counts_the_scene(self):
        summary = self.tb.datablocks_summary({})
        self.assertGreaterEqual(summary["counts"]["objects"], 1)
        self.assertGreaterEqual(summary["counts"]["meshes"], 1)
        self.assertIn("filepath", summary)

    def test_new_tools_are_registered(self):
        names = [s.name for s in self.tb.SPECS]
        self.assertIn("blender_api_help", names)
        self.assertIn("datablocks_summary", names)

    def test_execute_python_captures_output_and_result_and_blocks_quit(self):
        out = self.sandbox.run_python(
            "import bpy\nprint('hello')\nresult['count'] = len(bpy.data.objects)"
        )
        self.assertEqual(out["result"]["count"], len(bpy.data.objects))
        self.assertIn("hello", out["stdout"])
        blocked = self.sandbox.run_python("import bpy\nbpy.ops.wm.quit_blender()")
        self.assertIn("blocked", (blocked.get("error") or "").lower())
        self.assertTrue(len(bpy.data.objects) >= 1)

    def test_execute_python_respects_preference(self):
        prefs = submodule("prefs").get_prefs()
        prefs.mcp_allow_python = False
        try:
            with self.assertRaises(PermissionError):
                self.tb.execute_python({"code": "result['x'] = 1"})
        finally:
            prefs.mcp_allow_python = True

    def test_select_and_set_frame(self):
        self.tb.select_objects({"names": ["Crate"]})
        self.assertTrue(bpy.data.objects["Crate"].select_get())
        self.tb.set_frame({"frame": 42})
        self.assertEqual(bpy.context.scene.frame_current, 42)

    def test_list_models_and_schema_use_loaded_catalog(self):
        runtime = submodule("blender.runtime")
        catalog = submodule("core.api.catalog")
        handlers = submodule("blender.handlers")
        runtime.state.reset()
        rec = catalog.ModelRecord.from_api(
            json.loads((FIXTURES / "models" / "model_patina-material.json").read_text())["model"]
        )
        handlers.dispatch(("catalog", {"privacy": "public", "records": [rec], "detailed": [rec]}))
        listed = self.ts.list_models({"lane": "material"})
        self.assertEqual(listed["models"][0]["id"], "model_patina-material")
        schema = self.ts.model_schema({"model_id": "model_patina-material"})
        self.assertIn("maps", [p["name"] for p in schema["parameters"]])
        self.assertTrue(any(s.name == "generate" for s in self.ts.SPECS))
        self.assertTrue(any(s.name == "scene_summary" for s in self.tb.SPECS))

    def test_schema_and_validation_treat_undeclared_siblings_as_never_defined(self):
        runtime = submodule("blender.runtime")
        catalog = submodule("core.api.catalog")
        handlers = submodule("blender.handlers")
        runtime.state.reset()
        mini = catalog.ModelRecord.from_api(
            json.loads(
                (FIXTURES / "models" / "model_bytedance-seedance-2-0-mini.json").read_text()
            )["model"]
        )
        # Synthetic, shaped like a live video-extension schema whose prompt rule
        # names an image input the schema does not declare.
        extend = catalog.ModelRecord.from_api(
            {
                "id": "model_fixture-extend",
                "type": "custom",
                "capabilities": ["video2video"],
                "inputs": [
                    {
                        "name": "prompt",
                        "label": "Prompt",
                        "type": "string",
                        "prompt": True,
                        "required": {"ifNotDefined": {"image": {}}},
                    },
                    {"name": "video", "type": "file", "kind": "video", "required": True},
                ],
            }
        )
        records = [mini, extend]
        handlers.dispatch(
            ("catalog", {"privacy": "public", "records": records, "detailed": records})
        )
        required = {
            p["name"]: p["required"]
            for p in self.ts.model_schema({"model_id": mini.id})["parameters"]
        }
        self.assertNotIn("lastFrameImage", required)
        self.assertFalse(required["image"])
        record, body = self.ts._body_for(mini.id, {"prompt": "fixture"})
        self.assertEqual((record.id, body["prompt"]), (mini.id, "fixture"))
        self.assertNotIn("image", body)
        required = {
            p["name"]: p["required"]
            for p in self.ts.model_schema({"model_id": extend.id})["parameters"]
        }
        self.assertEqual(required, {"prompt": True, "video": True})
        with self.assertRaisesRegex(ValueError, "Prompt is required"):
            self.ts._body_for(extend.id, {"video": "clip"})
        self.assertEqual(
            self.ts._body_for(extend.id, {"video": "clip", "prompt": "fixture"})[1],
            {"prompt": "fixture", "video": "clip"},
        )

    def test_list_models_reports_the_picker_experimental_status(self):
        runtime = submodule("blender.runtime")
        catalog = submodule("core.api.catalog")
        handlers = submodule("blender.handlers")
        runtime.state.reset()
        records = [
            catalog.ModelRecord.from_api(
                {"id": model_id, "name": name, "type": "custom", "capabilities": capabilities}
            )
            for model_id, name, capabilities in (
                ("model_speech-studio", "Speech Studio", ["txt2audio", "audio2txt"]),
                ("model_music", "Music", ["txt2audio"]),
            )
        ]
        handlers.dispatch(
            ("catalog", {"privacy": "public", "records": records, "detailed": records})
        )
        listed = {item["id"]: item for item in self.ts.list_models({"lane": "audio"})["models"]}
        self.assertEqual(
            listed["model_speech-studio"]["capability_status"],
            "Experimental: speech-to-text in testing",
        )
        self.assertEqual(listed["model_music"]["capability_status"], "")
        self.assertNotIn("status", listed["model_music"])
