# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Native saved OBJ, FBX, glTF and PLY package snapshots, imports and rollback proofs."""

import hashlib
import json
import struct
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import addon_utils
import bpy
from helpers import FIXTURES, animated_glb, submodule, textured_model_exports
from mathutils import Vector


class ModelPackageTests(unittest.TestCase):
    def setUp(self):
        self.module = submodule("blender.model_application")
        self.formats = submodule("core.scene.model_formats")
        self.storage = submodule("core.jobs.store")
        self.transfers = submodule("core.jobs.transfers")
        self.names = self.module._PACKAGE_TRACKED
        self.previous_scene = bpy.context.scene
        self.before = {name: set(getattr(bpy.data, name)) for name in self.module._PACKAGE_DATA}
        self.scene = bpy.data.scenes.new("Model package fixture")
        self.scene.render.fps, self.scene.render.fps_base = 30, 1.0
        bpy.context.window.scene = self.scene
        self.existing = bpy.data.objects.new("Keep selection", None)
        self.scene.collection.objects.link(self.existing)
        self.existing.select_set(True)
        bpy.context.view_layer.objects.active = self.existing
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.enterContext(
            patch.object(bpy.utils, "extension_path_user", return_value=str(self.root))
        )
        self.saved = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.exports = textured_model_exports(
            Path(self.enterContext(tempfile.TemporaryDirectory()))
        )
        self.items, self.files = [], {}

    def tearDown(self):
        bpy.context.window.scene = self.previous_scene
        bpy.data.scenes.remove(self.scene)
        for name in self.module._PACKAGE_DATA:
            values = getattr(bpy.data, name)
            for value in set(values) - self.before[name]:
                values.remove(value, do_unlink=True)

    def save(self, asset_id, media_type, data, role=None):
        name = f"{len(self.items):03d}-{asset_id}.bin"
        path = self.saved / name
        path.write_bytes(data)
        receipt = self.transfers.DownloadedResult(name, len(data), hashlib.sha256(data).hexdigest())
        asset = self.storage.ResultAsset(asset_id, name, media_type, len(data), texture_role=role)
        item = self.storage.StoredResult(asset, receipt)
        self.items.append(item)
        self.files[asset_id] = (item, path)
        return path

    def unit(self, key):
        plan = self.formats.classify_packages(self.formats.members_from_results(self.items))
        unit = plan.unit(key)
        self.assertIsNotNone(unit, plan)
        return unit

    def legacy_obj(self, *, extra_maps=True):
        """The ingestion convention: {obj}.mtl and {obj}_<role>.png, missing maps appended."""
        obj = self.exports["obj"].read_text().replace("mtllib cube.mtl", "mtllib obj.mtl")
        mtl = self.exports["mtl"].read_text()
        self.assertIn("map_Kd tex.png", mtl)
        mtl = mtl.replace("map_Kd tex.png", "map_Kd obj_albedo.png")
        if extra_maps:
            mtl += (
                "map_Pm obj_metallic.png\nmap_Pr obj_roughness.png\nmap_Bump -bm 1 obj_normal.png\n"
            )
        self.save("obj", "model/obj", obj.encode())
        self.save("mtl", "model/mtl", mtl.encode())
        self.save("albedo", "image/png", self.exports["png"].read_bytes(), role="albedo")

    def apply(self, key, cursor=(4.0, 5.0, 6.0)):
        snapshot = self.module.prepare_snapshot(self.unit(key), self.files)
        try:
            self.assertEqual(snapshot.directory.parent, self.root)
            return self.module.import_snapshot(self.scene, snapshot, cursor=cursor)
        finally:
            snapshot.cleanup()

    def assert_published(self, result, key, cursor=(4.0, 5.0, 6.0)):
        self.assertIn(result.collection, tuple(self.scene.collection.children))
        self.assertEqual(result.root["scenario_asset"], key)
        self.assertEqual(result.root["scenario_assets"], ",".join(result.members))
        meshes = [obj for obj in result.objects if obj.type == "MESH"]
        self.assertTrue(meshes)
        points = [obj.matrix_world @ Vector(corner) for obj in meshes for corner in obj.bound_box]
        low = [min(point[i] for point in points) for i in range(3)]
        high = [max(point[i] for point in points) for i in range(3)]
        center = ((low[0] + high[0]) / 2, (low[1] + high[1]) / 2, low[2])
        for actual, expected in zip(center, cursor, strict=True):
            self.assertAlmostEqual(actual, expected, places=4)
        self.assertEqual(set(bpy.context.selected_objects), {self.existing})
        self.assertEqual(bpy.context.view_layer.objects.active, self.existing)
        images = set(bpy.data.images) - self.before["images"]
        self.assertTrue(all(image.packed_file is not None for image in images))
        self.assertTrue(all(image.filepath == "" for image in images))
        self.assertEqual(tuple(self.root.iterdir()), ())
        self.assertEqual((self.scene.render.fps, self.scene.render.fps_base), (30, 1.0))
        self.assertNotIn("Scenario import staging", {scene.name for scene in bpy.data.scenes})
        return images

    def test_legacy_obj_package_binds_its_map_and_drops_missing_maps(self):
        self.legacy_obj()
        unit = self.unit("obj")
        self.assertEqual((unit.material, unit.textures), ("mtl", (("albedo", "albedo"),)))
        result = self.apply("obj")
        images = self.assert_published(result, "obj")
        self.assertEqual(result.format, "obj")
        self.assertEqual(result.members, ("obj", "mtl", "albedo"))
        self.assertEqual(result.dropped_references, 3)
        self.assertEqual(len(images), 1)
        mesh = next(obj for obj in result.objects if obj.type == "MESH")
        material = mesh.data.materials[0]
        textures = [node.image for node in material.node_tree.nodes if node.type == "TEX_IMAGE"]
        self.assertEqual(textures, list(images))

    def test_obj_without_material_imports_untextured(self):
        self.save("obj", "model/obj", self.exports["obj"].read_bytes())
        result = self.apply("obj")
        self.assert_published(result, "obj")
        self.assertEqual(result.members, ("obj",))
        self.assertEqual(result.dropped_references, 1)  # The unbound mtllib.

    def test_embedded_fbx_texture_is_packed_without_its_recorded_path(self):
        self.save("fbx", "application/vnd.autodesk.fbx", self.exports["fbx"].read_bytes())
        result = self.apply("fbx")
        images = self.assert_published(result, "fbx")
        self.assertEqual(len(images), 1)
        self.assertEqual(result.format, "fbx")

    def test_fbx_clips_keep_file_timing_and_report_a_scene_rate_mismatch(self):
        self.save("fbx", "model/x-fbx", self.exports["fbx"].read_bytes())
        before = self.module._snapshot(self.names)
        result = self.apply("fbx")
        self.assertTrue(result.frame_rate_mismatch)
        self.assertEqual((self.scene.render.fps, self.scene.render.fps_base), (30, 1.0))
        self.assertTrue(
            any(obj.animation_data and obj.animation_data.action for obj in result.objects)
        )
        self.module._remove_new_data(before, self.module._PACKAGE_DATA)
        self.assertEqual(self.module._snapshot(self.names), before)
        self.scene.render.fps = 24
        self.assertFalse(self.apply("fbx").frame_rate_mismatch)

    def test_fbx_texture_outside_the_package_is_rolled_back(self):
        self.save("fbx", "model/x-fbx", self.exports["external_fbx"].read_bytes())
        before = self.module._snapshot(self.names)
        with self.assertRaises(self.module.ModelApplicationError) as raised:
            self.apply("fbx")
        self.assertNotIsInstance(raised.exception, self.module.ModelPreflightError)
        self.assertEqual(self.module._snapshot(self.names), before)
        self.assertEqual(set(bpy.context.selected_objects), {self.existing})
        self.assertEqual(tuple(self.root.iterdir()), ())

    def test_disabled_fbx_add_on_fails_before_a_snapshot(self):
        self.save("fbx", "model/x-fbx", self.exports["fbx"].read_bytes())
        unit = self.unit("fbx")
        addon_utils.disable("io_scene_fbx", default_set=True)
        try:
            with self.assertRaisesRegex(self.module.ModelPreflightError, "FBX add-on"):
                self.module.prepare_snapshot(unit, self.files)
        finally:
            addon_utils.enable("io_scene_fbx", default_set=True)
        self.assertEqual(tuple(self.root.iterdir()), ())
        self.assertTrue(hasattr(bpy.types, "IMPORT_SCENE_OT_fbx"))

    def test_ascii_fbx_fails_its_signature_before_import(self):
        self.save("fbx", "model/x-fbx", b"; FBX 7.4.0 project file\n")
        with self.assertRaises(self.module.ModelPreflightError):
            self.module.prepare_snapshot(self.unit("fbx"), self.files)
        self.assertEqual(tuple(self.root.iterdir()), ())

    def test_separate_gltf_reads_only_bound_package_files(self):
        self.gltf_package()
        unit = self.unit("gltf")
        self.assertEqual(set(unit.resources), {"gltf-buffer", "gltf-image"})
        result = self.apply("gltf")
        images = self.assert_published(result, "gltf")
        self.assertEqual(result.members, ("gltf", "gltf-buffer", "gltf-image"))
        self.assertEqual(len(images), 1)

    def test_gltf_reference_outside_the_package_stops_before_a_snapshot(self):
        self.gltf_package(buffer_uri="../cube.bin")
        with self.assertRaises(self.module.ModelPreflightError):
            self.module.prepare_snapshot(self.unit("gltf"), self.files)
        self.assertEqual(tuple(self.root.iterdir()), ())

    def test_mesh_ply_imports_and_splat_ply_stops_before_a_snapshot(self):
        self.save("ply", "model/ply", self.exports["ply"].read_bytes())
        result = self.apply("ply")
        self.assert_published(result, "ply")
        names = ("x", "y", "z", "f_dc_0", "f_dc_1", "f_dc_2", "opacity")
        names += ("scale_0", "scale_1", "scale_2")
        header = "ply\nformat binary_little_endian 1.0\nelement vertex 1\n"
        header += "".join(f"property float {name}\n" for name in names) + "end_header\n"
        self.save("splat", "application/x-ply", header.encode() + struct.pack("<10f", *[0.0] * 10))
        with self.assertRaisesRegex(self.module.ModelPreflightError, "Gaussian splat"):
            self.module.prepare_snapshot(self.unit("splat"), self.files)
        self.assertEqual(tuple(self.root.iterdir()), ())

    def test_model_glb_alias_imports_through_the_package_path(self):
        self.save("glb", "model/glb", (FIXTURES / "synthetic/static-triangle.glb").read_bytes())
        result = self.apply("glb")
        self.assert_published(result, "glb")
        self.assertEqual(result.format, "glb")

    def test_animated_glb_keeps_destination_timing_without_a_rate_mismatch(self):
        self.scene.render.fps, self.scene.render.fps_base = 30, 1.001
        self.save("glb", "model/gltf-binary", animated_glb())
        result = self.apply("glb")
        self.assertFalse(result.frame_rate_mismatch)
        rig = next(obj for obj in result.objects if obj.type == "ARMATURE")
        self.assertEqual(len(rig.animation_data.nla_tracks), 2)
        action = rig.animation_data.nla_tracks[0].strips[0].action
        self.assertAlmostEqual(action.frame_range[1], 30 / 1.001, places=3)
        self.assertEqual((self.scene.render.fps, round(self.scene.render.fps_base, 5)), (30, 1.001))

    def test_changed_member_bytes_fail_before_any_snapshot_file_remains(self):
        self.legacy_obj()
        unit = self.unit("obj")
        path = self.files["albedo"][1]
        path.write_bytes(path.read_bytes() + b"changed")
        before = self.module._snapshot(self.names)
        with self.assertRaisesRegex(self.module.ModelPreflightError, "changed"):
            self.module.prepare_snapshot(unit, self.files)
        self.assertEqual(self.module._snapshot(self.names), before)
        self.assertEqual(tuple(self.root.iterdir()), ())

    def test_failed_publication_restores_every_datablock(self):
        self.legacy_obj()
        before = self.module._snapshot(self.names)
        original = self.module._publish

        def fail(*args):
            original(*args)
            raise RuntimeError("synthetic publication failure")

        with (
            patch.object(self.module, "_publish", side_effect=fail),
            self.assertRaises(self.module.ModelApplicationError),
        ):
            self.apply("obj")
        self.assertEqual(self.module._snapshot(self.names), before)
        self.assertEqual(bpy.context.view_layer.objects.active, self.existing)
        self.assertEqual(tuple(self.root.iterdir()), ())

    def gltf_package(self, buffer_uri="gltf-buffer.bin"):
        document = json.loads(self.exports["gltf"].read_text())
        self.assertEqual(len(document["buffers"]), 1)
        document["buffers"][0]["uri"] = buffer_uri
        for image in document.get("images", []):
            image["uri"] = "gltf-image.png"
        self.save("gltf", "model/gltf+json", json.dumps(document).encode())
        self.save("gltf-buffer", "application/octet-stream", self.exports["bin"].read_bytes())
        self.save("gltf-image", "image/png", self.exports["png"].read_bytes())

    def test_windowless_gltf_imports_and_other_importers_stop_before_a_snapshot(self):
        self.gltf_package()
        self.save("fbx", "model/x-fbx", self.exports["fbx"].read_bytes())
        self.save("obj", "model/obj", self.exports["obj"].read_bytes())
        self.save("ply", "model/ply", self.exports["ply"].read_bytes())
        with bpy.context.temp_override(
            window=None, scene=self.scene, view_layer=self.scene.view_layers[0]
        ):
            self.assertIsNone(bpy.context.window)
            result = self.apply("gltf")
            # Blender's FBX armature build and its OBJ and PLY operators need a window.
            for key in ("fbx", "obj", "ply"):
                with self.subTest(key=key):
                    with self.assertRaisesRegex(self.module.ModelPreflightError, "window context"):
                        self.module.prepare_snapshot(self.unit(key), self.files)
        self.assert_published(result, "gltf")

    def test_snapshot_imports_once_and_never_on_a_worker(self):
        self.legacy_obj()
        unit = self.unit("obj")
        with ThreadPoolExecutor(max_workers=1) as pool:
            with self.assertRaises(self.module.ModelPreflightError):
                pool.submit(self.module.prepare_snapshot, unit, self.files).result(5)
        snapshot = self.module.prepare_snapshot(unit, self.files)
        try:
            self.module.import_snapshot(self.scene, snapshot, cursor=(0.0, 0.0, 0.0))
            with self.assertRaises(self.module.ModelApplicationError):
                self.module.import_snapshot(self.scene, snapshot, cursor=(0.0, 0.0, 0.0))
        finally:
            snapshot.cleanup()
        self.assertEqual(tuple(self.root.iterdir()), ())

    def test_splat_units_are_not_importable_in_this_release(self):
        self.save("spz", "model/spz", b"\x1f\x8b" + b"\0" * 30)
        unit = self.unit("spz")
        self.assertFalse(self.module.importable(unit))
        with self.assertRaises(self.module.ModelPreflightError):
            self.module.prepare_snapshot(unit, self.files)


if __name__ == "__main__":
    unittest.main()
