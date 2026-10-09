# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Bounded, bpy-free MP4 container inspection for owned local exports.

This reads ISO base media box headers and the movie metadata only. It never
decodes samples, follows data references or opens another file. Decoding
evidence comes separately from ffprobe or Blender's verification child.
"""

import os
import stat
import struct
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

MAX_MOVIE_BYTES = 64 * 1024**2
MAX_BOXES = 4096
MAX_TOP_LEVEL = 64
MAX_TRACKS = 16
# 8-bit 4:2:0 H.264 profiles (Baseline, Main, Extended and High); High also
# permits monochrome. Higher profiles can carry 10-bit or 4:2:2/4:4:4 video.
H264_420_PROFILES = frozenset({66, 77, 88, 100})
AAC_OBJECT_TYPE = 0x40
_CONTAINERS = frozenset({b"moov", b"trak", b"mdia", b"minf", b"stbl"})


class Mp4Error(ValueError):
    """The file is not a bounded, unambiguous MP4 container."""


@dataclass(frozen=True)
class Mp4Video:
    codec: str
    profile: int | None
    width: int
    height: int
    frames: int
    frame_rate: Fraction | None
    duration: Fraction


@dataclass(frozen=True)
class Mp4Audio:
    codec: str
    sample_rate: int
    channels: int
    duration: Fraction


@dataclass(frozen=True)
class Mp4Summary:
    video: tuple[Mp4Video, ...]
    audio: tuple[Mp4Audio, ...]
    other_tracks: int


class _Budget:
    def __init__(self):
        self.boxes = 0

    def spend(self):
        self.boxes += 1
        if self.boxes > MAX_BOXES:
            raise Mp4Error("MP4 metadata has too many boxes")


def _boxes(data, start, end, budget):
    offset = start
    while offset < end:
        budget.spend()
        if end - offset < 8:
            raise Mp4Error("Truncated MP4 box header")
        size, kind = struct.unpack_from(">I4s", data, offset)
        header = 8
        if size == 1:
            if end - offset < 16:
                raise Mp4Error("Truncated MP4 box header")
            size = struct.unpack_from(">Q", data, offset + 8)[0]
            header = 16
        elif size == 0:
            size = end - offset
        if size < header or size > end - offset:
            raise Mp4Error("MP4 box exceeds its container")
        yield kind, offset + header, offset + size
        offset += size


def _children(data, start, end, budget):
    found = {}
    for kind, body, stop in _boxes(data, start, end, budget):
        found.setdefault(kind, []).append((body, stop))
    return found


def _one(found, kind):
    values = found.get(kind, [])
    if len(values) != 1:
        raise Mp4Error(f"MP4 metadata needs exactly one {kind.decode('ascii', 'replace')} box")
    return values[0]


def _unpack(fmt, data, offset, stop):
    if offset < 0 or offset + struct.calcsize(fmt) > stop:
        raise Mp4Error("Truncated MP4 metadata field")
    return struct.unpack_from(fmt, data, offset)


def _full_box_duration(data, body, stop, *, track):
    """Return (timescale or None, duration) from mvhd/mdhd/tkhd version 0 or 1."""
    (version,) = _unpack(">B", data, body, stop)
    if version == 1:
        if track:
            return None, _unpack(">Q", data, body + 28, stop)[0]
        timescale, duration = _unpack(">IQ", data, body + 20, stop)
    elif version == 0:
        if track:
            return None, _unpack(">I", data, body + 20, stop)[0]
        timescale, duration = _unpack(">II", data, body + 12, stop)
    else:
        raise Mp4Error("Unsupported MP4 header version")
    if not 0 < timescale <= 10**9:
        raise Mp4Error("Invalid MP4 timescale")
    return timescale, duration


def _descriptor(data, offset, stop):
    (tag,) = _unpack(">B", data, offset, stop)
    offset += 1
    length = 0
    for _ in range(4):
        (byte,) = _unpack(">B", data, offset, stop)
        offset += 1
        length = (length << 7) | (byte & 0x7F)
        if not byte & 0x80:
            break
    if offset + length > stop:
        raise Mp4Error("Truncated MP4 elementary stream descriptor")
    return tag, offset, offset + length


def _aac(data, body, stop):
    """Read the ES descriptor object type; MPEG-4 Audio (0x40) carries AAC."""
    tag, offset, end = _descriptor(data, body + 4, stop)
    if tag != 0x03:
        raise Mp4Error("Missing MP4 elementary stream descriptor")
    _, flags = _unpack(">HB", data, offset, end)
    offset += 3
    if flags & 0x80:
        offset += 2
    if flags & 0x40:
        (url,) = _unpack(">B", data, offset, end)
        offset += 1 + url
    if flags & 0x20:
        offset += 2
    tag, offset, end = _descriptor(data, offset, end)
    if tag != 0x04:
        raise Mp4Error("Missing MP4 decoder configuration")
    return _unpack(">B", data, offset, end)[0]


def _entry(data, body, stop, budget):
    found = _children(data, body, stop, budget)
    entries = found.get(b"stsd", [])
    if len(entries) != 1:
        raise Mp4Error("MP4 track needs one sample description")
    start, end = entries[0]
    (count,) = _unpack(">I", data, start + 4, end)
    if count != 1:
        raise Mp4Error("MP4 track needs exactly one sample description")
    entries = list(_boxes(data, start + 8, end, budget))
    if len(entries) != 1:
        raise Mp4Error("MP4 sample description is ambiguous")
    return found, entries[0]


def _samples(data, found):
    start, end = _one(found, b"stsz")
    _, _, frames = _unpack(">III", data, start, end)
    start, end = _one(found, b"stts")
    (count,) = _unpack(">I", data, start + 4, end)
    if not 1 <= count <= 1_000_000 or start + 8 + count * 8 > end:
        raise Mp4Error("Invalid MP4 sample timing table")
    total, deltas = 0, set()
    for index in range(count):
        number, delta = struct.unpack_from(">II", data, start + 8 + index * 8)
        total += number
        if number:
            deltas.add(delta)
    if total != frames:
        raise Mp4Error("MP4 sample timing and size tables disagree")
    return frames, deltas


def _track(data, body, stop, movie_scale, budget):
    trak = _children(data, body, stop, budget)
    _, duration = _full_box_duration(data, *_one(trak, b"tkhd"), track=True)
    presented = Fraction(duration, movie_scale)
    mdia = _children(data, *_one(trak, b"mdia"), budget)
    scale, _ = _full_box_duration(data, *_one(mdia, b"mdhd"), track=False)
    start, end = _one(mdia, b"hdlr")
    (handler,) = _unpack(">4s", data, start + 8, end)
    minf = _children(data, *_one(mdia, b"minf"), budget)
    stbl, (kind, entry, entry_end) = _entry(data, *_one(minf, b"stbl"), budget)
    if handler == b"vide":
        width, height = _unpack(">HH", data, entry + 24, entry_end)
        profile, codec = None, kind.decode("ascii", "replace")
        if kind in {b"avc1", b"avc3"}:
            codec = "h264"
            config = _children(data, entry + 78, entry_end, budget)
            start, end = _one(config, b"avcC")
            version, profile = _unpack(">BB", data, start, end)
            if version != 1:
                raise Mp4Error("Unsupported H.264 configuration record")
        frames, deltas = _samples(data, stbl)
        rate = Fraction(scale, deltas.pop()) if len(deltas) == 1 and 0 not in deltas else None
        return Mp4Video(codec, profile, width, height, frames, rate, presented)
    if handler == b"soun":
        (version,) = _unpack(">H", data, entry + 8, entry_end)
        channels, _, _, _, rate = _unpack(">HHHHI", data, entry + 16, entry_end)
        extra = {0: 0, 1: 16, 2: 36}.get(version)
        if extra is None:
            raise Mp4Error("Unsupported MP4 audio sample description")
        codec = kind.decode("ascii", "replace")
        if kind == b"mp4a":
            config = _children(data, entry + 28 + extra, entry_end, budget)
            if _aac(data, *_one(config, b"esds")) == AAC_OBJECT_TYPE:
                codec = "aac"
        _samples(data, stbl)
        return Mp4Audio(codec, rate >> 16, channels, presented)
    return None


def inspect(path, *, maximum=16 * 1024**3):
    """Summarize one regular MP4 file's tracks without decoding any samples."""
    path = Path(path)
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0)
    # NONBLOCK keeps a substituted FIFO from hanging before the regular-file check.
    fd = os.open(path, flags | getattr(os, "O_NONBLOCK", 0))
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode):
            raise Mp4Error("Inspect only a regular MP4 file")
        if not 16 <= info.st_size <= maximum:
            raise Mp4Error("MP4 size is outside the inspection policy")
        offset, kinds, movie = 0, [], None
        while offset < info.st_size:
            if len(kinds) >= MAX_TOP_LEVEL:
                raise Mp4Error("MP4 has too many top-level boxes")
            stream.seek(offset)
            header = stream.read(16)
            if len(header) < 8:
                raise Mp4Error("Truncated MP4 box header")
            size, kind = struct.unpack_from(">I4s", header)
            length = 8
            if size == 1:
                if len(header) < 16:
                    raise Mp4Error("Truncated MP4 box header")
                size, length = struct.unpack_from(">Q", header, 8)[0], 16
            elif size == 0:
                size = info.st_size - offset
            if size < length or size > info.st_size - offset:
                raise Mp4Error("MP4 box exceeds the file")
            kinds.append(kind)
            if kind == b"moov":
                if movie is not None or size > MAX_MOVIE_BYTES:
                    raise Mp4Error("MP4 movie metadata is ambiguous or too large")
                stream.seek(offset)
                movie = stream.read(size)
                if len(movie) != size:
                    raise Mp4Error("MP4 movie metadata changed while reading")
            offset += size
    if not kinds or kinds[0] != b"ftyp" or b"mdat" not in kinds or movie is None:
        raise Mp4Error("File is not a complete MP4 movie")
    budget = _Budget()
    found = _children(movie, 8, len(movie), budget)
    movie_scale, _ = _full_box_duration(movie, *_one(found, b"mvhd"), track=False)
    tracks = found.get(b"trak", [])
    if not 1 <= len(tracks) <= MAX_TRACKS:
        raise Mp4Error("MP4 track inventory is outside the inspection policy")
    video, audio, other = [], [], 0
    for body, stop in tracks:
        track = _track(movie, body, stop, movie_scale, budget)
        if isinstance(track, Mp4Video):
            video.append(track)
        elif isinstance(track, Mp4Audio):
            audio.append(track)
        else:
            other += 1
    return Mp4Summary(tuple(video), tuple(audio), other)
