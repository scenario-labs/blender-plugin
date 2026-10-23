# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
import json
import unittest

import bpy
from helpers import FIXTURES, reset_scene, submodule


def rec(name):
    catalog = submodule("core.api.catalog")
    return catalog.ModelRecord.from_api(
        json.loads((FIXTURES / "models" / f"{name}.json").read_text())["model"]
    )


P2 = "model_tripo-p2-image-to-3d"


def p2_record():
    """Tripo P2 with the inputs of its live description that the lane's starting values touch."""
    catalog = submodule("core.api.catalog")
    return catalog.ModelRecord.from_api(
        {
            "id": P2,
            "name": "Tripo P2",
            "capabilities": ["img23d"],
            "status": "trained",
            "inputs": [
                {"name": "image", "type": "file", "kind": "image", "required": True},
                {"name": "texture", "type": "boolean", "default": True, "costImpact": True},
                {
                    "name": "textureQuality",
                    "type": "string",
                    "default": "standard",
                    "allowedValues": ["fast", "standard", "detailed", "extreme"],
                    "costImpact": True,
                },
                {"name": "pbr", "type": "boolean", "default": True},
                {"name": "faceLimit", "type": "number", "min": 48, "max": 50000},
                {"name": "autoSize", "type": "boolean", "default": False},
                {"name": "quad", "type": "boolean", "default": False, "costImpact": True},
            ],
        }
    )


P2_TEXT = "model_tripo-p2-text-to-3d"


def p2_text_record():
    """Tripo P2 Text to 3D: Tripo P2's settings with a prompt in place of the image."""
    catalog = submodule("core.api.catalog")
    inputs = p2_record().raw["inputs"][1:]
    return catalog.ModelRecord.from_api(
        {
            "id": P2_TEXT,
            "name": "Tripo P2 Text to 3D",
            "capabilities": ["txt23d"],
            "status": "trained",
            "inputs": [
                {"name": "prompt", "type": "string", "prompt": True, "required": True},
                *inputs,
            ],
        }
    )


