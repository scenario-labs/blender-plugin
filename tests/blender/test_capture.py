# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
import random
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import bpy
from helpers import FRAME_NOTIFYING, recording_context, reset_scene, submodule


def _is_video(render):
    settings = render.image_settings
    return getattr(settings, "media_type", "") == "VIDEO" or settings.file_format == "FFMPEG"


class CaptureTests(unittest.TestCase):
    def setUp(self):
        reset_scene()
        self.capture = submodule("blender.capture")
        self.tmp = Path(tempfile.mkdtemp(prefix="scenario-cap-"))
        self.calls = []

    def fake_runner(self, kind, context, scene):
        r = scene.render
        self.calls.append(
            {
                "kind": kind,
                "res": (r.resolution_x, r.resolution_y, r.resolution_percentage),
                "pixels": (r.pixel_aspect_x, r.pixel_aspect_y),
                "camera": scene.camera.name if scene.camera else None,
                "fmt": r.image_settings.file_format,
                "video": _is_video(r),
                "codec": r.ffmpeg.codec,
                "path": r.filepath,
                "range": (scene.frame_start, scene.frame_end),
                "stamp": r.use_stamp,
                "preview": (
                    scene.use_preview_range,
                    scene.frame_preview_start,
                    scene.frame_preview_end,
                ),
            }
        )
        target = Path(bpy.path.abspath(r.filepath))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"mp4" if kind == "animation" else b"png")

    def test_playblast_sets_720p_h264_and_restores_everything(self):
        scene = bpy.context.scene
        scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = (
            1920,
            1080,
            50,
        )
        scene.render.use_stamp = True
        scene.frame_start, scene.frame_end = 1, 48
        scene.frame_set(7)
        scene.render.filepath = "//renders/"
        out = self.tmp / "clip.mp4"
        info = self.capture.capture_playblast(
            bpy.context,
            str(out),
            source="VIEWPORT",
            frame_start=1,
            frame_end=24,
            runner=self.fake_runner,
        )
        call = self.calls[0]
        self.assertEqual(call["kind"], "animation")
        self.assertEqual(call["res"], (1280, 720, 100))
        self.assertTrue(call["video"])
        self.assertEqual(call["codec"], "H264")
        self.assertFalse(call["stamp"])
        self.assertEqual(call["range"], (1, 24))
        self.assertEqual(info["frame_start"], 1)
        self.assertEqual(info["frame_end"], 24)
        fps = scene.render.fps / scene.render.fps_base
        self.assertAlmostEqual(info["seconds"], 24 / fps, places=3)
        self.assertTrue(out.exists())
        self.assertEqual(
            (
                scene.render.resolution_x,
                scene.render.resolution_y,
                scene.render.resolution_percentage,
            ),
            (1920, 1080, 50),
        )
        self.assertTrue(scene.render.use_stamp)
        self.assertEqual((scene.frame_start, scene.frame_end), (1, 48))
        self.assertEqual(scene.render.filepath, "//renders/")
        self.assertFalse(_is_video(scene.render))
        self.assertEqual(scene.frame_current, 7)

    @staticmethod
    def encoding(ffmpeg):
        return (
            ffmpeg.format,
            ffmpeg.codec,
            ffmpeg.audio_codec,
            ffmpeg.constant_rate_factor,
            ffmpeg.gopsize,
            ffmpeg.use_lossless_output,
            ffmpeg.use_autosplit,
        )

    def test_playblast_pins_a_small_h264_encoding_and_restores_the_scenes_own(self):
        # A scene set to lossless output or a high bitrate would upload a clip tens of times
        # larger than the same frames at Medium quality.
        scene = bpy.context.scene
        ffmpeg = scene.render.ffmpeg
        ffmpeg.format, ffmpeg.codec = "MKV", "H264"
        ffmpeg.constant_rate_factor, ffmpeg.gopsize = "LOSSLESS", 1
        ffmpeg.use_lossless_output = ffmpeg.use_autosplit = True
        own = self.encoding(ffmpeg)
        before = self.capture.RenderSettings.snapshot(scene)
        seen = []

        def runner(kind, context, scene):
            seen.append(self.encoding(scene.render.ffmpeg))
            self.fake_runner(kind, context, scene)

        self.capture.capture_playblast(
            bpy.context, str(self.tmp / "clip.mp4"), source="VIEWPORT", runner=runner
        )
        self.assertEqual(seen, [("MPEG4", "H264", "NONE", "MEDIUM", 18, False, False)])
        self.assertEqual(self.encoding(ffmpeg), own)
        self.assertEqual(self.capture.RenderSettings.snapshot(scene), before)

    def test_playblast_of_a_scene_made_by_script_restores_what_it_could(self):
        # A scene made with bpy.data.scenes.new stores encoder settings that match no enum item;
        # they read as "" and cannot be written back by name, which must not stop the capture.
        scene = bpy.data.scenes.new("Fresh scene")
        self.addCleanup(bpy.data.scenes.remove, scene)
        camera = bpy.data.objects.new("Fresh camera", bpy.data.cameras.new("Fresh camera"))
        self.addCleanup(bpy.data.objects.remove, camera)
        scene.collection.objects.link(camera)
        scene.camera = camera
        before = self.capture.RenderSettings.snapshot(scene)
        context = SimpleNamespace(scene=scene, window_manager=bpy.context.window_manager)
        self.capture.capture_playblast(
            context, str(self.tmp / "clip.mp4"), source="CAMERA", runner=self.fake_runner
        )
        self.assertEqual(self.capture.RenderSettings.snapshot(scene), before)

    def test_playblast_encoding_keeps_a_clip_of_a_lossless_scene_small(self):
        if not getattr(bpy.app.ffmpeg, "supported", False):
            self.skipTest("this Blender build has no FFmpeg")
        rng = random.Random(4)
        scene = bpy.context.scene
        scene.render.engine = "BLENDER_WORKBENCH"
        scene.display.render_aa = "8"
        scene.frame_start, scene.frame_end = 1, 12
        scene.render.resolution_x, scene.render.resolution_y = 640, 360
        bpy.ops.object.camera_add(location=(8, -8, 6), rotation=(1.1, 0, 0.8))
        scene.camera = bpy.context.active_object
        # Cubes of random size and angle: enough detail for lossless coding to cost.
        for _ in range(30):
            bpy.ops.mesh.primitive_cube_add(
                location=(rng.uniform(-4, 4), rng.uniform(-4, 4), rng.uniform(0, 3)),
                rotation=(rng.uniform(0, 3), rng.uniform(0, 3), rng.uniform(0, 3)),
            )
            bpy.context.active_object.scale = [rng.uniform(0.2, 1.2) for _ in range(3)]
        # The scene's own output: H.264 at lossless quality.
        own = scene.render
        own.image_settings.media_type = "VIDEO"
        own.ffmpeg.format, own.ffmpeg.codec = "MPEG4", "H264"
        own.ffmpeg.constant_rate_factor, own.ffmpeg.gopsize = "LOSSLESS", 1
        lossless = self.tmp / "lossless.mp4"
        own.filepath = str(lossless)
        bpy.ops.render.render(animation=True)
        pinned = self.tmp / "pinned.mp4"
        self.capture.capture_playblast(
            bpy.context,
            str(pinned),
            source="CAMERA",
            width=640,
            height=360,
            runner=lambda kind, context, scene: bpy.ops.render.render(animation=True),
        )
        sizes = (lossless.stat().st_size, pinned.stat().st_size)
        self.assertLess(sizes[1] * 4, sizes[0], sizes)
        self.assertLess(sizes[1], 300_000, sizes)
        self.assertEqual(own.ffmpeg.constant_rate_factor, "LOSSLESS")  # the scene's own, restored

    def test_still_uses_png_and_camera_source_requires_camera(self):
        bpy.ops.object.camera_add()
        out = self.tmp / "still.png"
        path = self.capture.capture_still(
            bpy.context, str(out), source="CAMERA", runner=self.fake_runner
        )
        self.assertEqual(self.calls[0]["kind"], "still")
        self.assertEqual(self.calls[0]["fmt"], "PNG")
        self.assertTrue(Path(path).exists())
        for obj in list(bpy.data.objects):
            if obj.type == "CAMERA":
                bpy.data.objects.remove(obj)
        with self.assertRaises(RuntimeError):
            self.capture.capture_still(
                bpy.context, str(self.tmp / "x.png"), source="CAMERA", runner=self.fake_runner
            )

    def test_camera_capture_leaves_a_scene_without_an_active_camera_as_it_was(self):
        bpy.ops.object.camera_add()
        scene = bpy.context.scene
        scene.camera = None
        camera = bpy.context.active_object
        for capture, name in (
            (self.capture.capture_still, "still.png"),
            (self.capture.capture_playblast, "clip.mp4"),
        ):
            capture(bpy.context, str(self.tmp / name), source="CAMERA", runner=self.fake_runner)
            # The capture looks through the scene's only camera, then unsets it again.
            self.assertEqual(self.calls[-1]["camera"], camera.name)
            self.assertIsNone(scene.camera)

    def test_still_restores_an_output_bit_depth_that_png_lacks(self):
        bpy.ops.object.camera_add()
        settings = bpy.context.scene.render.image_settings
        settings.file_format, settings.color_depth = "DPX", "10"  # PNG offers 8 or 16
        self.capture.capture_still(
            bpy.context, str(self.tmp / "still.png"), source="CAMERA", runner=self.fake_runner
        )
        self.assertEqual(self.calls[0]["fmt"], "PNG")
        self.assertEqual((settings.file_format, settings.color_depth), ("DPX", "10"))

    def test_captures_send_no_frame_notifier_when_nothing_changes(self):
        # In the GUI, even a same-value write to these properties makes Blender run
        # frame_change_pre after the capture returns, invalidating upload origins.
        bpy.ops.object.camera_add()
        scene = bpy.context.scene
        scene.camera = bpy.context.active_object
        scene.frame_start, scene.frame_end = 1, 48
        # Blender ignores preview bounds while the preview range is disabled.
        scene.use_preview_range = True
        scene.frame_preview_start, scene.frame_preview_end = 10, 20
        scene.frame_set(7)
        for preview in (False, True):
            scene.use_preview_range = preview
            with self.subTest(preview=preview):
                before = self.capture.RenderSettings.snapshot(scene)
                writes = []
                context = recording_context(bpy.context, writes)
                self.capture.capture_still(
                    context, str(self.tmp / "still.png"), source="CAMERA", runner=self.fake_runner
                )
                info = self.capture.capture_playblast(
                    context, str(self.tmp / "clip.mp4"), source="CAMERA", runner=self.fake_runner
                )
                self.assertEqual(sorted(FRAME_NOTIFYING.intersection(writes)), [])
                self.assertEqual(self.capture.RenderSettings.snapshot(scene), before)
                span = (10, 20) if preview else (1, 48)
                self.assertEqual((info["frame_start"], info["frame_end"]), span)
                # Blender renders an enabled preview range, which already equals the span.
                self.assertEqual(self.calls[-1]["preview"], (preview, 10, 20))
                self.assertEqual(self.calls[-1]["range"], span)

    def test_explicit_clip_span_overrides_then_restores_enabled_preview_range(self):
        scene = bpy.context.scene
        scene.frame_start, scene.frame_end = 1, 48
        scene.use_preview_range = True
        scene.frame_preview_start, scene.frame_preview_end = 10, 20
        scene.frame_set(12)
        before = self.capture.RenderSettings.snapshot(scene)
        info = self.capture.capture_playblast(
            bpy.context,
            str(self.tmp / "clip.mp4"),
            frame_start=1,
            frame_end=24,
            runner=self.fake_runner,
        )
        self.assertEqual((info["frame_start"], info["frame_end"]), (1, 24))
        self.assertEqual(self.calls[-1]["preview"], (False, 10, 20))
        self.assertEqual(self.calls[-1]["range"], (1, 24))
        self.assertEqual(self.capture.RenderSettings.snapshot(scene), before)

    def test_capture_size_follows_the_render_frame_or_the_viewport(self):
        scene = bpy.context.scene
        render = scene.render
        render.resolution_x, render.resolution_y = 1080, 1920
        for source in ("CAMERA", "CAMERA_CLIP"):
            self.assertEqual(self.capture.capture_size(bpy.context, source), (720, 1280))
        render.pixel_aspect_x = 2.0  # the frame is displayed 2160 pixels wide
        self.assertEqual(self.capture.capture_size(bpy.context, "CAMERA"), (1280, 1138))
        # Without a 3D viewport, a viewport capture falls back to the render frame.
        headless = SimpleNamespace(
            scene=scene, area=None, window_manager=SimpleNamespace(windows=[])
        )
        self.assertEqual(self.capture.capture_size(headless, "VIEWPORT"), (1280, 1138))
        region = SimpleNamespace(type="WINDOW", width=900, height=1200)
        view = SimpleNamespace(view_perspective="PERSP")
        area = SimpleNamespace(
            type="VIEW_3D",
            regions=[region],
            spaces=SimpleNamespace(active=SimpleNamespace(region_3d=view)),
        )
        context = SimpleNamespace(
            scene=scene,
            area=area,
            region=region,
            window=object(),
            window_manager=bpy.context.window_manager,
        )
        for source in ("VIEWPORT", "VIEWPORT_CLIP"):
            self.assertEqual(self.capture.capture_size(context, source), (960, 1280))
        self.assertEqual(self.capture.capture_size(context, "CAMERA"), (1280, 1138))
        # A viewport looking through the camera renders the camera's frame.
        view.view_perspective = "CAMERA"
        self.assertEqual(self.capture.capture_size(context, "VIEWPORT"), (1280, 1138))

    def test_sized_captures_render_square_pixels_and_restore_the_pixel_aspect(self):
        bpy.ops.object.camera_add()
        render = bpy.context.scene.render
        render.pixel_aspect_x, render.pixel_aspect_y = 2.0, 1.5
        before = self.capture.RenderSettings.snapshot(bpy.context.scene)
        self.capture.capture_still(
            bpy.context,
            str(self.tmp / "still.png"),
            source="CAMERA",
            width=720,
            height=1280,
            runner=self.fake_runner,
        )
        self.capture.capture_playblast(
            bpy.context,
            str(self.tmp / "clip.mp4"),
            source="CAMERA",
            width=720,
            height=1280,
            runner=self.fake_runner,
        )
        self.assertEqual([call["res"] for call in self.calls], [(720, 1280, 100)] * 2)
        self.assertEqual([call["pixels"] for call in self.calls], [(1.0, 1.0)] * 2)
        self.assertEqual((render.pixel_aspect_x, render.pixel_aspect_y), (2.0, 1.5))
        self.assertEqual(self.capture.RenderSettings.snapshot(bpy.context.scene), before)

    def test_capture_dir_is_under_cache(self):
        self.assertTrue(str(self.capture.capture_dir()).endswith("captures"))
