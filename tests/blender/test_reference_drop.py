# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Image files dropped on the Scenario sidebar join the current form; other drops stay Blender's."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import bpy
from helpers import reset_scene, submodule
from test_apply_image import png

MODEL = "fixture-reference-drop"


class ReferenceDropTests(unittest.TestCase):
    def setUp(self):
        reset_scene()
        self.operators = submodule("blender.operators")
        self.uploads = submodule("blender.reference_uploads")
        generation = submodule("blender.generation")
        model = {
            "id": MODEL,
            "name": "Reference drop",
            "type": "custom",
            "capabilities": ["txt2img"],
            "inputs": [
                {"name": "prompt", "type": "string", "prompt": True},
                {"name": "video", "type": "file", "kind": "video"},
                {"name": "images", "type": "file_array", "kind": "image", "maxLength": 2},
            ],
        }
        self.model = model
        record = submodule("core.api.catalog").ModelRecord.from_api(model)
        generation.set_catalog([record], [record])
        self.scene = bpy.context.scene
        self.scene.scenario.lane = "image"
        self.lane = self.scene.scenario.lane_state("image")
        self.lane.model_id = MODEL
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        for name in ("a.png", "b.jpg", "c.webp"):
            (self.root / name).write_bytes(png())
        (self.root / "notes.txt").write_text("not an image")

    def context(self, area="VIEW_3D", region="UI", category="Scenario"):
        return SimpleNamespace(
            area=SimpleNamespace(type=area),
            region=SimpleNamespace(type=region, active_panel_category=category),
            scene=self.scene,
        )

    def test_the_handler_is_registered_for_reference_images(self):
        handler = self.operators.SCENARIO_FH_reference_drop
        self.assertTrue(hasattr(bpy.types, "SCENARIO_FH_reference_drop"))
        self.assertEqual(handler.bl_import_operator, "scenario.drop_reference")
        self.assertEqual(handler.bl_file_extensions.split(";"), [".png", ".jpg", ".jpeg", ".webp"])

    def test_only_the_scenario_sidebar_claims_a_drop(self):
        poll = self.operators.SCENARIO_FH_reference_drop.poll_drop
        self.assertTrue(poll(self.context()))
        for other in (
            self.context(region="WINDOW"),  # the viewport itself, where the composer floats
            self.context(region="HEADER"),
            self.context(category="Tool"),
            self.context(category=""),
            self.context(area="IMAGE_EDITOR"),
            self.context(area="SEQUENCE_EDITOR", region="UI"),
            SimpleNamespace(area=None, region=None, scene=self.scene),
        ):
            with self.subTest(context=other):
                self.assertFalse(poll(other))
        broken = SimpleNamespace(scene=self.scene)  # No area or region at all.
        self.assertFalse(poll(broken))

    def test_only_a_form_with_room_in_an_image_input_claims_a_drop(self):
        poll = self.operators.SCENARIO_FH_reference_drop.poll_drop
        for lane in ("render_image", "render_video", "panorama", "blockout"):
            with self.subTest(lane=lane):
                self.scene.scenario.lane = lane
                self.assertFalse(poll(self.context()))
        self.scene.scenario.lane = "3d"
        self.scene.scenario.three_d_mode = "EDIT"
        self.assertFalse(poll(self.context()))  # Edit mode drives the edit3d form.
        self.scene.scenario.lane = "image"
        # A listed model whose description has not been read: nothing tells its inputs.
        generation, runtime = submodule("blender.generation"), submodule("blender.runtime")
        listed = submodule("core.api.catalog").ModelRecord.from_api(
            {key: self.model[key] for key in ("id", "name", "type", "capabilities")}
        )
        with patch.dict(runtime.state.records, {MODEL: listed}), patch.dict(generation._schemas):
            generation._schemas.pop(MODEL, None)
            self.assertIsNone(generation.schema_for(MODEL))
            self.assertFalse(poll(self.context()))
        self.assertTrue(poll(self.context()))
        for _ in range(2):
            ref = self.lane.references.add()
            ref.param_name, ref.source = "images", "ASSET"
        self.assertFalse(poll(self.context()))

    def test_dropped_images_join_the_image_input_as_chosen_files(self):
        self.lane.estimate_state = "READY"
        with patch.object(
            self.uploads, "note_chosen_file", wraps=self.uploads.note_chosen_file
        ) as chosen:
            result = bpy.ops.scenario.drop_reference(
                "INVOKE_DEFAULT",
                directory=str(self.root),
                files=[{"name": "notes.txt"}, {"name": "a.png"}, {"name": "b.jpg"}],
            )
        self.assertEqual(result, {"FINISHED"})
        refs = [(r.param_name, r.source, r.label) for r in self.lane.references]
        self.assertEqual(refs, [("images", "FILE", "a.png"), ("images", "FILE", "b.jpg")])
        self.assertEqual(
            [Path(r.filepath) for r in self.lane.references],
            [self.root / "a.png", self.root / "b.jpg"],
        )
        self.assertEqual(
            [Path(call.args[0]) for call in chosen.call_args_list],
            [self.root / "a.png", self.root / "b.jpg"],
        )
        self.assertEqual(self.lane.estimate_state, "PENDING")

    def test_a_drop_stops_at_the_inputs_maximum_and_a_full_form_adds_nothing(self):
        files = [{"name": name} for name in ("a.png", "b.jpg", "c.webp")]
        self.assertEqual(
            bpy.ops.scenario.drop_reference(directory=str(self.root), files=files), {"FINISHED"}
        )
        self.assertEqual(len(self.lane.references), 2)
        self.assertEqual(
            bpy.ops.scenario.drop_reference(filepath=str(self.root / "c.webp")), {"CANCELLED"}
        )
        self.assertEqual(len(self.lane.references), 2)

    def test_a_single_dropped_file_path_is_accepted(self):
        path = self.root / "c.webp"
        self.assertEqual(bpy.ops.scenario.drop_reference(filepath=str(path)), {"FINISHED"})
        (ref,) = self.lane.references
        self.assertEqual((ref.param_name, Path(ref.filepath)), ("images", path))
