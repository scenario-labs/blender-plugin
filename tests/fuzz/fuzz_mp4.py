# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Fuzz the bounded MP4 inspection of owned exports, ``mp4_inspection.inspect``.

Any file either raises Mp4Error or returns a summary of one to 16 tracks whose
fields fit their box fields. Writing the top-level box headers with 64-bit sizes,
which ISO/IEC 14496-12 allows for every box, does not change the summary. Each
input is written to a private temporary directory that is removed afterwards.
"""

import sys
import tempfile
from fractions import Fraction
from pathlib import Path

from samples import avc1, box, largesize, mp4, mp4a, track
from support import DataProvider, split

from scenario.core.jobs import mp4_inspection
from scenario.core.jobs.mp4_inspection import Mp4Error, Mp4Summary

PROVIDER = DataProvider
SCALES = [0, 1, 25, 1000, 12288, 48000, 10**9, 10**9 + 1, 2**32 - 1]


def movie(fdp):
    """A movie assembled from valid boxes with fuzzed fields, then damaged."""
    tracks = []
    for _ in range(fdp.ConsumeIntInRange(0, 3)):
        kind = fdp.ConsumeIntInRange(0, 2)
        if kind == 0:
            entry = avc1(
                fdp.ConsumeIntInRange(0, 0xFFFF),
                fdp.ConsumeIntInRange(0, 0xFFFF),
                fdp.ConsumeIntInRange(0, 255),
            )
        elif kind == 1:
            entry = mp4a(fdp.ConsumeIntInRange(0, 0xFFFF), fdp.ConsumeIntInRange(0, 0xFFFF))
        else:
            entry = box(fdp.ConsumeBytes(4).ljust(4, b" "), fdp.ConsumeBytes(40))
        rows = [
            (fdp.ConsumeIntInRange(0, 64), fdp.ConsumeIntInRange(0, 4096))
            for _ in range(fdp.ConsumeIntInRange(0, 3))
        ]
        tracks.append(
            track(
                fdp.PickValueInList([b"vide", b"soun", b"text", b"meta"]),
                entry,
                scale=fdp.PickValueInList(SCALES),
                timing=rows,
                presented=fdp.ConsumeIntInRange(0, 2**32 - 1),
            )
        )
    data = bytearray(mp4(tracks, scale=fdp.PickValueInList(SCALES)))
    for _ in range(fdp.ConsumeIntInRange(0, 4)):
        data[fdp.ConsumeIntInRange(0, len(data) - 1)] = fdp.ConsumeIntInRange(0, 255)
    if fdp.ConsumeBool():
        del data[fdp.ConsumeIntInRange(0, len(data)) :]
    return bytes(data)


def inspect(directory, data, name):
    path = Path(directory) / name
    path.write_bytes(data)
    try:
        summary = mp4_inspection.inspect(path)
    except Mp4Error:
        return None
    check(summary)
    return summary


def check(summary):
    assert isinstance(summary, Mp4Summary)
    total = len(summary.video) + len(summary.audio) + summary.other_tracks
    assert 1 <= total <= mp4_inspection.MAX_TRACKS
    for video in summary.video:
        assert 0 <= video.width <= 0xFFFF and 0 <= video.height <= 0xFFFF
        assert video.profile is None or 0 <= video.profile <= 255
        assert type(video.frames) is int and video.frames >= 0
        assert video.frame_rate is None or video.frame_rate > 0
        assert isinstance(video.duration, Fraction) and video.duration >= 0
    for audio in summary.audio:
        assert 0 <= audio.channels <= 0xFFFF and 0 <= audio.sample_rate <= 0xFFFF
        assert isinstance(audio.duration, Fraction) and audio.duration >= 0


def TestOneInput(data):
    mode, rest = split(data)
    mode %= 3
    candidate = movie(PROVIDER(rest)) if mode == 2 else rest
    with tempfile.TemporaryDirectory(prefix="fuzz-mp4-") as directory:
        summary = inspect(directory, candidate, "movie.mp4")
        if mode != 1 or summary is None:
            return
        rewritten = largesize(candidate)
        if rewritten is not None:
            assert inspect(directory, rewritten, "large.mp4") == summary, "64-bit box sizes"


if __name__ == "__main__":
    import atheris

    PROVIDER = atheris.FuzzedDataProvider
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
