# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Installed Play, Play in Blender and waveform controls for saved shared results.

Waveforms decode in the real offline Blender child. Players are patched: the
system opener and the animation player process are recorded, never launched.
Nothing contacts Scenario; drawing is checked through recording layouts, not
physical input.
"""

import hashlib
import io
import math
import os
import stat
import struct
import subprocess
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
from helpers import draw_job_panels, drawn_texts, online_access, submodule, temp_credentials

MP4 = b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isomiso2" + b"\x00" * 64


def tone(seconds=0.25, rate=8000, amplitude=0.5):
    """Synthetic mono PCM: a 200 Hz tone generated here, never recorded media."""
    frames = int(seconds * rate)
    values = [
        round(32767 * amplitude * math.sin(2 * math.pi * 200 * frame / rate))
        for frame in range(frames)
    ]
    stream = io.BytesIO()
    with wave.open(stream, "wb") as sound:
        sound.setparams((1, 2, rate, 0, "NONE", "not compressed"))
        sound.writeframes(struct.pack(f"<{frames}h", *values))
    return stream.getvalue()


class Layout:
    """Records draw calls, including nested rows and boxes, in drawing order."""

    def __init__(self, calls=None):
        self.calls = [] if calls is None else calls

    def box(self):
        self.calls.append(("box",))
        return self

    def row(self, align=False):
        self.calls.append(("row",))
        return self

    def label(self, *, text, icon="NONE"):
        self.calls.append(("label", text, icon))

    def operator(self, idname, *, text="", icon="NONE", emboss=True):
        properties = {}
        self.calls.append(("operator", idname, text, icon, properties))
        return _Properties(properties)

    def template_icon(self, *, icon_value, scale):
        self.calls.append(("icon", icon_value, scale))


class _Properties:
    def __init__(self, properties):
        object.__setattr__(self, "_values", properties)

    def __setattr__(self, name, value):
        self._values[name] = value


class FakePlayer:
    """Stands in for Blender's animation player process."""

    def __init__(self, command, **options):
        self.command, self.options, self.code = command, options, None

    def poll(self):
        return self.code


