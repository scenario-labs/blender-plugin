# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
import struct
import tempfile
import unittest
import zlib
from pathlib import Path

import bpy
from helpers import FIXTURES, reset_scene, submodule

ALBEDO = str(FIXTURES / "patina-copper-512" / "albedo.png")


def _chunk(tag, data):
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))


def png(width=4, height=2, *, alpha=True):
    """A tiny 8-bit PNG, RGBA with half alpha or opaque RGB."""
    pixel = bytes((255, 64, 0, 128)) if alpha else bytes((255, 64, 0))
    rows = b"".join(b"\0" + pixel * width for _ in range(height))
    header = struct.pack(">IIBBBBB", width, height, 8, 6 if alpha else 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", header)
        + _chunk(b"IDAT", zlib.compress(rows))
        + _chunk(b"IEND", b"")
    )


def linked(tree, node_type, socket):
    """The node feeding input `socket` of the first node of `node_type`, or None.

    `socket` is the input's identifier: display names change between Blender
    versions, such as the Mix Shader's Fac, which Blender 5.2 names Factor.
    """
    for link in tree.links:
        if link.to_node.type == node_type and link.to_socket.identifier == socket:
            return link.from_node
    return None


class ApplyImageTests(unittest.TestCase):
    def setUp(self):
        reset_scene()
        self.apply_image = submodule("blender.apply_image")

    def test_load_image_packs(self):
        img = self.apply_image.load_image(ALBEDO)
        self.assertEqual(tuple(img.size), (512, 512))
        self.assertTrue(img.packed_file is not None)

    def test_apply_as_texture_links_base_color(self):
        bpy.ops.mesh.primitive_cube_add()
        cube = bpy.context.active_object
        img = self.apply_image.load_image(ALBEDO)
        mat = self.apply_image.apply_as_texture(cube, img)
        self.assertEqual(cube.active_material, mat)
        tex = next(n for n in mat.node_tree.nodes if n.type == "TEX_IMAGE")
        bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        self.assertEqual(tex.image, img)
        link = next(
            link
            for link in mat.node_tree.links
            if link.to_node == bsdf and link.to_socket.name == "Base Color"
        )
        self.assertEqual(link.from_node, tex)

    def test_add_as_plane_matches_aspect_and_cursor(self):
        img = self.apply_image.load_image(ALBEDO)
        bpy.context.scene.cursor.location = (1.0, 2.0, 3.0)
        plane = self.apply_image.add_as_plane(bpy.context, img)
        self.assertEqual(plane.type, "MESH")
        self.assertAlmostEqual(plane.scale.x / plane.scale.y, 1.0, places=4)
        self.assertAlmostEqual(tuple(plane.location)[2], 3.0, places=4)
        self.assertEqual(len(plane.data.materials), 1)

    def test_on_image_result_loads_every_file(self):
        records = submodule("core.jobs.records")
        rec = records.JobRecord.new(lane="image", kind="image", model_id="model_x", body={})
        rec.files = [ALBEDO, str(FIXTURES / "patina-copper-512" / "normal.png")]
        rec.job_id = "job_t"
        names = self.apply_image.on_image_result(rec)
        self.assertEqual(len(names), 2)
        self.assertTrue(all(name in bpy.data.images for name in names))


class PlaneAlphaTests(unittest.TestCase):
    def setUp(self):
        reset_scene()
        self.apply_image = submodule("blender.apply_image")
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))

    def test_add_as_plane_wires_a_files_alpha_and_offers_unlit(self):
        image_plane = submodule("blender.image_plane")
        path = self.root / "cutout.png"
        path.write_bytes(png())
        self.assertTrue(image_plane.file_alpha(path))
        self.assertFalse(image_plane.file_alpha(FIXTURES / "patina-copper-512" / "albedo.png"))
        self.assertFalse(image_plane.file_alpha(self.root / "missing.png"))
        image = self.apply_image.load_image(str(path))
        plane = self.apply_image.add_as_plane(bpy.context, image, alpha=True, unlit=True)
        material = plane.data.materials[0]
        self.assertEqual(material.surface_render_method, "BLENDED")
        self.assertEqual(linked(material.node_tree, "MIX_SHADER", "Fac").type, "TEX_IMAGE")
        self.assertEqual(linked(material.node_tree, "EMISSION", "Color").image, image)

    def test_add_plane_operator_reads_the_files_alpha(self):
        path = self.root / "cutout.png"
        path.write_bytes(png())
        self.assertEqual(bpy.ops.scenario.add_plane(filepath=str(path), unlit=True), {"FINISHED"})
        material = bpy.context.active_object.data.materials[0]
        self.assertEqual(material.surface_render_method, "BLENDED")
        self.assertIsNotNone(linked(material.node_tree, "EMISSION", "Color"))
