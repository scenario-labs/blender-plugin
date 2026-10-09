# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Installed offline waveform decoder: a real child Blender on synthetic media, no service.

Fixtures are generated here with Blender's audio module or Python's wave module,
or are the documented first-party files under tests/fixtures/synthetic.
"""

import math
import shutil
import struct
import tempfile
import threading
import time
import unittest
import wave
from pathlib import Path

import aud
import bpy
from helpers import FIXTURES, addon_name, submodule

RATE = 44100


def tone_wav(path, *, rate=8000, seconds=0.5, amplitude=0.5):
    frames = int(rate * seconds)
    values = (
        round(32767 * amplitude * math.sin(2 * math.pi * 220 * frame / rate))
        for frame in range(frames)
    )
    with wave.open(str(path), "wb") as sound:
        sound.setparams((1, 2, rate, 0, "NONE", "not compressed"))
        sound.writeframes(struct.pack(f"<{frames}h", *values))
    return path


def tone(path, container, codec, sample_format, *, channels=2, seconds=1.0, amplitude=0.5):
    sound = aud.Sound.sine(440, RATE).limit(0, seconds).volume(amplitude)
    layout = aud.CHANNELS_STEREO if channels == 2 else aud.CHANNELS_MONO
    if channels == 2:
        sound = sound.rechannel(2)
    sound.write(str(path), RATE, layout, sample_format, container, codec, 192000, 4096)
    return path


class WaveformWorkerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.decoder = submodule("core.jobs.audio_decode")
        cls.audio = submodule("core.audio_waveform")
        cls.spec = submodule("blender.runtime").waveform_spec()
        directory = bpy.utils.extension_path_user(addon_name(), path="test-waveforms", create=True)
        cls.temp = tempfile.TemporaryDirectory(dir=directory)
        cls.root = Path(cls.temp.name).resolve()
        media = cls.root / "media"
        media.mkdir()
        cls.media = {
            "pcm16.wav": tone_wav(media / "pcm16.wav"),
            "pcm24.wav": tone(
                media / "pcm24.wav", aud.CONTAINER_WAV, aud.CODEC_PCM, aud.FORMAT_S24
            ),
            "mp3": tone(media / "tone.mp3", aud.CONTAINER_MP3, aud.CODEC_MP3, aud.FORMAT_S16),
            "ogg": tone(
                media / "tone.ogg", aud.CONTAINER_OGG, aud.CODEC_VORBIS, aud.FORMAT_FLOAT32
            ),
            "flac": tone(
                media / "tone.flac",
                aud.CONTAINER_FLAC,
                aud.CODEC_FLAC,
                aud.FORMAT_S16,
                channels=1,
            ),
            "matroska-aac": tone(
                media / "tone.mka", aud.CONTAINER_MATROSKA, aud.CODEC_AAC, aud.FORMAT_FLOAT32
            ),
        }
        # ISO media with AAC, the container of M4A results: a documented fixture.
        cls.media["m4a"] = media / "tone.m4a"
        shutil.copyfile(FIXTURES / "synthetic/film-four-seconds-audio.mp4", cls.media["m4a"])

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.work = Path(tempfile.mkdtemp(dir=self.root))
        self.addCleanup(shutil.rmtree, self.work, True)

    def decode(self, path, spec=None, **options):
        cancel = options.pop("cancel", threading.Event())
        result = self.decoder.decode(path, self.work, spec or self.spec, cancel=cancel, **options)
        self.assertEqual(list(self.work.iterdir()), [], "The decode directory must be removed")
        return result

    def reference(self, path, bins):
        """Reduce this Blender's own decode in process, the slow but obvious way."""
        sound = aud.Sound(str(path))
        rate, channels = sound.specs
        samples = sound.data()
        builder = self.audio.EnvelopeBuilder(int(rate), channels)
        builder.add(memoryview(samples.reshape(-1)))
        return builder.finish(bins)

    def test_spec_points_at_the_installed_worker_and_this_blender(self):
        self.assertIsNotNone(self.spec)
        installed = Path(submodule("blender.runtime").__file__).resolve().parent
        self.assertEqual(self.spec.worker, installed / "waveform_worker.py")
        self.assertEqual(self.spec.binary, Path(bpy.app.binary_path).resolve())

    def test_formats_decode_offline_like_an_in_process_reduction(self):
        expected = {
            "pcm16.wav": (8000, 1, 0.5),
            "pcm24.wav": (RATE, 2, 1.0),
            "mp3": (RATE, 2, 1.0),
            "ogg": (RATE, 2, 1.0),
            "flac": (RATE, 1, 1.0),
            "matroska-aac": (RATE, 2, 1.0),
            "m4a": (48000, 1, 4.0),
        }
        for name, path in self.media.items():
            with self.subTest(format=name):
                rate, channels, seconds = expected[name]
                result = self.decode(path, bins=128)
                self.assertEqual((result.sample_rate, result.channels), (rate, channels))
                # Encoder priming and padding add at most a few codec frames.
                self.assertAlmostEqual(result.seconds, seconds, delta=0.08)
                reference = self.reference(path, 128)
                self.assertEqual(result.seconds, reference.seconds)
                self.assertEqual(len(result.rms), len(reference.rms))
                for value, other in (
                    *zip(result.rms, reference.rms, strict=True),
                    *zip(result.peaks, reference.peaks, strict=True),
                    (result.overall_rms, reference.overall_rms),
                ):
                    self.assertAlmostEqual(value, other, delta=2e-6)
                self.assertFalse(result.silent)
                # Generated tones peak near 0.5; ffmpeg's sine source defaults to 1/8.
                self.assertGreater(result.overall_peak, 0.1)
                self.assertLessEqual(result.overall_rms, result.overall_peak)
                self.assertTrue(path.is_file())

    def test_generated_silence_is_flat(self):
        for name in ("audio-silence.mp3", "audio-silence.ogg"):
            with self.subTest(fixture=name):
                result = self.decode(FIXTURES / "synthetic" / name)
                self.assertTrue(result.silent)
                self.assertEqual(max(result.peaks), result.overall_rms)

    def test_undecodable_and_too_long_audio_fail_with_fixed_reasons(self):
        corrupt = self.root / "corrupt.mp3"
        corrupt.write_bytes(b"ID3" + bytes(range(256)) * 8)
        with self.assertRaisesRegex(self.audio.WaveformError, "could not decode"):
            self.decode(corrupt)
        with self.assertRaisesRegex(self.audio.WaveformError, "duration limit"):
            self.decode(self.media["m4a"], max_seconds=1)
        small = self.decoder.WaveformSpec(self.spec.binary, self.spec.worker, max_samples=48000)
        with self.assertRaisesRegex(self.audio.WaveformError, "duration limit"):
            self.decode(self.media["m4a"], small)

    def test_cancellation_and_timeout_stop_the_child(self):
        cancel = threading.Event()
        timer = threading.Timer(0.2, cancel.set)
        timer.start()
        self.addCleanup(timer.cancel)
        started = time.monotonic()
        with self.assertRaises(self.audio.WaveformCanceled):
            self.decode(self.media["mp3"], cancel=cancel)
        # Polling sees the signal within 0.1 s; terminating waits at most 3 s.
        self.assertLess(time.monotonic() - started, 5)
        quick = self.decoder.WaveformSpec(self.spec.binary, self.spec.worker, timeout=0.05)
        with self.assertRaisesRegex(self.audio.WaveformError, "timed out"):
            self.decode(self.media["mp3"], quick)

    def test_decoding_never_holds_this_blenders_python_lock(self):
        long = tone(
            self.root / "long.mp3",
            aud.CONTAINER_MP3,
            aud.CODEC_MP3,
            aud.FORMAT_S16,
            seconds=300.0,
        )
        done, outcome = threading.Event(), {}

        def run():
            try:
                outcome["value"] = self.decode(long)
            finally:
                done.set()

        thread = threading.Thread(target=run)
        started = last = time.monotonic()
        gap = 0.0
        thread.start()
        while not done.is_set():
            now = time.monotonic()
            gap, last = max(gap, now - last), now
            time.sleep(0.001)
        thread.join(5)
        elapsed = time.monotonic() - started
        self.assertAlmostEqual(outcome["value"].seconds, 300.0, delta=0.08)
        # The whole decode took longer than any pause this thread observed.
        self.assertGreater(elapsed, 0.5)
        self.assertLess(gap, 0.1)
