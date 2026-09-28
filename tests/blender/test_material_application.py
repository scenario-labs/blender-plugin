# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Packed PBR graph, exact mesh-slot targeting and rollback in Blender."""

import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import bpy
from helpers import reset_scene, submodule


class MaterialApplicationTests(unittest.TestCase):
    def setUp(self):
        reset_scene()
        self.module = submodule("blender.material_application")
        self.storage = submodule("core.jobs.store")
        self.transfers = submodule("core.jobs.transfers")
        self.results = submodule("core.jobs.results")
        self.images = set(bpy.data.images)
        self.materials = set(bpy.data.materials)
        bpy.ops.mesh.primitive_cube_add()
        self.obj = bpy.context.active_object
        self.scene = bpy.context.scene
        self.target = self.module.capture_target(self.scene, self.obj)
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.enterContext(
            patch.object(bpy.utils, "extension_path_user", return_value=str(self.root))
        )

    def tearDown(self):
        for material in set(bpy.data.materials) - self.materials:
            bpy.data.materials.remove(material, do_unlink=True)
        for image in set(bpy.data.images) - self.images:
            bpy.data.images.remove(image, do_unlink=True)

    def fixture(self, roles=("albedo", "normal", "smoothness", "metallic", "height", "ao")):
        items, paths = [], []
        for index, role in enumerate(roles):
            image = bpy.data.images.new("Synthetic material map", width=2, height=2)
            path = self.root / f"map-{index}.png"
            try:
                image.pixels[:] = [0.5, 0.5, 1.0, 1.0] * 4
                image.file_format, image.filepath_raw = "PNG", str(path)
                image.save()
            finally:
                bpy.data.images.remove(image)
            data = path.read_bytes()
            asset = self.storage.ResultAsset(
                f"map-{index}", path.name, "image/png", len(data), texture_role=role
            )
            receipt = self.transfers.DownloadedResult(
                path.name, len(data), hashlib.sha256(data).hexdigest()
            )
            items.append(self.storage.StoredResult(asset, receipt))
            paths.append(path)
        intent = self.storage.JobIntent(
            "fixture-request",
            self.storage.JobScope("https://service.example.invalid/v1", "fixture"),
            self.storage.JobOrigin("file", "scene", "revision"),
            "model",
            "fixture-model",
            "a" * 64,
            "b" * 64,
            "1.0",
        )
        record = self.storage.StoredJob(intent, results=tuple(items))
        return self.results.VerifiedResults(record, tuple(paths))

    def test_packed_material_uses_roles_and_preserves_other_slots_and_old_graphs(self):
        old = bpy.data.materials.new("Keep original")
        old.use_nodes = True
        old_nodes = tuple(old.node_tree.nodes)
        old.node_tree.nodes.get("Principled BSDF").inputs["Roughness"].default_value = 0.25
        other = bpy.data.materials.new("Keep other slot")
        self.obj.data.materials.append(old)
        self.obj.data.materials.append(other)
        self.obj.active_material_index = 0
        target = self.module.capture_target(self.scene, self.obj)
        mesh = self.obj.data
        result = self.module.apply_material(self.fixture(), target)
        self.assertEqual(self.obj.data, mesh)
        self.assertEqual(tuple(self.obj.data.materials), (result.material, other))
        self.assertEqual(tuple(old.node_tree.nodes), old_nodes)
        self.assertEqual(
            old.node_tree.nodes.get("Principled BSDF").inputs["Roughness"].default_value, 0.25
        )
        self.assertEqual(bpy.context.active_object, self.obj)
        self.assertTrue(all(image.packed_file and not image.filepath for image in result.images))
        tree = result.material.node_tree
        textures = {node.label.lower(): node for node in tree.nodes if node.type == "TEX_IMAGE"}
        self.assertEqual(textures["albedo"].image.colorspace_settings.name, "sRGB")
        self.assertEqual(textures["normal"].image.colorspace_settings.name, "Non-Color")
        bsdf = next(node for node in tree.nodes if node.type == "BSDF_PRINCIPLED")
        self.assertEqual(bsdf.inputs["Roughness"].links[0].from_node.type, "INVERT")
        bump = bsdf.inputs["Normal"].links[0].from_node
        self.assertEqual(bump.type, "BUMP")
        self.assertEqual(bump.inputs["Normal"].links[0].from_node.type, "NORMAL_MAP")
        self.assertFalse(textures["ao"].outputs["Color"].is_linked)

    def test_ambiguous_maps_fail_before_loading_or_assignment(self):
        for roles in (
            ("albedo", "albedo"),
            ("base", "albedo"),
            ("normal",),
            ("base", "roughness", "smoothness"),
        ):
            with self.subTest(roles=roles), self.assertRaises(self.module.MaterialApplicationError):
                self.module.apply_material(self.fixture(roles), self.target)
        self.assertEqual(len(self.obj.material_slots), 0)
        self.assertEqual(set(bpy.data.materials), self.materials)
        self.assertEqual(set(bpy.data.images), self.images)

    def test_shared_mesh_is_rejected_without_changing_either_object(self):
        other = bpy.data.objects.new("Shared data user", self.obj.data)
        self.scene.collection.objects.link(other)
        with self.assertRaises(self.module.MaterialApplicationError):
            self.module.apply_material(self.fixture(("base",)), self.target)
        self.assertEqual(len(self.obj.material_slots), 0)
        self.assertEqual(len(other.material_slots), 0)

    def test_failed_assignment_rolls_back_slot_and_new_data(self):
        original = self.module._assign

        def fail(*args):
            original(*args)
            raise RuntimeError("synthetic assignment failure")

        with patch.object(self.module, "_assign", side_effect=fail):
            with self.assertRaises(self.module.MaterialApplicationError):
                self.module.apply_material(self.fixture(), self.target)
        self.assertEqual(self.module.capture_target(self.scene, self.obj), self.target)
        self.assertEqual(set(bpy.data.materials), self.materials)
        self.assertEqual(set(bpy.data.images), self.images)

    def test_changed_receipt_never_creates_a_material(self):
        verified = self.fixture(("base",))
        verified.paths[0].write_bytes(b"changed")
        with self.assertRaises(self.module.MaterialApplicationError):
            self.module.apply_material(verified, self.target)
        self.assertEqual(len(self.obj.material_slots), 0)
        self.assertEqual(set(bpy.data.materials), self.materials)

    def test_changed_slot_prevents_assignment(self):
        self.obj.data.materials.append(bpy.data.materials.new("User choice"))
        with self.assertRaises(self.module.MaterialApplicationError):
            self.module.apply_material(self.fixture(("base",)), self.target)
        self.assertEqual(self.obj.active_material.name, "User choice")

    def test_failed_first_slot_assignment_preserves_existing_face_indices(self):
        self.obj.data.polygons[0].material_index = 5
        target = self.module.capture_target(self.scene, self.obj)
        original = self.module._assign

        def fail(*args):
            original(*args)
            raise RuntimeError("synthetic assignment failure")

        with patch.object(self.module, "_assign", side_effect=fail):
            with self.assertRaises(self.module.MaterialApplicationError):
                self.module.apply_material(self.fixture(("base",)), target)
        self.assertEqual(len(self.obj.material_slots), 0)
        self.assertEqual(self.obj.data.polygons[0].material_index, 5)
        self.assertEqual(self.module.capture_target(self.scene, self.obj), target)

    def test_combined_pixel_budget_cleans_preceding_packed_images(self):
        verified = self.fixture(("base", "normal"))
        importer = submodule("blender.image_application")
        with self.assertRaises(importer.ImageApplicationError):
            importer.apply_images(verified, pixel_budget=4)
        self.assertEqual(set(bpy.data.images), self.images)
        self.assertEqual(len(self.obj.material_slots), 0)

    def test_object_shared_with_another_scene_is_not_silently_changed(self):
        other_scene = bpy.data.scenes.new("Other material user")
        try:
            other_scene.collection.objects.link(self.obj)
            with self.assertRaises(self.module.MaterialApplicationError):
                self.module.apply_material(self.fixture(("base",)), self.target)
            self.assertEqual(len(self.obj.material_slots), 0)
        finally:
            bpy.data.scenes.remove(other_scene)
