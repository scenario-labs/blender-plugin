# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""The advisory panorama report decodes generated PNG and OpenEXR files in Blender."""

import json
import math
import tempfile
import unittest
from pathlib import Path

import bpy
import panorama_report
from helpers import ACES_AP0, REC709, scanline_exr

# Rec.709 luminance of the uniform (4.0, 0.5, 0.25) fixture pixel.
FIXTURE_LUMINANCE = 0.2126 * 4.0 + 0.7152 * 0.5 + 0.0722 * 0.25


class PanoramaReportTests(unittest.TestCase):
    def setUp(self):
        self.before = set(bpy.data.images)
        self.temp = tempfile.TemporaryDirectory(dir=bpy.utils.resource_path("USER"))
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def tearDown(self):
        # Measurement never leaves its decoded image behind.
        self.assertEqual(set(bpy.data.images), self.before)

    def save(self, name, width, height, value, *, exr=False):
        image = bpy.data.images.new("Report Fixture", width, height, float_buffer=exr)
        try:
            pixels = []
            for y in range(height):
                for x in range(width):
                    level = value(x, y)
                    pixels += [level, level, level, 1.0]
            image.pixels.foreach_set(pixels)
            image.file_format = "OPEN_EXR" if exr else "PNG"
            path = self.root / name
            image.filepath_raw = str(path)
            image.save()
            return path
        finally:
            bpy.data.images.remove(image)

    def measure(self, path, width, height, *, exr=False):
        expected = {
            "format": "OPEN_EXR" if exr else "PNG",
            "width": width,
            "height": height,
            "openexr": exr,
        }
        return panorama_report.measure_file(path, expected)

    def test_wrapping_png_panorama_has_a_quiet_seam_and_poles(self):
        width, height = 64, 32

        def wrap(x, y):
            # Periodic around the horizon and fading to one value at both poles.
            latitude = math.sin(math.pi * (y + 0.5) / height)
            return 0.5 + 0.4 * math.cos(2 * math.pi * x / width) * latitude

        result = self.measure(self.save("wrap.png", width, height, wrap), width, height)
        self.assertEqual(
            {key: result["decoded"][key] for key in ("format", "width", "height", "float")},
            {"format": "PNG", "width": width, "height": height, "float": False},
        )
        self.assertEqual(result["decoded"]["colorspace"], "sRGB")
        self.assertIsNone(result["dynamic_range"])
        self.assertLess(result["seam"]["edge_to_neighbor"], 2.0)
        self.assertLess(result["seam"]["edge_to_quarter_turn"], 0.2)
        self.assertLess(result["poles"]["top"], 0.05)
        self.assertLess(result["poles"]["bottom"], 0.05)

    def test_ramp_png_reports_a_visible_seam(self):
        width, height = 64, 32
        path = self.save("ramp.png", width, height, lambda x, y: x / (width - 1))
        seam = self.measure(path, width, height)["seam"]
        self.assertGreater(seam["edge_to_neighbor"], 40.0)
        self.assertGreater(seam["edge_to_quarter_turn"], 1.0)

    def test_rec709_openexr_reports_scene_linear_luminance(self):
        path = self.root / "uniform.exr"
        path.write_bytes(scanline_exr(8, 4, REC709))
        result = self.measure(path, 8, 4, exr=True)
        self.assertTrue(result["decoded"]["float"])
        self.assertEqual(result["decoded"]["colorspace"], "Linear Rec.709")
        span = result["dynamic_range"]
        for value in span["percentiles"].values():
            self.assertAlmostEqual(value, FIXTURE_LUMINANCE, places=4)
        self.assertEqual(span["stops_p1_to_p99_9"], 0.0)
        self.assertEqual(span["non_finite"], 0)
        # A uniform image has no reference variation for its ratios.
        self.assertIsNone(result["seam"]["edge_to_neighbor"])
        self.assertIsNone(result["poles"]["top"])

    def test_openexr_stop_span_matches_the_written_range(self):
        width, height = 64, 32
        path = self.save(
            "range.exr", width, height, lambda x, y: 2.0 ** (-4 + 12 * x / (width - 1)), exr=True
        )
        span = self.measure(path, width, height, exr=True)["dynamic_range"]
        # p1 falls in the darkest column and p99.9 in the brightest: 12 stops,
        # within the rounding of Blender's OpenEXR write and color conversion.
        self.assertAlmostEqual(span["percentiles"]["1"], 2.0**-4, places=4)
        self.assertAlmostEqual(span["max"], 256.0, places=1)
        self.assertAlmostEqual(span["stops_p1_to_p99_9"], 12.0, places=3)

    def test_aces_ap0_openexr_is_measured_after_blender_converts_it(self):
        path = self.root / "aces.exr"
        path.write_bytes(scanline_exr(8, 4, ACES_AP0))
        result = self.measure(path, 8, 4, exr=True)
        self.assertEqual(result["decoded"]["colorspace"], "ACES2065-1")
        # Blender's scene-linear Rec.709 values differ from the raw AP0 numbers.
        median = result["dynamic_range"]["percentiles"]["50"]
        self.assertGreater(abs(median - FIXTURE_LUMINANCE), 0.01)

    def test_measure_writes_once_and_refuses_a_disagreeing_decode(self):
        path = self.root / "uniform.exr"
        path.write_bytes(scanline_exr(8, 4, REC709))
        entry = {"file": "uniform.exr", "format": "OPEN_EXR", "width": 8, "height": 4}
        manifest = self.root / "manifest.json"
        manifest.write_text(json.dumps({"files": [{**entry, "openexr": True}]}))
        output = self.root / "measurements.json"
        panorama_report.measure(manifest, output)
        measured = json.loads(output.read_text())
        self.assertEqual(measured["blender"], bpy.app.version_string)
        self.assertEqual([item["file"] for item in measured["files"]], ["uniform.exr"])
        with self.assertRaises(FileExistsError):
            panorama_report.measure(manifest, output)
        for change in ({"width": 16, "height": 8}, {"format": "PNG"}):
            wrong = self.root / f"wrong-{len(change)}.json"
            wrong.write_text(json.dumps({"files": [{**entry, "openexr": True, **change}]}))
            target = self.root / f"wrong-{len(change)}-out.json"
            with self.assertRaisesRegex(panorama_report.ReportError, "different image"):
                panorama_report.measure(wrong, target)
            self.assertFalse(target.exists())
        escape = self.root / "escape.json"
        escape.write_text(json.dumps({"files": [{**entry, "file": "../uniform.exr"}]}))
        with self.assertRaisesRegex(panorama_report.ReportError, "manifest"):
            panorama_report.measure(escape, self.root / "escape-out.json")


if __name__ == "__main__":
    unittest.main()
