# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Offline generated PNG/JPEG/EXR fixtures applied by the installed extension."""

import hashlib
import os
import re
import struct
import tempfile
import threading
import unittest.mock
import zlib
from dataclasses import replace
from pathlib import Path

import bpy
from helpers import ACES_AP0, ACES_AP1, FIXTURES, REC709, exr_attribute, scanline_exr, submodule

PROGRESSIVE_JPEG = FIXTURES / "synthetic" / "panorama-progressive.jpg"


def colorspaces():
    settings = bpy.types.ColorManagedInputColorspaceSettings.bl_rna.properties["name"]
    return {item.identifier for item in settings.enum_items}


def exif_orientation(data, orientation):
    """Insert a big-endian EXIF IFD0 orientation tag directly after SOI."""
    tiff = b"MM\x00\x2a" + struct.pack(">IH", 8, 1)
    tiff += struct.pack(">HHII", 0x0112, 3, 1, orientation << 16) + bytes(4)
    payload = b"Exif\0\0" + tiff
    return data[:2] + b"\xff\xe1" + struct.pack(">H", len(payload) + 2) + payload + data[2:]


def container_flag(value):
    return exr_attribute(b"acesImageContainerFlag", b"int", struct.pack("<i", value))


def interop(value):
    return exr_attribute(b"colorInteropID", b"string", value)


