# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Installed temporary preview decoding outside the open blend file.

Images are generated at test time and decode inside ``bpy.data.temp_data()``.
Besides sizes, display values, the PNG output and sanitized refusals, the tests
check that the open file never sees a decode: its images, scenes and dirty
flag stay unchanged, a dependency handler sees no ID update, and a job session
origin captured before decoding stays current. A control loads and removes the
same image in ``bpy.data`` and shows that this invalidates the origin. Failed
decodes must not leave a reference into the freed temporary block in their
error's context or in the locals of the helper frames on its traceback.
"""

import struct
import tempfile
import threading
import unittest
import zlib
from pathlib import Path, PurePath, PureWindowsPath
from unittest.mock import patch

import bpy
from helpers import exr_attribute, scanline_exr, submodule

# Linear 4.0, 0.5 and 0.25 as clamped sRGB display values.
DISPLAY = (1.0, 0.7354, 0.5371, 1.0)


def png(width, height, pixel=b"\x40\x80\xc0\xff"):
    """An 8-bit RGBA PNG of one color."""
    rows = b"".join(b"\x00" + pixel * width for _ in range(height))

    def chunk(kind, data):
        return (
            struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
        )

    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(rows))
        + chunk(b"IEND", b"")
    )


def half_exr(width, height, value=(4.0, 0.5, 0.25), alpha=None):
    """Uncompressed HALF B/G/R scanline OpenEXR, the 16-bit counterpart of scanline_exr.

    With ``alpha``, the file also holds an A channel; OpenEXR color values are
    premultiplied by it.
    """
    names = (b"B", b"G", b"R") if alpha is None else (b"A", b"B", b"G", b"R")
    channels = b"".join(
        name + b"\0" + struct.pack("<iBBBBii", 1, 0, 0, 0, 0, 1, 1) for name in names
    )
    window = struct.pack("<iiii", 0, 0, width - 1, height - 1)
    header = (
        b"\x76\x2f\x31\x01"
        + struct.pack("<I", 2)
        + exr_attribute(b"channels", b"chlist", channels + b"\0")
        + exr_attribute(b"compression", b"compression", b"\0")
        + exr_attribute(b"dataWindow", b"box2i", window)
        + exr_attribute(b"displayWindow", b"box2i", window)
        + exr_attribute(b"lineOrder", b"lineOrder", b"\0")
        + exr_attribute(b"pixelAspectRatio", b"float", struct.pack("<f", 1.0))
        + exr_attribute(b"screenWindowCenter", b"v2f", bytes(8))
        + exr_attribute(b"screenWindowWidth", b"float", struct.pack("<f", 1.0))
        + b"\0"
    )
    red, green, blue = value
    samples = (blue, green, red) if alpha is None else (alpha, blue, green, red)
    line = b"".join(struct.pack("<e", channel) * width for channel in samples)
    start = len(header) + height * 8
    table = b"".join(struct.pack("<Q", start + row * (len(line) + 8)) for row in range(height))
    blocks = b"".join(struct.pack("<ii", row, len(line)) + line for row in range(height))
    return header + table + blocks


def accept(width, height):
    return True


def open_file_state():
    """What a decode must leave unchanged in the open file."""
    return (
        len(bpy.data.images),
        tuple(image.name for image in bpy.data.images),
        tuple(scene.name for scene in bpy.data.scenes),
        bpy.data.is_dirty,
    )


class PreviewDecodeTests(unittest.TestCase):
    def setUp(self):
        self.module = submodule("blender.preview_decode")
        directory = self.enterContext(
            tempfile.TemporaryDirectory(dir=bpy.utils.resource_path("USER"))
        )
        self.root = Path(directory)
        self.before = open_file_state()

    def tearDown(self):
        self.assertEqual(open_file_state(), self.before)

    def file(self, name, data):
        path = self.root / name
        path.write_bytes(data)
        return path

    def refused(self, *args, **kwargs):
        """The error a decode raises, with its traceback intact.

        assertRaises clears the traceback's frames, which would hide the locals
        a leaked reference lives in.
        """
        try:
            self.module.decode(*args, **kwargs)
        except self.module.PreviewDecodeError as error:
            return error
        raise self.failureException("The decode did not raise PreviewDecodeError")

    def assertNoBlockReferences(self, error):
        """No reference into the freed temporary block survives on ``error``."""
        self.assertIsNone(error.__context__)
        self.assertIsNone(error.__cause__)
        frames, traceback = [], error.__traceback__
        while traceback is not None:
            # Only the helper's frames: a test frame may hold the open file's data.
            if traceback.tb_frame.f_globals is vars(self.module):
                frames.append(traceback.tb_frame)
            traceback = traceback.tb_next
        self.assertTrue(frames)
        for frame in frames:
            for name, value in frame.f_locals.items():
                # isinstance reads the Python type only; the message never reads
                # the value, whose repr would read freed memory.
                with self.subTest(frame=frame.f_code.co_name, local=name):
                    self.assertFalse(
                        isinstance(value, (bpy.types.bpy_struct, bpy.types.bpy_prop_collection)),
                        "A traceback local refers to Blender data",
                    )

    def assertPixels(self, pixels, size, expected, places=3):
        self.assertEqual(len(pixels), size[0] * size[1] * 4)
        for index in (0, len(pixels) // 2, len(pixels) - 4):
            for value, wanted in zip(pixels[index : index + 4], expected, strict=True):
                self.assertAlmostEqual(value, wanted, places=places)

    def test_fit_scales_down_to_the_edge_without_upscaling(self):
        fit = self.module.fit
        self.assertEqual(fit(640, 320, 256), (256, 128))
        self.assertEqual(fit(320, 640, 256), (128, 256))
        self.assertEqual(fit(100, 50, 256), (100, 50))
        self.assertEqual(fit(256, 256, 256), (256, 256))
        # A thin image keeps at least one pixel on its short side.
        self.assertEqual(fit(3, 1000, 256), (1, 256))

    def test_linear_values_encode_to_clamped_srgb(self):
        encode = self.module._encode
        self.assertEqual(encode(0.0), 0.0)
        self.assertEqual(encode(-1.0), 0.0)
        self.assertEqual(encode(float("nan")), 0.0)
        self.assertEqual(encode(1.0), 1.0)
        self.assertEqual(encode(4.0), 1.0)
        self.assertAlmostEqual(encode(0.002), 0.002 * 12.92)
        self.assertAlmostEqual(encode(0.5), 0.7354, places=4)
        self.assertAlmostEqual(encode(0.25), 0.5371, places=4)

    def test_png_decodes_to_the_fitted_size_with_its_display_values(self):
        size, pixels = self.module.decode(self.file("result.png", png(640, 320)), 256, accept)
        self.assertEqual(size, (256, 128))
        # 8-bit files already hold display values: 0x40, 0x80 and 0xc0.
        self.assertPixels(pixels, size, (64 / 255, 128 / 255, 192 / 255, 1.0))

    def test_small_png_keeps_its_size(self):
        size, pixels = self.module.decode(self.file("small.png", png(40, 20)), 256, accept)
        self.assertEqual(size, (40, 20))
        self.assertPixels(pixels, size, (64 / 255, 128 / 255, 192 / 255, 1.0))

    def test_half_and_float_openexr_decode_to_srgb_display_values(self):
        for name, data in (
            ("half.exr", half_exr(512, 256)),
            ("float.exr", scanline_exr(512, 256, value=(4.0, 0.5, 0.25))),
        ):
            with self.subTest(name):
                size, pixels = self.module.decode(self.file(name, data), 64, accept)
                self.assertEqual(size, (64, 32))
                # Linear values are encoded for display; 4.0 clamps to 1.0.
                self.assertPixels(pixels, size, DISPLAY)

    def test_semi_transparent_float_pixels_decode_to_straight_display_values(self):
        # Premultiplied linear 0.5, 0.25 and 0.125 at alpha 0.5 are straight 1.0,
        # 0.5 and 0.25, the same display values as 8-bit files and the PNG output.
        expected = (*DISPLAY[:3], 0.5)
        path = self.file("alpha.exr", half_exr(64, 32, value=(0.5, 0.25, 0.125), alpha=0.5))
        size, pixels = self.module.decode(path, 64, accept)
        self.assertEqual(size, (64, 32))
        self.assertPixels(pixels, size, expected)
        output = self.root / "alpha.png"
        self.assertEqual(self.module.decode(path, 64, accept, output=output), (size, None))
        size, pixels = self.module.decode(output, 64, accept)
        self.assertPixels(pixels, size, expected, places=2)

    def test_output_writes_an_eight_bit_rgba_png(self):
        output = self.root / "preview.png"
        size, pixels = self.module.decode(
            self.file("float.exr", scanline_exr(512, 256, value=(4.0, 0.5, 0.25))),
            64,
            accept,
            output=output,
        )
        self.assertEqual((size, pixels), ((64, 32), None))
        data = output.read_bytes()
        self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(data[12:16], b"IHDR")
        # Width, height, 8 bits per channel and color type 6 (RGBA).
        self.assertEqual(struct.unpack(">IIBB", data[16:26]), (64, 32, 8, 6))
        # The Standard view transform wrote the same display values.
        size, pixels = self.module.decode(output, 64, accept)
        self.assertEqual(size, (64, 32))
        self.assertPixels(pixels, size, DISPLAY, places=2)

    def test_limit_sees_the_loaded_size_and_its_refusal_raises(self):
        path = self.file("result.png", png(640, 320))
        output = self.root / "refused.png"
        seen = []

        def refuse(width, height):
            seen.append((width, height))
            return False

        def fail(width, height):
            raise ValueError(f"{path} is too large")

        for limit in (refuse, fail):
            for target in (None, output):
                with self.subTest(limit=limit.__name__, output=target is not None):
                    error = self.refused(path, 256, limit, output=target)
                    self.assertEqual(str(error), "Blender could not decode this preview")
                    self.assertNoBlockReferences(error)
                    self.assertFalse(output.exists())
        self.assertEqual(seen, [(640, 320), (640, 320)])

    def test_unreadable_files_raise_a_sanitized_error(self):
        corrupt = png(64, 32)
        start = corrupt.index(b"IDAT") + 4
        cases = (
            ("text.png", b"not an image"),
            ("empty.exr", b""),
            ("corrupt.png", corrupt[:start] + b"\x00" * 32 + corrupt[start + 32 :]),
        )
        for name, data in cases:
            with self.subTest(name):
                path = self.file(name, data)
                for output in (None, self.root / "never.png"):
                    error = self.refused(path, 64, accept, output=output)
                    message = str(error)
                    self.assertEqual(message, "Blender could not decode this preview")
                    self.assertNotIn(name, message)
                    self.assertNoBlockReferences(error)
        self.assertFalse((self.root / "never.png").exists())
        for output in (None, self.root / "never.png"):
            error = self.refused(self.root / "missing.png", 64, accept, output=output)
            self.assertNoBlockReferences(error)
        self.assertFalse((self.root / "never.png").exists())

    def test_string_paths_pass_the_blender_path_check_as_path_objects(self):
        local_render = submodule("core.jobs.local_render")
        path = self.file("result.png", png(64, 32))
        output = self.root / "preview.png"
        with patch.object(self.module, "blender_path", wraps=local_render.blender_path) as checked:
            result = self.module.decode(str(path), 16, accept, output=str(output))
        self.assertEqual(result, ((16, 8), None))
        self.assertTrue(output.exists())
        # On Windows, only path objects receive the ordinary path length check.
        self.assertEqual([call.args for call in checked.call_args_list], [(path,), (output,)])
        for call in checked.call_args_list:
            self.assertIsInstance(call.args[0], PurePath)

    def test_paths_blender_cannot_use_raise_a_sanitized_error(self):
        local_render = submodule("core.jobs.local_render")
        path = self.file("result.png", png(8, 8))
        refused = local_render.LocalRenderError(f"Cannot use {path}")
        with patch.object(self.module, "blender_path", side_effect=refused):
            with self.assertRaises(self.module.PreviewDecodeError) as caught:
                self.module.decode(path, 64, accept)
        self.assertEqual(
            str(caught.exception), "Preview paths are too long for Blender on this system"
        )
        # The original error, which names the path here, is not reachable.
        self.assertIsNone(caught.exception.__cause__)
        self.assertIsNone(caught.exception.__context__)

    def test_paths_blender_cannot_encode_raise_a_sanitized_error(self):
        # On Windows the path check encodes paths as UTF-16, which rejects a lone
        # surrogate with UnicodeEncodeError rather than LocalRenderError.
        path = "C:\\previews\\result\udc80.png"
        start = path.index("\udc80")
        refused = UnicodeEncodeError("utf-16-le", path, start, start + 1, "surrogates not allowed")
        cases = (
            # The real check on Windows path objects, on any system.
            ("source", patch.object(self.module, "Path", PureWindowsPath), (path,), {}),
            (
                "output",
                patch.object(self.module, "Path", PureWindowsPath),
                ("C:\\previews\\result.png",),
                {"output": path},
            ),
            ("raised", patch.object(self.module, "blender_path", side_effect=refused), (path,), {}),
        )
        for name, patched, args, kwargs in cases:
            with self.subTest(name), patched:
                with self.assertRaises(self.module.PreviewDecodeError) as caught:
                    self.module.decode(*args, 64, accept, **kwargs)
                message = str(caught.exception)
                self.assertEqual(message, "Blender cannot use these preview paths on this system")
                self.assertNotIn("previews", message)
                # UnicodeEncodeError.object would hold the whole path.
                self.assertIsNone(caught.exception.__cause__)
                self.assertIsNone(caught.exception.__context__)

    def test_decode_refuses_other_threads(self):
        path = self.file("result.png", png(8, 8))
        errors = []

        def run():
            try:
                self.module.decode(path, 64, accept)
            except Exception as error:
                errors.append(error)

        worker = threading.Thread(target=run)
        worker.start()
        worker.join(5)
        self.assertFalse(worker.is_alive())
        (error,) = errors
        self.assertIsInstance(error, RuntimeError)
        self.assertNotIsInstance(error, self.module.PreviewDecodeError)
        self.assertIn("main thread", str(error))


class PreviewDecodeOriginTests(unittest.TestCase):
    """A captured scene origin, which any dependency update invalidates."""

    def setUp(self):
        import httpx

        self.module = submodule("blender.preview_decode")
        self.sessions = submodule("blender.job_session")
        api = submodule("core.api.sdk_adapter")
        storage = submodule("core.jobs.store")
        directory = self.enterContext(
            tempfile.TemporaryDirectory(dir=bpy.utils.resource_path("USER"))
        )
        self.root = Path(directory)
        self.previous = bpy.context.scene
        self.scene = bpy.data.scenes.new("Preview decode fixture")
        bpy.context.window.scene = self.scene
        self.target = bpy.data.objects.new("Preview decode target", None)
        self.scene.collection.objects.link(self.target)
        bpy.context.view_layer.update()
        scope = storage.JobScope("https://fixture.invalid/v1", "fixture-account")
        store = storage.JobStore(self.root / "jobs.sqlite3", scope)
        self.calls = []

        def respond(request):
            # Only the estimate's dry run is expected; nothing is submitted.
            self.calls.append(request)
            if request.url.params.get("dryRun") != "true":
                raise AssertionError("A preview decode test submitted a job")
            return httpx.Response(200, json={"creativeUnitsCost": 1})

        adapter = api.SDKAdapter(
            api.Credentials("key", "secret"),
            online=lambda: True,
            account_id=scope.account_id,
            base_url=scope.service,
            transport=httpx.MockTransport(respond),
        )
        self.addCleanup(adapter.close)
        self.session = self.sessions.JobSession(adapter, store, workers=1)
        self.updates = []
        bpy.app.handlers.depsgraph_update_post.append(self.record)

    def tearDown(self):
        if self.record in bpy.app.handlers.depsgraph_update_post:
            bpy.app.handlers.depsgraph_update_post.remove(self.record)
        self.session.shutdown()
        if self.previous in tuple(bpy.data.scenes):
            bpy.context.window.scene = self.previous
        if self.target in tuple(bpy.data.objects):
            bpy.data.objects.remove(self.target, do_unlink=True)
        if self.scene in tuple(bpy.data.scenes):
            bpy.data.scenes.remove(self.scene)

    def record(self, scene, depsgraph=None):
        # Names only: a reference into a temporary block must not outlive it.
        if depsgraph is None:
            self.updates.append(("<no dependency graph>",))
        else:
            self.updates.append(tuple(update.id.name for update in depsgraph.updates))

    def file(self, name, data):
        path = self.root / name
        path.write_bytes(data)
        return path

    def quote(self):
        """A captured origin and its estimate, as a composer captures them."""
        origin = self.session.capture(self.scene, self.target)
        estimate = self.session._coordinator._adapter.estimate_workflow(
            {"id": "fixture-workflow", "inputs": []}, {}
        )
        return origin, estimate

    def test_decode_reports_no_updates_and_keeps_captured_origins_current(self):
        image = self.file("result.png", png(640, 320))
        exr = self.file("result.exr", scanline_exr(512, 256))
        origin, estimate = self.quote()
        before = open_file_state()
        self.updates.clear()
        self.module.decode(image, 256, accept)
        self.module.decode(exr, 64, accept)
        self.module.decode(image, 64, accept, output=self.root / "preview.png")
        with self.assertRaises(self.module.PreviewDecodeError):
            self.module.decode(self.file("text.png", b"not an image"), 64, accept)
        with self.assertRaises(self.module.PreviewDecodeError):
            self.module.decode(image, 64, lambda width, height: False)
        bpy.context.view_layer.update()
        # Writing the PNG can run the handler, but with no ID updates.
        self.assertEqual([names for names in self.updates if names], [])
        self.assertEqual(open_file_state(), before)
        self.assertTrue(self.session._origins.current(origin))
        self.assertEqual(self.session.capture(self.scene, self.target), origin)
        prepared = self.session.prepare(estimate, origin=origin)
        self.assertEqual(prepared.intent.origin, origin)
        self.assertEqual(len(self.calls), 1)

    def test_main_data_load_and_remove_invalidates_captured_origins(self):
        # The control: the same image through bpy.data, which decode avoids.
        image = self.file("result.png", png(640, 320))
        origin, estimate = self.quote()
        self.updates.clear()
        loaded = bpy.data.images.load(str(image), check_existing=False)
        bpy.data.images.remove(loaded)
        del loaded
        bpy.context.view_layer.update()
        updated = {name for names in self.updates for name in names}
        self.assertIn(self.scene.name, updated)
        self.assertIn(self.target.name, updated)
        self.assertFalse(self.session._origins.current(origin))
        with self.assertRaises(self.sessions.OriginUnavailable):
            self.session.prepare(estimate, origin=origin)


if __name__ == "__main__":
    unittest.main()
