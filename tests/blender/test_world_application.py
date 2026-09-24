# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Offline generated PNG/EXR fixtures applied by the installed extension."""

import hashlib
import os
import struct
import tempfile
import threading
import unittest.mock
import zlib
from dataclasses import replace
from pathlib import Path

import bpy
from helpers import submodule


class WorldApplicationTests(unittest.TestCase):
    def setUp(self):
        self.module = submodule("blender.world_application")
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

    def fixture(self, *, exr=False, width=4, height=2):
        image = bpy.data.images.new("Fixture Pixels", width=width, height=height, float_buffer=exr)
        try:
            image.pixels[:] = [4.0 if exr else 0.5, 0.25, 0.125, 1.0] * (width * height)
            image.file_format = "OPEN_EXR" if exr else "PNG"
            path = Path(self.temp.name) / ("fixture.exr" if exr else "fixture.png")
            image.filepath_raw = str(path)
            image.save()
            return path
        finally:
            bpy.data.images.remove(image)

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
