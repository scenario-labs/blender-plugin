# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Fuzz audio envelopes: the decoder output check and the builder that folds it.

``audio_decode.envelope`` reads the owned decoder's ``envelope.json`` and
``blocks.bin``; any bytes raise only WaveformError or give a valid envelope.
``EnvelopeBuilder`` rejects non-finite or overlong audio with WaveformError, and
blocks that a correct decoder reduced from the same float32 samples are accepted by
``add_blocks`` and give the levels ``add`` gives. A stored envelope that
``AudioEnvelope.from_dict`` accepts folds and rasterizes within its bounds.
Decoder files live in a private temporary directory removed after each input.
"""

import json
import math
import struct
import sys
import tempfile
from pathlib import Path

from support import DataProvider, json_value, split

from scenario.core.audio_waveform import (
    BINS,
    AudioEnvelope,
    EnvelopeBuilder,
    WaveformError,
    fold,
    raster,
)
from scenario.core.jobs.audio_decode import envelope

PROVIDER = DataProvider
WORDS = ["format", "sample_rate", "channels", "frames", "block", "rms", "peaks", "seconds"]
SPECIAL = [0.0, -0.0, 1.0, -1.0, 1.5, -2.0, 1e-30, 1e30, math.inf, -math.inf, math.nan]


def check_envelope(result, bins):
    assert isinstance(result, AudioEnvelope)
    assert 1 <= len(result.rms) == len(result.peaks) <= bins
    for rms, peak in (
        *zip(result.rms, result.peaks, strict=True),
        (result.overall_rms, result.overall_peak),
    ):
        assert 0 <= rms <= 1 and 0 <= peak <= 1 and rms <= peak + 2e-6


def decoder_files(mode, fdp, rest):
    if mode == 0:
        length = int.from_bytes(rest[:2], "big")
        return rest[2 : 2 + length], rest[2 + length :]
    header = {
        "format": 1,
        "sample_rate": fdp.PickValueInList([1, 99, 100, 8000, 48000, 192000, 192001]),
        "channels": fdp.ConsumeIntInRange(0, 9),
        "frames": fdp.ConsumeIntInRange(0, 2000),
    }
    header["block"] = max(1, header["sample_rate"] // 100)
    count = -(-max(header["frames"], 1) // header["block"]) + fdp.ConsumeIntInRange(-1, 1)
    for key in list(header):
        choice = fdp.ConsumeIntInRange(0, 15)
        if choice == 0:
            del header[key]
        elif choice == 1:
            header[key] = json_value(fdp, WORDS, 1)
    blocks = b"".join(
        struct.pack("<dd", fdp.ConsumeFloat(), fdp.PickValueInList(SPECIAL[:5]))
        for _ in range(max(0, min(count, 2048)))
    )
    return json.dumps(header).encode(), blocks + fdp.ConsumeBytes(fdp.ConsumeIntInRange(0, 8))


def check_decoder_output(mode, fdp, rest):
    header, blocks = decoder_files(mode, fdp, rest)
    with tempfile.TemporaryDirectory(prefix="fuzz-audio-") as directory:
        (Path(directory) / "envelope.json").write_bytes(header)
        (Path(directory) / "blocks.bin").write_bytes(blocks)
        try:
            result = envelope(Path(directory))
        except WaveformError:
            return
    check_envelope(result, BINS)


def float32(fdp):
    if fdp.ConsumeIntInRange(0, 3):
        return struct.unpack("<f", fdp.ConsumeBytes(4).ljust(4, b"\0"))[0]
    return struct.unpack("<f", struct.pack("<f", fdp.PickValueInList(SPECIAL)))[0]


def reduce(samples, frames, channels, block):
    """Per-block sums of squares and peaks of clamped samples, as the decoder writes them."""
    clamped = [min(1.0, max(-1.0, value)) for value in samples]
    sums, peaks = [], []
    for start in range(0, frames, block):
        part = clamped[start * channels : min(frames, start + block) * channels]
        sums.append(math.fsum(value * value for value in part))
        peaks.append(max(abs(value) for value in part))
    return sums, peaks


def check_builder(fdp):
    rate, channels = fdp.ConsumeIntInRange(1, 1200), fdp.ConsumeIntInRange(1, 8)
    seconds, bins = fdp.ConsumeIntInRange(1, 2), fdp.ConsumeIntInRange(1, 8)
    frames = fdp.ConsumeIntInRange(0, 48)
    samples = [float32(fdp) for _ in range(frames * channels)]
    first = EnvelopeBuilder(rate, channels, max_seconds=seconds)
    try:
        offset = 0
        while offset < frames:
            take = fdp.ConsumeIntInRange(1, frames - offset)
            first.add(samples[offset * channels : (offset + take) * channels])
            offset += take
        expected = first.finish(bins)
    except WaveformError:
        finite = all(math.isfinite(value) for value in samples)
        assert not finite or not 1 <= frames <= rate * seconds, "valid samples were refused"
        return
    check_envelope(expected, bins)
    second = EnvelopeBuilder(rate, channels, max_seconds=seconds)
    second.add_blocks(*reduce(samples, frames, channels, second.block), frames)
    actual = second.finish(bins)
    assert actual.seconds == expected.seconds and len(actual.rms) == len(expected.rms)
    for left, right in zip(
        (*actual.rms, *actual.peaks, actual.overall_rms, actual.overall_peak),
        (*expected.rms, *expected.peaks, expected.overall_rms, expected.overall_peak),
        strict=True,
    ):
        assert abs(left - right) <= 2e-6, "decoder blocks and samples disagree"


def level(fdp):
    return fdp.PickValueInList([0.0, 1e-7, 0.25, 0.5, 0.999999, 1.0])


def check_stored(fdp):
    rms = [level(fdp) for _ in range(fdp.ConsumeIntInRange(1, 40))]
    overall = level(fdp)
    value = {
        "seconds": fdp.PickValueInList([0.01, 1, 2.5, 600]),
        "sample_rate": fdp.PickValueInList([1, 48000, 192000]),
        "channels": fdp.PickValueInList([1, 2, 8]),
        "rms": rms,
        "peaks": [max(item, level(fdp)) for item in rms],
        "overall_rms": overall,
        "overall_peak": max(overall, level(fdp)),
    }
    hostile = [0, 601, math.nan, math.inf, -0.1, 1.5, "1", True, 192001, 9, [], None]
    for key in list(value):
        choice = fdp.ConsumeIntInRange(0, 15)
        if choice == 0:
            value[key] = fdp.PickValueInList(hostile)
        elif choice == 1:
            value[key] = json_value(fdp, WORDS, 1)
        elif choice == 2 and isinstance(value[key], list):
            value[key] = value[key][: fdp.ConsumeIntInRange(0, len(value[key]))]
    if not fdp.ConsumeIntInRange(0, 15):
        value = json_value(fdp, WORDS, 2)
    try:
        stored = AudioEnvelope.from_dict(value)
    except WaveformError:
        return
    check_envelope(stored, len(stored.rms))
    bins = fdp.ConsumeIntInRange(1, 12)
    rms, peaks = fold(stored, bins)
    assert len(rms) == len(peaks) == min(bins, len(stored.rms))
    assert all(0 <= low <= 1 and low <= high + 2e-6 for low, high in zip(rms, peaks, strict=True))
    width, height = fdp.ConsumeIntInRange(0, 40), fdp.ConsumeIntInRange(0, 40)
    try:
        pixels = raster(stored, width=width, height=height)
    except WaveformError:
        assert not (8 <= width and 8 <= height), "valid raster dimensions were refused"
        return
    assert len(pixels) == width * height * 4


def TestOneInput(data):
    mode, rest = split(data)
    mode %= 4
    fdp = PROVIDER(rest)
    if mode < 2:
        check_decoder_output(mode, fdp, rest)
    elif mode == 2:
        check_builder(fdp)
    else:
        check_stored(fdp)


if __name__ == "__main__":
    import atheris

    PROVIDER = atheris.FuzzedDataProvider
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
