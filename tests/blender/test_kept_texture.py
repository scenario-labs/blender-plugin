# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Replace textures keeps the source's own texture on the selected faces or a character's head."""

import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import bmesh
import bpy
import numpy
from helpers import submodule
from mathutils import Matrix

RED = (0.8, 0.1, 0.1, 1.0)
BLUE = (0.1, 0.2, 0.9, 1.0)
# Packed glTF maps: roughness in green, metallic in blue.
MATTE = (0.0, 0.9, 0.0, 1.0)
METAL = (0.0, 0.2, 1.0, 1.0)
FLAT = (0.5, 0.5, 1.0, 1.0)
TILTED = (0.8, 0.5, 0.6, 1.0)
SIZE = 32


def flat_image(name, rgba, *, colour=True):
    image = bpy.data.images.new(name, SIZE, SIZE, is_data=not colour)
    image.pixels.foreach_set(numpy.tile(numpy.array(rgba, dtype=numpy.float32), SIZE * SIZE))
    image.update()
    return image


def textured(name, colour, packed, normal):
    """A material laid out as Blender's glTF importer builds one."""
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    tree = material.node_tree
    bsdf = tree.nodes["Principled BSDF"]
    base = tree.nodes.new("ShaderNodeTexImage")
    base.image = flat_image(f"{name} colour", colour)
    tree.links.new(base.outputs["Color"], bsdf.inputs["Base Color"])
    orm = tree.nodes.new("ShaderNodeTexImage")
    orm.image = flat_image(f"{name} roughness metallic", packed, colour=False)
    split = tree.nodes.new("ShaderNodeSeparateColor")
    tree.links.new(orm.outputs["Color"], split.inputs["Color"])
    tree.links.new(split.outputs["Green"], bsdf.inputs["Roughness"])
    tree.links.new(split.outputs["Blue"], bsdf.inputs["Metallic"])
    bump = tree.nodes.new("ShaderNodeTexImage")
    bump.image = flat_image(f"{name} normal", normal, colour=False)
    mapper = tree.nodes.new("ShaderNodeNormalMap")
    tree.links.new(bump.outputs["Color"], mapper.inputs["Color"])
    tree.links.new(mapper.outputs["Normal"], bsdf.inputs["Normal"])
    return material


def grid(name, size=1.0, segments=8):
    shape = bmesh.new()
    shape.loops.layers.uv.new()
    bmesh.ops.create_grid(
        shape, x_segments=segments, y_segments=segments, size=size / 2, calc_uvs=True
    )
    data = bpy.data.meshes.new(name)
    shape.to_mesh(data)
    shape.free()
    return data


def texel(image, u, v):
    width, height = image.size
    pixels = numpy.empty(width * height * 4, dtype=numpy.float32)
    image.pixels.foreach_get(pixels)
    return pixels.reshape(height, width, 4)[int(v * height), int(u * width)]


