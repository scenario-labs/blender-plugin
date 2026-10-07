# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Real native snapshot identity/context preservation without invoking GPU rendering."""

import json
import os
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import bpy
from helpers import reset_scene, submodule


class LocalCaptureTests(unittest.TestCase):
    def setUp(self):
        reset_scene()
        self.capture = submodule("blender.local_capture")
        self.render = submodule("core.jobs.local_render")
        self.directory = self.enterContext(
            tempfile.TemporaryDirectory(dir=bpy.utils.resource_path("USER"))
        )
        self.scene = bpy.context.scene
        camera = bpy.data.objects.new("Snapshot camera", bpy.data.cameras.new("Snapshot camera"))
        self.scene.collection.objects.link(camera)
        self.scene.camera = camera
        self.before_scenes = set(bpy.data.scenes)
        self.before_objects = set(bpy.data.objects)
        self.addCleanup(reset_scene)

    def snapshot(self, **kwargs):
        return self.capture.snapshot(
            self.scene,
            self.directory,
            frame_start=5,
            frame_end=5,
            kind="STILL",
            width=64,
            height=64,
            **kwargs,
        )

    def test_export_preserves_working_file_scene_frame_and_render_settings(self):
        scene = self.scene
        scene.frame_set(9)
        scene.render.filepath = "//existing-render"
        scene.render.resolution_x, scene.render.resolution_y = 777, 555
        before = (
            bpy.data.filepath,
            bpy.context.scene,
            scene.frame_current,
            scene.camera,
            scene.render.filepath,
            scene.render.resolution_x,
            scene.render.resolution_y,
            scene.render.image_settings.file_format,
        )
        spec = self.snapshot()
        self.assertEqual(
            spec.snapshot_sha256, self.render.digest(spec.directory / "snapshot.blend")
        )
        self.assertEqual((spec.frame_start, spec.frame_end), (5, 5))
        self.assertEqual(
            before,
            (
                bpy.data.filepath,
                bpy.context.scene,
                scene.frame_current,
                scene.camera,
                scene.render.filepath,
                scene.render.resolution_x,
                scene.render.resolution_y,
                scene.render.image_settings.file_format,
            ),
        )
        self.assertEqual(set(bpy.data.scenes), self.before_scenes)
        self.assertEqual(set(bpy.data.objects), self.before_objects)
        with bpy.data.libraries.load(str(spec.directory / "snapshot.blend"), link=False) as (
            source,
            target,
        ):
            target.scenes = source.scenes
        try:
            self.assertEqual(len(target.scenes), 1)
            self.assertEqual(target.scenes[0].frame_current, 9)
            self.assertIsNotNone(target.scenes[0].camera)
        finally:
            for loaded in target.scenes:
                bpy.data.scenes.remove(loaded)

    def test_video_dependencies_checked_before_export(self):
        with patch.object(
            self.capture, "media_tools", side_effect=self.render.LocalRenderError("Missing tools")
        ):
            with self.assertRaisesRegex(self.render.LocalRenderError, "Missing"):
                self.capture.snapshot(
                    self.scene,
                    self.directory,
                    frame_start=1,
                    frame_end=24,
                    kind="VIDEO",
                )
        self.assertEqual(list(Path(self.directory).iterdir()), [])

    def check_snapshot_child_handoff(self, root):
        self.scene.frame_set(9)
        before = (bpy.data.filepath, bpy.context.scene, self.scene.frame_current)
        spec = self.capture.snapshot(
            self.scene,
            root,
            frame_start=5,
            frame_end=5,
            kind="STILL",
            width=64,
            height=64,
            timeout=60,
        )
        if os.name == "nt":
            self.assertTrue(str(spec.directory).startswith("\\\\?\\"))
        # Exercise the real render() subprocess handoff without requiring GPU
        # rendering in CI. The child reads Blender's loaded snapshot, then emits
        # a synthetic header and an inspection receipt from its private worker.
        worker = spec.directory / "handoff_worker.py"
        worker.write_text(
            """import json
import struct
import sys
from pathlib import Path
import bpy

spec_path = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
parameters = json.loads(spec_path.read_text())
scene = bpy.data.scenes[parameters["scene_name"]]
assert scene.camera in tuple(scene.objects)
assert scene.frame_current == 9
assert Path(bpy.data.filepath).samefile(spec_path.parent / "snapshot.blend")
output = spec_path.parent / "frames" / "Frame-000001.png"
output.write_bytes(bytes.fromhex("89504e470d0a1a0a0000000d49484452")
                   + struct.pack(">II", parameters["width"], parameters["height"]))
(spec_path.parent / "handoff.json").write_text(json.dumps({
    "scene": scene.name, "camera": scene.camera.name,
    "frame": scene.frame_current, "offline": not bpy.app.online_access,
}))
""",
            encoding="utf-8",
        )
        result = self.render.render(replace(spec, worker=worker))
        receipt = json.loads((spec.directory / "handoff.json").read_text())
        self.assertEqual(
            receipt,
            dict(scene=self.scene.name, camera=self.scene.camera.name, frame=9, offline=True),
        )
        self.assertEqual((result.frames, result.width, result.height), (1, 64, 64))
        self.assertEqual(result.sha256, self.render.digest(result.path))
        self.assertEqual(before, (bpy.data.filepath, bpy.context.scene, self.scene.frame_current))
        self.assertFalse(list(spec.directory.glob("worker-*")))

    def test_snapshot_is_loaded_by_the_owned_blender_child(self):
        self.check_snapshot_child_handoff(self.directory)

    @unittest.skipUnless(os.name == "nt", "Windows extended-path regression")
    def test_deep_windows_snapshot_is_loaded_by_the_owned_blender_child(self):
        # The owner also cleans up through the extended namespace.
        with tempfile.TemporaryDirectory(dir=self.capture._root(self.directory)) as directory:
            root = Path(directory)
            for component in ("a" * 64, "b" * 64, "c" * 64):
                root /= component
                root.mkdir()
            self.assertGreater(len(str(root)), 260)
            self.check_snapshot_child_handoff(root)

    def test_worker_overrides_snapshot_output_flags_without_changing_source(self):
        source = self.scene
        flags = ("use_border", "use_crop_to_border", "use_multiview", "use_compositing")
        for name in flags:
            setattr(source.render, name, True)
        source.view_layers[0].use = False
        spec = self.snapshot()
        with bpy.data.libraries.load(str(spec.directory / "snapshot.blend"), link=False) as (
            _source,
            target,
        ):
            target.scenes = _source.scenes
        child = target.scenes[0]
        specification = spec.directory / "worker-test.json"
        specification.write_text(
            json.dumps(
                {
                    "frame_start": 5,
                    "frame_end": 5,
                    "width": 64,
                    "height": 64,
                    "color_type": "MATERIAL",
                    "scene_name": child.name,
                }
            )
        )
        (spec.directory / "frames").mkdir(exist_ok=True)

        def render(**kwargs):
            self.assertEqual(
                kwargs, dict(write_still=True, scene=child.name, layer=child.view_layers[0].name)
            )
            self.assertFalse(any(getattr(child.render, name) for name in flags))
            self.assertTrue(child.render.use_single_layer)
            self.assertTrue(child.view_layers[0].use)
            self.assertEqual((child.render.resolution_x, child.render.resolution_y), (64, 64))
            Path(child.render.filepath).write_bytes(b"fixture frame")

        try:
            operation = Mock(side_effect=render)
            with (
                patch.object(sys, "argv", ["render_worker.py", "--", str(specification)]),
                patch.object(bpy, "ops", SimpleNamespace(render=SimpleNamespace(render=operation))),
            ):
                submodule("blender.render_worker").main()
            operation.assert_called_once()
            self.assertTrue(all(getattr(source.render, name) for name in flags))
            self.assertFalse(source.view_layers[0].use)
        finally:
            bpy.context.window.scene = source
            bpy.data.scenes.remove(child)
            for name in flags:
                setattr(source.render, name, False)
            source.view_layers[0].use = True

    def test_missing_camera_rejected_without_files(self):
        self.scene.camera = None
        with self.assertRaisesRegex(ValueError, "camera"):
            self.snapshot()
        self.assertEqual(list(Path(self.directory).iterdir()), [])

    def test_worker_cannot_read_scene_for_snapshot(self):
        with ThreadPoolExecutor(max_workers=1) as pool:
            with self.assertRaisesRegex(RuntimeError, "main thread"):
                pool.submit(self.snapshot).result()
        self.assertEqual(list(Path(self.directory).iterdir()), [])

    def test_snapshot_failure_removes_only_new_private_directory(self):
        kept = Path(self.directory) / "unrelated"
        kept.write_text("keep")
        with patch.object(
            self.capture, "digest", side_effect=OSError("Snapshot verification failed")
        ):
            with self.assertRaises(OSError):
                self.snapshot()
        self.assertEqual(list(Path(self.directory).iterdir()), [kept])

    def test_exact_video_range_is_not_padded_to_provider_source_duration(self):
        with patch.object(
            self.capture, "media_tools", return_value=(Path("/ffmpeg"), Path("/ffprobe"))
        ):
            spec = self.capture.snapshot(
                self.scene,
                self.directory,
                frame_start=7,
                frame_end=18,
                kind="VIDEO",
            )
        self.assertEqual((spec.frame_start, spec.frame_end, spec.frames), (7, 18, 12))
        self.assertEqual(spec.fps, self.scene.render.fps / self.scene.render.fps_base)