class ThreeDLaneTests(unittest.TestCase):
    def setUp(self):
        reset_scene()

    def test_three_d_models_by_mode(self):
        generation = submodule("blender.generation")
        records = [
            rec("model_meshy-7-txt23d"),
            rec("model_meshy-7-img23d"),
            rec("model_tripo-v3-1-image-to-3d"),
        ]
        self.assertEqual(
            [r.id for r in generation.three_d_models("TEXT", records)], ["model_meshy-7-txt23d"]
        )
        image_ids = [r.id for r in generation.three_d_models("IMAGE", records)]
        self.assertIn("model_tripo-v3-1-image-to-3d", image_ids)
        multi_ids = [r.id for r in generation.three_d_models("MULTI", records)]
        self.assertIn("model_meshy-7-img23d", multi_ids)
        self.assertNotIn("model_meshy-7-txt23d", multi_ids)

    def test_mode_change_refreshes_model_enum(self):
        runtime = submodule("blender.runtime")
        handlers = submodule("blender.handlers")
        runtime.state.reset()
        records = [rec("model_meshy-7-txt23d"), rec("model_meshy-7-img23d")]
        handlers.dispatch(
            ("catalog", {"privacy": "public", "records": records, "detailed": records})
        )
        scene = bpy.context.scene
        scene.scenario.three_d_mode = "TEXT"
        self.assertEqual(
            [i[0] for i in runtime.enum_items(("models", "3d"))], ["model_meshy-7-txt23d"]
        )
        scene.scenario.three_d_mode = "MULTI"
        self.assertEqual(
            [i[0] for i in runtime.enum_items(("models", "3d"))], ["model_meshy-7-img23d"]
        )

    def test_list_only_models_are_classified_by_name(self):
        generation = submodule("blender.generation")
        catalog = submodule("core.api.catalog")
        multi = catalog.ModelRecord.from_api(
            {
                "id": "model_tripo-v3-1-multiview-to-3d",
                "name": "Tripo 3.1 Multi View",
                "capabilities": ["img23d"],
            }
        )
        single = catalog.ModelRecord.from_api(
            {"id": "model_hitem-3d-3-0", "name": "Hitem3D 3.0", "capabilities": ["img23d"]}
        )
        self.assertEqual(
            [r.id for r in generation.three_d_models("MULTI", [multi, single])],
            ["model_tripo-v3-1-multiview-to-3d"],
        )
        self.assertEqual(
            [r.id for r in generation.three_d_models("IMAGE", [multi, single])],
            ["model_hitem-3d-3-0"],
        )

    def test_add_sources_depend_on_input_kind(self):
        props = submodule("blender.props")
        self.assertEqual(
            [s[0] for s in props.addable_sources_for("3d")], ["FILE"]
        )  # selection auto-attaches; Upload overrides
        self.assertEqual(
            [s[0] for s in props.addable_sources_for("image")],
            ["FILE", "RENDER", "VIEWPORT", "CAMERA"],
        )
        self.assertEqual(
            [s[0] for s in props.addable_sources_for("video")],
            ["FILE", "VIEWPORT_CLIP", "CAMERA_CLIP"],
        )
        self.assertEqual([s[0] for s in props.addable_sources_for("audio")], ["FILE"])
        self.assertNotIn(
            "VIEWPORT", [s[0] for s in props.addable_sources_for("3d")]
        )  # never an image capture on a mesh input

    def test_selected_mesh_attaches_to_a_text_to_motion_character_input(self):
        # Uthana Text to Motion is txt23d with an optional character mesh (characterFile, kind 3d). Selecting a mesh
        # and adding it must reach the inference as that param, exported like edit3d does.
        generation = submodule("blender.generation")
        runtime = submodule("blender.runtime")
        handlers = submodule("blender.handlers")
        runtime.state.reset()
        record = rec("model_uthana-text-to-motion-3.0")
        handlers.dispatch(
            ("catalog", {"privacy": "public", "records": [record], "detailed": [record]})
        )
        scene = bpy.context.scene
        scene.scenario.three_d_mode = "TEXT"
        lane = scene.scenario.lane_state("3d")
        lane.model_id = "model_uthana-text-to-motion-3.0"
        lane.prompt = "a slow bow"
        ref = lane.references.add()
        ref.param_name, ref.source = "characterFile", "MESH"
        request = generation.build_request(scene, "3d")
        self.assertEqual(request.errors, [])
        self.assertIn(
            {"param": "characterFile", "source": "MESH", "camera": None}, request.captures
        )

    def test_selected_mesh_auto_attaches_without_a_click(self):
        # the scene selection feeds a 3D character input automatically (no button): a selected mesh is used, and
        # deselecting gives a text-only generation.
        generation = submodule("blender.generation")
        runtime = submodule("blender.runtime")
        handlers = submodule("blender.handlers")
        runtime.state.reset()
        record = rec("model_uthana-text-to-motion-3.0")
        handlers.dispatch(
            ("catalog", {"privacy": "public", "records": [record], "detailed": [record]})
        )
        scene = bpy.context.scene
        scene.scenario.three_d_mode = "TEXT"
        lane = scene.scenario.lane_state("3d")
        lane.model_id = "model_uthana-text-to-motion-3.0"
        lane.prompt = "a slow bow"
        bpy.ops.mesh.primitive_cube_add(size=2.0)
        cube = bpy.context.active_object
        request = generation.build_request(scene, "3d")
        self.assertEqual(len(lane.references), 0)  # nothing attached by hand
        self.assertIn(
            {"param": "characterFile", "source": "MESH", "camera": None, "first": True},
            request.captures,
        )
        cube.select_set(False)
        bpy.context.view_layer.objects.active = None
        request = generation.build_request(scene, "3d")
        self.assertEqual([c for c in request.captures if c["param"] == "characterFile"], [])

    def test_rodin_material_override_applies_when_allowed(self):
        params_ui = submodule("blender.params_ui")
        params = submodule("core.schema.params")
        catalog = submodule("core.api.catalog")
        rec = catalog.ModelRecord.from_api(
            {
                "id": "model_rodin-hyper3d-v2-5-text-to-3d",
                "name": "Rodin",
                "capabilities": ["txt23d"],
                "inputs": [
                    {
                        "name": "prompt",
                        "type": "string",
                        "prompt": True,
                        "required": {"always": True},
                    },
                    {
                        "name": "material",
                        "type": "string",
                        "allowedValues": ["PBR", "Shaded", "All", "None"],
                        "default": "All",
                    },
                ],
            }
        )
        schema = params.parse_schema(rec)
        lane = bpy.context.scene.scenario.lane_state("3d")
        params_ui.sync_params(lane, schema, rec.id)
        self.assertEqual(lane.params["material"].enum_value, "PBR")
        self.assertTrue(lane.params["material"].enabled)

    def p2_form(self):
        """The 3D lane in Image mode with Tripo P2 chosen and its image attached."""
        runtime = submodule("blender.runtime")
        handlers = submodule("blender.handlers")
        runtime.state.reset()
        records = [rec("model_tripo-v3-1-image-to-3d"), rec("model_meshy-7-img23d"), p2_record()]
        handlers.dispatch(
            ("catalog", {"privacy": "public", "records": records, "detailed": records})
        )
        scene = bpy.context.scene
        scene.scenario.three_d_mode = "IMAGE"
        lane = scene.scenario.lane_state("3d")
        lane.model_id = P2
        ref = lane.references.add()
        ref.param_name, ref.source, ref.asset_id = "image", "ASSET", "asset_fixture"
        return scene, lane, records

    def test_tripo_p2_leads_the_image_models_and_tripo_3_1_stays_listed(self):
        runtime = submodule("blender.runtime")
        handlers = submodule("blender.handlers")
        runtime.state.reset()
        records = [rec("model_tripo-v3-1-image-to-3d"), rec("model_meshy-7-img23d"), p2_record()]
        handlers.dispatch(
            ("catalog", {"privacy": "public", "records": records, "detailed": records})
        )
        scene = bpy.context.scene
        scene.scenario.three_d_mode = "IMAGE"
        shown = [item[0] for item in runtime.enum_items(("models", "3d"))]
        self.assertEqual(shown[0], P2)
        self.assertIn("model_tripo-v3-1-image-to-3d", shown)
        # A form that never chose a model shows the lane's first one.
        self.assertEqual(scene.scenario.lane_state("3d").model_id, P2)

    def test_tripo_p2_form_starts_at_real_size_with_a_light_mesh(self):
        generation = submodule("blender.generation")
        scene, lane, _ = self.p2_form()
        generation.on_model_changed(bpy.context, lane)
        self.assertTrue(lane.params["autoSize"].bool_value)
        face_limit = lane.params["faceLimit"]
        self.assertEqual(face_limit.int_value, 50000)
        self.assertTrue(face_limit.enabled)
        # The schema's own starts are untouched.
        self.assertTrue(lane.params["pbr"].bool_value)
        self.assertFalse(lane.params["quad"].bool_value)
        request = generation.build_request(scene, "3d", for_estimate=True)
        self.assertEqual(request.errors, [])
        self.assertEqual(request.body["faceLimit"], 50000)
        self.assertIs(request.body["autoSize"], True)
        self.assertEqual(request.body["image"], "asset_fixture")

    def test_tripo_p2_start_never_replaces_a_value_the_user_changed(self):
        generation = submodule("blender.generation")
        handlers = submodule("blender.handlers")
        scene, lane, records = self.p2_form()
        generation.on_model_changed(bpy.context, lane)
        lane.params["faceLimit"].int_value = 20000
        lane.params["autoSize"].bool_value = False
        # A catalog refresh and another synchronization keep the user's values.
        handlers.dispatch(
            ("catalog", {"privacy": "public", "records": records, "detailed": records})
        )
        generation.on_model_changed(bpy.context, lane)
        self.assertEqual(lane.params["faceLimit"].int_value, 20000)
        self.assertFalse(lane.params["autoSize"].bool_value)
        body = generation.build_request(scene, "3d", for_estimate=True).body
        self.assertEqual((body["faceLimit"], body["autoSize"]), (20000, False))
        # Switching the setting off stays off: the service decides the face count.
        lane.params["faceLimit"].enabled = False
        generation.on_model_changed(bpy.context, lane)
        self.assertFalse(lane.params["faceLimit"].enabled)
        self.assertNotIn("faceLimit", generation.build_request(scene, "3d").body)

    def test_local_mcp_payload_starts_where_the_form_starts(self):
        generation = submodule("blender.generation")
        tools = submodule("mcp.tools_scenario")
        scene, lane, _ = self.p2_form()
        generation.on_model_changed(bpy.context, lane)
        form = generation.build_request(scene, "3d", for_estimate=True).body
        _, body = tools._body_for(P2, {"image": "asset_fixture"})
        self.assertEqual(
            {k: body[k] for k in ("faceLimit", "autoSize")}, {"faceLimit": 50000, "autoSize": True}
        )
        self.assertEqual({k: form[k] for k in body}, body)
        self.assertIs(type(body["faceLimit"]), type(form["faceLimit"]))
        # What the caller sets wins, and null leaves the setting to the service.
        _, chosen = tools._body_for(
            P2, {"image": "asset_fixture", "faceLimit": 20000, "autoSize": False}
        )
        self.assertEqual((chosen["faceLimit"], chosen["autoSize"]), (20000, False))
        _, left_out = tools._body_for(P2, {"image": "asset_fixture", "faceLimit": None})
        self.assertNotIn("faceLimit", left_out)
        # Another Tripo model keeps its schema's starts.
        _, other = tools._body_for("model_tripo-v3-1-image-to-3d", {"image": "asset_fixture"})
        self.assertNotIn("faceLimit", other)
        self.assertNotIn("autoSize", other)

    def test_tripo_p2_text_leads_the_text_models_and_starts_a_light_prop_at_real_size(self):
        generation = submodule("blender.generation")
        runtime = submodule("blender.runtime")
        handlers = submodule("blender.handlers")
        tools = submodule("mcp.tools_scenario")
        runtime.state.reset()
        records = [rec("model_meshy-7-txt23d"), p2_text_record()]
        handlers.dispatch(
            ("catalog", {"privacy": "public", "records": records, "detailed": records})
        )
        scene = bpy.context.scene
        scene.scenario.three_d_mode = "TEXT"
        shown = [item[0] for item in runtime.enum_items(("models", "3d"))]
        self.assertEqual(shown, [P2_TEXT, "model_meshy-7-txt23d"])
        lane = scene.scenario.lane_state("3d")
        # A form that never chose a model shows the lane's first one.
        self.assertEqual(lane.model_id, P2_TEXT)
        generation.on_model_changed(bpy.context, lane)
        self.assertTrue(lane.params["autoSize"].bool_value)
        self.assertEqual(lane.params["faceLimit"].int_value, 50000)
        self.assertTrue(lane.params["faceLimit"].enabled)
        self.assertTrue(lane.params["pbr"].bool_value)
        lane.prompt = "A weathered wooden treasure chest"
        request = generation.build_request(scene, "3d", for_estimate=True)
        self.assertEqual(request.errors, [])
        self.assertEqual((request.body["faceLimit"], request.body["autoSize"]), (50000, True))
        # Local MCP starts where the form starts.
        _, body = tools._body_for(P2_TEXT, {"prompt": "A weathered wooden treasure chest"})
        self.assertEqual({k: request.body[k] for k in body}, body)
