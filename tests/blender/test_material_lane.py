# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
import json
import unittest

import bpy
from helpers import FIXTURES, reset_scene, submodule


class MaterialLaneTests(unittest.TestCase):
    def setUp(self):
        reset_scene()
        self.generation = submodule("blender.generation")
        self.runtime = submodule("blender.runtime")
        catalog = submodule("core.api.catalog")
        handlers = submodule("blender.handlers")
        self.runtime.state.reset()
        data = json.loads((FIXTURES / "models" / "model_patina-material.json").read_text())["model"]
        rec = catalog.ModelRecord.from_api(data)
        handlers.dispatch(("catalog", {"privacy": "public", "records": [rec], "detailed": [rec]}))

    def test_material_request_records_selected_meshes(self):
        bpy.ops.mesh.primitive_cube_add()
        cube = bpy.context.active_object
        lane = bpy.context.scene.scenario.lane_state("material")
        lane.prompt = "mossy stone"
        request = self.generation.build_request(bpy.context.scene, "material")
        self.assertEqual(request.model_id, "model_patina-material")
        self.assertEqual(
            request.body["maps"], ["basecolor", "normal", "roughness", "metalness", "height"]
        )
        self.assertEqual(request.errors, [])
        meta = self.generation.request_meta(bpy.context, "material")
        self.assertEqual(meta["target_objects"], [cube.name])

    def test_lane_lists_patina_then_scenario_texture_then_other_texture_models(self):
        catalog = submodule("core.api.catalog")
        handlers = submodule("blender.handlers")
        picker = submodule("blender.model_picker")
        saved = {
            key: list(value) if isinstance(value, list) else value
            for key, value in picker._ctx.items()
        }
        self.addCleanup(picker._ctx.update, saved)

        def texture(model_id, name, **extra):
            raw = {"id": model_id, "name": name, "type": "custom", "status": "trained"}
            raw.update(capabilities=["txt2img", "img2img"], tags=["sc:texture"], **extra)
            return catalog.ModelRecord.from_api(raw)

        data = json.loads((FIXTURES / "models" / "model_patina-material.json").read_text())
        records = [
            texture("model_ideogram-v4-tiling", "Ideogram V4 Tiling"),
            texture("model_textures-moss", "Textures - Moss", type="flux.1-lora"),
            texture("model_scenario-texture", "Scenario Texture"),
            catalog.ModelRecord.from_api(data["model"]),
        ]
        self.runtime.state.reset()
        handlers.dispatch(
            ("catalog", {"privacy": "public", "records": records, "detailed": records})
        )
        expected = ["model_patina-material", "model_scenario-texture", "model_ideogram-v4-tiling"]
        self.assertEqual([r.id for r in self.runtime.state.lane_models["material"]], expected)
        picker.prepare(bpy.context, "material")
        items = bpy.context.window_manager.scenario_picker_items
        self.assertEqual([item.model_id for item in items], expected)
        render = {r.id for r in self.runtime.state.lane_models["render_image"]}
        self.assertFalse(render & set(expected))

    def test_lane_hint_describes_explicit_saved_application(self):
        # Shared material jobs stop at saved results; only Apply saved material assigns them.
        from test_model_picker import FakeLayout

        panels = submodule("blender.panels")
        hint = ["Saved only, not applied to meshes", "Apply from Jobs to a mesh slot"]
        bpy.ops.mesh.primitive_cube_add()
        cube = bpy.context.active_object
        for selected in (True, False):
            with self.subTest(selected=selected):
                cube.select_set(selected)
                layout = FakeLayout()
                panels.draw_generate_lane(layout, bpy.context, "material")
                labels = [
                    call[2].get("text") or ""
                    for node in layout.walk()
                    for call in node.named("label")
                ]
                # One aligned column, short enough not to be clipped beside an icon.
                columns = [
                    [call[2].get("text") for call in node.named("label")]
                    for node in layout.walk()
                    if node.kind == "column"
                ]
                self.assertIn(hint, columns)
                self.assertTrue(all(len(line) <= 36 for line in hint))
                self.assertFalse(
                    [text for text in labels if "selected mesh" in text or "arrival" in text]
                )

    def test_retile_operator_changes_mapping_scale(self):
        mp = submodule("core.scene.material_plan")
        apply_material = submodule("blender.apply_material")
        manifest = json.loads((FIXTURES / "patina-copper-512" / "manifest.json").read_text())
        files = [
            (a["type"], str(FIXTURES / "patina-copper-512" / a["file"])) for a in manifest["assets"]
        ]
        mat = apply_material.build_material(mp.plan_material("T", files))
        bpy.ops.scenario.retile_material(material_name=mat.name, scale=2.5)
        mapping = next(n for n in mat.node_tree.nodes if n.type == "MAPPING")
        self.assertEqual(tuple(mapping.inputs["Scale"].default_value), (2.5, 2.5, 2.5))
