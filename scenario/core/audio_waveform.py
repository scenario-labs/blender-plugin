# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Bounded audio envelopes and their raster, without Blender, files or playback.

``EnvelopeBuilder`` reduces decoded samples to 10 ms sum-of-squares and peak
blocks, then folds them into bounded RMS and peak bins. ``add`` accepts samples
and ``add_blocks`` accepts blocks that an owned decoder process already reduced;
both are checked against the frame count before they are folded. Nothing here
reads files or decodes audio: see ``core.jobs.audio_decode`` for the decoder.
"""

import array
import math
import operator
from dataclasses import dataclass

MAX_SECONDS = 600
BINS = 256
ENVELOPE_MAX_BINS = 1024
ENVELOPE_MAX_CHANNELS = 8
ENVELOPE_MAX_RATE = 192_000
# Peaks at or below this linear amplitude (about -80 dBFS) count as silence.
SILENCE = 1e-4
# Float tolerance when checking decoder-reduced blocks against their peaks.
_TOLERANCE = 1e-6
_PEAK_COLOR = b"\x76\xc9\xf5\x90"
_RMS_COLOR = b"\x76\xc9\xf5\xff"
_LINE_COLOR = b"\x88\x88\x88\x70"


class WaveformError(ValueError):
    """A local preview failure with no private path or decoder detail."""


class WaveformCanceled(WaveformError):
    pass


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
        # A partial block from ``add_blocks`` must stay the last one.
        self._ended = False

    @property
    def frames(self):
        return self._frames

    @property
    def block(self):
        """Frames per 10 ms block, at least one."""
        return self._block

    def _flush(self):
        total, peak, frames = self._pending
        self._sums.append(total)
        self._peaks.append(peak)
        self._counts.append(frames)
        self._pending = [0.0, 0.0, 0]

    def _check_open(self):
        if self._finished or self._ended:
            raise WaveformError("This audio envelope is already complete")

    def add_blocks(self, sums, peaks, frames):
        """Accept whole blocks reduced elsewhere: per-block sums of squares and peaks.

        ``sums`` and ``peaks`` hold one value per ``block`` frames of clamped
        samples, summed or maximized across channels; only the last block may
        be partial, and nothing can follow it. Each block is checked against
        what its frames could produce: finite, peaks within full scale and a
        root mean square no louder than its peak. A decoder process therefore
        cannot report levels its samples could not have, though it remains
        trusted for which samples it decoded.
        """
        self._check_open()
        if self._pending[2]:
            raise WaveformError("Decoded audio blocks must start on a block boundary")
        if type(frames) is not int or frames < 1:
            raise WaveformError("Decoded audio blocks must cover at least one frame")
        if frames > self._limit - self._frames:
            raise WaveformError("Audio exceeds the preview duration limit")
        count = -(-frames // self._block)
        try:
            if len(sums) != count or len(peaks) != count:
                raise WaveformError("Decoded audio blocks do not match their frame count")
            pairs = tuple(zip(sums, peaks, strict=True))
        except TypeError:
            raise WaveformError("Decoded audio blocks must be sequences of numbers") from None
        totals, maxima, counts = array.array("d"), array.array("d"), array.array("L")
        for index, (total, peak) in enumerate(pairs):
            size = min(self._block, frames - index * self._block)
            if (
                type(total) is not float
                or type(peak) is not float
                or not math.isfinite(total)
                or not 0.0 <= peak <= 1.0
                or not 0.0 <= total <= size * self._channels * peak * peak * (1 + _TOLERANCE)
            ):
                raise WaveformError("Decoded audio levels are invalid")
            totals.append(total)
            maxima.append(peak)
            counts.append(size)
        self._sums.extend(totals)
        self._peaks.extend(maxima)
        self._counts.extend(counts)
        self._frames += frames
        self._ended = bool(frames % self._block)

    def add(self, samples):
        self._check_open()
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


def raster(envelope, *, width=256, height=96):
    """Small transparent RGBA waveform: peak bars with solid RMS cores around a center line.

    Rows are symmetric, so Blender's bottom-up preview pixel order needs no flip.
    """
    if not isinstance(envelope, AudioEnvelope):
        raise WaveformError("Provide a decoded audio envelope")
    if any(type(value) is not int or not 8 <= value <= 4096 for value in (width, height)):
        raise WaveformError("Use waveform raster dimensions from 8 to 4096 pixels")
    pixels = bytearray(width * height * 4)
    center = height // 2
    radius = max(1, center - 2)
    bins = len(envelope.peaks)
    for x in range(width):
        index = min(bins - 1, x * bins // width)
        for level, color in (
            (envelope.peaks[index], _PEAK_COLOR),
            (envelope.rms[index], _RMS_COLOR),
        ):
            extent = round(level * radius)
            if extent:
                for y in range(center - extent, center + extent + 1):
                    offset = (y * width + x) * 4
                    pixels[offset : offset + 4] = color
        offset = (center * width + x) * 4
        if not pixels[offset + 3]:
            pixels[offset : offset + 4] = _LINE_COLOR
    return bytes(pixels)