class WorldApplicationTests(unittest.TestCase):
    def setUp(self):
        self.module = submodule("blender.world_application")
        self.panorama = submodule("core.scene.panorama")
        self.before_worlds = set(bpy.data.worlds)
        self.before_images = set(bpy.data.images)
        self.original = bpy.data.worlds.new("Fixture Original")
        self.original.use_nodes = True
        self.original.node_tree.nodes.get("Background").inputs["Strength"].default_value = 0.375
        self.scene = bpy.data.scenes.new("Fixture Explicit Target")
        self.other = bpy.data.scenes.new("Fixture Shared Original")
        self.scene.world = self.other.world = self.original
        self.temp = tempfile.TemporaryDirectory(dir=bpy.utils.resource_path("USER"))
        self.addCleanup(self.temp.cleanup)

    def tearDown(self):
        for scene in (self.scene, self.other):
            if scene in tuple(bpy.data.scenes):
                bpy.data.scenes.remove(scene)
        for world in set(bpy.data.worlds) - self.before_worlds:
            bpy.data.worlds.remove(world)
        for image in set(bpy.data.images) - self.before_images:
            bpy.data.images.remove(image)

    def fixture(self, *, exr=False, jpeg=False, width=4, height=2):
        image = bpy.data.images.new("Fixture Pixels", width=width, height=height, float_buffer=exr)
        try:
            image.pixels[:] = [4.0 if exr else 0.5, 0.25, 0.125, 1.0] * (width * height)
            image.file_format = "OPEN_EXR" if exr else "JPEG" if jpeg else "PNG"
            name = "fixture.exr" if exr else "fixture.jpg" if jpeg else "fixture.png"
            path = Path(self.temp.name) / name
            image.filepath_raw = str(path)
            image.save()
            return path
        finally:
            bpy.data.images.remove(image)

    def write(self, name, data):
        path = Path(self.temp.name) / name
        path.write_bytes(data)
        return path

    def assert_original(self):
        self.assertEqual(self.scene.world, self.original)
        self.assertEqual(self.other.world, self.original)
        self.assertEqual(
            self.original.node_tree.nodes.get("Background").inputs["Strength"].default_value, 0.375
        )

    def test_png_explicit_target_packed_graph_and_shared_original_restore(self):
        active = bpy.context.scene
        active_world = active.world
        path = self.fixture()
        receipt = self.module.apply_world(self.scene, path)
        path.unlink()
        world, image = self.scene.world, receipt._image
        self.assertEqual(active.world, active_world)
        self.assertEqual(self.other.world, self.original)
        self.assertFalse(receipt.info.hdr_capable)
        self.assertEqual(tuple(image.size), (4, 2))
        self.assertIsNotNone(image.packed_file)
        self.assertEqual(image.filepath, "")
        environment = next(node for node in world.node_tree.nodes if node.type == "TEX_ENVIRONMENT")
        self.assertEqual(environment.projection, "EQUIRECTANGULAR")
        self.assertEqual(environment.image, image)
        self.assertEqual(len(world.node_tree.links), 2)
        self.assertTrue(receipt.restore())
        self.assertFalse(receipt.restore())
        self.assert_original()
        self.assertNotIn(world, tuple(bpy.data.worlds))
        self.assertNotIn(image, tuple(bpy.data.images))

    def test_exr_floating_fixture_is_hdr_capable(self):
        receipt = self.module.apply_world(self.scene, self.fixture(exr=True))
        self.assertTrue(receipt.info.hdr_capable)
        self.assertTrue(receipt._image.is_float)
        self.assertGreater(max(receipt._image.pixels), 1.0)
        self.assertTrue(receipt.restore())
        self.assert_original()

    def test_jpeg_fixture_applies_as_packed_ldr_byte_image(self):
        path = self.fixture(jpeg=True, width=8, height=4)
        expected = self.download_receipt(path)
        receipt = self.module.apply_world(
            self.scene, path, expected_receipt=expected, media_type="image/jpeg"
        )
        path.unlink()
        world, image = self.scene.world, receipt._image
        self.assertEqual(receipt.info, self.panorama.PanoramaInfo("JPEG", 8, 4, False))
        self.assertEqual((image.file_format, tuple(image.size)), ("JPEG", (8, 4)))
        self.assertFalse(image.is_float)
        self.assertEqual(image.colorspace_settings.name, "sRGB")
        self.assertEqual(image.filepath, "")
        self.assertEqual(hashlib.sha256(image.packed_file.data).hexdigest(), expected.sha256)
        environment = next(node for node in world.node_tree.nodes if node.type == "TEX_ENVIRONMENT")
        self.assertEqual((environment.projection, environment.image), ("EQUIRECTANGULAR", image))
        self.assertTrue(receipt.restore())
        self.assert_original()
        self.assertNotIn(world, tuple(bpy.data.worlds))
        self.assertNotIn(image, tuple(bpy.data.images))

    def test_nonpanoramic_or_truncated_jpeg_rejected_before_decode(self):
        for size, cut, message in (((4, 4), 0, "2:1"), ((8, 4), 3, "incomplete")):
            path = self.fixture(jpeg=True, width=size[0], height=size[1])
            if cut:
                # libjpeg would conceal this truncated scan; the EOI check rejects it.
                path.write_bytes(path.read_bytes()[:-cut])
            with (
                self.subTest(size=size, cut=cut),
                unittest.mock.patch.object(self.module, "_load_image") as decode,
            ):
                worlds, images = set(bpy.data.worlds), set(bpy.data.images)
                with self.assertRaisesRegex(self.module.PanoramaError, message):
                    self.module.apply_world(self.scene, path)
                decode.assert_not_called()
                self.assertEqual((set(bpy.data.worlds), set(bpy.data.images)), (worlds, images))
                self.assert_original()

    def test_exif_rotated_jpeg_rejected_because_blender_ignores_orientation(self):
        image = bpy.data.images.new("Fixture Gradient", width=8, height=4)
        try:
            image.pixels[:] = [
                value
                for index in range(32)
                for value in ((index % 8) / 7, (index // 8) / 3, 0.25, 1.0)
            ]
            image.file_format = "JPEG"
            plain = Path(self.temp.name) / "plain.jpg"
            image.filepath_raw = str(plain)
            image.save()
        finally:
            bpy.data.images.remove(image)
        rotated = self.write("rotated.jpg", exif_orientation(plain.read_bytes(), 6))
        upright = self.write("upright.jpg", exif_orientation(plain.read_bytes(), 1))
        decoded = []
        for path in (plain, rotated):
            # Blender's own decoder applies stored pixel order whatever the tag says.
            loaded = bpy.data.images.load(str(path), check_existing=False)
            try:
                decoded.append((tuple(loaded.size), tuple(loaded.pixels)))
            finally:
                bpy.data.images.remove(loaded)
        self.assertEqual(decoded[0], decoded[1])
        with unittest.mock.patch.object(self.module, "_load_image") as decode:
            with self.assertRaisesRegex(self.module.PanoramaError, "EXIF-rotated or mirrored"):
                self.module.apply_world(self.scene, rotated, media_type="image/jpeg")
            decode.assert_not_called()
        self.assert_original()
        receipt = self.module.apply_world(self.scene, upright, media_type="image/jpeg")
        self.assertEqual((tuple(receipt._image.size), tuple(receipt._image.pixels)), decoded[0])
        self.assertTrue(receipt.restore())
        self.assert_original()

    def test_progressive_jpeg_fixture_decodes_natively(self):
        data = PROGRESSIVE_JPEG.read_bytes()
        self.assertIn(b"\xff\xc2", data[: data.index(b"\xff\xda")])
        self.assertEqual(data.count(b"\xff\xda"), 10)
        path = self.write("progressive.jpg", data)
        expected = self.download_receipt(path)
        receipt = self.module.apply_world(
            self.scene, path, expected_receipt=expected, media_type="image/jpeg"
        )
        image = receipt._image
        self.assertEqual(receipt.info, self.panorama.PanoramaInfo("JPEG", 32, 16, False))
        self.assertEqual(
            (image.file_format, image.is_float, image.colorspace_settings.name),
            ("JPEG", False, "sRGB"),
        )
        self.assertEqual(hashlib.sha256(image.packed_file.data).hexdigest(), expected.sha256)
        pixels = tuple(image.pixels)
        # Blender rows start at the bottom: blue and yellow below, red and green above.
        corners = {
            (0, 0): (40, 40, 200),
            (31, 0): (200, 200, 40),
            (0, 15): (200, 40, 40),
            (31, 15): (40, 200, 40),
        }
        for (x, y), color in corners.items():
            index = (y * 32 + x) * 4
            for actual, wanted in zip(pixels[index : index + 3], color, strict=True):
                self.assertAlmostEqual(actual, wanted / 255, delta=0.03)
        self.assertTrue(receipt.restore())
        self.assert_original()

    def test_extended_sequential_jpeg_decodes_like_its_baseline_twin(self):
        baseline = self.fixture(jpeg=True, width=8, height=4)
        data = baseline.read_bytes()
        frame = data.index(b"\xff\xc0")
        self.assertLess(frame, data.index(b"\xff\xda"))
        # A baseline frame is a valid extended-sequential (SOF1) Huffman frame.
        extended = self.write("extended.jpg", data[:frame] + b"\xff\xc1" + data[frame + 2 :])
        pixels = []
        for path in (baseline, extended):
            receipt = self.module.apply_world(self.scene, path, media_type="image/jpeg")
            self.assertEqual(receipt._image.colorspace_settings.name, "sRGB")
            pixels.append(tuple(receipt._image.pixels))
            self.assertTrue(receipt.restore())
        self.assertEqual(pixels[0], pixels[1])
        self.assert_original()

    def test_progressive_scan_flood_rejected_before_blender_decodes(self):
        data = PROGRESSIVE_JPEG.read_bytes()
        start = data.index(b"\xff\xda")
        header = data[start : start + 2 + struct.unpack_from(">H", data, start + 2)[0]]
        # About 15 bytes per scan; each would make libjpeg revisit every block.
        flood = (header + b"\x00") * self.panorama.MAX_JPEG_SCANS
        path = self.write("flood.jpg", data[:-2] + flood + b"\xff\xd9")
        with unittest.mock.patch.object(self.module, "_load_image") as decode:
            with self.assertRaisesRegex(self.module.PanoramaError, "scan limit"):
                self.module.apply_world(self.scene, path, media_type="image/jpeg")
            decode.assert_not_called()
        self.assert_original()

    def test_comment_flood_after_the_first_scan_rejected_before_blender_decodes(self):
        data = PROGRESSIVE_JPEG.read_bytes()
        segments = len(re.findall(rb"\xff[^\x00\xd0-\xd7\xff]", data)) - 2  # SOI and EOI
        second_scan = data.index(b"\xff\xda", data.index(b"\xff\xda") + 2)
        comment = b"\xff\xfe\x00\x02"
        # Blender keeps JPEG comments and libjpeg walks its saved-marker list to
        # append each one, so 160,000 of them would stall the main thread.
        flood = comment * 160_000
        for name, flooded in (
            ("after.jpg", data[:-2] + flood + data[-2:]),
            ("between.jpg", data[:second_scan] + flood + data[second_scan:]),
        ):
            path = self.write(name, flooded)
            with (
                self.subTest(name=name),
                unittest.mock.patch.object(self.module, "_load_image") as decode,
            ):
                with self.assertRaisesRegex(self.module.PanoramaError, "segment limit"):
                    self.module.apply_world(self.scene, path, media_type="image/jpeg")
                decode.assert_not_called()
            self.assert_original()
        # Up to the shared segment budget, Blender still decodes the same pixels.
        room = self.panorama.MAX_JPEG_SEGMENTS - segments
        pixels = []
        for count in (0, room):
            flooded = data[:second_scan] + comment * count + data[second_scan:]
            path = self.write(f"comments-{count}.jpg", flooded)
            receipt = self.module.apply_world(self.scene, path, media_type="image/jpeg")
            pixels.append(tuple(receipt._image.pixels))
            self.assertTrue(receipt.restore())
        self.assertEqual(pixels[0], pixels[1])
        flooded = data[:second_scan] + comment * (room + 1) + data[second_scan:]
        with self.assertRaisesRegex(self.module.PanoramaError, "segment limit"):
            self.module.apply_world(self.scene, self.write("over.jpg", flooded))
        self.assert_original()

    def test_aces_ap0_exr_uses_aces2065_1_and_restore_guards_colorspace(self):
        self.assertIn("ACES2065-1", colorspaces())
        path = self.write("aces.exr", scanline_exr(8, 4, ACES_AP0))
        expected = self.download_receipt(path)
        receipt = self.module.apply_world(
            self.scene, path, expected_receipt=expected, media_type="image/aces"
        )
        world, image = self.scene.world, receipt._image
        self.assertEqual(receipt.info.chromaticities, "aces_ap0")
        self.assertTrue(receipt.info.hdr_capable and image.is_float)
        self.assertEqual(image.colorspace_settings.name, "ACES2065-1")
        # AP0 red converts to a different scene-linear Rec.709 value than raw 4.0.
        self.assertNotAlmostEqual(image.pixels[0], 4.0, delta=0.5)
        self.assertEqual(hashlib.sha256(image.packed_file.data).hexdigest(), expected.sha256)
        image.colorspace_settings.name = "Linear Rec.709"
        with self.assertRaises(self.module.WorldApplicationError):
            receipt.restore()
        self.assertEqual(self.scene.world, world)
        image.colorspace_settings.name = "ACES2065-1"
        self.assertTrue(receipt.restore())
        self.assert_original()

    def test_rec709_and_undeclared_exr_keep_blender_linear_default(self):
        for primaries in (None, REC709):
            path = self.write("linear.exr", scanline_exr(8, 4, primaries))
            with self.subTest(primaries=primaries):
                receipt = self.module.apply_world(self.scene, path, media_type="image/x-exr")
                image = receipt._image
                self.assertEqual(image.colorspace_settings.name, "Linear Rec.709")
                self.assertAlmostEqual(image.pixels[0], 4.0, places=4)
                self.assertTrue(receipt.restore())
                self.assert_original()

    def test_other_declared_primaries_rejected_before_decode(self):
        path = self.write("ap1.exr", scanline_exr(8, 4, ACES_AP1))
        with unittest.mock.patch.object(self.module, "_load_image") as decode:
            with self.assertRaisesRegex(self.module.PanoramaError, "Rec.709 or ACES AP0"):
                self.module.apply_world(self.scene, path, media_type="image/aces")
            decode.assert_not_called()
        self.assert_original()

    def test_aces_container_flag_or_interop_id_selects_aces2065_1(self):
        for name, extra in (
            ("flag", container_flag(1)),
            ("interop", interop(b"lin_ap0_scene")),
        ):
            path = self.write(f"{name}.exr", scanline_exr(8, 4, extra=extra))
            with self.subTest(name):
                receipt = self.module.apply_world(self.scene, path, media_type="image/aces")
                image = receipt._image
                self.assertEqual(receipt.info.chromaticities, "aces_ap0")
                self.assertEqual(image.colorspace_settings.name, "ACES2065-1")
                self.assertNotAlmostEqual(image.pixels[0], 4.0, delta=0.5)
                self.assertTrue(receipt.restore())
                self.assert_original()

    def blender_colorspace(self, path):
        loaded = bpy.data.images.load(str(path), check_existing=False)
        try:
            return loaded.colorspace_settings.name
        finally:
            bpy.data.images.remove(loaded)

    def test_conflicting_color_declarations_rejected_before_decode(self):
        # Blender itself selects ACES2065-1 for the flag beside Rec.709 primaries.
        path = self.write("conflict.exr", scanline_exr(8, 4, REC709, extra=container_flag(1)))
        self.assertEqual(self.blender_colorspace(path), "ACES2065-1")
        with unittest.mock.patch.object(self.module, "_load_image") as decode:
            with self.assertRaisesRegex(self.module.PanoramaError, "declarations conflict"):
                self.module.apply_world(self.scene, path, media_type="image/aces")
            decode.assert_not_called()
        self.assert_original()

    def test_interop_id_conflicting_with_declared_primaries_fails_after_decode(self):
        # The preflight leaves lin_ap1_scene unclassified; Blender selects ACEScg.
        path = self.write("ap1-id.exr", scanline_exr(8, 4, REC709, extra=interop(b"lin_ap1_scene")))
        self.assertEqual(self.blender_colorspace(path), "ACEScg")
        worlds, images = set(bpy.data.worlds), set(bpy.data.images)
        with self.assertRaisesRegex(self.module.WorldApplicationError, "ACEScg"):
            self.module.apply_world(self.scene, path, media_type="image/aces")
        self.assertEqual((set(bpy.data.worlds), set(bpy.data.images)), (worlds, images))
        self.assert_original()

    def test_interop_id_without_other_declarations_keeps_blender_colorspace(self):
        cases = (
            # Blender converts this AP1 declaration itself.
            (scanline_exr(8, 4, extra=interop(b"lin_ap1_scene")), None, "ACEScg"),
            # Rec.709 primaries with the sRGB transfer another writer may declare.
            (
                scanline_exr(8, 4, REC709, extra=interop(b"srgb_rec709_display")),
                "rec709",
                "sRGB",
            ),
        )
        for data, declared, colorspace in cases:
            path = self.write("interop.exr", data)
            with self.subTest(colorspace=colorspace):
                receipt = self.module.apply_world(self.scene, path, media_type="image/x-exr")
                image = receipt._image
                self.assertEqual(receipt.info.chromaticities, declared)
                self.assertEqual(image.colorspace_settings.name, colorspace)
                self.assertNotAlmostEqual(image.pixels[0], 4.0, delta=0.5)
                self.assertTrue(receipt.restore())
                self.assert_original()

    def test_blender_written_exr_keeps_blender_colorspace_choice(self):
        # Blender 5.0-5.2 label their own Image.save EXR output with a
        # colorInteropID that the preflight does not classify.
        path = self.fixture(exr=True, width=8, height=4)
        self.assertIn(b"colorInteropID", path.read_bytes()[:4096])
        receipt = self.module.apply_world(self.scene, path, media_type="image/x-exr")
        self.assertIsNone(receipt.info.chromaticities)
        self.assertEqual(receipt._image.colorspace_settings.name, self.blender_colorspace(path))
        self.assertGreater(max(receipt._image.pixels), 1.0)
        self.assertTrue(receipt.restore())
        self.assert_original()

    def test_unexpected_decoded_colorspace_fails_without_leaking_world_or_image(self):
        # Stand-ins for metadata the preflight cannot classify or a configuration
        # naming color spaces differently: application fails closed.
        path = self.write("aces.exr", scanline_exr(8, 4, ACES_AP0))
        inspect = self.module.inspect_panorama

        def misclassified(data):
            return replace(inspect(data), chromaticities="rec709")

        for patcher in (
            unittest.mock.patch.object(self.module, "inspect_panorama", misclassified),
            unittest.mock.patch.dict(
                self.module._COLORSPACES, {"aces_ap0": frozenset({"Fixture Space"})}
            ),
        ):
            worlds, images = set(bpy.data.worlds), set(bpy.data.images)
            with self.subTest(patcher=patcher), patcher:
                with self.assertRaisesRegex(self.module.WorldApplicationError, "ACES2065-1"):
                    self.module.apply_world(self.scene, path)
            self.assertEqual((set(bpy.data.worlds), set(bpy.data.images)), (worlds, images))
            self.assert_original()

    def test_saved_media_type_must_name_the_actual_container(self):
        path = self.fixture()
        for media_type in ("image/jpeg", "image/aces", "image/x-exr"):
            with (
                self.subTest(media_type=media_type),
                unittest.mock.patch.object(self.module, "_load_image") as decode,
            ):
                with self.assertRaisesRegex(self.module.WorldApplicationError, "media type"):
                    self.module.apply_world(self.scene, path, media_type=media_type)
                decode.assert_not_called()
        for media_type in ("image/webp", "image/vnd.radiance", "", 3):
            with (
                self.subTest(media_type=media_type),
                unittest.mock.patch.object(self.module.os, "open") as opened,
            ):
                with self.assertRaisesRegex(self.module.WorldApplicationError, "PNG, JPEG"):
                    self.module.apply_world(self.scene, path, media_type=media_type)
                opened.assert_not_called()
        self.assert_original()
        receipt = self.module.apply_world(self.scene, path, media_type="image/png")
        self.assertTrue(receipt.restore())
        self.assert_original()

    def download_receipt(self, path):
        data = path.read_bytes()
        return self.module.DownloadedResult(path.name, len(data), hashlib.sha256(data).hexdigest())

    def test_saved_download_receipt_accepts_png_and_exr_snapshots(self):
        for exr in (False, True):
            with self.subTest(exr=exr):
                path = self.fixture(exr=exr)
                expected = self.download_receipt(path)
                handle = self.module.apply_world(self.scene, path, expected_receipt=expected)
                self.assertEqual(
                    hashlib.sha256(handle._image.packed_file.data).hexdigest(), expected.sha256
                )
                self.assertTrue(handle.restore())
                self.assert_original()

    def test_receipt_mismatch_rejects_before_decode_and_preserves_scene(self):
        path = self.fixture()
        expected = self.download_receipt(path)
        for changed in (
            replace(expected, name="another.png"),
            replace(expected, size=expected.size + 1),
            replace(expected, sha256="0" * 64),
        ):
            with (
                self.subTest(receipt=changed),
                unittest.mock.patch.object(self.module, "_load_image") as decode,
            ):
                worlds, images = set(bpy.data.worlds), set(bpy.data.images)
                with self.assertRaisesRegex(self.module.WorldApplicationError, "download receipt"):
                    self.module.apply_world(self.scene, path, expected_receipt=changed)
                decode.assert_not_called()
                self.assertEqual(set(bpy.data.worlds), worlds)
                self.assertEqual(set(bpy.data.images), images)
                self.assert_original()

    def test_changed_download_with_same_length_is_rejected_before_container_parsing(self):
        path = self.fixture()
        expected = self.download_receipt(path)
        data = bytearray(path.read_bytes())
        data[-1] ^= 1
        path.write_bytes(data)
        with unittest.mock.patch.object(self.module, "inspect_panorama") as inspect:
            with self.assertRaisesRegex(self.module.WorldApplicationError, "download receipt"):
                self.module.apply_world(self.scene, path, expected_receipt=expected)
            inspect.assert_not_called()
        self.assert_original()

    def test_replacement_after_verification_cannot_change_decoded_snapshot(self):
        path = self.fixture()
        expected = self.download_receipt(path)
        load = self.module._load_image

        def replace_source(data, info):
            path.write_bytes(b"changed after the verified snapshot")
            return load(data, info)

        with unittest.mock.patch.object(self.module, "_load_image", side_effect=replace_source):
            handle = self.module.apply_world(self.scene, path, expected_receipt=expected)
        self.assertNotEqual(hashlib.sha256(path.read_bytes()).hexdigest(), expected.sha256)
        self.assertEqual(
            hashlib.sha256(handle._image.packed_file.data).hexdigest(), expected.sha256
        )
        self.assertTrue(handle.restore())
        self.assert_original()

    def test_invalid_receipt_rejected_before_source_access(self):
        for value in (True, {}, object()):
            with (
                self.subTest(value=type(value)),
                unittest.mock.patch.object(self.module.os, "open") as opened,
            ):
                with self.assertRaisesRegex(
                    self.module.WorldApplicationError, "downloaded-result receipt"
                ):
                    self.module.apply_world(self.scene, "unused.png", expected_receipt=value)
                opened.assert_not_called()
        self.assert_original()

    def test_oversized_snapshot_reports_byte_limit_before_receipt_mismatch(self):
        path = self.fixture()
        expected = self.download_receipt(path)
        before = set(bpy.data.worlds), set(bpy.data.images)
        for receipt in (expected, None):
            with (
                self.subTest(receipt=receipt),
                unittest.mock.patch.object(self.module, "MAX_FILE_BYTES", 32),
                unittest.mock.patch.object(self.module, "inspect_panorama") as inspect,
                unittest.mock.patch.object(self.module, "_load_image") as decode,
            ):
                with self.assertRaisesRegex(self.module.PanoramaError, "byte limit"):
                    self.module.apply_world(self.scene, path, expected_receipt=receipt)
                inspect.assert_not_called()
                decode.assert_not_called()
        self.assertEqual((set(bpy.data.worlds), set(bpy.data.images)), before)
        self.assert_original()

    def test_actual_container_wins_over_filename(self):
        path = self.fixture()
        renamed = path.with_suffix(".exr")
        path.rename(renamed)
        receipt = self.module.apply_world(self.scene, renamed)
        self.assertEqual(receipt.info.file_format, "PNG")
        receipt.restore()

    def test_scene_without_original_world_restores_none(self):
        self.scene.world = None
        receipt = self.module.apply_world(self.scene, self.fixture())
        self.assertTrue(receipt.restore())
        self.assertIsNone(self.scene.world)

    def test_new_world_shared_with_another_scene_is_preserved(self):
        receipt = self.module.apply_world(self.scene, self.fixture())
        owned_world, image = self.scene.world, receipt._image
        self.other.world = owned_world
        self.assertTrue(receipt.restore())
        self.assertEqual(self.scene.world, self.original)
        self.assertEqual(self.other.world, owned_world)
        self.assertIn(image, tuple(bpy.data.images))
        self.assertTrue(image.packed_file)

    def test_image_shared_with_material_is_preserved_on_restore(self):
        receipt = self.module.apply_world(self.scene, self.fixture())
        image = receipt._image
        material = bpy.data.materials.new("Fixture Shared Panorama")
        try:
            material.use_nodes = True
            texture = material.node_tree.nodes.new("ShaderNodeTexImage")
            texture.image = image
            self.assertTrue(receipt.restore())
            self.assertEqual(texture.image, image)
            self.assertIsNotNone(image.packed_file)
            self.assert_original()
        finally:
            bpy.data.materials.remove(material)

    def test_manual_world_or_image_edits_refuse_restore(self):
        mutations = (
            # Blender 5 always uses World nodes; use_nodes=False is a no-op.
            lambda world, image: world.node_tree.nodes.clear(),
            lambda world, image: setattr(world, "color", (0.2, 0.3, 0.4)),
            lambda world, image: setattr(
                world.node_tree.nodes.get("Background").inputs["Strength"], "default_value", 2.0
            ),
            lambda world, image: world.node_tree.nodes.new("ShaderNodeMath"),
            lambda world, image: setattr(
                next(
                    node for node in world.node_tree.nodes if node.type == "TEX_ENVIRONMENT"
                ).image_user,
                "frame_offset",
                3,
            ),
            lambda world, image: setattr(image.colorspace_settings, "name", "Non-Color"),
            lambda world, image: image.pixels.__setitem__(0, 0.75),
        )
        for index, mutate in enumerate(mutations):
            with self.subTest(mutation=index):
                self.scene.world = self.original
                receipt = self.module.apply_world(self.scene, self.fixture())
                world, image = self.scene.world, receipt._image
                mutate(world, image)
                with self.assertRaises(self.module.WorldApplicationError):
                    receipt.restore()
                self.assertEqual(self.scene.world, world)
                self.assertIn(image, tuple(bpy.data.images))

    def test_readonly_ramp_pointer_still_guards_edited_elements(self):
        receipt = self.module.apply_world(self.scene, self.fixture())
        world = self.scene.world
        environment = next(node for node in world.node_tree.nodes if node.type == "TEX_ENVIRONMENT")
        environment.color_mapping.color_ramp.elements[0].color = (1.0, 0.0, 0.0, 1.0)
        with self.assertRaises(self.module.WorldApplicationError):
            receipt.restore()
        self.assertEqual(self.scene.world, world)

    def test_fingerprint_does_not_copy_pixel_buffer_into_python_floats(self):
        array_type = type(
            self.original.node_tree.nodes.get("Background").inputs["Color"].default_value
        )
        original = self.module._value

        def bounded(value):
            if isinstance(value, array_type) and len(value) > 16:
                raise AssertionError("Fingerprint copied the image pixel buffer")
            return original(value)

        path = self.fixture()
        with unittest.mock.patch.object(self.module, "_value", side_effect=bounded):
            receipt = self.module.apply_world(self.scene, path)
            self.assertTrue(receipt.restore())
        self.assert_original()

    def test_repacked_pixel_edits_refuse_restore(self):
        receipt = self.module.apply_world(self.scene, self.fixture())
        world, image = self.scene.world, receipt._image
        image.pixels[0] = 0.875
        image.pack()
        with self.assertRaises(self.module.WorldApplicationError):
            receipt.restore()
        self.assertEqual(self.scene.world, world)
        self.assertIn(image, tuple(bpy.data.images))

    def test_replaced_world_is_not_overwritten(self):
        receipt = self.module.apply_world(self.scene, self.fixture())
        self.scene.world = self.original
        with self.assertRaises(self.module.WorldApplicationError):
            receipt.restore()
        self.assert_original()

    def test_removed_original_world_refuses_restore(self):
        receipt = self.module.apply_world(self.scene, self.fixture())
        owned_world = self.scene.world
        bpy.data.worlds.remove(self.original)
        with self.assertRaises(self.module.WorldApplicationError):
            receipt.restore()
        self.assertEqual(self.scene.world, owned_world)

    def test_removed_scene_invalidates_handle(self):
        receipt = self.module.apply_world(self.scene, self.fixture())
        bpy.data.scenes.remove(self.scene)
        with self.assertRaises(self.module.WorldApplicationError):
            receipt.restore()

    def test_worker_rejected_before_blender_access(self):
        errors = []

        def run():
            try:
                self.module.apply_world(None, "unused")
            except Exception as exc:
                errors.append(exc)

        worker = threading.Thread(target=run)
        worker.start()
        worker.join(3)
        self.assertFalse(worker.is_alive())
        self.assertIsInstance(errors[0], self.module.WorldApplicationError)
        self.assert_original()

    def test_missing_corrupt_nonpanoramic_files_preserve_original(self):
        invalid = Path(self.temp.name) / "corrupt.png"
        invalid.write_bytes(b"not an image")
        for path in (invalid, invalid.with_name("missing.png"), self.fixture(width=4, height=4)):
            with (
                self.subTest(path=path),
                self.assertRaises((self.module.WorldApplicationError, self.module.PanoramaError)),
            ):
                self.module.apply_world(self.scene, path)
            self.assert_original()

    def test_invalid_png_pixel_stream_fails_after_header_preflight(self):
        def chunk(kind, payload=b""):
            body = kind + payload
            return struct.pack(">I", len(payload)) + body + struct.pack(">I", zlib.crc32(body))

        data = (
            b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", 4, 2, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", b"invalid compressed pixels")
            + chunk(b"IEND")
        )
        self.assertEqual(self.module.inspect_panorama(data).width, 4)
        path = Path(self.temp.name) / "bad-pixels.png"
        path.write_bytes(data)
        worlds, images = set(bpy.data.worlds), set(bpy.data.images)
        with self.assertRaises(self.module.WorldApplicationError):
            self.module.apply_world(self.scene, path)
        self.assertEqual(set(bpy.data.worlds), worlds)
        self.assertEqual(set(bpy.data.images), images)
        self.assert_original()

    def test_truncated_exr_cannot_publish_world_or_leak_image(self):
        path = self.fixture(exr=True)
        path.write_bytes(path.read_bytes()[:-20])
        worlds, images = set(bpy.data.worlds), set(bpy.data.images)
        with self.assertRaises((self.module.WorldApplicationError, self.module.PanoramaError)):
            self.module.apply_world(self.scene, path)
        self.assertEqual(set(bpy.data.worlds), worlds)
        self.assertEqual(set(bpy.data.images), images)
        self.assert_original()

    def test_excess_png_chunks_rejected_before_decode_without_scene_changes(self):
        panorama = submodule("core.scene.panorama")
        path = self.fixture()
        data = path.read_bytes()
        # Insert legal private ancillary chunks after IHDR in a real decoded fixture.
        kind = b"vpAg"
        chunk = struct.pack(">I", 0) + kind + struct.pack(">I", zlib.crc32(kind))
        path.write_bytes(data[:33] + chunk * panorama.MAX_PNG_CHUNKS + data[33:])
        worlds, images = set(bpy.data.worlds), set(bpy.data.images)
        with unittest.mock.patch.object(self.module, "_load_image") as decode:
            with self.assertRaisesRegex(self.module.PanoramaError, "chunk limit"):
                self.module.apply_world(self.scene, path)
            decode.assert_not_called()
        self.assertEqual(set(bpy.data.worlds), worlds)
        self.assertEqual(set(bpy.data.images), images)
        self.assert_original()

    @unittest.skipUnless(hasattr(os, "mkfifo"), "POSIX special-file fixture")
    def test_fifo_rejected_without_waiting_for_a_writer(self):
        path = Path(self.temp.name) / "fifo.png"
        os.mkfifo(path)
        with self.assertRaises(self.module.WorldApplicationError):
            self.module.apply_world(self.scene, path)
        self.assert_original()

    def test_failure_after_decode_cleans_owned_data_and_preserves_original(self):
        path = self.fixture()
        worlds, images = set(bpy.data.worlds), set(bpy.data.images)
        with unittest.mock.patch.object(
            self.module, "_fingerprint", side_effect=RuntimeError("fixture failure")
        ):
            with self.assertRaises(self.module.WorldApplicationError):
                self.module.apply_world(self.scene, path)
        self.assertEqual(set(bpy.data.worlds), worlds)
        self.assertEqual(set(bpy.data.images), images)
        self.assert_original()
