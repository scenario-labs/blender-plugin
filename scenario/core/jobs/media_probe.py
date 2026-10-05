# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Receipt-bound local media inspection with an optional installed ffprobe."""

import hashlib
import json
import os
import re
import shutil
import tempfile
import threading
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

from .local_render import LocalRenderError, RenderCancelled, _environment, _run
from .transfers import DownloadedResult, TransferError, _root
from .upload_sources import _open, _stamp

MAX_BYTES = 512 * 1024**2
# Force a reviewed container demuxer; never interpret playlists or infer a URL.
FORMATS = {
    "video/mp4": ("video", ".mp4", "mov"),
    "video/quicktime": ("video", ".mov", "mov"),
    "video/webm": ("video", ".webm", "matroska"),
    "video/x-matroska": ("video", ".mkv", "matroska"),
    "video/x-msvideo": ("video", ".avi", "avi"),
    "audio/wav": ("audio", ".wav", "wav"),
    "audio/x-wav": ("audio", ".wav", "wav"),
    "audio/mpeg": ("audio", ".mp3", "mp3"),
    "audio/ogg": ("audio", ".ogg", "ogg"),
    "audio/flac": ("audio", ".flac", "flac"),
    "audio/x-flac": ("audio", ".flac", "flac"),
    "audio/mp4": ("audio", ".m4a", "mov"),
    "audio/aac": ("audio", ".aac", "aac"),
}


class MediaProbeError(RuntimeError):
    """Inspection failed without changing a source, uploading or spending."""


@dataclass(frozen=True)
class MediaInfo:
    kind: str
    sha256: str
    size: int
    duration: Fraction
    width: int | None = None
    height: int | None = None
    frame_rate: Fraction | None = None
    audio_duration: Fraction | None = None


def probe_tool():
    tool = shutil.which("ffprobe")
    if not tool:
        raise MediaProbeError("Install ffprobe on PATH before inspecting Film media")
    return Path(tool).resolve()


def _fraction(value):
    if not isinstance(value, (str, int)) or isinstance(value, bool) or len(str(value)) > 64:
        raise ValueError("Invalid media number")
    return Fraction(value)


def _duration(stream, metadata, *, single):
    if stream.get("duration_ts") not in (None, "N/A") and stream.get("time_base"):
        duration = _fraction(stream["duration_ts"]) * _fraction(stream["time_base"])
    elif stream.get("duration") not in (None, "N/A"):
        duration = _fraction(stream["duration"])
    else:
        tags = stream.get("tags", {})
        tag = tags.get("DURATION", tags.get("duration")) if isinstance(tags, dict) else None
        match = (
            re.fullmatch(r"(\d{1,3}):([0-5]\d):([0-5]\d(?:\.\d{1,12})?)", tag)
            if isinstance(tag, str)
            else None
        )
        if match:
            duration = 3600 * int(match[1]) + 60 * int(match[2]) + Fraction(match[3])
        elif single:
            duration = _fraction(metadata.get("format", {}).get("duration"))
        else:
            raise ValueError("Missing per-stream duration")
    if not 0 < duration <= 86400:
        raise ValueError("Unbounded media duration")
    return duration


def _metadata(raw, kind, receipt):
    try:
        metadata = json.loads(raw)
        streams = metadata["streams"]
        if not isinstance(streams, list) or not 1 <= len(streams) <= 64:
            raise ValueError("Invalid stream inventory")
        video, audio = [], []
        for stream in streams:
            if not isinstance(stream, dict):
                raise ValueError("Invalid stream")
            media_kind = stream.get("codec_type")
            if media_kind == "video":
                if stream.get("disposition", {}).get("attached_pic") != 1:
                    video.append(stream)
            elif media_kind == "audio":
                audio.append(stream)
        if (
            len(video) > 1
            or len(audio) > 1
            or (kind == "video" and not video)
            or (kind == "audio" and (not audio or video))
        ):
            raise ValueError("Ambiguous media streams")
        single = len(video) + len(audio) == 1
        sound_duration = _duration(audio[0], metadata, single=single) if audio else None
        if kind == "audio":
            return MediaInfo(
                kind, receipt.sha256, receipt.size, sound_duration, audio_duration=sound_duration
            )
        picture = video[0]
        width, height = picture["width"], picture["height"]
        if any(type(n) is not int or not 1 <= n <= 16384 for n in (width, height)):
            raise ValueError("Invalid media dimensions")
        fps = _fraction(picture.get("avg_frame_rate"))
        if not 0 < fps <= 240:
            raise ValueError("Invalid media frame rate")
        return MediaInfo(
            kind,
            receipt.sha256,
            receipt.size,
            _duration(picture, metadata, single=single),
            width,
            height,
            fps,
            sound_duration,
        )
    except (ValueError, TypeError, KeyError, ZeroDivisionError, AttributeError, RecursionError):
        raise MediaProbeError(
            "Media has unsupported, ambiguous or missing timing metadata"
        ) from None


