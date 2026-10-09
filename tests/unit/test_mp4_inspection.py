# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Bounded MP4 container inspection without decoding or external tools."""

import os
import struct
from fractions import Fraction

import pytest
from conftest import FIXTURES

from scenario.core.jobs import mp4_inspection as mp4


def box(kind, *parts):
    payload = b"".join(parts)
    return struct.pack(">I4s", 8 + len(payload), kind) + payload


def full(kind, payload, version=0):
    return box(kind, bytes([version, 0, 0, 0]), payload)


def descriptor(tag, payload):
    return bytes([tag, len(payload)]) + payload


def avc1(width, height, profile=100, kind=b"avc1"):
    fields = bytes(6) + struct.pack(">H", 1) + bytes(16) + struct.pack(">HH", width, height)
    return box(kind, fields, bytes(50), box(b"avcC", bytes([1, profile, 0, 31])))


def mp4a(rate=48000, channels=2, object_type=mp4.AAC_OBJECT_TYPE):
    fields = bytes(6) + struct.pack(">H", 1)
    fields += struct.pack(">HH4sHHHHI", 0, 0, bytes(4), channels, 16, 0, 0, rate << 16)
    es = struct.pack(">HB", 1, 0) + descriptor(0x04, bytes([object_type]) + bytes(12))
    return box(b"mp4a", fields, full(b"esds", descriptor(0x03, es)))


def track(handler, entry, *, scale, timing, presented, samples=None):
    count = sum(number for number, _ in timing) if samples is None else samples
    table = struct.pack(">I", len(timing)) + b"".join(struct.pack(">II", *row) for row in timing)
    return box(
        b"trak",
        full(b"tkhd", struct.pack(">IIIII", 0, 0, 1, 0, presented) + bytes(60)),
        box(
            b"mdia",
            full(b"mdhd", struct.pack(">IIII", 0, 0, scale, 0) + bytes(4)),
            full(b"hdlr", bytes(4) + handler + bytes(12) + b"\0"),
            box(
                b"minf",
                box(
                    b"stbl",
                    full(b"stsd", struct.pack(">I", 1) + entry),
                    full(b"stts", table),
                    full(b"stsz", struct.pack(">II", 0, count)),
                ),
            ),
        ),
    )


def video_track(width=64, height=64, frames=48, fps=24, profile=100, kind=b"avc1", timing=None):
    return track(
        b"vide",
        avc1(width, height, profile, kind),
        scale=fps * 512,
        timing=timing or [(frames, 512)],
        presented=frames * 1000 // fps,
    )


def audio_track(seconds=Fraction(2), **options):
    return track(
        b"soun",
        mp4a(**options),
        scale=48000,
        timing=[(int(seconds * 48000 // 1024), 1024)],
        presented=int(seconds * 1000),
    )


def movie(*tracks, leading=b"ftyp", extra=b""):
    head = box(leading, b"isom", bytes(4), b"isomavc1")
    return head + box(b"mdat", bytes(32)) + box(b"moov", full(b"mvhd", mvhd()), *tracks) + extra


def mvhd():
    return struct.pack(">IIII", 0, 0, 1000, 2000) + bytes(80)


def write(tmp_path, data, name="film.mp4"):
    path = tmp_path / name
    path.write_bytes(data)
    return path


def test_summarizes_h264_and_aac_tracks(tmp_path):
    summary = mp4.inspect(write(tmp_path, movie(video_track(), audio_track())))
    assert summary.other_tracks == 0
    (video,) = summary.video
    assert (video.codec, video.profile, video.width, video.height) == ("h264", 100, 64, 64)
    assert (video.frames, video.frame_rate, video.duration) == (48, 24, 2)
    (audio,) = summary.audio
    assert (audio.codec, audio.sample_rate, audio.channels, audio.duration) == ("aac", 48000, 2, 2)


def test_real_mpeg4_part2_fixture_is_not_reported_as_h264():
    summary = mp4.inspect(FIXTURES / "synthetic" / "film-four-seconds-audio.mp4")
    (video,) = summary.video
    assert video.codec == "mp4v" and video.profile is None
    assert (video.frames, video.frame_rate) == (96, 24)
    assert summary.audio[0].codec == "aac"


def test_variable_frame_durations_have_no_constant_rate(tmp_path):
    data = movie(video_track(timing=[(47, 512), (1, 1024)]))
    assert mp4.inspect(write(tmp_path, data)).video[0].frame_rate is None


def test_non_aac_mpeg4_audio_keeps_its_sample_entry_name(tmp_path):
    data = movie(video_track(), audio_track(object_type=0x6B))
    assert mp4.inspect(write(tmp_path, data)).audio[0].codec == "mp4a"


def test_other_handlers_are_counted(tmp_path):
    text = track(b"text", box(b"tx3g", bytes(8)), scale=1000, timing=[(1, 1000)], presented=1000)
    assert mp4.inspect(write(tmp_path, movie(video_track(), text))).other_tracks == 1


def test_large_size_box_headers_are_supported(tmp_path):
    data = movie(video_track())
    large = struct.pack(">I4sQ", 1, b"free", 16 + 4) + bytes(4)
    assert mp4.inspect(write(tmp_path, data + large)).video[0].frames == 48


@pytest.mark.parametrize(
    "data",
    [
        movie(video_track(), leading=b"free"),
        movie(video_track()) + box(b"moov", full(b"mvhd", mvhd())),
        movie(video_track())[:-5],
        movie(track(b"vide", avc1(64, 64), scale=512, timing=[(48, 1)], presented=0, samples=47)),
        box(b"ftyp", b"isom") + box(b"moov", full(b"mvhd", mvhd()), video_track()),
        movie(video_track()).replace(b"avcC\x01", b"avcC\x02"),
        movie(),
        b"\x00" * 64,
    ],
    ids=[
        "no-leading-ftyp",
        "duplicate-moov",
        "truncated",
        "sample-tables-disagree",
        "no-mdat",
        "unknown-avc-config",
        "no-tracks",
        "garbage",
    ],
)
def test_ambiguous_or_truncated_metadata_is_rejected(tmp_path, data):
    with pytest.raises(mp4.Mp4Error):
        mp4.inspect(write(tmp_path, data))


def test_box_count_is_bounded(tmp_path):
    spam = b"".join(box(b"free") for _ in range(mp4.MAX_BOXES + 1))
    data = box(b"ftyp", b"isom") + box(b"mdat") + box(b"moov", full(b"mvhd", mvhd()), spam)
    with pytest.raises(mp4.Mp4Error, match="too many boxes"):
        mp4.inspect(write(tmp_path, data))


def test_size_policy_and_symlinks_are_rejected(tmp_path):
    path = write(tmp_path, movie(video_track()))
    with pytest.raises(mp4.Mp4Error, match="size"):
        mp4.inspect(path, maximum=32)
    link = tmp_path / "link.mp4"
    link.symlink_to(path)
    with pytest.raises(OSError):
        mp4.inspect(link)


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="POSIX FIFO regression")
def test_inspection_never_follows_a_non_regular_file(tmp_path):
    fifo = tmp_path / "fifo.mp4"
    os.mkfifo(fifo)
    with pytest.raises(mp4.Mp4Error, match="regular"):
        mp4.inspect(fifo)