class ResultMediaTests(unittest.TestCase):
    def setUp(self):
        import httpx

        self.runtime = submodule("blender.runtime")
        self.media = submodule("blender.result_media")
        self.recovery = submodule("blender.job_recovery")
        self.storemod = submodule("core.jobs.store")
        self.transfers = submodule("core.jobs.transfers")
        self.module = submodule("blender.job_session")
        self.enterContext(patch.object(self.runtime, "state", self.runtime.RuntimeState()))
        self.enterContext(online_access(False))
        self.prefs = self.enterContext(temp_credentials())
        source = self.prefs.credential_source
        self.addCleanup(setattr, self.prefs, "credential_source", source)
        self.prefs.credential_source = "PREFERENCES"
        root = self.enterContext(tempfile.TemporaryDirectory(dir=bpy.utils.resource_path("USER")))
        self.root = Path(root).resolve()
        self.enterContext(
            patch.object(
                self.runtime,
                "paths",
                return_value=SimpleNamespace(state_dir=self.root, cache_dir=self.root / "cache"),
            )
        )
        api = submodule("core.api.sdk_adapter")
        self.requests, self.sessions = [], []
        catalog_type, session_type = self.runtime.SDKCatalog, self.runtime.JobSession

        def respond(request):
            self.requests.append(request)
            raise AssertionError("Saved media controls must not contact Scenario")

        def adapter(credentials, **options):
            return api.SDKAdapter(credentials, transport=httpx.MockTransport(respond), **options)

        def session(*args, **options):
            value = session_type(*args, **options)
            self.sessions.append(value)
            return value

        self.enterContext(
            patch.object(
                self.runtime,
                "SDKCatalog",
                side_effect=lambda *a, **k: catalog_type(*a, adapter_factory=adapter, **k),
            )
        )
        self.enterContext(patch.object(self.runtime, "JobSession", side_effect=session))
        self.opened = []
        self.enterContext(patch.object(self.media, "_system_open", side_effect=self.open))
        self.players = []
        # subprocess is shared: only the animation player is faked, while the
        # offline waveform decoder still starts its real child process.
        self.popen = subprocess.Popen
        self.enterContext(patch.object(subprocess, "Popen", side_effect=self.launch))
        self.media.controller.retire()
        self.addCleanup(self.cleanup)

    def open(self, path):
        self.opened.append(path)
        return {"FINISHED"}

    def launch(self, command, **options):
        if len(command) != 3 or command[1] != "-a":
            return self.popen(command, **options)
        player = FakePlayer(command, **options)
        self.players.append(player)
        return player

    def cleanup(self):
        for player in self.players:
            player.code = 0
        self.media.controller.poll()
        self.media.controller.retire()
        self.runtime.state.reset()
        for session in self.sessions:
            session.shutdown()

    def saved(self, assets, request_id="request"):
        """A READY job whose receipts match private local bytes; the projected view."""
        m = self.storemod
        store = self.runtime.ensure_job_store()
        session = self.runtime.ensure_job_session()
        current = store.create(
            m.JobIntent(
                request_id,
                store.scope,
                m.JobOrigin("file", "scene", "revision"),
                "model",
                "model",
                "a" * 64,
                "b" * 64,
                "0.10000000000000001",
            )
        )
        for state in (m.JobState.SUBMITTING, m.JobState.REMOTE, m.JobState.SUCCEEDED):
            current = store.transition(
                request_id,
                expected_revision=current.revision,
                state=state,
                remote_job_id="remote" if state == m.JobState.REMOTE else None,
            )
        manifest = tuple(
            m.ResultAsset(asset_id, name, media_type, len(data))
            for asset_id, name, media_type, data in assets
        )
        current = store.set_results(request_id, manifest, expected_revision=current.revision)
        current = store.transition(
            request_id, expected_revision=current.revision, state=m.JobState.DOWNLOADING
        )
        directory = session._coordinator._results._directory(current)
        for item, (*_, data) in zip(manifest, assets, strict=True):
            (directory / item.name).write_bytes(data)
            receipt = self.transfers.DownloadedResult(
                item.name, len(data), hashlib.sha256(data).hexdigest()
            )
            current = store.record_download(
                request_id, item.asset_id, receipt, expected_revision=current.revision
            )
        store.transition(request_id, expected_revision=current.revision, state=m.JobState.READY)
        self.results = directory
        owner = self.runtime.inspect_model_jobs()
        return owner.views[request_id]

    def control(self, view, key):
        (item,) = [item for item in self.recovery.result_actions(view) if item.key == key]
        return item

    def args(self, view, key):
        return dict(self.control(view, key).properties)

    def settle(self, predicate, timeout=30):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            # The same maintenance entry points as GUI timers.
            self.module.reap_retired()
            self.media.controller.poll()
            if predicate():
                return
            time.sleep(0.01)
        selected = self.media.controller.selection
        detail = None if selected is None else (selected.status, selected.message)
        self.fail(f"Saved media did not settle: {detail}")

    def play(self, view, key):
        args = self.args(view, key)
        self.media.controller.play(
            args["context_id"],
            args["request_id"],
            args["expected_revision"],
            args["asset_id"],
            args["player"],
        )
        self.settle(lambda: self.media.controller._play is None)

    def waveform(self, view, key="waveform:sound"):
        self.assertEqual(
            bpy.ops.scenario.preview_saved_waveform(**self.args(view, key)), {"FINISHED"}
        )
        return self.media.controller.selection

    def playback_root(self):
        return self.root / "cache" / "media-playback"

    def copies(self):
        root = self.playback_root()
        return sorted(path.name for path in root.iterdir()) if root.exists() else []

    # -- descriptors --------------------------------------------------------

    def test_restarted_rows_offer_play_and_waveform_from_their_media_types(self):
        view = self.saved(
            [
                ("clip", "clip.mp4", "video/mp4", MP4),
                ("sound", "sound.wav", "audio/wav", tone()),
            ]
        )
        self.assertEqual(view.kind, "model")  # A restarted generic row, not a lane kind.
        labels = [item.label for item in self.recovery.result_actions(view)]
        self.assertEqual(
            labels,
            [
                "Add video strip (1)",
                "Add audio strip (2)",
                "Play video (1)",
                "Play in Blender (1)",
                "Play audio (2)",
                "Waveform (2)",
                "Downloaded result awaits application review",
            ],
        )
        layout = Layout()
        self.recovery.draw_controls(layout, view)
        rows = [index for index, call in enumerate(layout.calls) if call == ("row",)]
        self.assertEqual(len(rows), 2)
        operators = [call[2] for call in layout.calls if call[0] == "operator"]
        self.assertEqual(operators, labels[:-1])
        self.assertFalse(bpy.ops.scenario.play_saved_media.poll())  # No player in background.
        self.assertEqual(self.requests, [])

    # -- play -----------------------------------------------------------------

    def test_play_opens_a_private_canonical_copy_and_reuses_it(self):
        view = self.saved([("clip", "run.command", "video/mp4", MP4)])
        self.play(view, "play:clip")
        (opened,) = self.opened
        path = Path(opened)
        self.assertEqual(path.name, "media.mp4")
        self.assertTrue(path.parent.name.startswith("play-"))
        self.assertEqual(path.parent.parent.resolve(), self.playback_root().resolve())
        self.assertFalse(path.resolve().is_relative_to(self.results.resolve()))
        self.assertEqual(path.read_bytes(), MP4)
        if os.name != "nt":
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o400)
            self.assertEqual(stat.S_IMODE(path.parent.stat().st_mode), 0o700)
        self.assertIn("system player", self.runtime.state.last_message)
        self.play(view, "play:clip")
        self.assertEqual(self.opened, [opened, opened])
        self.assertEqual(len(self.copies()), 1)
        self.assertEqual((self.results / "run.command").read_bytes(), MP4)
        self.assertEqual(self.requests, [])

    def test_play_in_blender_starts_a_scrubbed_animation_player_that_pins_its_copy(self):
        view = self.saved(
            [
                ("clip", "clip.mp4", "video/mp4", MP4),
                ("sound", "sound.wav", "audio/wav", tone()),
            ]
        )
        with patch.dict(os.environ, {"SCENARIO_API_KEY": "fixture-secret"}):
            self.play(view, "play_in_blender:clip")
        (player,) = self.players
        binary, flag, path = player.command
        self.assertEqual(flag, "-a")
        self.assertEqual(Path(binary).resolve(), Path(bpy.app.binary_path).resolve())
        self.assertEqual(Path(path).name, "media.mp4")
        self.assertEqual(player.options["cwd"], str(Path(path).parent))
        self.assertNotIn("SCENARIO_API_KEY", player.options["env"])
        self.assertFalse(any(key.upper().startswith("PYTHON") for key in player.options["env"]))
        for stream in ("stdin", "stdout", "stderr"):
            self.assertIs(player.options[stream], subprocess.DEVNULL)
        # A full cache never evicts the copy a running player reads.
        with patch.object(self.media, "COPY_LIMIT", 1):
            self.play(view, "play:sound")
            self.assertTrue(Path(path).is_file())
            self.assertEqual(len(self.copies()), 2)
            player.code = 0
            self.media.controller.poll()
            self.assertFalse(Path(path).exists())
        self.assertEqual(len(self.copies()), 1)
        with self.assertRaisesRegex(self.media.MediaError, "video"):
            args = self.args(view, "play:sound")
            self.media.controller.play(
                args["context_id"], "request", args["expected_revision"], "sound", "BLENDER"
            )

    def test_the_oldest_unused_copy_is_evicted_before_a_new_one(self):
        view = self.saved(
            [
                ("clip", "clip.mp4", "video/mp4", MP4),
                ("sound", "sound.wav", "audio/wav", tone()),
            ]
        )
        with patch.object(self.media, "COPY_LIMIT", 1):
            self.play(view, "play:clip")
            (first,) = self.copies()
            self.play(view, "play:sound")
            (second,) = self.copies()
        self.assertNotEqual(first, second)
        self.assertEqual([Path(path).name for path in self.opened], ["media.mp4", "media.wav"])

    def test_at_most_two_animation_players_run_at_once(self):
        view = self.saved([("clip", "clip.mp4", "video/mp4", MP4)])
        self.play(view, "play_in_blender:clip")
        self.play(view, "play_in_blender:clip")
        self.assertEqual(len(self.players), 2)
        args = self.args(view, "play_in_blender:clip")
        with self.assertRaisesRegex(self.media.MediaError, "Close"):
            self.media.controller.play(
                args["context_id"], "request", args["expected_revision"], "clip", "BLENDER"
            )
        self.players[0].code = 0
        self.play(view, "play_in_blender:clip")
        self.assertEqual(len(self.players), 3)

    def test_a_tampered_saved_file_is_reported_and_controls_remain(self):
        view = self.saved([("clip", "clip.mp4", "video/mp4", MP4)])
        (self.results / "clip.mp4").write_bytes(MP4[:-1] + b"\x01")
        self.play(view, "play:clip")
        self.assertEqual(self.opened, [])
        self.assertIn("no longer matches its receipt", self.runtime.state.last_message)
        self.assertEqual(self.copies(), [])
        self.assertIn("Play video (1)", [item.label for item in self.recovery.result_actions(view)])

    def test_stale_foreign_or_unsupported_requests_are_refused_before_copying(self):
        view = self.saved(
            [
                ("clip", "clip.mp4", "video/mp4", MP4),
                ("image", "image.png", "image/png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 32),
            ]
        )
        args = self.args(view, "play:clip")
        controller = self.media.controller
        cases = {
            "connection": (dict(args, context_id="another-context"), "SYSTEM"),
            "revision": (dict(args, expected_revision=args["expected_revision"] + 1), "SYSTEM"),
            "image": (dict(args, asset_id="image"), "SYSTEM"),
            "missing": (dict(args, asset_id="absent"), "SYSTEM"),
            "player": (args, "OTHER"),
        }
        for name, (values, player) in cases.items():
            with self.subTest(name=name), self.assertRaises(self.media.MediaError):
                controller.play(
                    values["context_id"],
                    values["request_id"],
                    values["expected_revision"],
                    values["asset_id"],
                    player,
                )
        with patch.object(self.media, "_blender_binary", return_value=None):
            with self.assertRaisesRegex(self.media.MediaError, "executable"):
                controller.play(
                    args["context_id"], "request", args["expected_revision"], "clip", "BLENDER"
                )
        self.assertEqual(self.copies(), [])
        self.assertIsNone(controller._play)

    def test_a_late_copy_after_a_connection_change_is_discarded_unopened(self):
        view = self.saved([("clip", "clip.mp4", "video/mp4", MP4)])
        args = self.args(view, "play:clip")
        task = self.media.controller.play(
            args["context_id"], "request", args["expected_revision"], "clip", "SYSTEM"
        )
        task.result(10)
        self.runtime.state.reset()  # Credentials, project or file changed.
        self.settle(lambda: not self.media.controller.loading)
        self.assertEqual(self.opened, [])
        self.assertEqual(self.copies(), [])

    def test_retirement_and_file_load_remove_copies_except_a_running_players(self):
        view = self.saved([("clip", "clip.mp4", "video/mp4", MP4)])
        self.play(view, "play:clip")
        self.assertEqual(len(self.copies()), 1)
        self.media._file_load(None)
        self.assertEqual(self.copies(), [])
        view = self.runtime.inspect_model_jobs().views["request"]
        self.play(view, "play_in_blender:clip")
        self.runtime.state.reset()
        self.assertEqual(len(self.copies()), 1)  # Its player still reads it.
        self.players[-1].code = 0
        self.media.controller.poll()
        self.assertEqual(self.copies(), [])

    def test_a_player_that_exits_after_a_file_load_releases_its_copy(self):
        view = self.saved([("clip", "clip.mp4", "video/mp4", MP4)])
        self.play(view, "play_in_blender:clip")
        self.media._file_load(None)
        self.assertEqual(len(self.copies()), 1)  # Its player still reads it.
        # The player exits before any timer tick reaps it; unregistering then
        # must not mistake it for a running player and leave its copy behind.
        self.players[-1].code = 0
        self.media.controller.shutdown()
        self.assertEqual(self.copies(), [])

    def test_the_update_timer_survives_file_loads(self):
        # Blender drops nonpersistent timers on a file load, which would leave a
        # running animation player unreaped. Background Blender registers none.
        registered = []
        timers = SimpleNamespace(
            is_registered=lambda function: False,
            unregister=lambda function: None,
            register=lambda function, **options: registered.append((function, options)),
        )
        app = SimpleNamespace(background=False, timers=timers)
        with patch.object(self.media, "bpy", SimpleNamespace(app=app)):
            self.media._start_timer()
        self.assertEqual(
            registered,
            [
                (
                    self.media._tick,
                    {"first_interval": self.media.LOADING_INTERVAL, "persistent": True},
                )
            ],
        )

    # -- waveform -------------------------------------------------------------

    def test_waveform_decodes_offline_and_draws_from_cached_state(self):
        sound = tone()
        view = self.saved([("sound", "sound.wav", "audio/wav", sound)])
        record = self.runtime.state.job_store.get("request")
        selected = self.waveform(view)
        self.assertEqual(selected.status, "LOADING")
        self.settle(lambda: selected.status != "LOADING")
        self.assertEqual(selected.status, "READY", selected.message)
        self.assertEqual(selected.label, "Audio (1)")
        self.assertEqual(selected.message, "Verified saved audio · 0.25 s · Mono · 8 kHz")
        self.assertGreaterEqual(selected.icon_id, 0)  # Background builds have no drawable ID.
        icon = self.media.controller._previews["waveform"]
        self.assertEqual(tuple(icon.image_size), (256, 96))
        self.assertGreater(max(icon.image_pixels_float), 0)
        self.assertAlmostEqual(selected.envelope.overall_peak, 0.5, delta=0.01)
        self.assertEqual((self.results / "sound.wav").read_bytes(), sound)
        self.assertEqual(self.runtime.state.job_store.get("request"), record)
        self.assertEqual(self.requests, [])
        layout = Layout()
        store = self.runtime.state.job_store
        refuse = AssertionError("drawing read or started jobs")
        with (
            patch.object(store, "get", side_effect=refuse),
            patch.object(self.runtime, "ensure_job_session", side_effect=refuse),
            patch.object(os, "open", side_effect=refuse),
            patch.object(os, "stat", side_effect=refuse),
            patch.object(os, "lstat", side_effect=refuse),
        ):
            self.recovery.draw_controls(layout, view)
        box = layout.calls.index(("box",))
        self.assertEqual(layout.calls[box + 2][:3], ("label", "Waveform: Audio (1)", "SOUND"))
        self.assertEqual(layout.calls[box + 3][:2], ("operator", "scenario.close_saved_waveform"))
        self.assertEqual(layout.calls[-1][0], "icon")
        self.assertEqual(selected.status, "READY")

    def test_waveform_draw_scales_with_blenders_custom_ui_scale(self):
        view = self.saved([("sound", "sound.wav", "audio/wav", tone())])
        selected = self.waveform(view)
        self.settle(lambda: selected.status == "READY")

        def draw(preferences, width=800):
            layout = Layout()
            context = SimpleNamespace(region=SimpleNamespace(width=width), preferences=preferences)
            with patch.object(self.media, "bpy", SimpleNamespace(context=context)):
                self.media.draw(layout, view)
            return layout.calls

        # Blender 5.2.1 on Retina at a resolution scale of 2 reports system.ui_scale
        # 4 and pixel size 4; multiplying by the resolution scale would size for 8.
        retina = SimpleNamespace(
            system=SimpleNamespace(ui_scale=4.0, pixel_size=4.0),
            view=SimpleNamespace(ui_scale=2.0),
        )
        calls = draw(retina)
        self.assertEqual(calls, draw(SimpleNamespace(system=SimpleNamespace(ui_scale=4.0))))
        columns = int((800 / 4 - 80) / 7)
        lines = textwrap.wrap(selected.message, width=columns)
        self.assertEqual(
            [call for call in calls if call[0] in ("label", "icon")],
            [
                ("label", "Waveform: Audio (1)", "SOUND"),
                ("label", lines[0], "INFO"),
                *(("label", line, "NONE") for line in lines[1:]),
                ("icon", selected.icon_id, 6.0),
            ],
        )
        # Background Blender reports a custom-interface scale of 0; draw uses 1.
        self.assertEqual(
            draw(SimpleNamespace(system=SimpleNamespace(ui_scale=0.0))),
            draw(SimpleNamespace(system=SimpleNamespace(ui_scale=1.0))),
        )

    def blocked_decode(self):
        """Hold the offline decoder until it is canceled, like a long decode."""
        decoder = submodule("core.jobs.audio_decode")
        canceled = submodule("core.jobs.local_render").RenderCancelled
        started, stopped = threading.Event(), []

        def run(command, *, cancel, **options):
            started.set()
            if not cancel.wait(10):
                raise AssertionError("The waveform decoder was not canceled")
            stopped.append(threading.current_thread().name)
            raise canceled("Local capture cancelled")

        patcher = patch.object(decoder, "_run", side_effect=run)
        patcher.start()
        self.addCleanup(patcher.stop)
        return started, stopped, patcher

    def test_cancel_terminates_the_decode_and_retry_decodes_again(self):
        view = self.saved([("sound", "sound.wav", "audio/wav", tone())])
        started, stopped, patcher = self.blocked_decode()
        selected = self.waveform(view)
        self.settle(started.is_set)
        self.assertTrue(bpy.ops.scenario.cancel_saved_waveform.poll())
        self.assertEqual(bpy.ops.scenario.cancel_saved_waveform(), {"FINISHED"})
        self.assertEqual((selected.status, selected.message), ("CANCELED", "Waveform canceled"))
        self.settle(lambda: stopped == ["ScenarioPreview"])
        self.settle(self.idle)
        self.assertEqual(selected.status, "CANCELED")
        self.assertEqual(selected.icon_id, 0)
        self.assertFalse(bpy.ops.scenario.cancel_saved_waveform.poll())
        layout = Layout()
        self.media.draw(layout, view)
        retry = [call for call in layout.calls if call[0] == "operator" and call[2] == "Retry"]
        (retry,) = retry
        self.assertEqual(retry[4], self.args(view, "waveform:sound"))
        patcher.stop()
        selected = self.waveform(view)
        self.settle(lambda: selected.status != "LOADING")
        self.assertEqual(selected.status, "READY", selected.message)

    def idle(self):
        return self.runtime.state.job_session._workers.previews_idle

    def test_selecting_another_result_shows_only_the_latest(self):
        view = self.saved(
            [
                ("first", "first.wav", "audio/wav", tone(amplitude=0.25)),
                ("second", "second.wav", "audio/wav", tone(amplitude=0.75)),
            ]
        )
        self.waveform(view, "waveform:first")
        selected = self.waveform(view, "waveform:second")
        self.assertIs(self.media.controller.selection, selected)
        self.settle(lambda: selected.status != "LOADING")
        self.assertEqual(selected.status, "READY", selected.message)
        self.assertEqual(selected.label, "Audio (2)")
        self.assertAlmostEqual(selected.envelope.overall_peak, 0.75, delta=0.01)

    def test_close_hides_the_waveform_and_releases_its_icon(self):
        view = self.saved([("sound", "sound.wav", "audio/wav", tone())])
        selected = self.waveform(view)
        self.settle(lambda: selected.status == "READY")
        self.assertEqual(bpy.ops.scenario.close_saved_waveform(), {"FINISHED"})
        self.assertIsNone(self.media.controller.selection)
        self.assertIsNone(self.media.controller._previews)
        layout = Layout()
        self.media.draw(layout, view)
        self.assertEqual(layout.calls, [])

    def test_context_change_or_file_load_retires_the_waveform(self):
        view = self.saved([("sound", "sound.wav", "audio/wav", tone())])
        for retire in ("reset", "file-load"):
            with self.subTest(retire=retire):
                selected = self.waveform(view)
                self.settle(lambda selected=selected: selected.status == "READY")
                if retire == "reset":
                    self.runtime.state.reset()
                    self.media.controller.poll()
                else:
                    self.media._file_load(None)
                self.assertIsNone(self.media.controller.selection)
                self.assertIsNone(self.media.controller._previews)
                view = self.runtime.inspect_model_jobs().views["request"]

    def test_waveform_refuses_video_missing_executable_and_stale_requests(self):
        view = self.saved(
            [
                ("clip", "clip.mp4", "video/mp4", MP4),
                ("sound", "sound.wav", "audio/wav", tone()),
            ]
        )
        args = self.args(view, "waveform:sound")
        controller = self.media.controller
        with self.assertRaisesRegex(self.media.MediaError, "audio"):
            controller.select_waveform(
                args["context_id"], "request", args["expected_revision"], "clip"
            )
        with self.assertRaises(self.media.MediaError):
            controller.select_waveform("another", "request", args["expected_revision"], "sound")
        with patch.object(self.runtime, "waveform_spec", return_value=None):
            with self.assertRaisesRegex(self.media.MediaError, "executable"):
                controller.select_waveform(
                    args["context_id"], "request", args["expected_revision"], "sound"
                )
        self.assertIsNone(controller.selection)

    def test_an_undecodable_saved_audio_reports_an_error_with_retry(self):
        view = self.saved([("sound", "sound.mp3", "audio/mpeg", b"ID3\x04" + b"\x00" * 128)])
        selected = self.waveform(view)
        self.settle(lambda: selected.status != "LOADING")
        self.assertEqual(selected.status, "ERROR")
        self.assertEqual(selected.message, "Blender could not decode this audio")
        self.assertIn("Play audio (1)", [item.label for item in self.recovery.result_actions(view)])

    def test_jobs_panel_draws_the_waveform_without_storage_reads(self):
        view = self.saved([("sound", "sound.wav", "audio/wav", tone())])
        selected = self.waveform(view)
        self.settle(lambda: selected.status == "READY")
        with patch.object(self.media, "draw", wraps=self.media.draw) as draw:
            _, jobs, _, _ = draw_job_panels()
        self.assertIn(view, [call.args[1] for call in draw.call_args_list])
        texts = drawn_texts(jobs)
        self.assertIn("Waveform: Audio (1)", texts)
        self.assertIn("Waveform (1)", texts)

    def test_controller_rejects_worker_threads(self):
        errors = []

        def call():
            for method in (
                self.media.controller.poll,
                self.media.controller.retire,
                self.media.controller.cancel_waveform,
            ):
                try:
                    method()
                except RuntimeError as error:
                    errors.append(str(error))

        thread = threading.Thread(target=call)
        thread.start()
        thread.join(5)
        self.assertEqual(len(errors), 3)

    def test_unregister_style_shutdown_leaves_running_players_alone(self):
        view = self.saved([("clip", "clip.mp4", "video/mp4", MP4)])
        self.play(view, "play_in_blender:clip")
        self.play(view, "play:clip")
        controller = self.media.controller
        controller.shutdown()
        self.assertEqual(len(self.copies()), 1)
        self.assertEqual(controller._players, [])


if __name__ == "__main__":
    unittest.main()
