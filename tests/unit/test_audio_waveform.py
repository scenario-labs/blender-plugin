# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Decoder-reduced level blocks and the envelope raster: pure math, no file or decoder."""

import math

import pytest

from scenario.core import audio_waveform as audio
from scenario.core.audio_waveform import AudioEnvelope, EnvelopeBuilder, WaveformError


def blocks(samples, rate, channels):
    """Reduce interleaved samples the way the offline decoder process does."""
    block = max(1, rate // 100)
    frames = len(samples) // channels
    sums, peaks = [], []
    for start in range(0, frames, block):
        part = [
            min(1.0, max(-1.0, value))
            for value in samples[start * channels : min(frames, start + block) * channels]
        ]
        sums.append(float(sum(value * value for value in part)))
        peaks.append(float(max(abs(value) for value in part)))
    return sums, peaks, frames


def tone(rate, seconds, amplitude, channels=1):
    values = []
    for frame in range(int(rate * seconds)):
        values.extend([amplitude * math.sin(2 * math.pi * 50 * frame / rate)] * channels)
    return values


@pytest.mark.parametrize("channels", [1, 2])
def test_reduced_blocks_fold_like_samples_including_a_partial_last_block(channels):
    rate = 8000
    samples = tone(rate, 0.5, 0.6, channels) + [1.5, -2.0] * channels  # Clamped, partial.
    by_samples = EnvelopeBuilder(rate, channels, max_seconds=1)
    by_samples.add(samples)
    by_blocks = EnvelopeBuilder(rate, channels, max_seconds=1)
    by_blocks.add_blocks(*blocks(samples, rate, channels))
    assert by_blocks.frames == by_samples.frames == 4002
    assert by_blocks.finish(bins=16) == by_samples.finish(bins=16)


def test_blocks_continue_after_whole_blocks_but_not_after_a_partial_one():
    builder = EnvelopeBuilder(100, 1)  # One-frame blocks at 100 Hz.
    builder.add_blocks([0.25], [0.5], 1)
    builder.add([0.5, -0.5])
    builder.add_blocks([0.0], [0.0], 1)
    assert builder.frames == 4
    partial = EnvelopeBuilder(1000, 1)
    partial.add_blocks([0.0, 0.0], [0.0, 0.0], 15)
    for extra in (lambda: partial.add([0.0]), lambda: partial.add_blocks([0.0], [0.0], 1)):
        with pytest.raises(WaveformError, match="complete"):
            extra()
    assert partial.finish().silent
    misaligned = EnvelopeBuilder(1000, 1)
    misaligned.add([0.0] * 3)
    with pytest.raises(WaveformError, match="boundary"):
        misaligned.add_blocks([0.0], [0.0], 10)


@pytest.mark.parametrize(
    "sums,peaks,frames,message",
    [
        ([0.0], [0.0], 0, "at least one"),
        ([0.0], [0.0], True, "at least one"),
        ([0.0, 0.0], [0.0], 20, "match"),
        ([0.0], [0.0], 11, "match"),
        ([math.nan], [0.5], 10, "invalid"),
        ([math.inf], [0.5], 10, "invalid"),
        ([0.1], [math.nan], 10, "invalid"),
        ([0.1], [1.5], 10, "invalid"),
        ([-0.1], [0.5], 10, "invalid"),
        ([10 * 0.25 + 0.01], [0.5], 10, "invalid"),  # RMS above its peak.
        ([0], [0.5], 10, "invalid"),
        (iter([0.0]), [0.0], 10, "sequences"),
    ],
)
def test_reduced_blocks_must_be_consistent_with_their_frames(sums, peaks, frames, message):
    with pytest.raises(WaveformError, match=message):
        EnvelopeBuilder(1000, 1).add_blocks(sums, peaks, frames)


def test_reduced_blocks_respect_the_duration_limit():
    builder = EnvelopeBuilder(100, 2, max_seconds=1)
    builder.add_blocks([0.0] * 100, [0.0] * 100, 100)
    with pytest.raises(WaveformError, match="duration"):
        builder.add_blocks([0.0], [0.0], 1)


def envelope(levels, *, rms=None):
    return AudioEnvelope(
        1.0,
        8000,
        1,
        tuple(rms if rms is not None else [level / 2 for level in levels]),
        tuple(levels),
        0.1,
        max(levels),
    )


def column(pixels, x, width, height):
    return [bytes(pixels[(y * width + x) * 4 : (y * width + x) * 4 + 4]) for y in range(height)]


def test_raster_draws_peak_bars_rms_cores_and_a_silent_center_line():
    width, height = 16, 24
    pixels = audio.raster(envelope([0.0, 1.0]), width=width, height=height)
    assert len(pixels) == width * height * 4
    silent = column(pixels, 0, width, height)
    assert silent[12] == audio._LINE_COLOR
    assert silent.count(b"\x00" * 4) == height - 1
    loud = column(pixels, 15, width, height)
    # A full-scale peak spans the band; its half-level RMS core is solid.
    assert loud[2] == loud[22] == audio._PEAK_COLOR
    assert loud[7] == loud[12] == loud[17] == audio._RMS_COLOR
    assert loud[1] == loud[23] == b"\x00" * 4


@pytest.mark.parametrize(
    "value,options",
    [
        ("not an envelope", {}),
        (envelope([0.5]), {"width": 7}),
        (envelope([0.5]), {"height": 4097}),
        (envelope([0.5]), {"width": 16.0}),
    ],
)
def test_raster_rejects_invalid_input(value, options):
    with pytest.raises(WaveformError):
        audio.raster(value, **options)
