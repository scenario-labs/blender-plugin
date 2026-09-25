# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Bounded local PCM-WAV snapshots and envelopes, without Blender or playback."""

import array
import hashlib
import io
import os
import stat
import sys
import wave
from dataclasses import dataclass
from pathlib import Path

MAX_BYTES = 32 * 1024 * 1024
MAX_FRAMES = 10_000_000
MAX_SECONDS = 600
BINS = 256


class WaveformError(ValueError):
    """A local preview failure with no private path or decoder detail."""


class WaveformCanceled(WaveformError):
    pass


def stamp(info):
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def _check(cancel):
    if cancel.is_set():
        raise WaveformCanceled("Waveform preview canceled")


@dataclass(frozen=True)
class Waveform:
    seconds: float
    channels: int
    sample_rate: int
    peaks: tuple
    sha256: str
    source_stamp: tuple


def _snapshot(path, cancel):
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    fd = os.open(path, flags | getattr(os, "O_BINARY", 0))
    with os.fdopen(fd, "rb") as source:
        before = os.fstat(source.fileno())
        if not stat.S_ISREG(before.st_mode) or path.is_symlink():
            raise WaveformError("Choose an unchanged regular audio file")
        if not 1 <= before.st_size <= MAX_BYTES:
            raise WaveformError("Waveform preview supports files up to 32 MiB")
        data = bytearray()
        while len(data) < before.st_size:
            _check(cancel)
            chunk = source.read(min(65536, before.st_size - len(data)))
            if not chunk:
                raise WaveformError("Audio file changed while reading")
            data.extend(chunk)
        _check(cancel)
        after = path.lstat()
        if (
            source.read(1)
            or stamp(before) != stamp(os.fstat(source.fileno()))
            or not stat.S_ISREG(after.st_mode)
            or not os.path.samestat(before, after)
        ):
            raise WaveformError("Audio file changed while reading")
        return data, stamp(after)


def _samples(raw, width):
    if width == 1:
        return (value - 128 for value in raw)
    if width == 3:
        return (
            int.from_bytes(raw[i : i + 3], "little", signed=True) for i in range(0, len(raw), 3)
        )
    values = array.array("h" if width == 2 else "i")
    values.frombytes(raw)
    if sys.byteorder != "little":
        values.byteswap()
    return iter(values)


def read_waveform(path, cancel):
    """Read a stable local snapshot; cancellation is checked between bounded chunks.

    The digest identifies these local bytes, not a remote job or durable receipt.
    Filesystem operations themselves retain the operating system's wait behavior.
    """
    path = Path(path)
    _check(cancel)
    if path.suffix.lower() != ".wav":
        raise WaveformError("Waveform preview supports PCM WAV; Play and Add remain available")
    try:
        data, identity = _snapshot(path, cancel)
        with wave.open(io.BytesIO(data), "rb") as sound:
            channels, width, rate, frames = (
                sound.getnchannels(),
                sound.getsampwidth(),
                sound.getframerate(),
                sound.getnframes(),
            )
            if channels not in (1, 2) or width not in (1, 2, 3, 4) or sound.getcomptype() != "NONE":
                raise WaveformError("Use 8, 16, 24 or 32-bit mono/stereo PCM WAV")
            if (
                not 1 <= rate <= 192000
                or not 1 <= frames <= MAX_FRAMES
                or frames / rate > MAX_SECONDS
            ):
                raise WaveformError("Audio exceeds the waveform frame or ten-minute duration limit")
            count = min(BINS, frames)
            peaks = [[[1.0, -1.0] for _ in range(count)] for _ in range(channels)]
            scale, offset = float(1 << (width * 8 - 1)), 0
            while offset < frames:
                _check(cancel)
                amount = min(4096, frames - offset)
                raw = sound.readframes(amount)
                if len(raw) != amount * channels * width:
                    raise WaveformError("Audio file is truncated")
                samples = _samples(raw, width)
                for frame in range(offset, offset + amount):
                    bucket = frame * count // frames
                    for channel in range(channels):
                        value = next(samples) / scale
                        peak = peaks[channel][bucket]
                        peak[0], peak[1] = min(peak[0], value), max(peak[1], value)
                offset += amount
            _check(cancel)
        return Waveform(
            frames / rate,
            channels,
            rate,
            tuple(tuple(tuple(pair) for pair in channel) for channel in peaks),
            hashlib.sha256(data).hexdigest(),
            identity,
        )
    except WaveformError:
        raise
    except (OSError, EOFError, wave.Error, ValueError, OverflowError):
        raise WaveformError("Audio is missing, corrupt or unsupported PCM WAV") from None


def raster(waveform, *, width=256, height=96):
    """Small transparent RGBA waveform; each channel has its own amplitude band."""
    pixels = bytearray(width * height * 4)
    band = height // waveform.channels
    for channel, peaks in enumerate(waveform.peaks):
        center, radius = channel * band + band // 2, max(1, band // 2 - 4)
        for x in range(width):
            low, high = peaks[min(len(peaks) - 1, x * len(peaks) // width)]
            first, last = round(center + low * radius), round(center + high * radius)
            for y in range(first, last + 1):
                index = (y * width + x) * 4
                pixels[index : index + 4] = b"\x76\xc9\xf5\xff"
            index = (center * width + x) * 4
            if not pixels[index + 3]:
                pixels[index : index + 4] = b"\x88\x88\x88\x70"
    return bytes(pixels)
