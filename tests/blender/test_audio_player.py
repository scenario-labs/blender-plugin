# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Installed offline audio player: a real child Blender on synthetic media, never audible.

Most children run the installed worker through a shim that replaces only
``aud.Device`` with a recording output, so request parsing, decoding, reports,
the lifeline and exit codes are the worker's own and nothing reaches a sound
device. One test runs the unmodified worker on Blender's None output, which
accepts a sound but never plays it. Fixtures are generated here with
Blender's audio module or Python's wave module, or are the documented
first-party files under tests/fixtures/synthetic.
"""

import json
import math
import shutil
import struct
import tempfile
import time
import unittest
import wave
from pathlib import Path

import aud
import bpy
from helpers import FIXTURES, addon_name, submodule

RATE = 44100
SHIM = '''\
"""Test shim: the installed audio player worker with a recording, silent output."""
import importlib.util
import json
import time

import aud

WORKER = {worker!r}
RECORD = {record!r}
SECONDS = {seconds!r}


def note(*values):
    with open(RECORD, "a", encoding="utf-8") as stream:
        stream.write(json.dumps(values) + "\\n")


class Handle:
    def __init__(self):
        self.started, self.stopped = time.monotonic(), False

    def done(self):
        return time.monotonic() - self.started >= SECONDS

    @property
    def status(self):
        return aud.STATUS_INVALID if self.stopped or self.done() else aud.STATUS_PLAYING

    def stop(self):
        if not self.stopped and not self.done():
            note("stop")
        self.stopped = True
        return True


class Device:
    def __init__(self, name):
        note("device", name)

    def play(self, sound):
        rate, channels = sound.specs
        note("play", rate, channels)
        return Handle()


aud.Device = Device
spec = importlib.util.spec_from_file_location("audio_player_worker", WORKER)
worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)
worker.main()
'''
# A worker that starts but never reports, for the start timeout.
SILENT = "import time\ntime.sleep(60)\n"


def tone_wav(path, *, rate=8000, seconds=1.0, amplitude=0.5):
    frames = int(rate * seconds)
    values = (
        round(32767 * amplitude * math.sin(2 * math.pi * 220 * frame / rate))
        for frame in range(frames)
    )
    with wave.open(str(path), "wb") as sound:
        sound.setparams((1, 2, rate, 0, "NONE", "not compressed"))
        sound.writeframes(struct.pack(f"<{frames}h", *values))
    return path


def tone(path, container, codec, sample_format, *, channels=2, seconds=1.0):
    sound = aud.Sound.sine(440, RATE).limit(0, seconds).volume(0.5)
    layout = aud.CHANNELS_STEREO if channels == 2 else aud.CHANNELS_MONO
    if channels == 2:
        sound = sound.rechannel(2)
    sound.write(str(path), RATE, layout, sample_format, container, codec, 192000, 4096)
    return path


def media(directory):
    """One synthetic file per saved audio type that Play audio accepts."""
    files = {
        "wav": tone_wav(directory / "tone.wav"),
        "mp3": tone(directory / "tone.mp3", aud.CONTAINER_MP3, aud.CODEC_MP3, aud.FORMAT_S16),
        "ogg": tone(
            directory / "tone.ogg", aud.CONTAINER_OGG, aud.CODEC_VORBIS, aud.FORMAT_FLOAT32
        ),
        "flac": tone(
            directory / "tone.flac",
            aud.CONTAINER_FLAC,
            aud.CODEC_FLAC,
            aud.FORMAT_S16,
            channels=1,
        ),
        "aac": tone(directory / "tone.aac", aud.CONTAINER_AAC, aud.CODEC_AAC, aud.FORMAT_FLOAT32),
    }
    # ISO media with AAC, the container of M4A results: a documented fixture.
    files["m4a"] = directory / "tone.m4a"
    shutil.copyfile(FIXTURES / "synthetic/film-four-seconds-audio.mp4", files["m4a"])
    return files


def recording_spec(directory, *, seconds, device="Test", **options):
    """A spec whose child runs the installed worker with a recording output."""
    spec = submodule("blender.runtime").audio_player_spec(device)
    record = directory / "record.jsonl"
    shim = directory / "shim.py"
    shim.write_text(
        SHIM.format(worker=str(spec.worker), record=str(record), seconds=float(seconds)),
        encoding="utf-8",
    )
    module = submodule("core.jobs.audio_player")
    return module.PlayerSpec(spec.binary, shim, device, **options), record


def notes(record):
    if not record.exists():
        return []
    return [tuple(json.loads(line)) for line in record.read_text(encoding="utf-8").splitlines()]


class AudioPlayerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.player = submodule("core.jobs.audio_player")
        directory = bpy.utils.extension_path_user(addon_name(), path="test-players", create=True)
        cls.temp = tempfile.TemporaryDirectory(dir=directory)
        cls.base = Path(cls.temp.name).resolve()
        (cls.base / "media").mkdir()
        cls.media = media(cls.base / "media")

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.work = Path(tempfile.mkdtemp(dir=self.base))
        self.addCleanup(shutil.rmtree, self.work, True)
        self.root = self.work / "players"
        self.started = []
        self.addCleanup(self.stop_all)

    def stop_all(self):
        for player in self.started:
            player.wait()

    def start(self, source, spec):
        player = self.player.start(source, self.root, spec)
        self.started.append(player)
        return player

    def settle(self, player, predicate, timeout=30):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            player.poll()
            if predicate():
                return
            time.sleep(0.02)
        self.fail(f"The audio player did not settle: {player.phase} {player.reason}")

    def assert_released(self, player):
        # The player's watcher thread removes the directory once the child exits.
        self.settle(player, lambda: player.released)
        self.assertTrue(player.exited)
        self.assertFalse(player.directory.exists())
        self.assertEqual(list(self.root.iterdir()), [])

    def test_each_saved_audio_type_plays_on_the_named_output_until_it_ends(self):
        expected = {"wav": 1.0, "mp3": 1.0, "ogg": 1.0, "flac": 1.0, "aac": 1.0, "m4a": 4.0}
        for name, path in self.media.items():
            with self.subTest(media=name):
                directory = Path(tempfile.mkdtemp(dir=self.work))
                spec, record = recording_spec(directory, seconds=0.3)
                player = self.start(path, spec)
                self.assertEqual(player.phase, self.player.STARTING)
                self.settle(player, lambda player=player: player.phase != self.player.STARTING)
                self.assertEqual(player.phase, self.player.PLAYING, player.reason)
                # Containers declare an estimated length; it is close to the tone's.
                self.assertAlmostEqual(player.seconds, expected[name], delta=0.15)
                self.settle(player, lambda player=player: not player.active)
                self.assertEqual(player.phase, self.player.ENDED, player.reason)
                rate, channels = aud.Sound(str(path)).specs
                self.assertEqual(notes(record), [("device", "Test"), ("play", rate, channels)])
                self.assert_released(player)

    def test_stop_ends_playback_at_once_and_removes_the_childs_directory(self):
        spec, record = recording_spec(self.work, seconds=60)
        player = self.start(self.media["wav"], spec)
        self.settle(player, lambda: player.phase == self.player.PLAYING)
        self.assertFalse(player.released)  # A running child keeps its directory.
        self.assertTrue(player.directory.exists())
        started = time.monotonic()
        player.stop()
        self.assertEqual(player.phase, self.player.STOPPED)
        self.assertFalse(player.active)
        self.settle(player, lambda: player.exited, timeout=10)
        # Terminated, not killed after the grace period.
        self.assertLess(time.monotonic() - started, self.player.STOP_GRACE)
        self.assertEqual(player.phase, self.player.STOPPED)
        self.assert_released(player)

    def test_closing_standard_input_stops_the_child_like_a_parent_exit(self):
        spec, record = recording_spec(self.work, seconds=60)
        player = self.start(self.media["wav"], spec)
        self.settle(player, lambda: player.phase == self.player.PLAYING)
        # A parent that exits or crashes closes its end of the pipe without a signal.
        player._process.stdin.close()
        self.assertEqual(player._process.wait(timeout=10), 0)
        self.assertEqual(notes(record)[-1], ("stop",))
        self.settle(player, lambda: player.phase == self.player.ENDED)
        self.assert_released(player)

    def test_undecodable_or_too_long_audio_fails_before_any_output_opens(self):
        bad = self.work / "bad.mp3"
        bad.write_bytes(b"ID3\x04" + b"\x00" * 128)
        cases = {
            "unreadable": (bad, {}, "Blender could not decode this audio"),
            "missing": (self.work / "absent.wav", {}, "Blender could not decode this audio"),
            "too long": (self.media["m4a"], {"max_seconds": 2}, "system player"),
        }
        for name, (path, options, reason) in cases.items():
            with self.subTest(case=name):
                directory = Path(tempfile.mkdtemp(dir=self.work))
                spec, record = recording_spec(directory, seconds=60, **options)
                player = self.start(path, spec)
                self.settle(player, lambda player=player: not player.active)
                self.assertEqual(player.phase, self.player.FAILED)
                self.assertIn(reason, player.reason)
                self.assertNotIn(str(path), player.reason)
                self.assertEqual(notes(record), [])  # No output device was opened.
                self.assert_released(player)

    def test_the_unmodified_worker_reports_blenders_none_output_as_unplayable(self):
        spec = submodule("blender.runtime").audio_player_spec("None")
        player = self.start(self.media["wav"], spec)
        self.settle(player, lambda: not player.active)
        self.assertEqual(player.phase, self.player.FAILED)
        self.assertEqual(
            player.reason, "Blender could not play through the audio output chosen in Preferences"
        )
        self.assert_released(player)

    def test_a_child_that_never_reports_is_stopped_at_its_start_timeout(self):
        silent = self.work / "silent.py"
        silent.write_text(SILENT, encoding="utf-8")
        binary = submodule("blender.runtime").audio_player_spec("Test").binary
        spec = self.player.PlayerSpec(binary, silent, "Test", start_timeout=1.0)
        player = self.start(self.media["wav"], spec)
        self.settle(player, lambda: not player.active)
        self.assertEqual(player.phase, self.player.FAILED)
        self.assertIn("did not start in time", player.reason)
        self.assert_released(player)

    def test_a_missing_executable_or_worker_refuses_before_any_child_starts(self):
        spec = submodule("blender.runtime").audio_player_spec("Test")
        for name, (binary, worker) in {
            "executable": (self.work / "absent-blender", spec.worker),
            "worker": (spec.binary, self.work / "absent-worker.py"),
        }.items():
            with self.subTest(missing=name):
                missing = self.player.PlayerSpec(binary, worker, "Test")
                with self.assertRaisesRegex(self.player.AudioPlayerError, "executable"):
                    self.player.start(self.media["wav"], self.root, missing)
        self.assertFalse(self.root.exists())

    def test_the_runtime_resolves_the_installed_worker_and_this_blender(self):
        spec = submodule("blender.runtime").audio_player_spec("CoreAudio")
        self.assertEqual(spec.binary, Path(bpy.app.binary_path).resolve())
        self.assertEqual(spec.worker.name, "audio_player_worker.py")
        self.assertTrue(spec.worker.is_file())
        self.assertEqual(spec.device, "CoreAudio")
        self.assertEqual(spec.max_seconds, 600)


if __name__ == "__main__":
    unittest.main()