class KeptTextureTests(unittest.TestCase):
    def setUp(self):
        self.module = submodule("blender.mesh_result_application")
        self.mesh = submodule("blender.mesh_application")
        self.model = submodule("blender.model_application")
        self.kept = submodule("blender.kept_texture")
        self.storage = submodule("core.jobs.store")
        self.transfers = submodule("core.jobs.transfers")
        self.before = self.model._snapshot()
        self.previous = bpy.context.scene
        self.scene = bpy.data.scenes.new("Kept texture fixture")
        bpy.context.window.scene = self.scene
        self.temp = self.enterContext(tempfile.TemporaryDirectory())
        self.enterContext(patch.object(bpy.utils, "extension_path_user", return_value=self.temp))
        self.source = bpy.data.objects.new("Retextured source", grid("Source surface"))
        self.source.data.materials.append(textured("Source look", RED, MATTE, FLAT))
        self.scene.collection.objects.link(self.source)
        result = bpy.data.objects.new("Provider result", self.source.data.copy())
        result.data.materials.clear()
        result.data.materials.append(textured("Result look", BLUE, METAL, TILTED))
        self.scene.collection.objects.link(result)
        bpy.context.view_layer.update()
        path = Path(self.temp) / "retextured.glb"
        submodule("blender.mesh_export").export_glb(bpy.context, [result], str(path))
        bpy.data.objects.remove(result)
        body = path.read_bytes()
        receipt = self.transfers.DownloadedResult(
            path.name, len(body), hashlib.sha256(body).hexdigest()
        )
        asset = self.storage.ResultAsset("mesh", path.name, "model/gltf-binary", len(body))
        self.files = {"mesh": (self.storage.StoredResult(asset, receipt), path)}
        self.source.select_set(True)
        bpy.context.view_layer.objects.active = self.source

    def tearDown(self):
        bpy.context.window.scene = self.previous
        self.model._remove_new_data(self.before)

    def select_left_half(self):
        for polygon in self.source.data.polygons:
            polygon.select = polygon.center.x < 0
        return sum(polygon.select for polygon in self.source.data.polygons)

    def apply(self, mode, **options):
        formats = submodule("core.scene.model_formats")
        target = self.mesh.capture_target(self.scene, self.source)
        items = (item for item, _ in self.files.values())
        unit = formats.classify_packages(formats.members_from_results(items)).units[0]
        region = self.kept.review((target,), mode) if mode is not None else None
        options = dict(
            policy="RETEXTURE",
            result_to_source=Matrix.Identity(4),
            keep_original=True,
            keep_texture=region,
            **options,
        )
        snapshot = self.module.prepare_saved_mesh(target, unit, self.files, **options)
        try:
            return self.module.apply_saved_mesh(target, snapshot, **options)
        finally:
            snapshot.cleanup()

    def result_maps(self):
        return self.kept.material_maps(self.source.data.materials[0])

    def test_material_maps_reads_roles_from_a_gltf_material(self):
        maps = self.kept.material_maps(self.source.data.materials[0])
        self.assertEqual(sorted(maps), ["base_color", "metallic", "normal", "roughness"])
        self.assertEqual(maps["base_color"][1], (0, 1, 2))
        self.assertEqual(maps["roughness"][1], (1,))
        self.assertEqual(maps["metallic"][1], (2,))
        self.assertEqual(maps["roughness"][0], maps["metallic"][0])
        self.assertEqual(self.kept.material_maps(bpy.data.materials.new("No nodes")), {})

    def test_selected_faces_keep_every_map_and_the_rest_takes_the_result(self):
        count = self.select_left_half()
        application = self.apply("SELECTED")
        self.assertEqual(
            application.kept_texture,
            {
                "mode": "SELECTED",
                "source": "selection",
                "faces": count,
                "maps": ["base_color", "normal", "roughness", "metallic"],
                "skipped": {},
            },
        )
        maps = self.result_maps()
        colour = maps["base_color"][0].image
        self.assertFalse(colour.name.startswith("Source look"))
        # Grid UVs run with x: the left half holds the source's maps, the right the result's.
        numpy.testing.assert_allclose(texel(colour, 0.2, 0.5)[:3], RED[:3], atol=0.02)
        numpy.testing.assert_allclose(texel(colour, 0.8, 0.5)[:3], BLUE[:3], atol=0.02)
        packed = maps["roughness"][0].image
        numpy.testing.assert_allclose(texel(packed, 0.2, 0.5)[1:3], MATTE[1:3], atol=0.02)
        numpy.testing.assert_allclose(texel(packed, 0.8, 0.5)[1:3], METAL[1:3], atol=0.02)
        normal = maps["normal"][0].image
        numpy.testing.assert_allclose(texel(normal, 0.2, 0.5)[:3], FLAT[:3], atol=0.02)
        numpy.testing.assert_allclose(texel(normal, 0.8, 0.5)[:3], TILTED[:3], atol=0.02)
        # Painted maps are packed losslessly; the source keeps its own material untouched.
        for image in (colour, packed, normal):
            self.assertEqual(image.file_format, "PNG")
            self.assertEqual(image.packed_file.data[:8], b"\x89PNG\r\n\x1a\n")
        original = application.original.data.materials[0]
        source_colour = self.kept.material_maps(original)["base_color"][0].image
        numpy.testing.assert_allclose(texel(source_colour, 0.8, 0.5)[:3], RED[:3], atol=0.02)

    def test_the_edge_of_a_selection_blends_into_the_result(self):
        self.select_left_half()
        mesh = self.source.data
        layer = mesh.uv_layers.active.data
        edge = max(
            layer[loop].uv.x
            for polygon in mesh.polygons
            if polygon.select
            for loop in polygon.loop_indices
        )
        self.apply("SELECTED")
        colour = self.result_maps()["base_color"][0].image
        # Just past the selected faces the weight falls across the next face: the colours mix.
        edge = texel(colour, edge + 0.5 / SIZE, 0.5)
        self.assertGreater(edge[0], BLUE[0] + 0.01)
        self.assertLess(edge[0], RED[0] - 0.01)

    def test_without_a_region_the_result_is_untouched(self):
        self.select_left_half()
        for mode in (None, "NONE"):
            with self.subTest(mode=mode):
                application = self.apply(mode)
                colour = self.result_maps()["base_color"][0].image
                numpy.testing.assert_allclose(texel(colour, 0.2, 0.5)[:3], BLUE[:3], atol=0.02)
                if mode is None:
                    self.assertIsNone(application.kept_texture)
                else:
                    self.assertEqual(application.kept_texture["maps"], [])

    def test_a_flat_mesh_keeps_no_head(self):
        application = self.apply("HEAD")
        self.assertEqual(application.kept_texture["source"], None)
        self.assertEqual(application.kept_texture["faces"], 0)
        colour = self.result_maps()["base_color"][0].image
        numpy.testing.assert_allclose(texel(colour, 0.2, 0.5)[:3], BLUE[:3], atol=0.02)

    def test_review_starts_on_the_selection_then_a_standing_characters_head(self):
        target = self.mesh.capture_target(self.scene, self.source)
        # Every face selected, as after an import, is no choice; a flat grid is no character.
        self.assertEqual(self.kept.review((target,), "AUTO").mode, "NONE")
        self.select_left_half()
        target = self.mesh.capture_target(self.scene, self.source)
        self.assertEqual(self.kept.review((target,), "AUTO").mode, "SELECTED")
        self.assertEqual(self.kept.starting_mode([self.source], self.scene, True), "SELECTED")
        for polygon in self.source.data.polygons:
            polygon.select = False
        # Stood up at a person's height it reads as a character, unless Keep head is off.
        self.source.scale = (0.5, 1.8, 1.0)
        self.source.rotation_euler = (1.5707963, 0.0, 0.0)
        bpy.context.view_layer.update()
        self.assertTrue(self.kept.standing([self.source], self.scene))
        self.assertEqual(self.kept.starting_mode([self.source], self.scene, True), "HEAD")
        self.assertEqual(self.kept.starting_mode([self.source], self.scene, False), "NONE")

    def test_a_region_reviewed_for_other_sources_is_refused(self):
        target = self.mesh.capture_target(self.scene, self.source)
        region = self.kept.review((target,), "NONE")
        region_type = submodule("core.scene.kept_texture").KeptRegion
        other = region_type("NONE", None, 0, "", region.weights[:4])
        with self.assertRaises(self.module.MeshResultApplicationError):
            self.module.validate_request(
                target,
                policy="RETEXTURE",
                result_to_source=Matrix.Identity(4),
                keep_original=True,
                keep_texture=other,
            )
        with self.assertRaises(self.module.MeshResultApplicationError):
            self.module.validate_request(
                target,
                policy="UV",
                result_to_source=Matrix.Identity(4),
                keep_original=True,
                keep_texture=region,
            )


