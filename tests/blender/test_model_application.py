# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Native static GLB import, hierarchy, packed texture and rollback proofs."""

import hashlib
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import bpy
from helpers import FIXTURES, animated_glb, submodule
from mathutils import Vector


class ModelApplicationTests(unittest.TestCase):
    def setUp(self):
        self.module = submodule("blender.model_application")
        self.storage = submodule("core.jobs.store")
        self.transfers = submodule("core.jobs.transfers")
        self.previous_scene = bpy.context.scene
        self.before = {name: set(getattr(bpy.data, name)) for name in self.module._DATA}
        self.scene = bpy.data.scenes.new("Model application fixture")
        bpy.context.window.scene = self.scene
        self.existing = bpy.data.objects.new("Keep selection", None)
        self.scene.collection.objects.link(self.existing)
        self.existing.select_set(True)
        bpy.context.view_layer.objects.active = self.existing
        self.scene["keep"] = "unchanged"
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.enterContext(
            patch.object(bpy.utils, "extension_path_user", return_value=str(self.root))
        )
        data = (FIXTURES / "synthetic/static-triangle.glb").read_bytes()
        self.path = self.root / "saved.glb"
        self.path.write_bytes(data)
        receipt = self.transfers.DownloadedResult(
            self.path.name, len(data), hashlib.sha256(data).hexdigest()
        )
        self.item = self.storage.StoredResult(
            self.storage.ResultAsset("model", self.path.name, "model/gltf-binary", len(data)),
            receipt,
        )

    def tearDown(self):
        bpy.context.window.scene = self.previous_scene
        bpy.data.scenes.remove(self.scene)
        for name in self.module._DATA:
            values = getattr(bpy.data, name)
            for value in set(values) - self.before[name]:
                values.remove(value, do_unlink=True)

    def test_import_preserves_hierarchy_materials_selection_and_places_bottom_at_cursor(self):
        result = self.module.apply_model(self.scene, self.item, self.path, cursor=(4, 5, 6))
        self.assertEqual(len(result.objects), 2)
        mesh = next(obj for obj in result.objects if obj.type == "MESH")
        self.assertEqual(mesh.parent.parent, result.root)
        self.assertEqual(len(mesh.data.polygons), 1)
        self.assertEqual(mesh.data.materials[0].name, "Fixture material")
        images = set(bpy.data.images) - self.before["images"]
        self.assertEqual(len(images), 1)
        self.assertTrue(all(image.packed_file for image in images))
        self.assertTrue(all(image.filepath == "" for image in images))
        points = [mesh.matrix_world @ Vector(corner) for corner in mesh.bound_box]
        low = [min(point[i] for point in points) for i in range(3)]
        high = [max(point[i] for point in points) for i in range(3)]
        self.assertEqual(((low[0] + high[0]) / 2, (low[1] + high[1]) / 2, low[2]), (4, 5, 6))
        self.assertEqual(set(bpy.context.selected_objects), {self.existing})
        self.assertEqual(bpy.context.view_layer.objects.active, self.existing)
        self.assertEqual(self.scene["keep"], "unchanged")
        self.assertEqual(tuple(self.root.iterdir()), (self.path,))

    def test_failed_publication_removes_only_new_data(self):
        previous = {name: set(getattr(bpy.data, name)) for name in self.module._DATA}
        original = self.module._publish

        def fail(*args):
            original(*args)
            raise RuntimeError("synthetic publication failure")

        with (
            patch.object(self.module, "_publish", side_effect=fail),
            self.assertRaises(self.module.ModelApplicationError),
        ):
            self.module.apply_model(self.scene, self.item, self.path, cursor=(0, 0, 0))
        self.assertEqual(
            {name: set(getattr(bpy.data, name)) for name in self.module._DATA}, previous
        )
        self.assertEqual(bpy.context.view_layer.objects.active, self.existing)
        self.assertTrue(self.path.exists())

    def test_changed_bytes_fail_before_import(self):
        self.path.write_bytes(self.path.read_bytes() + b"changed")
        with (
            patch.object(self.module, "_import") as importer,
            self.assertRaises(self.module.ModelApplicationError),
        ):
            self.module.apply_model(self.scene, self.item, self.path, cursor=(0, 0, 0))
        importer.assert_not_called()

    def test_worker_cannot_import(self):
        with ThreadPoolExecutor(max_workers=1) as pool:
            with self.assertRaises(self.module.ModelApplicationError):
                pool.submit(
                    self.module.apply_model, self.scene, self.item, self.path, cursor=(0, 0, 0)
                ).result(5)

    def test_incomplete_rollback_is_uncertain_even_when_cleanup_does_not_raise(self):
        original = self.module._publish

        def fail(*args):
            original(*args)
            raise RuntimeError("synthetic publication failure")

        with (
            patch.object(self.module, "_publish", side_effect=fail),
            patch.object(self.module, "_remove_new_data"),
            self.assertRaisesRegex(RuntimeError, "cleanup is incomplete") as raised,
        ):
            self.module.apply_model(self.scene, self.item, self.path, cursor=(0, 0, 0))
        self.assertNotIsInstance(raised.exception, self.module.ModelApplicationError)
        self.assertGreater(len(bpy.data.objects), len(self.before["objects"]) + 1)

    def test_temporary_cleanup_failure_preserves_completed_packed_model(self):
        cleanup = tempfile.TemporaryDirectory.cleanup

        def fail(directory):
            cleanup(directory)
            raise OSError("synthetic cleanup failure")

        with (
            patch.object(tempfile.TemporaryDirectory, "cleanup", fail),
            self.assertLogs("scenario.jobs", level="WARNING") as logs,
        ):
            result = self.module.apply_model(self.scene, self.item, self.path, cursor=(0, 0, 0))
        self.assertEqual(len(result.objects), 2)
        self.assertIn(result.root, tuple(self.scene.objects))
        self.assertTrue(
            all(image.packed_file for image in set(bpy.data.images) - self.before["images"])
        )
        self.assertIn("temporary files may remain", logs.output[0])

    def use_animation(self):
        data = animated_glb()
        self.path.write_bytes(data)
        self.item = self.storage.StoredResult(
            self.storage.ResultAsset("model", self.path.name, "model/gltf-binary", len(data)),
            self.transfers.DownloadedResult(
                self.path.name, len(data), hashlib.sha256(data).hexdigest()
            ),
        )

    def test_rig_morph_and_multiple_clips_survive_with_destination_timing(self):
        self.use_animation()
        self.scene.render.fps = 30
        self.scene.render.fps_base = 1.001
        self.scene.frame_start, self.scene.frame_end = 12, 160
        self.scene.frame_set(7, subframe=0.25)
        result = self.module.apply_model(self.scene, self.item, self.path, cursor=(4, 5, 6))
        rig = next(obj for obj in result.objects if obj.type == "ARMATURE")
        mesh = next(obj for obj in result.objects if obj.type == "MESH")
        self.assertEqual(len(rig.data.bones), 2)
        self.assertEqual(rig.data.bones["TipJoint"].parent.name, "RootJoint")
        self.assertEqual(mesh.modifiers[0].object, rig)
        self.assertEqual(mesh.vertex_groups[0].name, "RootJoint")
        self.assertEqual(mesh.data.vertices[0].groups[0].weight, 1)
        self.assertEqual(len(mesh.data.shape_keys.key_blocks), 2)
        for owner in (rig, mesh.data.shape_keys):
            animation = owner.animation_data
            self.assertIsNotNone(animation.action)
            self.assertEqual(len(animation.nla_tracks), 2)
            for track in animation.nla_tracks:
                self.assertTrue(track.mute)
                action = track.strips[0].action
                self.assertAlmostEqual(action.frame_range[0], 0, places=3)
                self.assertAlmostEqual(action.frame_range[1], 30 / 1.001, places=3)
        self.assertEqual((self.scene.frame_start, self.scene.frame_end), (12, 160))
        self.assertEqual(self.scene.frame_current, 7)
        self.assertAlmostEqual(self.scene.frame_subframe, 0.25)
        self.assertEqual(self.scene.render.fps, 30)
        self.assertAlmostEqual(self.scene.render.fps_base, 1.001, places=5)
        self.assertEqual(bpy.context.view_layer.objects.active, self.existing)
        self.scene.frame_set(0)
        first = mesh.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices[0].co.copy()
        self.scene.frame_set(30)
        last = mesh.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices[0].co.copy()
        self.assertAlmostEqual(last.x - first.x, 2, places=4)
        self.assertGreater((last - first).length, 2)
        self.assertTrue(
            all(image.packed_file for image in set(bpy.data.images) - self.before["images"])
        )

    def test_failed_rig_import_removes_skin_shape_keys_and_actions(self):
        self.use_animation()
        layer = self.scene.view_layers.new("Keep chosen view layer")
        bpy.context.window.view_layer = layer
        layer.objects.active = self.existing
        self.existing.select_set(True)
        previous = self.module._snapshot()
        original = self.module._publish

        def fail(*args):
            original(*args)
            raise RuntimeError("synthetic failure after rig publication")

        with (
            patch.object(self.module, "_publish", side_effect=fail) as publisher,
            self.assertRaises(self.module.ModelApplicationError),
        ):
            self.module.apply_model(self.scene, self.item, self.path, cursor=(0, 0, 0))
        publisher.assert_called_once()
        self.assertEqual(bpy.context.window.scene, self.scene)
        self.assertEqual(bpy.context.window.view_layer, layer)
        self.assertEqual(bpy.context.view_layer.objects.active, self.existing)
        self.assertEqual(set(bpy.context.selected_objects), {self.existing})
        self.assertEqual(self.module._snapshot(), previous)
        self.assertTrue(self.path.exists())

    def test_optional_gltf_animation_ui_metadata_is_preserved_on_success_and_failure(self):
        self.use_animation()
        prefs = bpy.context.preferences.addons["io_scene_gltf2"].preferences
        old = prefs.animation_ui
        prefs.animation_ui = True
        scene = bpy.data.scenes[0]
        before = tuple(t.name for t in scene.gltf2_animation_tracks)
        active, applied = scene.gltf2_animation_active, scene.gltf2_animation_applied
        try:
            scene.gltf2_animation_tracks.add().name = "Existing clip"
            expected = tuple(t.name for t in scene.gltf2_animation_tracks)
            self.module.apply_model(self.scene, self.item, self.path, cursor=(0, 0, 0))
            self.assertEqual(tuple(t.name for t in scene.gltf2_animation_tracks), expected)
            self.assertEqual(
                (scene.gltf2_animation_active, scene.gltf2_animation_applied), (active, applied)
            )
            original = self.module._import

            def fail(path):
                original(path)
                raise RuntimeError("synthetic import failure")

            with (
                patch.object(self.module, "_import", side_effect=fail),
                self.assertRaises(self.module.ModelApplicationError),
            ):
                self.module.apply_model(self.scene, self.item, self.path, cursor=(0, 0, 0))
            self.assertEqual(tuple(t.name for t in scene.gltf2_animation_tracks), expected)
            self.assertEqual(
                (scene.gltf2_animation_active, scene.gltf2_animation_applied), (active, applied)
            )
        finally:
            scene.gltf2_animation_tracks.clear()
            for name in before:
                scene.gltf2_animation_tracks.add().name = name
            scene.gltf2_animation_active, scene.gltf2_animation_applied = active, applied
            prefs.animation_ui = old
