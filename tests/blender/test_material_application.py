# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Packed PBR graph, real-world tiling, exact mesh-slot targeting and rollback in Blender."""

import hashlib
import struct
import tempfile
import unittest
import zlib
from dataclasses import replace
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

    def fixture(
        self, roles=("albedo", "normal", "smoothness", "metallic", "height", "ao"), *, jpeg=False
    ):
        items, paths = [], []
        file_format, media_type = ("JPEG", "image/jpeg") if jpeg else ("PNG", "image/png")
        for index, role in enumerate(roles):
            image = bpy.data.images.new("Synthetic material map", width=2, height=2)
            path = self.root / f"map-{index}.{'jpg' if jpeg else 'png'}"
            try:
                image.pixels[:] = [0.5, 0.5, 1.0, 1.0] * 4
                image.file_format, image.filepath_raw = file_format, str(path)
                image.save()
            finally:
                bpy.data.images.remove(image)
            data = path.read_bytes()
            asset = self.storage.ResultAsset(
                f"map-{index}", path.name, media_type, len(data), texture_role=role
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

    def plane(self, size=40.0, *, uvs=False):
        """A flat mesh `size` metres wide, selected as the active object."""
        bpy.ops.mesh.primitive_plane_add(size=size, calc_uvs=uvs)
        obj = bpy.context.active_object
        bpy.context.view_layer.update()
        return obj

    @staticmethod
    def nodes(material, kind):
        return [node for node in material.node_tree.nodes if node.type == kind]

    def assert_one_shared_mapping(self, material):
        """Every map reads the one Mapping node, which reads the coordinates node."""
        (mapping,) = self.nodes(material, "MAPPING")
        textures = self.nodes(material, "TEX_IMAGE")
        self.assertTrue(textures)
        for texture in textures:
            (link,) = texture.inputs["Vector"].links
            self.assertEqual(link.from_node, mapping, texture.label)
        (link,) = mapping.inputs["Vector"].links
        self.assertEqual(mapping.vector_type, "POINT")
        return mapping, link.from_socket

    @staticmethod
    def scale(mapping):
        """The Mapping scale; Blender stores it as single-precision floats."""
        return tuple(round(value, 5) for value in mapping.inputs["Scale"].default_value)

    def world_tile(self, obj, mapping):
        """Metres one texture repeat spans along each object axis."""
        return tuple(
            round(length / scale, 4)
            for length, scale in zip(obj.matrix_world.to_scale(), self.scale(mapping), strict=True)
        )

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
        # The cube has UVs: its maps keep the named UV map behind the shared Mapping node.
        mapping, source = self.assert_one_shared_mapping(result.material)
        self.assertEqual((source.node.type, source.node.uv_map), ("UVMAP", target.uv_name))
        self.assertTrue(all(node.projection == "FLAT" for node in textures.values()))

    def test_ambiguous_maps_fail_before_loading_or_assignment(self):
        for roles in (
            ("albedo", "albedo"),
            ("base", "base", "albedo"),
            ("base", "albedo", "albedo"),
            ("normal",),
            ("base", "roughness", "smoothness"),
        ):
            with self.subTest(roles=roles), self.assertRaises(self.module.MaterialApplicationError):
                self.module.apply_material(self.fixture(roles), self.target)
        self.assertEqual(len(self.obj.material_slots), 0)
        self.assertEqual(set(bpy.data.materials), self.materials)
        self.assertEqual(set(bpy.data.images), self.images)

    def test_complete_texture_set_uses_albedo_without_loading_its_base_preview(self):
        maps = ("albedo", "normal", "smoothness", "metallic", "height", "ao", "edge")
        for roles in (("base", *maps), (*maps, "base")):
            with self.subTest(roles=roles):
                verified = self.fixture(roles)
                before = {path: path.read_bytes() for path in verified.paths}
                target = self.module.capture_target(self.scene, self.obj)
                result = self.module.apply_material(verified, target)
                tree = result.material.node_tree
                textures = {node.label for node in tree.nodes if node.type == "TEX_IMAGE"}
                self.assertEqual(textures, {role.title() for role in maps})
                self.assertEqual(len(result.images), len(maps))
                bsdf = next(node for node in tree.nodes if node.type == "BSDF_PRINCIPLED")
                self.assertEqual(bsdf.inputs["Base Color"].links[0].from_node.label, "Albedo")
                self.assertTrue(all(image.packed_file for image in result.images))
                self.assertEqual({path: path.read_bytes() for path in verified.paths}, before)

    def test_grayscale_scalar_maps_decode_pack_and_connect_without_conversion(self):
        def chunk(kind, payload):
            body = kind + payload
            return struct.pack(">I", len(payload)) + body + struct.pack(">I", zlib.crc32(body))

        for depth in (8, 16):
            with self.subTest(depth=depth):
                verified = self.fixture(
                    ("base", "albedo", "normal", "smoothness", "metallic", "height")
                )
                items = list(verified.record.results)
                for index, item in enumerate(items):
                    if item.asset.texture_role not in {"smoothness", "metallic", "height"}:
                        continue
                    sample = b"\x80" if depth == 8 else b"\x80\x00"
                    data = (
                        b"\x89PNG\r\n\x1a\n"
                        + chunk(b"IHDR", struct.pack(">IIBBBBB", 2, 2, depth, 0, 0, 0, 0))
                        + chunk(b"IDAT", zlib.compress((b"\x00" + sample * 2) * 2))
                        + chunk(b"IEND", b"")
                    )
                    verified.paths[index].write_bytes(data)
                    items[index] = replace(
                        item,
                        asset=replace(item.asset, expected_size=len(data)),
                        receipt=self.transfers.DownloadedResult(
                            item.receipt.name, len(data), hashlib.sha256(data).hexdigest()
                        ),
                    )
                verified = replace(verified, record=replace(verified.record, results=tuple(items)))
                before = [path.read_bytes() for path in verified.paths]
                result = self.module.apply_material(
                    verified, self.module.capture_target(self.scene, self.obj)
                )
                self.assertEqual(self.obj.data.materials[0], result.material)
                textures = {
                    node.label: node.image
                    for node in result.material.node_tree.nodes
                    if node.type == "TEX_IMAGE"
                }
                self.assertEqual(len(textures), 5)
                for label in ("Smoothness", "Metallic", "Height"):
                    image = textures[label]
                    self.assertTrue(image.packed_file)
                    self.assertEqual(image.colorspace_settings.name, "Non-Color")
                    self.assertAlmostEqual(
                        image.pixels[0], 128 / 255 if depth == 8 else 32768 / 65535, places=3
                    )
                    self.assertEqual(tuple(image.pixels[:3]), (image.pixels[0],) * 3)
                self.assertEqual([path.read_bytes() for path in verified.paths], before)

    def test_single_jpeg_base_texture_applies_as_packed_srgb_base_color(self):
        # Seamless texture models can return one JPEG base-color map.
        verified = self.fixture(("base",), jpeg=True)
        before = verified.paths[0].read_bytes()
        result = self.module.apply_material(verified, self.target)
        self.assertEqual(self.obj.data.materials[0], result.material)
        (image,) = result.images
        self.assertEqual((image.file_format, tuple(image.size)), ("JPEG", (2, 2)))
        self.assertTrue(image.packed_file and not image.filepath)
        self.assertEqual(image.colorspace_settings.name, "sRGB")
        bsdf = next(n for n in result.material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        self.assertEqual(bsdf.inputs["Base Color"].links[0].from_node.label, "Base")
        self.assertEqual(verified.paths[0].read_bytes(), before)

    def test_jpeg_needs_its_saved_media_type_and_stays_out_of_image_import(self):
        verified = self.fixture(("base",), jpeg=True)
        importer = submodule("blender.image_application")
        # Image import keeps its PNG/EXR preflight; only material maps accept JPEG.
        with self.assertRaises(importer.ImageApplicationError):
            importer.apply_images(verified)
        (item,) = verified.record.results
        relabeled = replace(item, asset=replace(item.asset, media_type="image/png"))
        mismatch = replace(verified, record=replace(verified.record, results=(relabeled,)))
        with self.assertRaises(self.module.MaterialApplicationError):
            self.module.apply_material(mismatch, self.target)
        self.assertEqual(len(self.obj.material_slots), 0)
        self.assertEqual(set(bpy.data.materials), self.materials)
        self.assertEqual(set(bpy.data.images), self.images)

    def test_dense_generated_mesh_takes_a_material_and_rolls_back(self):
        # Image-to-3D results commonly exceed one million triangles.
        bpy.ops.mesh.primitive_grid_add(x_subdivisions=1100, y_subdivisions=1100)
        obj = bpy.context.active_object
        self.assertGreater(len(obj.data.polygons), 1_000_000)
        obj.data.polygons[-1].material_index = 3
        target = self.module.capture_target(self.scene, obj)
        original = self.module._assign

        def fail(*args):
            original(*args)
            raise RuntimeError("synthetic assignment failure")

        with patch.object(self.module, "_assign", side_effect=fail):
            with self.assertRaises(self.module.MaterialApplicationError):
                self.module.apply_material(self.fixture(("base",)), target)
        self.assertEqual(self.module.capture_target(self.scene, obj), target)
        result = self.module.apply_material(self.fixture(("base",)), target)
        self.assertEqual(tuple(obj.data.materials), (result.material,))
        self.assertEqual(obj.data.polygons[-1].material_index, 3)
        with (
            patch.object(self.module, "_MAX_POLYGONS", len(obj.data.polygons) - 1),
            self.assertRaisesRegex(self.module.MaterialApplicationError, "polygon limit"),
        ):
            self.module.capture_target(self.scene, obj)

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

    def test_plane_without_uvs_gets_box_mapping_at_two_metre_tiles_and_stays_unchanged(self):
        plane = self.plane(40.0)
        mesh, vertices = plane.data, [tuple(vertex.co) for vertex in plane.data.vertices]
        self.assertFalse(mesh.uv_layers)
        target = self.module.capture_target(self.scene, plane)
        self.assertEqual(target.uv_name, "")
        before = set(bpy.data.meshes)
        result = self.module.apply_material(self.fixture(), target)
        # Nothing on the mesh changes: no UV layer, same vertices, one new material slot.
        self.assertEqual((plane.data, set(bpy.data.meshes)), (mesh, before))
        self.assertFalse(mesh.uv_layers)
        self.assertEqual([tuple(vertex.co) for vertex in mesh.vertices], vertices)
        self.assertEqual(tuple(mesh.materials), (result.material,))
        mapping, source = self.assert_one_shared_mapping(result.material)
        # A 40 m plane at 2 m tiles repeats 20 times: 0.5 per object-space metre.
        self.assertEqual(self.scale(mapping), (0.5, 0.5, 0.5))
        self.assertEqual((source.node.type, source.name), ("TEX_COORD", "Object"))
        self.assertFalse(self.nodes(result.material, "UVMAP"))
        self.assertEqual(
            (result.mapping.projection, result.mapping.tile_size, result.mapping.measured),
            ("BOX", 2.0, True),
        )
        textures = {node.label.lower(): node for node in self.nodes(result.material, "TEX_IMAGE")}
        self.assertEqual(len(textures), 6)
        for role, texture in textures.items():
            with self.subTest(role=role):
                self.assertEqual(texture.projection, "BOX")
                self.assertAlmostEqual(texture.projection_blend, 0.1)
        # Every map shares that placement, the AO map included, and keeps its colour space.
        self.assertEqual(textures["albedo"].image.colorspace_settings.name, "sRGB")
        for role in ("normal", "smoothness", "metallic", "height", "ao"):
            self.assertEqual(textures[role].image.colorspace_settings.name, "Non-Color")
        (normal,) = self.nodes(result.material, "NORMAL_MAP")
        self.assertEqual(normal.inputs["Color"].links[0].from_node, textures["normal"])
        bump = next(node for node in self.nodes(result.material, "BUMP"))
        self.assertEqual(bump.inputs["Normal"].links[0].from_node, normal)
        self.assertEqual(self.world_tile(plane, mapping), (2.0, 2.0, 2.0))

    def test_tile_size_sets_the_repeat_length_in_world_metres(self):
        plane = self.plane(40.0)
        for tile, scale in ((0.5, 2.0), (5.0, 0.2), (40.0, 0.025)):
            with self.subTest(tile=tile):
                target = self.module.capture_target(self.scene, plane)
                result = self.module.apply_material(self.fixture(("base",)), target, tile)
                (mapping,) = self.nodes(result.material, "MAPPING")
                self.assertEqual(self.scale(mapping), (scale, scale, scale))
                self.assertEqual(result.mapping.tile_size, tile)

    def test_scaled_object_keeps_the_tile_size_in_world_metres(self):
        plane = self.plane(2.0)
        plane.scale = (20.0, 20.0, 1.0)
        bpy.context.view_layer.update()
        target = self.module.capture_target(self.scene, plane)
        result = self.module.apply_material(self.fixture(("base", "normal")), target)
        (mapping,) = self.nodes(result.material, "MAPPING")
        # The 2-unit plane is 40 m wide: 20 repeats over its 2 object units.
        self.assertEqual(self.scale(mapping), (10.0, 10.0, 0.5))
        self.assertEqual(self.world_tile(plane, mapping), (2.0, 2.0, 2.0))

    def test_uneven_rotated_and_parented_scale_keeps_world_tiles(self):
        plane = self.plane(2.0)
        parent = bpy.data.objects.new("Scaled parent", None)
        self.scene.collection.objects.link(parent)
        parent.scale = (5.0, 5.0, 5.0)
        plane.parent = parent
        plane.scale = (4.0, 8.0, 1.0)
        plane.rotation_euler = (0.0, 0.0, 0.7)
        bpy.context.view_layer.update()
        target = self.module.capture_target(self.scene, plane)
        result = self.module.apply_material(self.fixture(("base",)), target, 0.5)
        (mapping,) = self.nodes(result.material, "MAPPING")
        self.assertEqual(self.scale(mapping), (40.0, 80.0, 10.0))
        self.assertEqual(self.world_tile(plane, mapping), (0.5, 0.5, 0.5))

    def test_mirrored_object_scale_still_tiles_at_the_requested_size(self):
        plane = self.plane(2.0)
        plane.scale = (-3.0, 3.0, 1.0)
        bpy.context.view_layer.update()
        result = self.module.apply_material(
            self.fixture(("base",)), self.module.capture_target(self.scene, plane)
        )
        (mapping,) = self.nodes(result.material, "MAPPING")
        self.assertEqual(self.scale(mapping), (1.5, 1.5, 0.5))

    def test_uv_mesh_scales_its_layout_from_metres_per_uv_unit(self):
        plane = self.plane(40.0, uvs=True)
        uv_name = plane.data.uv_layers.active.name
        result = self.module.apply_material(
            self.fixture(("base", "normal")), self.module.capture_target(self.scene, plane)
        )
        mapping, source = self.assert_one_shared_mapping(result.material)
        # The UVs cover 0..1 over 40 m: 40 m per UV unit, so 20 repeats at 2 m tiles.
        self.assertEqual(self.scale(mapping), (20.0, 20.0, 20.0))
        self.assertEqual((source.node.type, source.node.uv_map), ("UVMAP", uv_name))
        self.assertEqual(
            (result.mapping.projection, result.mapping.measured, mapping.label),
            ("UV", True, "Tiling"),
        )
        (normal,) = self.nodes(result.material, "NORMAL_MAP")
        self.assertEqual(normal.uv_map, uv_name)
        self.assertEqual(plane.data.uv_layers.active.name, uv_name)

    def test_uv_scale_follows_the_layout_object_scale_and_tile_size(self):
        plane = self.plane(2.0, uvs=True)
        for item in plane.data.uv_layers.active.uv:
            item.vector = item.vector * 4.0
        plane.scale = (10.0, 10.0, 1.0)
        bpy.context.view_layer.update()
        target = self.module.capture_target(self.scene, plane)
        result = self.module.apply_material(self.fixture(("base",)), target, 4.0)
        (mapping,) = self.nodes(result.material, "MAPPING")
        # 20 m over 4 UV units is 5 m per unit: 1.25 repeats per unit at 4 m tiles.
        self.assertEqual(self.scale(mapping), (1.25, 1.25, 1.25))

    def test_a_cube_with_one_uv_tile_per_face_measures_the_face_size(self):
        bpy.ops.mesh.primitive_cube_add(size=1.0)
        cube = bpy.context.active_object
        layer = cube.data.uv_layers.active
        corners = ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))
        for polygon in cube.data.polygons:
            for corner, loop in zip(corners, polygon.loop_indices, strict=True):
                layer.uv[loop].vector = corner
        bpy.context.view_layer.update()
        result = self.module.apply_material(
            self.fixture(("base",)), self.module.capture_target(self.scene, cube), 4.0
        )
        # Every 1 m face spans one UV unit, so a 4 m tile is 0.25 repeats per unit.
        self.assertTrue(result.mapping.measured)
        (mapping,) = self.nodes(result.material, "MAPPING")
        self.assertEqual(self.scale(mapping), (0.25, 0.25, 0.25))

    def test_unmeasurable_uvs_keep_tiling_one_and_label_the_mapping(self):
        plane = self.plane(40.0, uvs=True)
        for item in plane.data.uv_layers.active.uv:
            item.vector = (0.0, 0.0)
        result = self.module.apply_material(
            self.fixture(("base",)), self.module.capture_target(self.scene, plane)
        )
        (mapping,) = self.nodes(result.material, "MAPPING")
        self.assertEqual(self.scale(mapping), (1.0, 1.0, 1.0))
        self.assertFalse(result.mapping.measured)
        self.assertIn("UV size unknown", mapping.label)

    def test_uv_measurement_is_bounded_on_a_dense_mesh(self):
        bpy.ops.mesh.primitive_grid_add(x_subdivisions=300, y_subdivisions=300, size=30.0)
        grid = bpy.context.active_object
        bpy.context.view_layer.update()
        self.assertGreater(len(grid.data.polygons), 80_000)
        with patch.object(
            self.module.tiling, "polygon_area", wraps=self.module.tiling.polygon_area
        ) as area:
            metres = self.module._metres_per_uv(self.module.capture_target(self.scene, grid))
        self.assertLessEqual(area.call_count, 2 * 2 * self.module._UV_SAMPLE_FACES)
        self.assertAlmostEqual(metres, 30.0, places=3)

    def test_invalid_tile_size_is_refused_before_any_data_is_created(self):
        plane = self.plane(40.0)
        target = self.module.capture_target(self.scene, plane)
        for value in (0, -2.0, 0.001, 1000.5, float("nan"), True, "2"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(self.module.MaterialApplicationError, "tile_size_m"):
                    self.module.apply_material(self.fixture(("base",)), target, value)
        self.assertEqual(len(plane.material_slots), 0)
        self.assertEqual(set(bpy.data.materials), self.materials)
        self.assertEqual(set(bpy.data.images), self.images)

    def test_failed_box_application_rolls_back_and_leaves_the_mesh_without_uvs(self):
        plane = self.plane(40.0)
        plane.data.polygons[0].material_index = 2
        target = self.module.capture_target(self.scene, plane)
        original = self.module._assign

        def fail(*args):
            original(*args)
            raise RuntimeError("synthetic assignment failure")

        with patch.object(self.module, "_assign", side_effect=fail):
            with self.assertRaisesRegex(self.module.MaterialApplicationError, "files remain"):
                self.module.apply_material(self.fixture(), target)
        self.assertEqual(self.module.capture_target(self.scene, plane), target)
        self.assertFalse(plane.data.uv_layers)
        self.assertEqual(plane.data.polygons[0].material_index, 2)
        self.assertEqual(set(bpy.data.materials), self.materials)
        self.assertEqual(set(bpy.data.images), self.images)

    def test_failed_mapping_or_graph_build_rolls_back_new_images_and_material(self):
        plane = self.plane(40.0)
        target = self.module.capture_target(self.scene, plane)
        for name in ("_mapping", "_build"):
            with self.subTest(step=name):
                with patch.object(self.module, name, side_effect=RuntimeError("synthetic")):
                    with self.assertRaises(self.module.MaterialApplicationError):
                        self.module.apply_material(self.fixture(), target)
                self.assertEqual(self.module.capture_target(self.scene, plane), target)
                self.assertEqual(set(bpy.data.materials), self.materials)
                self.assertEqual(set(bpy.data.images), self.images)

    def test_a_mesh_without_uvs_keeps_the_destination_refusals(self):
        plane = self.plane(40.0)
        target = self.module.capture_target(self.scene, plane)
        other = bpy.data.objects.new("Shared plane data", plane.data)
        self.scene.collection.objects.link(other)
        with self.assertRaises(self.module.MaterialApplicationError):
            self.module.apply_material(self.fixture(("base",)), target)
        with self.assertRaisesRegex(self.module.MaterialApplicationError, "single-user mesh"):
            self.module.capture_target(self.scene, plane)
        self.assertEqual(len(plane.material_slots) + len(other.material_slots), 0)
        bpy.data.objects.remove(other)
        # A non-mesh object and a mesh outside Object Mode are still refused.
        empty = bpy.data.objects.new("Not a mesh", None)
        self.scene.collection.objects.link(empty)
        with self.assertRaises(self.module.MaterialApplicationError):
            self.module.capture_target(self.scene, empty)
        bpy.context.view_layer.objects.active = plane
        bpy.ops.object.mode_set(mode="EDIT")
        try:
            with self.assertRaises(self.module.MaterialApplicationError):
                self.module.capture_target(self.scene, plane)
        finally:
            bpy.ops.object.mode_set(mode="OBJECT")
        self.assertEqual(self.module.capture_target(self.scene, plane).uv_name, "")