def _snapshot(path, receipt, target, cancel):
    source, before = _open(path)
    size, digest = 0, hashlib.sha256()
    with source, target.open("xb") as output:
        if before.st_size != receipt.size:
            raise MediaProbeError("Saved media size changed")
        while chunk := source.read(min(65536, receipt.size - size + 1)):
            if cancel.is_set():
                raise RenderCancelled("Media inspection cancelled")
            size += len(chunk)
            if size > receipt.size:
                raise MediaProbeError("Saved media changed while copying")
            digest.update(chunk)
            output.write(chunk)
        output.flush()
        os.fsync(output.fileno())
        if (
            size != receipt.size
            or digest.hexdigest() != receipt.sha256
            or (_stamp(before) != _stamp(os.fstat(source.fileno())))
        ):
            raise MediaProbeError("Saved media no longer matches its receipt")


def measure(path, receipt, media_type, *, root, cancel=None, timeout=30):
    """Inspect only a private copy matching the exact saved receipt, then remove it.

    The caller owns the trusted source/root and selected scope. Container metadata
    is measured, not a full decode or human motion/audio acceptance certificate.
    """
    if not isinstance(receipt, DownloadedResult) or not 0 < receipt.size <= MAX_BYTES:
        raise ValueError("Use a bounded saved media receipt")
    if type(timeout) not in (int, float) or not 0 < timeout <= 120:
        raise ValueError("Use a positive media timeout of at most 120 seconds")
    path = Path(path)
    if not path.is_absolute() or path.name != receipt.name or media_type not in FORMATS:
        raise ValueError("Select a supported receipt-bound local media file")
    root = _root(root)
    cancel = cancel if cancel is not None else threading.Event()
    if cancel.is_set():
        raise RenderCancelled("Media inspection cancelled")
    tool = probe_tool()
    kind, suffix, demuxer = FORMATS[media_type]
    try:
        with tempfile.TemporaryDirectory(prefix="film-probe-", dir=root) as temporary:
            directory = Path(temporary)
            media = directory / ("source" + suffix)
            _snapshot(path, receipt, media, cancel)
            scratch, profile = directory / "tmp", directory / "profile"
            scratch.mkdir()
            profile.mkdir()
            command = [
                str(tool),
                "-v",
                "error",
                "-max_alloc",
                "33554432",
                "-protocol_whitelist",
                "file",
                "-f",
                demuxer,
            ]
            if demuxer == "mov":
                command += ["-enable_drefs", "0", "-use_absolute_path", "0"]
            command += [
                "-i",
                str(media),
                "-show_entries",
                "stream=codec_type,duration_ts,time_base,duration,width,height,avg_frame_rate:stream_disposition=attached_pic:stream_tags=DURATION,duration:format=duration",
                "-of",
                "json",
            ]
            output = directory / "metadata.json"
            _run(
                command,
                log=directory / "probe.log",
                env=_environment(profile, scratch),
                timeout=timeout,
                cancel=cancel,
                stdout=output,
            )
            if cancel.is_set():
                raise RenderCancelled("Media inspection cancelled")
            if not 0 < output.stat().st_size <= 65536:
                raise MediaProbeError("Media metadata exceeded the inspection limit")
            return _metadata(output.read_bytes(), kind, receipt)
    except (MediaProbeError, RenderCancelled):
        raise
    except (OSError, ValueError, LocalRenderError, TransferError):
        raise MediaProbeError(
            "Could not inspect saved media; check its receipt and installed ffprobe"
        ) from None
