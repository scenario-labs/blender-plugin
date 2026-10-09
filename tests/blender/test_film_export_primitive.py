# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Installed offline Film export: snapshot, real Blender child, verification and ownership."""

import os
import shutil
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import bpy
from helpers import FIXTURES, submodule


class FilmExportPrimitiveTests(unittest.TestCase):
    def setUp(self):
        import httpx

        self.capture = submodule("blender.local_capture")
        self.export = submodule("core.jobs.local_export")
        self.render = submodule("core.jobs.local_render")
        self.module = submodule("blender.job_session")
        api = submodule("core.api.sdk_adapter")
        storage = submodule("core.jobs.store")
        self.directory = Path(
            self.enterContext(tempfile.TemporaryDirectory(dir=bpy.utils.resource_path("USER")))
        ).resolve()
        self.output = self.directory / "Film"
        self.output.mkdir()
        self.media = self.directory / "media.mp4"
        self.media.write_bytes((FIXTURES / "synthetic/film-four-seconds-audio.mp4").read_bytes())
        self.previous = bpy.context.scene
        self.working = bpy.data.scenes.new("Export working scene")
        bpy.context.window.scene = self.working
        self.working.frame_set(7)
        self.review = self.review_scene()
        bpy.context.view_layer.update()
        scope = storage.JobScope("https://fixture.invalid/v1", "fixture-account")
        self.store = storage.JobStore(self.directory / "jobs.sqlite3", scope)

        def offline(request):
            raise AssertionError("Film export must not contact Scenario")

        adapter = api.SDKAdapter(
            api.Credentials("key", "secret"),
            online=lambda: True,
            account_id=scope.account_id,
            base_url=scope.service,
            transport=httpx.MockTransport(offline),
        )
        self.addCleanup(adapter.close)
        self.session = self.module.JobSession(adapter, self.store, workers=1)

    def tearDown(self):
        self.session.shutdown()
        if self.previous in tuple(bpy.data.scenes):
            bpy.context.window.scene = self.previous
        for scene in (self.review, self.working):
            if scene in tuple(bpy.data.scenes):
                bpy.data.scenes.remove(scene)
        for sound in tuple(bpy.data.sounds):
            if not sound.users:
                bpy.data.sounds.remove(sound)

    def review_scene(self, *, frames=48, fps=24):
        scene = bpy.data.scenes.new("Export review fixture")
        scene.render.fps, scene.render.fps_base = fps, 1.0
        scene.render.resolution_x, scene.render.resolution_y = 64, 64
        scene.render.resolution_percentage = 100
        scene.frame_start, scene.frame_end = 1, frames
        editor = scene.sequence_editor_create()
        editor.strips.new_movie("Picture", str(self.media), 1, 1, fit_method="FILL")
        editor.strips.new_sound("Native audio", str(self.media), 2, 1)
        return scene

    def snapshot(self, scene=None, **options):
        return self.capture.export_snapshot(scene or self.review, self.directory, **options)

    def wait(self, task, timeout=60):
        deadline = time.monotonic() + timeout
        while not task.done():
            self.assertLess(time.monotonic(), deadline, "Film export did not finish")
            time.sleep(0.05)
        (completion,) = self.session.drain(task=task)
        return completion

    def state(self):
        return (
            bpy.data.filepath,
            bpy.context.scene,
            self.working.frame_current,
            set(bpy.data.scenes),
            self.review.frame_current,
        )

    def test_snapshot_preserves_working_context_and_stamps_media(self):
        before = self.state()
        spec = self.snapshot()
        self.assertEqual(before, self.state())
        self.assertTrue(spec.directory.name.startswith("film-export-"))
        self.assertEqual((spec.frame_start, spec.frame_end, spec.fps), (1, 48, 24))
        self.assertEqual((spec.width, spec.height, spec.audio), (64, 64, True))
        self.assertEqual([item.path for item in spec.media], [self.media])
        self.assertEqual(spec.media[0].size, self.media.stat().st_size)
        self.assertEqual(
            spec.snapshot_sha256, self.render.digest(spec.directory / "snapshot.blend")
        )
        self.assertEqual(spec.worker.name, "film_export_worker.py")
        self.assertTrue(spec.worker.is_file())
        with bpy.data.libraries.load(str(spec.directory / "snapshot.blend")) as (source, target):
            self.assertIn(self.review.name, source.scenes)
        # Explicit overrides are validated before any file is written.
        muted = self.snapshot(frame_end=24, audio=False)
        self.assertEqual((muted.frames, muted.audio), (24, False))
        with self.assertRaises(ValueError):
            self.snapshot(width=65)

    def test_silent_review_defaults_to_no_audio_track(self):
        for strip in self.review.sequence_editor.strips_all:
            if strip.type == "SOUND":
                strip.mute = True
        self.assertFalse(self.snapshot().audio)

    def test_unsupported_scenes_are_rejected_without_files(self):
        before = set(self.directory.iterdir())

        def rejects(error, scene=None):
            with self.assertRaises(error):
                self.snapshot(scene)
            self.assertEqual(set(self.directory.iterdir()), before)

        # Python-created clip/mask strips make Blender log user-count errors when
        # freed, so the native case uses a scene strip; all three share the set.
        self.assertEqual(self.capture.BLOCKED_STRIPS, {"SCENE", "MOVIECLIP", "MASK"})
        worker = submodule("blender.film_export_worker")
        self.assertEqual(worker.BLOCKED_STRIPS, self.capture.BLOCKED_STRIPS)
        editor = self.review.sequence_editor
        strip = editor.strips.new_scene("Nested 3D", self.working, 5, 1)
        rejects(ValueError)
        editor.strips.remove(strip)
        self.review.render.fps_base = 1.001
        rejects(ValueError)
        self.review.render.fps_base = 1.0
        empty = bpy.data.scenes.new("Export empty fixture")
        self.addCleanup(bpy.data.scenes.remove, empty)
        rejects(ValueError, empty)
        missing = self.review_scene()
        self.addCleanup(bpy.data.scenes.remove, missing)
        (movie,) = [s for s in missing.sequence_editor.strips_all if s.type == "MOVIE"]
        movie.filepath = str(self.directory / "absent.mp4")
        rejects(self.export.LocalExportError, missing)
        with ThreadPoolExecutor(max_workers=1) as pool:
            with self.assertRaisesRegex(RuntimeError, "main thread"):
                pool.submit(self.snapshot).result()

    def export_real(self, spec, destination, *, ffprobe):
        if ffprobe:
            staged = self.export.render(spec)
        else:
            with patch.object(self.export.shutil, "which", return_value=None):
                staged = self.export.render(spec)
        published = self.export.publish(staged, destination)
        return staged, published

    def test_real_child_export_verified_by_blender_decode(self):
        before = self.state()
        spec = self.snapshot()
        destination = self.export.validate_destination(self.output / "Review.mp4")
        staged, published = self.export_real(spec, destination, ffprobe=False)
        self.assertEqual(before, self.state())
        self.assertEqual(staged.verification, "blender")
        self.assertEqual((published.frames, published.fps, published.width), (48, 24, 64))
        self.assertTrue(published.audio)
        self.assertEqual(published.sha256, self.render.digest(destination))
        self.assertEqual(sorted(p.name for p in self.output.iterdir()), ["Review.mp4"])
        summary = submodule("core.jobs.mp4_inspection").inspect(destination)
        self.assertEqual((summary.video[0].codec, summary.audio[0].codec), ("h264", "aac"))
        self.assertTrue(staged.path.exists())

    @unittest.skipUnless(shutil.which("ffprobe"), "ffprobe is not installed")
    def test_real_child_export_verified_by_ffprobe(self):
        spec = self.snapshot()
        staged, published = self.export_real(spec, self.output / "Review.mp4", ffprobe=True)
        self.assertEqual(staged.verification, "ffprobe")
        self.assertEqual(published.frames, 48)

    def origins(self):
        # The snapshot synchronizes view layers; a second synchronization is a
        # no-op, so origins captured afterwards remain current.
        for layer in self.review.view_layers:
            layer.update()
        return self.session.capture(self.working), self.session.capture(self.review)

    def test_session_export_uses_owned_thread_and_delivers_receipt(self):
        origin, source = self.origins()
        spec = self.snapshot()
        self.assertTrue(self.session._origins.current(source))
        destination = self.export.validate_destination(self.output / "Review.mp4")
        threads = []
        render = self.export.render

        def record(*args, **kwargs):
            threads.append(threading.current_thread())
            return render(*args, **kwargs)

        with patch.object(self.export, "render", side_effect=record):
            task = self.session.export_film(spec, destination, origin=origin, source_origin=source)
            completion = self.wait(task)
        self.assertTrue(completion.local_export)
        result = self.session.deliver_local_export(completion)
        self.assertEqual(result.export.destination, destination)
        self.assertEqual(result.export.sha256, self.render.digest(destination))
        self.assertEqual(threads[0].name, "ScenarioFilmExport")
        self.assertNotIn(threads[0], self.session._workers._threads)
        with self.assertRaises(self.module.OriginUnavailable):
            self.session.deliver_local_export(completion)
        self.export.discard_staging(spec.directory)
        self.assertTrue(destination.exists())

    def test_publish_failure_allows_copy_only_republish(self):
        origin, source = self.origins()
        spec = self.snapshot(audio=False)
        publish = self.export.publish
        calls = []

        def fail_once(staged, destination, *args, **kwargs):
            calls.append(destination)
            if len(calls) == 1:
                self.export.release(args[0])
                raise self.export.ExportPublishError("fixture publish failure", staged)
            return publish(staged, destination, *args, **kwargs)

        first = self.output / "Locked.mp4"
        with patch.object(self.export, "publish", side_effect=fail_once):
            completion = self.wait(
                self.session.export_film(spec, first, origin=origin, source_origin=source)
            )
            with self.assertRaises(self.export.ExportPublishError) as caught:
                self.session.deliver_local_export(completion)
            staged = caught.exception.staged
            self.assertFalse(first.exists())
            with patch.object(self.export, "_run", side_effect=AssertionError("re-rendered")):
                completion = self.wait(
                    self.session.publish_film_export(
                        staged, self.output / "Copy.mp4", origin=origin, source_origin=source
                    )
                )
        result = self.session.deliver_local_export(completion)
        self.assertEqual(result.export.sha256, staged.sha256)
        self.assertEqual(sorted(p.name for p in self.output.iterdir()), ["Copy.mp4"])

    def test_session_retirement_cancels_a_running_child(self):
        self.review.frame_end = 24000
        self.review.render.fps = 30
        origin, source = self.origins()
        spec = self.snapshot(audio=False)
        destination = self.output / "Long.mp4"
        task = self.session.export_film(spec, destination, origin=origin, source_origin=source)
        deadline = time.monotonic() + 60
        while not (task.progress()[0] == "render" and task.progress()[1] > 0):
            self.assertLess(time.monotonic(), deadline, "Export child did not report progress")
            self.assertFalse(task.done(), "Export finished before cancellation")
            time.sleep(0.05)
        self.assertTrue(destination.exists())
        self.session.deactivate()
        completion = self.wait(task, timeout=30)
        self.assertIsInstance(completion.error, self.render.RenderCancelled)
        self.assertFalse(destination.exists())
        self.assertEqual(list(self.output.iterdir()), [])
        self.session._exports.shutdown()
        self.assertTrue(self.session._exports.stopped)

    @unittest.skipUnless(os.name == "nt", "Windows extended-path regression")
    def test_deep_windows_staging_fails_before_snapshot(self):
        root = self.capture._root(self.directory)
        for component in ("a" * 64, "b" * 64, "c" * 64, "d" * 64):
            root /= component
            root.mkdir()
        with self.assertRaisesRegex(self.render.LocalRenderError, "shorter absolute paths"):
            self.capture.export_snapshot(self.review, root)
        self.assertEqual(list(root.iterdir()), [])
