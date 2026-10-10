# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Bounded local PCM-WAV snapshots and envelopes, without Blender or playback.

``EnvelopeBuilder`` reduces samples that a caller already decoded (for example
with Blender's audio module on its own schedule) to bounded RMS and peak bins.
It performs no file I/O and no decoding.
"""

import array
import hashlib
import io
import math
import operator
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
ENVELOPE_MAX_BINS = 1024
ENVELOPE_MAX_CHANNELS = 8
ENVELOPE_MAX_RATE = 192_000
# Peaks at or below this linear amplitude (about -80 dBFS) count as silence.
SILENCE = 1e-4


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


def _level(value):
    if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
        raise WaveformError("Invalid audio envelope level")
    return float(value)


@dataclass(frozen=True)
class AudioEnvelope:
    """Channel-mixed RMS and peak levels per time bin, as linear amplitude in [0, 1]."""

    seconds: float
    sample_rate: int
    channels: int
    rms: tuple
    peaks: tuple
    overall_rms: float
    overall_peak: float

    def __post_init__(self):
        if (
            type(self.sample_rate) is not int
            or not 1 <= self.sample_rate <= ENVELOPE_MAX_RATE
            or type(self.channels) is not int
            or not 1 <= self.channels <= ENVELOPE_MAX_CHANNELS
            or type(self.seconds) not in (int, float)
            or not math.isfinite(self.seconds)
            or not 0 < self.seconds <= MAX_SECONDS
            or not isinstance(self.rms, tuple)
            or not isinstance(self.peaks, tuple)
            or not 1 <= len(self.rms) <= ENVELOPE_MAX_BINS
            or len(self.peaks) != len(self.rms)
        ):
            raise WaveformError("Invalid audio envelope")
        for rms, peak in (
            *zip(self.rms, self.peaks, strict=True),
            (self.overall_rms, self.overall_peak),
        ):
            if _level(rms) > _level(peak) + 1e-6:
                raise WaveformError("Invalid audio envelope level")

    @property
    def silent(self):
        return self.overall_peak <= SILENCE

    def to_dict(self):
        return {
            "seconds": self.seconds,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "rms": list(self.rms),
            "peaks": list(self.peaks),
            "overall_rms": self.overall_rms,
            "overall_peak": self.overall_peak,
        }

    @classmethod
    def from_dict(cls, value):
        names = {
            "seconds",
            "sample_rate",
            "channels",
            "rms",
            "peaks",
            "overall_rms",
            "overall_peak",
        }
        if (
            not isinstance(value, dict)
            or set(value) != names
            or not isinstance(value["rms"], list)
            or not isinstance(value["peaks"], list)
        ):
            raise WaveformError("Invalid audio envelope")
        return cls(
            value["seconds"],
            value["sample_rate"],
            value["channels"],
            tuple(value["rms"]),
            tuple(value["peaks"]),
            value["overall_rms"],
            value["overall_peak"],
        )


def _measure(part):
    """Sum of squares and peak magnitude, clamping to full scale only when needed."""
    try:
        total = sum(map(operator.mul, part, part))
        peak = max(map(abs, part), default=0.0)
        if not math.isfinite(total) or not math.isfinite(peak):
            if not all(map(math.isfinite, part)):
                raise WaveformError("Audio samples must be finite")
            peak = 2.0  # Finite values whose squares overflow are clamped below.
        if peak > 1.0:
            clamped = [min(1.0, max(-1.0, value)) for value in part]
            total, peak = sum(map(operator.mul, clamped, clamped)), 1.0
    except TypeError:
        raise WaveformError("Audio samples must be numbers") from None
    return float(total), float(peak)


class EnvelopeBuilder:
    """Accumulate interleaved decoded samples into bounded 10 ms blocks.

    ``add`` accepts flat sequences of floats (a memoryview with format "f" or
    "d", an ``array.array`` or a list). Values outside [-1, 1] are clamped.
    Non-finite samples and audio longer than ``max_seconds`` are rejected
    instead of being silently truncated. Memory grows with the bounded
    duration in 10 ms blocks, never with the sample count.
    """

    def __init__(self, sample_rate, channels, *, max_seconds=MAX_SECONDS):
        if (
            type(sample_rate) is not int
            or not 1 <= sample_rate <= ENVELOPE_MAX_RATE
            or type(channels) is not int
            or not 1 <= channels <= ENVELOPE_MAX_CHANNELS
            or type(max_seconds) is not int
            or not 1 <= max_seconds <= MAX_SECONDS
        ):
            raise WaveformError("Use a supported audio rate, channel count and duration limit")
        self._rate, self._channels = sample_rate, channels
        self._block = max(1, sample_rate // 100)
        self._limit = sample_rate * max_seconds
        self._frames = 0
        self._sums, self._peaks = array.array("d"), array.array("d")
        self._counts = array.array("L")
        self._pending = [0.0, 0.0, 0]
        self._finished = False

    @property
    def frames(self):
        return self._frames

    def _flush(self):
        total, peak, frames = self._pending
        self._sums.append(total)
        self._peaks.append(peak)
        self._counts.append(frames)
        self._pending = [0.0, 0.0, 0]

    def add(self, samples):
        if self._finished:
            raise WaveformError("This audio envelope is already complete")
        try:
            count = len(samples)
        except TypeError:
            raise WaveformError("Audio samples must be a sequence of numbers") from None
        if count % self._channels:
            raise WaveformError("Audio samples must contain whole interleaved frames")
        frames = count // self._channels
        if frames > self._limit - self._frames:
            raise WaveformError("Audio exceeds the preview duration limit")
        offset = 0
        while offset < count:
            take = min(self._block - self._pending[2], (count - offset) // self._channels)
            end = offset + take * self._channels
            total, peak = _measure(samples[offset:end])
            self._pending[0] += total
            self._pending[1] = max(self._pending[1], peak)
            self._pending[2] += take
            offset = end
            if self._pending[2] == self._block:
                self._flush()
        self._frames += frames

    def finish(self, bins=BINS):
        """Fold the accumulated blocks into at most ``bins`` levels, once."""
        if type(bins) is not int or not 1 <= bins <= ENVELOPE_MAX_BINS:
            raise WaveformError("Use from 1 to 1024 envelope bins")
        if self._finished:
            raise WaveformError("This audio envelope is already complete")
        if self._pending[2]:
            self._flush()
        if not self._frames:
            raise WaveformError("Audio contains no samples")
        self._finished = True
        blocks = len(self._sums)
        count = min(bins, blocks)

        def level(total, frames):
            return min(1.0, round(math.sqrt(total / (frames * self._channels)), 6))

        rms, peaks = [], []
        for index in range(count):
            start, end = index * blocks // count, (index + 1) * blocks // count
            rms.append(level(sum(self._sums[start:end]), sum(self._counts[start:end])))
            peaks.append(min(1.0, round(max(self._peaks[start:end]), 6)))
        return AudioEnvelope(
            self._frames / self._rate,
            self._rate,
            self._channels,
            tuple(rms),
            tuple(peaks),
            level(sum(self._sums), self._frames),
            max(peaks),
        )
