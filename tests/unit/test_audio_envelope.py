# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Bounded RMS envelopes from already decoded samples: pure math, no file or decoder."""

import array
import math

import pytest

from scenario.core.audio_waveform import (
    AudioEnvelope,
    EnvelopeBuilder,
    WaveformError,
)


def sine(rate, seconds, amplitude, channels=1):
    frames = int(rate * seconds)
    values = array.array("f")
    for frame in range(frames):
        sample = amplitude * math.sin(2 * math.pi * 440 * frame / rate)
        values.extend([sample] * channels)
    return values


def test_sine_rms_peak_and_duration_from_interleaved_chunks():
    builder = EnvelopeBuilder(8000, 2, max_seconds=5)
    samples = sine(8000, 2.0, 0.5, channels=2)
    view = memoryview(samples)
    for start in range(0, len(view), 2 * 777):  # Chunks straddle 10 ms blocks.
        builder.add(view[start : start + 2 * 777])
    envelope = builder.finish(bins=64)
    assert envelope.seconds == pytest.approx(2.0)
    assert (envelope.sample_rate, envelope.channels, len(envelope.rms)) == (8000, 2, 64)
    assert envelope.overall_peak == pytest.approx(0.5, abs=1e-3)
    assert envelope.overall_rms == pytest.approx(0.5 / math.sqrt(2), abs=1e-3)
    assert all(rms <= peak for rms, peak in zip(envelope.rms, envelope.peaks, strict=True))
    assert not envelope.silent


def test_silence_and_loud_section_are_located_in_time():
    rate = 1000
    builder = EnvelopeBuilder(rate, 1, max_seconds=10)
    builder.add([0.0] * rate)
    builder.add(sine(rate, 1.0, 0.8))
    envelope = builder.finish(bins=2)
    assert envelope.rms[0] == envelope.peaks[0] == 0.0
    assert envelope.peaks[1] == pytest.approx(0.8, abs=0.01)
    silent = EnvelopeBuilder(rate, 1)
    silent.add([0.0] * 50)
    assert silent.finish().silent


def test_fewer_blocks_than_bins_and_partial_last_block():
    builder = EnvelopeBuilder(44100, 1)
    builder.add([0.25] * 1000)  # Under three 441-frame blocks.
    envelope = builder.finish(bins=256)
    assert len(envelope.rms) == len(envelope.peaks) == 3
    assert envelope.rms == (0.25, 0.25, 0.25)
    assert envelope.seconds == pytest.approx(1000 / 44100)


def test_out_of_range_samples_are_clamped_not_rejected():
    builder = EnvelopeBuilder(100, 1)
    builder.add([4.0, -3.0, 1e200, -1e200])
    envelope = builder.finish()
    assert envelope.overall_peak == envelope.overall_rms == 1.0


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
def test_non_finite_samples_are_rejected(bad):
    builder = EnvelopeBuilder(100, 1)
    with pytest.raises(WaveformError, match="finite"):
        builder.add([0.1, bad, 0.2])


def test_duration_frames_and_types_are_bounded():
    builder = EnvelopeBuilder(100, 2, max_seconds=1)
    with pytest.raises(WaveformError, match="whole"):
        builder.add([0.0] * 3)
    builder.add([0.0] * 200)
    with pytest.raises(WaveformError, match="duration"):
        builder.add([0.0, 0.0])
    with pytest.raises(WaveformError, match="numbers"):
        EnvelopeBuilder(100, 1).add(["loud"])
    with pytest.raises(WaveformError, match="sequence"):
        EnvelopeBuilder(100, 1).add(iter([0.0]))
    with pytest.raises(WaveformError, match="no samples"):
        EnvelopeBuilder(100, 1).finish()


@pytest.mark.parametrize(
    "options",
    [
        {"sample_rate": 0, "channels": 1},
        {"sample_rate": 192001, "channels": 1},
        {"sample_rate": 100, "channels": 9},
        {"sample_rate": 100, "channels": True},
        {"sample_rate": 100, "channels": 1, "max_seconds": 601},
    ],
)
def test_invalid_specs_are_rejected(options):
    with pytest.raises(WaveformError):
        EnvelopeBuilder(**options)


def test_finish_is_single_use_and_bins_are_bounded():
    builder = EnvelopeBuilder(100, 1)
    builder.add([0.5] * 10)
    with pytest.raises(WaveformError, match="1024"):
        builder.finish(bins=1025)
    builder.finish(bins=1)
    with pytest.raises(WaveformError, match="complete"):
        builder.finish()
    with pytest.raises(WaveformError, match="complete"):
        builder.add([0.5])


def test_envelope_round_trip_and_strict_validation():
    builder = EnvelopeBuilder(1000, 1)
    builder.add(sine(1000, 0.5, 0.3))
    envelope = builder.finish(bins=16)
    assert AudioEnvelope.from_dict(envelope.to_dict()) == envelope
    value = envelope.to_dict()
    for change in (
        {"extra": 1},
        {"rms": [2.0] * len(value["rms"])},
        {"rms": [0.9] * len(value["rms"]), "peaks": [0.1] * len(value["peaks"])},
        {"peaks": value["peaks"][:-1]},
        {"seconds": 601},
        {"sample_rate": 0},
        {"overall_rms": math.nan},
    ):
        with pytest.raises(WaveformError):
            AudioEnvelope.from_dict({**value, **change})
