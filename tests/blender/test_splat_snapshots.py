# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Installed splat decoders run on Blender's Python and feed buffer-based mesh writes.

The prototype Add to scene operator reports SPZ files the decoder rejects.
"""

import gzip
import io
import struct
import tempfile
import threading
import unittest
from pathlib import Path

import bpy
from helpers import reset_scene, submodule


def spz_bytes(count):
    """SPZ v3 with points (i, 1, -i) in saved OPENGL axes and identity rotations."""
    header = struct.pack("<IIIBBBB", 0x5053474E, 3, count, 0, 12, 0, 0)
    positions = bytearray()
    for index in range(count):
        for value in (index, 1, -index):
            raw = (value << 12) & 0xFFFFFF
            positions += bytes((raw & 0xFF, (raw >> 8) & 0xFF, raw >> 16))
    body = positions + bytes([255] * count) + bytes([128] * 3 * count) + bytes([96] * 3 * count)
    return gzip.compress(header + body + b"\x00\x00\x00\xc0" * count)


class SplatSnapshotTests(unittest.TestCase):
    def setUp(self):
        reset_scene()
        self.splats = submodule("core.scene.splats")

    def decode_off_main_thread(self, data, media_type, axes):
        outcome = {}

        def run():
            try:
                outcome["data"] = self.splats.decode(
                    io.BytesIO(data),
                    media_type,
                    options=self.splats.SplatOptions(4, axes),
                    size=len(data),
                )
            except Exception as error:  # surfaced on the test thread
                outcome["error"] = error

        worker = threading.Thread(target=run)
        worker.start()
        worker.join(30)
        self.assertNotIn("error", outcome)
        return outcome["data"]

    def build(self, data):
        mesh = bpy.data.meshes.new("Splat snapshot test")
        mesh.vertices.add(data.kept)
        mesh.vertices.foreach_set("co", data.floats("positions"))
        for name, kind in (("splat_color", "FLOAT_COLOR"), ("splat_radius", "FLOAT")):
            mesh.attributes.new(name, kind, "POINT")
        # Adding an attribute can invalidate earlier references; look each up by name.
        mesh.attributes["splat_color"].data.foreach_set("color", data.floats("colors"))
        mesh.attributes["splat_radius"].data.foreach_set("value", data.floats("radii"))
        mesh.update()
        return mesh

    def test_spz_snapshot_builds_a_thinned_point_mesh_in_blender_axes(self):
        data = self.decode_off_main_thread(spz_bytes(8), "model/spz", "OPENGL")
        self.assertEqual((data.count, data.kept, data.step), (8, 4, 2))
        self.assertTrue(data.floats("positions").readonly)
        mesh = self.build(data)
        # Saved OPENGL (i, 1, -i) is Blender (i, i, 1).
        self.assertEqual([tuple(v.co) for v in mesh.vertices], [(i, i, 1.0) for i in (0, 2, 4, 6)])
        color = mesh.attributes["splat_color"].data[1].color
        self.assertAlmostEqual(color[3], 1.0)
        self.assertAlmostEqual(color[0], 0.5 + 0.28209479177387814 * (128 / 255 - 0.5) / 0.15, 5)
        self.assertGreater(mesh.attributes["splat_radius"].data[0].value, 0.0)

    def test_splat_records_and_mesh_ply_routes_on_blender_python(self):
        record = struct.pack(
            "<3f3f4B4B", 1, 2, 3, 0.1, 0.1, 0.1, 255, 0, 0, 255, 128, 128, 128, 255
        )
        data = self.decode_off_main_thread(record * 2, "model/splat", "OPENCV")
        mesh = self.build(data)
        # Saved OPENCV (1, 2, 3) is Blender (1, 3, -2).
        self.assertEqual(tuple(mesh.vertices[0].co), (1.0, 3.0, -2.0))
        ply = (
            b"ply\nformat ascii 1.0\nelement vertex 1\n"
            b"property float x\nproperty float y\nproperty float z\nend_header\n0 0 0\n"
        )
        self.assertIsNone(self.decode_off_main_thread(ply, "model/ply", "OPENCV"))
        # Without x, y and z the layout is neither a splat nor a mesh.
        bare = b"ply\nformat ascii 1.0\nelement vertex 1\nproperty float x\nend_header\n0\n"
        with self.assertRaisesRegex(self.splats.SplatError, "Unsupported PLY layout"):
            self.splats.decode(
                io.BytesIO(bare),
                "model/ply",
                options=self.splats.SplatOptions(10, "OPENCV"),
                size=len(bare),
            )

    def test_add_to_scene_reports_rejected_spz_files_without_a_traceback(self):
        folder = Path(tempfile.mkdtemp(prefix="scenario-spz-reject-"))
        cases = (
            # Version 1 stored float16 positions; it is rejected rather than misread.
            ("legacy.spz", 1, 1, "SPZ v1 (float16 positions) is not supported; the saved file is"),
            ("empty.spz", 2, 0, "point count is empty"),
        )
        for name, version, count, message in cases:
            with self.subTest(name=name):
                path = folder / name
                header = struct.pack("<IIIBBBB", 0x5053474E, version, count, 0, 12, 0, 0)
                path.write_bytes(gzip.compress(header + bytes(16 * count)))
                before = set(bpy.data.objects.keys())
                # Blender raises an operator's ERROR report to a Python caller.
                with self.assertRaises(RuntimeError) as caught:
                    bpy.ops.scenario.import_mesh_file(filepath=str(path))
                report = str(caught.exception)
                self.assertIn(message, report)
                self.assertNotIn("Traceback", report)
                self.assertEqual(set(bpy.data.objects.keys()), before)
                self.assertTrue(path.exists())


if __name__ == "__main__":
    unittest.main()
