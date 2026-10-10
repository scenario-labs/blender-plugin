# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Installed local-result UI admission and completion tests; no service or playback.

Waveforms decode in the real offline Blender child; blocked reads patch it.
"""

import tempfile
import textwrap
import threading
import time
import unittest
import wave
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import bpy
from helpers import FIXTURES, isolated_manager, submodule, temp_credentials


class _Layout:
    """Records the preview box's draw calls; draw() must only read cached state."""

    def __init__(self):
        self.calls = []

    def box(self):
        return self

    def label(self, *, text, icon):
        self.calls.append(("label", text, icon))

    def operator(self, idname, *, text, icon):
        self.calls.append(("operator", idname))

    def template_icon(self, *, icon_value, scale):
        self.calls.append(("icon", icon_value, scale))


class AudioPreviewTests(unittest.TestCase):
    def setUp(self):
        self.preview = submodule("blender.audio_preview")
        self.core = submodule("core.audio_waveform")
        self.decoder = submodule("core.jobs.audio_decode")
        self.runtime = submodule("blender.runtime")
        self.preview.controller.clear()
        self.manager = self.enterContext(isolated_manager())
        self.directory = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.record = submodule("core.jobs.records").JobRecord.new(
            lane="audio", kind="audio", model_id="synthetic-pcm", body={}
        )
        self.record.status = "success"
        for index in range(2):
            path = self.directory / f"tone-{index}.wav"
            with wave.open(str(path), "wb") as sound:
                sound.setparams((1, 2, 8000, 0, "NONE", "not compressed"))
                sound.writeframes(
                    (b"\x00\x00\xff\x7f" if index == 0 else b"\x00\x00\x00\x80") * 400
                )
            self.record.files.append(str(path))
        self.manager.registry.add(self.record)
        self.gates = []
        self.addCleanup(self.finish)

    def finish(self):
        for gate in self.gates:
            gate.set()
        controller = self.preview.controller
        controller.clear()
        for reader in controller._readers:
            reader.thread.join(30)
            self.assertFalse(reader.thread.is_alive())
        controller.poll()

    def worker(self):
        return self.preview.controller._readers[-1].thread

    def ready(self):
        # Each preview starts an offline Blender child; allow for a loaded host.
        deadline = time.monotonic() + 30
        controller = self.preview.controller
        while controller.selection is not None and controller.selection.status == "LOADING":
            controller.poll()
            if time.monotonic() > deadline:
                self.fail("Local waveform worker did not complete")
            time.sleep(0.005)
        return controller.selection

    def select(self, index=0):
        self.assertEqual(
            bpy.ops.scenario.preview_audio(local_id=self.record.local_id, file_index=index),
            {"FINISHED"},
        )

    def blocked_read(self, count=1):
        entered, release = threading.Event(), threading.Event()
        self.gates.append(release)
        original = self.decoder.decode
        calls = []

        def read(path, directory, spec, *, cancel, **options):
            calls.append((str(path), threading.current_thread()))
            if len(calls) <= count:
                if len(calls) == count:
                    entered.set()
                if not release.wait(10):
                    raise AssertionError("Native test did not release its reader")
            # Deliberately finish despite cancellation to exercise stale-result rejection.
            return original(path, directory, spec, cancel=threading.Event(), **options)

        self.enterContext(patch.object(self.decoder, "decode", side_effect=read))
        self.select()
        if count == 2:
            self.select(1)
        self.assertTrue(entered.wait(5))
        return release, calls

    def test_operator_builds_native_icon_off_thread_without_changing_audio(self):
        before = Path(self.record.files[0]).read_bytes()
        original = self.decoder.decode
        threads, directories = [], []

        def read(path, directory, spec, *, cancel, **options):
            threads.append(threading.current_thread())
            directories.append(directory)
            self.assertEqual(spec, self.runtime.waveform_spec())
            return original(path, directory, spec, cancel=cancel, **options)

        with patch.object(self.decoder, "decode", side_effect=read):
            self.select()
            selected = self.ready()
        self.assertEqual(selected.status, "READY")
        # Background Blender has no drawable icon ID; GUI proof covers rendering.
        self.assertGreaterEqual(selected.icon_id, 0)
        self.assertEqual(selected.waveform.channels, 1)
        self.assertEqual(Path(selected.path).read_bytes(), before)
        # The child used a private directory under the extension cache and left nothing.
        cache = Path(self.runtime.paths().cache_dir).resolve()
        self.assertEqual([path.resolve() for path in directories], [cache / "audio-preview"])
        self.assertEqual(list(directories[0].iterdir()), [])
        self.assertTrue(all(thread is not threading.main_thread() for thread in threads))
        self.assertEqual(tuple(self.preview.controller._previews["waveform"].image_size), (256, 96))
        pixels = self.preview.controller._previews["waveform"].image_pixels_float
        self.assertEqual(len(pixels), 256 * 96 * 4)
        self.assertGreater(max(pixels), 0)

    def draw_with(self, preferences, width=800):
        layout = _Layout()
        context = SimpleNamespace(
            scene=bpy.context.scene,
            window=bpy.context.window,
            region=SimpleNamespace(width=width),
            preferences=preferences,
        )
        with patch.object(self.preview, "bpy", SimpleNamespace(context=context)):
            self.preview.draw(layout, self.record, 0)
        return layout.calls

    def test_draw_sizes_text_and_waveform_with_blenders_custom_ui_scale(self):
        self.select()
        selected = self.ready()
        self.assertEqual(selected.status, "READY")
        # Blender 5.2.1 on Retina at a Preferences resolution scale of 2 reports
        # system.ui_scale 4 and pixel size 4, a line width derived from DPI 288.
        # Multiplying that pixel size by the resolution scale would size for 8.
        retina = SimpleNamespace(
            system=SimpleNamespace(ui_scale=4.0, pixel_size=4.0),
            view=SimpleNamespace(ui_scale=2.0),
        )
        calls = self.draw_with(retina)
        # Only the custom-interface scale exists here; reading anything else fails.
        custom = SimpleNamespace(system=SimpleNamespace(ui_scale=4.0))
        self.assertEqual(calls, self.draw_with(custom))
        columns = int((800 / 4 - 80) / 7)
        self.assertEqual(columns, 17)
        lines = textwrap.wrap(selected.message, width=columns)
        # Scale 8 would wrap at the 12-column minimum with the smallest waveform.
        self.assertNotEqual(lines, textwrap.wrap(selected.message, width=12))
        self.assertEqual(
            calls,
            [
                ("label", Path(selected.path).name, "SOUND"),
                *(("label", line, "INFO") for line in lines),
                ("icon", selected.icon_id, 6.0),
            ],
        )
        # Background Blender reports a custom-interface scale of 0; draw uses 1.
        self.assertEqual(
            self.draw_with(SimpleNamespace(system=SimpleNamespace(ui_scale=0.0))),
            self.draw_with(SimpleNamespace(system=SimpleNamespace(ui_scale=1.0))),
        )
        layout = _Layout()
        self.preview.draw(layout, self.record, 0)
        self.assertEqual(layout.calls[0], ("label", Path(selected.path).name, "SOUND"))
        self.assertEqual(layout.calls[-1][0], "icon")

    def test_cancel_rejects_late_completion_and_preserves_result(self):
        release, _ = self.blocked_read()
        bpy.ops.scenario.cancel_audio_preview()
        release.set()
        self.worker().join(5)
        self.preview.controller.poll()
        selected = self.preview.controller.selection
        self.assertEqual(selected.status, "CANCELED")
        self.assertEqual(selected.icon_id, 0)
        self.assertEqual(len(self.record.files), 2)
        self.assertTrue(all(Path(path).is_file() for path in self.record.files))

    def test_new_selection_coalesces_requests_and_never_publishes_old_file(self):
        release, calls = self.blocked_read(count=2)
        for index in (0, 1, 0, 1):
            self.select(index)
        self.assertEqual(len(calls), 2)
        self.assertEqual(len(self.preview.controller._readers), self.preview.MAX_READERS)
        release.set()
        selected = self.ready()
        self.assertEqual(selected.status, "READY")
        self.assertEqual(selected.path, self.record.files[1])
        self.assertEqual([path for path, _ in calls], [*self.record.files, self.record.files[1]])
        self.assertGreater(max(selected.waveform.peaks), 0.9)

    def test_blocked_canceled_read_does_not_prevent_another_preview(self):
        release, calls = self.blocked_read()
        blocked = calls[0][1]
        bpy.ops.scenario.cancel_audio_preview()
        self.select(1)
        selected = self.ready()
        self.assertEqual(selected.status, "READY")
        self.assertEqual(selected.path, self.record.files[1])
        self.assertTrue(blocked.is_alive())
        self.assertFalse(release.is_set())
        pixels = tuple(self.preview.controller._previews["waveform"].image_pixels_float)
        release.set()
        blocked.join(5)
        self.preview.controller.poll()
        self.assertIs(self.preview.controller.selection, selected)
        self.assertEqual(
            tuple(self.preview.controller._previews["waveform"].image_pixels_float), pixels
        )

    def test_file_load_and_deadline_can_retire_a_still_blocked_read(self):
        for retire in ("file-load", "deadline"):
            with self.subTest(retire=retire):
                release, calls = self.blocked_read()
                blocked = calls[0][1]
                if retire == "file-load":
                    self.preview._file_load(None)
                    self.assertIsNone(self.preview.controller.selection)
                else:
                    selected = self.preview.controller.selection
                    with patch.object(
                        self.preview, "monotonic", return_value=selected.deadline + 1
                    ):
                        self.preview.controller.poll()
                    self.assertEqual(selected.status, "ERROR")
                    self.assertIn("timed out", selected.message)
                self.select(1)
                self.assertEqual(self.ready().status, "READY")
                self.assertTrue(blocked.is_alive())
                release.set()
                blocked.join(5)
                self.preview.controller.clear()
                self.preview.controller.poll()

    def test_two_blocked_readers_are_bounded_and_admission_times_out_explicitly(self):
        release, calls = self.blocked_read(count=2)
        self.select(0)
        selected = self.preview.controller.selection
        with patch.object(self.preview, "monotonic", return_value=selected.deadline + 1):
            self.preview.controller.poll()
        self.assertEqual(selected.status, "ERROR")
        self.assertIn("restart Blender", selected.message)
        self.assertEqual(len(calls), 2)
        self.assertTrue(all(thread.is_alive() for _, thread in calls))
        self.assertEqual(len(self.preview.controller._readers), self.preview.MAX_READERS)
        release.set()
        for _, thread in calls:
            thread.join(5)
        self.preview.controller.poll()
        self.assertEqual(len(calls), 2)
        self.assertEqual(selected.status, "ERROR")
        self.assertIsNone(self.preview.controller._pending)
        self.assertEqual(self.preview.controller._readers, [])
        self.select(1)
        self.assertEqual(self.ready().status, "READY")

    def test_only_an_outcome_finished_before_the_deadline_publishes(self):
        # Blender's timer can run after the deadline; the reader's finish time decides.
        self.select()
        self.worker().join(30)
        selected = self.preview.controller.selection
        with patch.object(self.preview, "monotonic", return_value=selected.deadline + 1):
            self.preview.controller.poll()
        self.assertEqual(selected.status, "READY")
        self.assertEqual(selected.waveform.channels, 1)
        # A reader that finishes at or after its deadline never publishes.
        release, _ = self.blocked_read()
        selected = self.preview.controller.selection
        with patch.object(self.preview, "monotonic", return_value=selected.deadline):
            release.set()
            self.worker().join(30)
            self.preview.controller.poll()
        self.assertEqual(selected.status, "ERROR")
        self.assertIn("timed out", selected.message)
        self.assertIsNone(selected.waveform)
        self.assertIsNone(self.preview.controller._previews)
        self.select(1)
        self.assertEqual(self.ready().status, "READY")

    def test_shutdown_cancels_and_waits_for_a_running_decoder(self):
        # Python abandons daemon readers at exit, so unregistering, which Blender
        # also does on exit, must let each one stop its offline child first. This
        # stand-in for the child process runs until it is canceled.
        canceled = submodule("core.jobs.local_render").RenderCancelled
        started, stopped = threading.Event(), []

        def run(command, *, cancel, **options):
            started.set()
            if not cancel.wait(10):
                raise AssertionError("Shutdown did not cancel the decoder")
            time.sleep(0.2)  # Like terminating the child, which the wait must cover.
            stopped.append(threading.current_thread())
            raise canceled("Local capture cancelled")

        self.enterContext(patch.object(self.decoder, "_run", side_effect=run))
        self.select()
        self.assertTrue(started.wait(10))
        (reader,) = self.preview.controller._readers
        self.preview.controller.shutdown()
        self.assertFalse(reader.thread.is_alive())
        self.assertEqual(stopped, [reader.thread])
        self.assertEqual(self.preview.controller._readers, [])
        self.assertIsNone(self.preview.controller.selection)
        cache = Path(self.runtime.paths().cache_dir) / "audio-preview"
        self.assertEqual(list(cache.iterdir()), [])

    def test_reader_start_failure_is_terminal_sanitized_and_retryable(self):
        with patch.object(threading.Thread, "start", side_effect=RuntimeError("private detail")):
            self.select()
        selected = self.preview.controller.selection
        self.assertEqual(selected.status, "ERROR")
        self.assertEqual(selected.message, "Could not start the waveform reader; try again")
        self.assertIsNone(self.preview.controller._pending)
        self.assertEqual(self.preview.controller._readers, [])
        self.assertEqual(self.preview._tick(), self.preview.IDLE_INTERVAL)
        self.select(1)
        self.assertEqual(self.ready().status, "READY")

    def test_cancel_preserves_finished_preview_and_terminal_timer_slows_down(self):
        self.select()
        selected = self.ready()
        collection = self.preview.controller._previews
        self.assertFalse(bpy.ops.scenario.cancel_audio_preview.poll())
        self.preview.controller.cancel()
        self.assertEqual(selected.status, "READY")
        self.assertIs(self.preview.controller._previews, collection)
        self.assertEqual(self.preview._tick(), self.preview.IDLE_INTERVAL)
        with patch.object(self.runtime.state, "manager", None):
            self.assertIsNone(self.preview._tick())
        self.assertIsNone(self.preview.controller.selection)
        self.assertIsNone(self.preview.controller._previews)
        release, _ = self.blocked_read()
        self.assertEqual(self.preview._tick(), self.preview.LOADING_INTERVAL)
        self.assertTrue(bpy.ops.scenario.cancel_audio_preview.poll())
        bpy.ops.scenario.cancel_audio_preview()
        self.assertEqual(self.preview._tick(), self.preview.IDLE_INTERVAL)
        self.assertFalse(bpy.ops.scenario.cancel_audio_preview.poll())
        release.set()

    def test_reselect_restarts_existing_native_timer_at_loading_cadence(self):
        self.select()
        self.assertEqual(self.ready().status, "READY")
        self.assertEqual(self.preview._tick(), self.preview.IDLE_INTERVAL)
        timers = bpy.app.timers
        timers.register(self.preview._tick, first_interval=self.preview.IDLE_INTERVAL)
        self.addCleanup(
            lambda: (
                timers.unregister(self.preview._tick)
                if timers.is_registered(self.preview._tick)
                else None
            )
        )
        # The installed operator uses the GUI branch with Blender's real timer
        # API, while this isolated background fixture supplies the GUI flag.
        gui_bpy = SimpleNamespace(
            app=SimpleNamespace(background=False, timers=timers),
            data=bpy.data,
            context=bpy.context,
        )
        with (
            patch.object(self.preview, "bpy", gui_bpy),
            patch.object(timers, "unregister", wraps=timers.unregister) as unregister,
            patch.object(timers, "register", wraps=timers.register) as register,
        ):
            release, _ = self.blocked_read()
            unregister.assert_called_once_with(self.preview._tick)
            register.assert_called_once_with(
                self.preview._tick, first_interval=self.preview.LOADING_INTERVAL
            )
            self.assertTrue(timers.is_registered(self.preview._tick))
            self.assertEqual(self.preview._tick(), self.preview.LOADING_INTERVAL)
        release.set()
        self.assertEqual(self.ready().status, "READY")
        self.assertEqual(self.preview._tick(), self.preview.IDLE_INTERVAL)

    def test_changed_file_after_worker_verification_keeps_captured_snapshot(self):
        self.select()
        self.worker().join(5)
        Path(self.record.files[0]).write_bytes(b"changed after decoding")
        # Publication performs no filesystem calls on the Blender thread. The
        # displayed bytes remain the already verified local snapshot, not a
        # promise that an externally mutable file is still unchanged.
        with patch.object(Path, "lstat", side_effect=AssertionError("Main-thread metadata IO")):
            selected = self.ready()
        self.assertEqual(selected.status, "READY")
        self.assertIn("Snapshot", selected.message)
        self.assertAlmostEqual(selected.waveform.seconds, 0.1)

    def test_worker_rejects_file_changed_during_raster_preparation(self):
        original = self.core.raster

        def raster(waveform):
            self.assertIsNot(threading.current_thread(), threading.main_thread())
            Path(self.record.files[0]).write_bytes(b"changed during raster")
            return original(waveform)

        with patch.object(self.core, "raster", side_effect=raster):
            self.select()
            selected = self.ready()
        self.assertEqual(selected.status, "ERROR")
        self.assertIn("changed", selected.message)

    def test_manager_credential_record_and_path_changes_reject_queued_outcome(self):
        for mutation in ("manager", "credentials", "record", "path"):
            with self.subTest(mutation=mutation):
                self.select()
                self.worker().join(5)
                if mutation == "manager":
                    with patch.object(self.runtime.state, "manager", None):
                        self.assertTrue(self.preview.controller.poll())
                elif mutation == "credentials":
                    with temp_credentials("different-fixture", "different-secret"):
                        self.preview.controller.poll()
                elif mutation == "record":
                    with patch.object(self.manager.registry, "by_local_id", return_value=None):
                        self.preview.controller.poll()
                else:
                    previous = self.record.files[0]
                    self.record.files[0] = self.record.files[1]
                    self.preview.controller.poll()
                    self.record.files[0] = previous
                self.assertIsNone(self.preview.controller.selection)
                self.assertIsNone(self.preview.controller._previews)

    def test_file_load_and_scene_switch_clear_current_preview(self):
        self.select()
        self.ready()
        self.preview._file_load(None)
        self.assertIsNone(self.preview.controller.selection)
        self.assertIsNone(self.preview.controller._previews)
        if bpy.context.window is None:
            self.skipTest("Native background build has no window scene")
        self.select()
        self.worker().join(5)
        previous = bpy.context.window.scene
        other = bpy.data.scenes.new("Waveform context test")
        try:
            bpy.context.window.scene = other
            self.preview.controller.poll()
            self.assertIsNone(self.preview.controller.selection)
        finally:
            bpy.context.window.scene = previous
            bpy.data.scenes.remove(other)

    def test_undecodable_file_reports_an_error_without_mutating_playback_path(self):
        path = self.directory / "example.mp3"
        path.write_bytes(b"synthetic undecodable media")
        self.record.files[0] = str(path)
        self.select()
        selected = self.ready()
        self.assertEqual(selected.status, "ERROR")
        self.assertEqual(selected.message, "Blender could not decode this audio")
        self.assertEqual(self.record.files[0], str(path))
        self.assertEqual(path.read_bytes(), b"synthetic undecodable media")

    def test_compressed_audio_now_previews_through_the_offline_decoder(self):
        path = self.directory / "silence.mp3"
        path.write_bytes((FIXTURES / "synthetic/audio-silence.mp3").read_bytes())
        self.record.files[0] = str(path)
        self.select()
        selected = self.ready()
        self.assertEqual(selected.status, "READY")
        self.assertTrue(selected.waveform.silent)
        self.assertIn("Mono", selected.message)

    def test_missing_executable_is_refused_before_any_reader_starts(self):
        with patch.object(self.runtime, "waveform_spec", return_value=None):
            with self.assertRaisesRegex(ValueError, "executable"):
                self.preview.controller.select(bpy.context, self.record.local_id, 0)
        self.assertIsNone(self.preview.controller.selection)
        self.assertEqual(self.preview.controller._readers, [])

    def test_unknown_failed_and_wrong_kind_results_are_not_admitted(self):
        controller = self.preview.controller
        with self.assertRaises(ValueError):
            controller.select(bpy.context, "missing", 0)
        with self.assertRaises(ValueError):
            controller.select(bpy.context, self.record.local_id, 2)
        self.record.status = "failed"
        with self.assertRaises(ValueError):
            controller.select(bpy.context, self.record.local_id, 0)
        self.record.status, self.record.kind = "success", "image"
        with self.assertRaises(ValueError):
            controller.select(bpy.context, self.record.local_id, 0)
        self.assertIsNone(controller.selection)

    def test_controller_rejects_worker_thread_before_touching_blender(self):
        errors = []

        def call():
            for method in (
                self.preview.controller.poll,
                self.preview.controller.clear,
                self.preview.controller.cancel,
            ):
                try:
                    method()
                except RuntimeError as error:
                    errors.append(str(error))

        thread = threading.Thread(target=call)
        thread.start()
        thread.join(5)
        self.assertEqual(len(errors), 3)
