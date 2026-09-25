# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Synthetic PCM samples are generated here; no recorded or third-party media."""

import hashlib
import os
import threading
import wave

import pytest

from scenario.core import audio_waveform as audio


def fixture(path, *, width=2, channels=1, frames=None, rate=8000):
    limit = 1 << (width * 8 - 1)
    frames = frames if frames is not None else [(-limit,), (limit - 1,), (0,), (limit // 2,)]
    raw = bytearray()
    for frame in frames:
        for channel in range(channels):
            value = frame[channel % len(frame)]
            raw.extend(
                (value + 128).to_bytes(1, "little")
                if width == 1
                else value.to_bytes(width, "little", signed=True)
            )
    with wave.open(str(path), "wb") as sound:
        sound.setnchannels(channels)
        sound.setsampwidth(width)
        sound.setframerate(rate)
        sound.writeframes(raw)
    return path


@pytest.mark.parametrize("width", [1, 2, 3, 4])
@pytest.mark.parametrize("channels", [1, 2])
def test_pcm_depths_channels_duration_and_snapshot_digest(tmp_path, width, channels):
    path = fixture(tmp_path / "synthetic.wav", width=width, channels=channels)
    original = path.read_bytes()
    result = audio.read_waveform(path, threading.Event())
    assert result.channels == channels
    assert result.seconds == 4 / 8000
    assert result.sha256 == hashlib.sha256(original).hexdigest()
    assert result.peaks[0][0] == (-1.0, -1.0)
    assert result.peaks[0][1][1] == pytest.approx(1 - 1 / (1 << (width * 8 - 1)))
    assert result.peaks[0][2] == (0.0, 0.0)
    assert path.read_bytes() == original
    assert len(audio.raster(result)) == 256 * 96 * 4


def test_short_impulses_and_distinct_stereo_channels_survive_binning(tmp_path, monkeypatch):
    monkeypatch.setattr(audio, "BINS", 2)
    path = fixture(
        tmp_path / "stereo.wav",
        channels=2,
        frames=[(0, 0), (32767, -32768), (0, 0), (-16384, 8192)],
    )
    result = audio.read_waveform(path, threading.Event())
    assert result.peaks == (
        ((0.0, 32767 / 32768), (-0.5, 0.0)),
        ((-1.0, 0.0), (0.0, 0.25)),
    )


@pytest.mark.parametrize(
    "kind", ["missing", "corrupt", "truncated", "float", "channels", "duration", "frames"]
)
def test_invalid_media_is_rejected_with_sanitized_errors(tmp_path, kind):
    path = tmp_path / "private-name.wav"
    if kind == "corrupt":
        path.write_bytes(b"private decoder input")
    elif kind != "missing":
        fixture(
            path,
            channels=3 if kind == "channels" else 1,
            frames=[(0,)] * 601 if kind == "duration" else None,
            rate=1 if kind == "duration" else 8000,
        )
        raw = bytearray(path.read_bytes())
        if kind == "truncated":
            raw = raw[:-2]
        elif kind == "float":
            raw[20:22] = (3).to_bytes(2, "little")
        elif kind == "frames":
            raw[40:44] = ((audio.MAX_FRAMES + 1) * 2).to_bytes(4, "little")
        path.write_bytes(raw)
    with pytest.raises(audio.WaveformError) as error:
        audio.read_waveform(path, threading.Event())
    assert "private" not in str(error.value)


def test_oversized_file_is_rejected_before_reading_its_contents(tmp_path, monkeypatch):
    path = fixture(tmp_path / "large.wav")
    monkeypatch.setattr(audio, "MAX_BYTES", 8)
    with pytest.raises(audio.WaveformError, match="32 MiB"):
        audio.read_waveform(path, threading.Event())


def test_unsupported_extension_needs_no_file_access(tmp_path, monkeypatch):
    monkeypatch.setattr(audio.os, "open", lambda *a: pytest.fail("must not open unsupported file"))
    with pytest.raises(audio.WaveformError, match="PCM WAV"):
        audio.read_waveform(tmp_path / "anything.mp3", threading.Event())


def test_cancellation_before_read_and_between_decoding_chunks(tmp_path):
    path = fixture(tmp_path / "cancel.wav", frames=[(123,)] * 20000)
    cancel = threading.Event()
    cancel.set()
    with pytest.raises(audio.WaveformCanceled):
        audio.read_waveform(path, cancel)

    class DuringDecode:
        calls = 0

        def is_set(self):
            self.calls += 1
            return self.calls >= 6

    with pytest.raises(audio.WaveformCanceled):
        audio.read_waveform(path, DuringDecode())


def test_changed_snapshot_is_not_published(tmp_path):
    path = fixture(tmp_path / "changing.wav")

    class ChangeAfterRead:
        calls = 0

        def is_set(self):
            self.calls += 1
            if self.calls == 3:
                path.write_bytes(b"replacement")
            return False

    with pytest.raises(audio.WaveformError, match="changed"):
        audio.read_waveform(path, ChangeAfterRead())
    assert path.read_bytes() == b"replacement"


def test_symlink_is_not_followed(tmp_path):
    original = fixture(tmp_path / "original.wav")
    link = tmp_path / "link.wav"
    try:
        link.symlink_to(original)
    except OSError:
        pytest.skip("Symlink creation is unavailable")
    with pytest.raises(audio.WaveformError):
        audio.read_waveform(link, threading.Event())


@pytest.mark.skipif(os.name == "nt", reason="POSIX FIFO guard")
def test_fifo_is_rejected_without_waiting_for_a_writer(tmp_path):
    path = tmp_path / "fifo.wav"
    os.mkfifo(path)
    with pytest.raises(audio.WaveformError):
        audio.read_waveform(path, threading.Event())