class PixelTests(unittest.TestCase):
    def setUp(self):
        self.kept = submodule("blender.kept_texture")

    def test_rasterize_covers_texel_centres_inside_each_triangle(self):
        triangle = numpy.array([[[0.0, 0.0], [4.0, 0.0], [0.0, 4.0]]])
        index, x, y, weights = self.kept.rasterize(triangle, 8, 8, numpy)
        texels = set(zip(x.tolist(), y.tolist(), strict=True))
        # Centres (x + 0.5, y + 0.5) with x + y + 1 <= 4.
        self.assertEqual(texels, {(x, y) for x in range(4) for y in range(4) if x + y <= 3})
        self.assertEqual(set(index.tolist()), {0})
        numpy.testing.assert_allclose(weights.sum(1), 1.0)
        # Triangles outside the image or with no area give nothing.
        outside = numpy.array([[[9.0, 9.0], [12.0, 9.0], [9.0, 12.0]]])
        self.assertEqual(len(self.kept.rasterize(outside, 8, 8, numpy)[0]), 0)
        flat = numpy.array([[[0.0, 0.0], [4.0, 0.0], [8.0, 0.0]]])
        self.assertEqual(len(self.kept.rasterize(flat, 8, 8, numpy)[0]), 0)

    def test_sample_is_bilinear_and_repeats(self):
        pixels = numpy.zeros((2, 2, 4), dtype=numpy.float32)
        pixels[0, 0] = pixels[1, 1] = 1.0
        centre = self.kept.sample(pixels, numpy.array([[0.25, 0.25], [0.5, 0.5]]), numpy)
        numpy.testing.assert_allclose(centre[0], 1.0)
        numpy.testing.assert_allclose(centre[1], 0.5)
        wrapped = self.kept.sample(pixels, numpy.array([[1.25, -0.75]]), numpy)
        numpy.testing.assert_allclose(wrapped[0], 1.0)

    def test_gutter_takes_the_kept_colour_around_kept_texels_only(self):
        pixels = numpy.zeros((8, 8, 4), dtype=numpy.float32)
        covered = numpy.zeros((8, 8), dtype=bool)
        covered[3:5, 3:5] = True
        pixels[3:5, 3:5] = 1.0
        self.kept.fill_gutter(pixels, covered, covered, 2, numpy)
        numpy.testing.assert_allclose(pixels[1:7, 1:7], 1.0)
        self.assertEqual(pixels[0].sum() + pixels[:, 0].sum(), 0.0)
        # Texels other faces cover keep their own colour.
        pixels = numpy.zeros((8, 8, 4), dtype=numpy.float32)
        pixels[3:5, 3:5] = 1.0
        mine = numpy.zeros((8, 8), dtype=bool)
        mine[3:5, 3:5] = True
        others = mine.copy()
        others[:, 5:] = True
        self.kept.fill_gutter(pixels, others, mine, 2, numpy)
        self.assertEqual(pixels[:, 5:].sum(), 0.0)


if __name__ == "__main__":
    unittest.main()
