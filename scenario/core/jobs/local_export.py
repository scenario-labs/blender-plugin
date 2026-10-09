# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Owned offline Film video export, without bpy, service calls or a shared worker.

The parent writes an immutable scene snapshot on Blender's main thread. This
module renders it with Blender's built-in FFmpeg encoder in an offline child,
verifies the staged MP4 and publishes a verified copy that never overwrites an
existing file. The caller owns approval, the private staging directory and its
cleanup. Nothing here contacts Scenario, spends credits or writes a job record.
"""

import hashlib
import json
import math
import os
import re
import secrets
import shutil
import stat
import tempfile
import threading
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path

from . import mp4_inspection
from .local_render import (
    LocalRenderError,
    RenderCancelled,
    _environment,
    _run,
    blender_path,
    digest,
)

MAX_SECONDS = 900
MAX_FRAMES = 108000
MAX_MEDIA = 2000
MAX_MEDIA_BYTES = 16 * 1024**3
MAX_OUTPUT_BYTES = 16 * 1024**3
MAX_TIMEOUT = 21600
VIDEO_NAME = "film.mp4"
AUDIO_RATE = 48000
AUDIO_CHANNELS = 2
_PROGRESS = re.compile(rb"SCENARIO_PROGRESS (\d{1,6})/(\d{1,6})")
# Windows device names stay reserved with any extension; reject them everywhere.
_RESERVED = frozenset(
    {"CON", "PRN", "AUX", "NUL"} | {f"{port}{i}" for port in ("COM", "LPT") for i in range(1, 10)}
)


class LocalExportError(LocalRenderError):
    """Export failed; staged files may remain and the destination is never overwritten."""


class ExportPublishError(LocalExportError):
    """Rendering and verification succeeded, but copying to the destination did not.

    ``staged`` keeps the verified private output for another explicit publish.
    """

    def __init__(self, message, staged):
        super().__init__(message)
        self.staged = staged


class ExportPublishCancelled(ExportPublishError, RenderCancelled):
    """Publishing stopped before the destination changed; the staged output remains."""


@dataclass(frozen=True)
class ExportMedia:
    """A file stamp captured with the snapshot; re-checked before and after rendering."""

    path: Path
    size: int
    mtime_ns: int
    device: int
    inode: int

    def __post_init__(self):
        if not isinstance(self.path, Path) or not self.path.is_absolute():
            raise ValueError("Use absolute export media paths")
        if any(
            type(value) is not int or value < 0
            for value in (self.size, self.mtime_ns, self.device, self.inode)
        ):
            raise ValueError("Use an exact export media file stamp")


def media_stamp(path):
    """Stamp one referenced regular file, following the path Blender will open."""
    path = Path(path)
    try:
        info = path.stat()
    except OSError:
        raise LocalExportError("Export media must be existing regular files") from None
    if not stat.S_ISREG(info.st_mode) or info.st_size < 1:
        raise LocalExportError("Export media must be existing regular files")
    return ExportMedia(path, info.st_size, info.st_mtime_ns, info.st_dev, info.st_ino)


def _same(media, info):
    return (info.st_size, info.st_mtime_ns, info.st_dev, info.st_ino) == (
        media.size,
        media.mtime_ns,
        media.device,
        media.inode,
    ) and stat.S_ISREG(info.st_mode)


@dataclass(frozen=True)
class ExportSpec:
    directory: Path
    binary: Path
    worker: Path
    scene_name: str
    snapshot_sha256: str
    frame_start: int
    frame_end: int
    fps: int
    width: int
    height: int
    audio: bool
    media: tuple[ExportMedia, ...] = ()
    timeout: float | None = None
    verify_timeout: float | None = None

    def __post_init__(self):
        if any(
            not isinstance(p, Path) or not p.is_absolute()
            for p in (self.directory, self.binary, self.worker)
        ):
            raise ValueError("Use absolute owned export paths")
        if not isinstance(self.scene_name, str) or not self.scene_name or "\0" in self.scene_name:
            raise ValueError("Choose a named local scene")
        if (
            not isinstance(self.snapshot_sha256, str)
            or len(self.snapshot_sha256) != 64
            or any(c not in "0123456789abcdef" for c in self.snapshot_sha256)
        ):
            raise ValueError("Bind the exact scene snapshot")
        if type(self.fps) is not int or not 1 <= self.fps <= 120:
            raise ValueError("Use an integer export frame rate from 1 to 120")
        if (
            type(self.frame_start) is not int
            or type(self.frame_end) is not int
            or not 1 <= self.frame_start <= self.frame_end <= 1048574
            or self.frames > min(MAX_FRAMES, MAX_SECONDS * self.fps)
        ):
            raise ValueError("Export at most fifteen minutes of positive frames")
        if any(
            type(n) is not int or not 64 <= n <= 4096 or n % 2 for n in (self.width, self.height)
        ):
            raise ValueError("Use even export dimensions from 64 to 4096 pixels")
        if type(self.audio) is not bool:
            raise ValueError("Choose whether the export includes audio")
        if (
            not isinstance(self.media, tuple)
            or len(self.media) > MAX_MEDIA
            or any(not isinstance(item, ExportMedia) for item in self.media)
            or len({item.path for item in self.media}) != len(self.media)
            or sum(item.size for item in self.media) > MAX_MEDIA_BYTES
        ):
            raise ValueError("Export at most 2,000 distinct media files totalling 16 GiB")
        if any(
            n is not None
            and (
                isinstance(n, bool)
                or not isinstance(n, (int, float))
                or not math.isfinite(n)
                or not 0 < n <= MAX_TIMEOUT
            )
            for n in (self.timeout, self.verify_timeout)
        ):
            raise ValueError("Use finite positive export timeouts of at most six hours")

    @property
    def frames(self):
        return self.frame_end - self.frame_start + 1

    @property
    def duration(self):
        return Fraction(self.frames, self.fps)

    @property
    def render_timeout(self):
        """Explicit timeout, else five minutes plus two seconds per frame, at most six hours."""
        if self.timeout is not None:
            return self.timeout
        return min(MAX_TIMEOUT, 300 + 2 * self.frames)

    @property
    def check_timeout(self):
        """Explicit verification timeout, else scaled for a full decode of every frame."""
        if self.verify_timeout is not None:
            return self.verify_timeout
        return min(7200, 120 + self.frames // 25)

    def parameters(self):
        return {
            "mode": "render",
            "scene_name": self.scene_name,
            "frame_start": self.frame_start,
            "frame_end": self.frame_end,
            "fps": self.fps,
            "width": self.width,
            "height": self.height,
            "audio": self.audio,
        }


@dataclass(frozen=True)
class MediaReceipt:
    """Provenance for one exported input: basename, size and content hash only."""

    name: str
    size: int
    sha256: str


@dataclass(frozen=True, eq=False)
class StagedExport:
    """A verified private MP4 that the caller may publish again without rendering."""

    directory: Path = field(repr=False)
    path: Path = field(repr=False)
    sha256: str
    size: int
    frames: int
    fps: int
    width: int
    height: int
    audio: bool
    verification: str
    media: tuple[MediaReceipt, ...] = field(repr=False)


@dataclass(frozen=True)
class PublishedExport:
    destination: Path
    sha256: str
    size: int
    frames: int
    fps: int
    width: int
    height: int
    audio: bool
    verification: str
    media: tuple[MediaReceipt, ...] = field(repr=False)


@dataclass(frozen=True)
class Reservation:
    """A zero-byte placeholder created exclusively before a long render."""

    path: Path
    device: int
    inode: int


def validate_destination(path, *, private_roots=()):
    """Return the absolute destination with a canonical parent; never accept an existing name."""
    raw = os.fspath(path) if isinstance(path, (str, os.PathLike)) else None
    if not isinstance(raw, str) or not raw or any(ord(c) < 32 or ord(c) == 127 for c in raw):
        raise LocalExportError("Choose a destination path without control characters")
    destination = Path(raw)
    name = destination.name
    if not destination.is_absolute():
        raise LocalExportError("Choose an absolute destination path")
    if not name.lower().endswith(".mp4") or len(name) < 5 or name.startswith("."):
        raise LocalExportError("Choose a visible destination file ending in .mp4")
    if len(name.encode("utf-8")) > 255 or name.split(".")[0].upper() in _RESERVED:
        raise LocalExportError("Choose a portable destination file name")
    if os.path.lexists(destination):
        raise LocalExportError("The destination already exists; choose a new file name")
    try:
        parent = destination.parent.resolve(strict=True)
    except (OSError, RuntimeError):
        raise LocalExportError("The destination folder must already exist") from None
    if not parent.is_dir():
        raise LocalExportError("The destination folder must already exist")
    for root in private_roots:
        try:
            private = Path(root).resolve()
        except (OSError, RuntimeError):
            continue
        if parent == private or parent.is_relative_to(private):
            raise LocalExportError("Choose a destination outside Blender and extension storage")
    result = parent / name
    if os.path.lexists(result):
        raise LocalExportError("The destination already exists; choose a new file name")
    return result


def reserve(destination):
    """Create the destination exclusively as an empty placeholder; never overwrite."""
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0)
    try:
        fd = os.open(destination, flags, 0o666)
    except FileExistsError:
        raise LocalExportError("The destination already exists; choose a new file name") from None
    except OSError:
        raise LocalExportError("Cannot create the destination file; check its folder") from None
    try:
        info = os.fstat(fd)
    finally:
        os.close(fd)
    return Reservation(Path(destination), info.st_dev, info.st_ino)


def release(reservation):
    """Remove only our own still-empty placeholder; keep anything else in place."""
    try:
        info = os.lstat(reservation.path)
    except OSError:
        return
    if (
        stat.S_ISREG(info.st_mode)
        and info.st_size == 0
        and (info.st_dev, info.st_ino) == (reservation.device, reservation.inode)
    ):
        try:
            os.unlink(reservation.path)
        except OSError:
            pass


def estimated_bytes(spec):
    """Conservative output estimate: about 25 Mbit/s at 1080p, scaled by pixels."""
    seconds = float(spec.duration)
    video = seconds * 25_000_000 / 8 * (spec.width * spec.height) / (1920 * 1080)
    audio = seconds * 192_000 / 8 if spec.audio else 0
    return math.ceil(video + audio) + 64 * 1024**2


def check_space(spec, destination):
    """Fail early on an obviously full disk; a full disk later still fails cleanly."""
    needed = estimated_bytes(spec)
    try:
        staging = os.stat(spec.directory).st_dev
        target = os.stat(Path(destination).parent).st_dev
        enough = (
            shutil.disk_usage(spec.directory).free >= needed * (2 if staging == target else 1)
            and shutil.disk_usage(Path(destination).parent).free >= needed
        )
    except OSError:
        enough = False
    if not enough:
        raise LocalExportError("Not enough free disk space for this video export")


def _hash_media(spec, cancel, progress):
    total, done, receipts = sum(item.size for item in spec.media), 0, []
    # NONBLOCK keeps a substituted FIFO from hanging before the identity check.
    flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_BINARY", 0)
    for item in spec.media:
        try:
            with os.fdopen(os.open(item.path, flags), "rb") as stream:
                if not _same(item, os.fstat(stream.fileno())):
                    raise LocalExportError("Export media changed after the scene snapshot")
                value = hashlib.sha256()
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    if cancel.is_set():
                        raise RenderCancelled("Film export cancelled")
                    value.update(chunk)
                    done += len(chunk)
                    progress("media", min(done, total), total)
                if not _same(item, os.fstat(stream.fileno())):
                    raise LocalExportError("Export media changed while hashing")
        except OSError:
            raise LocalExportError("Export media is unavailable") from None
        receipts.append(MediaReceipt(item.path.name, item.size, value.hexdigest()))
    return tuple(receipts)


def _check_media(spec):
    for item in spec.media:
        try:
            info = os.stat(item.path)
        except OSError:
            info = None
        if info is None or not _same(item, info):
            raise LocalExportError("Export media changed during rendering; export again")


def _progress_from_log(log, total):
    """Read only the bounded log tail; ignore malformed or out-of-range progress."""
    try:
        with log.open("rb") as stream:
            size = os.fstat(stream.fileno()).st_size
            stream.seek(max(0, size - 4096))
            tail = stream.read(4096)
    except OSError:
        return None
    matches = _PROGRESS.findall(tail)
    if not matches:
        return None
    done, reported = (int(value) for value in matches[-1])
    return done if reported == total and 0 <= done <= total else None


def _child(command, **options):
    """Run one owned process, reporting failures in export rather than capture terms."""
    try:
        _run(command, **options)
    except LocalExportError:
        raise
    except RenderCancelled:
        raise RenderCancelled("Film export cancelled; staged files are retained") from None
    except LocalRenderError:
        raise LocalExportError(
            "A Film export process failed or timed out; inspect its retained log"
        ) from None


def _fraction(value):
    if not isinstance(value, (str, int)) or isinstance(value, bool) or len(str(value)) > 64:
        raise ValueError("Invalid media number")
    return Fraction(value)


def _tolerance(spec):
    return max(Fraction(1, spec.fps), Fraction(1, 20))


def check_container(spec, summary):
    """Require one exact H.264 picture stream and AAC audio only when requested."""
    if (
        len(summary.video) != 1
        or summary.other_tracks
        or len(summary.audio) != (1 if spec.audio else 0)
    ):
        raise LocalExportError("Exported video has an unexpected stream inventory")
    video = summary.video[0]
    if (
        video.codec != "h264"
        or video.profile not in mp4_inspection.H264_420_PROFILES
        or (video.width, video.height) != (spec.width, spec.height)
        or video.frames != spec.frames
        or video.frame_rate != spec.fps
    ):
        raise LocalExportError("Exported video does not match the approved H.264 frames")
    if spec.audio:
        audio = summary.audio[0]
        if (
            audio.codec != "aac"
            or (audio.sample_rate, audio.channels) != (AUDIO_RATE, AUDIO_CHANNELS)
            or abs(audio.duration - spec.duration) > _tolerance(spec)
        ):
            raise LocalExportError("Exported audio does not match the approved AAC soundtrack")


def check_probe(spec, raw):
    """Check ffprobe's decoded frame count, pixel format and stream inventory."""
    try:
        streams = json.loads(raw)["streams"]
        if not isinstance(streams, list) or not 1 <= len(streams) <= 8:
            raise ValueError("Invalid stream inventory")
        video = [
            s
            for s in streams
            if s.get("codec_type") == "video" and s.get("disposition", {}).get("attached_pic") != 1
        ]
        audio = [s for s in streams if s.get("codec_type") == "audio"]
        valid = len(video) == 1 and len(audio) == int(spec.audio) and len(streams) == 1 + spec.audio
        if valid:
            picture = video[0]
            valid = (
                picture.get("codec_name") == "h264"
                and picture.get("pix_fmt") == "yuv420p"
                and (picture.get("width"), picture.get("height")) == (spec.width, spec.height)
                and int(picture.get("nb_read_frames")) == spec.frames
                and _fraction(picture.get("avg_frame_rate")) == spec.fps
            )
        if valid and spec.audio:
            sound = audio[0]
            if sound.get("duration_ts") not in (None, "N/A") and sound.get("time_base"):
                duration = _fraction(sound["duration_ts"]) * _fraction(sound["time_base"])
            else:
                duration = _fraction(sound.get("duration"))
            valid = (
                sound.get("codec_name") == "aac"
                and int(sound.get("sample_rate")) == AUDIO_RATE
                and sound.get("channels") == AUDIO_CHANNELS
                and abs(duration - spec.duration) <= _tolerance(spec)
            )
    except (ValueError, TypeError, KeyError, AttributeError, ZeroDivisionError, RecursionError):
        valid = False
    if not valid:
        raise LocalExportError("Decoded video does not match the approved frames, format or audio")


def check_blender(spec, raw):
    """Check what Blender's own FFmpeg decoder measured and decoded."""
    try:
        measured = json.loads(raw)
        sound = measured["sound"]
        frames = measured["frames"]
        valid = (
            (measured["width"], measured["height"]) == (spec.width, spec.height)
            and type(frames) is int
            and frames == spec.frames
            and abs(float(measured["fps"]) - spec.fps) < 0.0001
            and measured["decoded"] == [True, True]
        )
        if valid and spec.audio:
            slack = max(1, math.ceil(spec.fps / 20))
            valid = (
                isinstance(sound, dict)
                and sound["rate"] == AUDIO_RATE
                and sound["channels"] == "STEREO"
                and type(sound["frames"]) is int
                and abs(sound["frames"] - spec.frames) <= slack
            )
        elif valid:
            valid = sound is None or sound.get("rate") == 0
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
        valid = False
    if not valid:
        raise LocalExportError("Blender could not decode the approved frames and audio")


def _verify(spec, output, env, cancel):
    """Decode-check the staged MP4; prefer an installed ffprobe, else Blender itself."""
    tool = shutil.which("ffprobe")
    if tool:
        probe = spec.directory / "probe.json"
        _child(
            [
                str(Path(tool).resolve()),
                "-v",
                "error",
                "-protocol_whitelist",
                "file",
                "-f",
                "mov",
                "-enable_drefs",
                "0",
                "-use_absolute_path",
                "0",
                "-count_frames",
                "-show_entries",
                "stream=codec_type,codec_name,pix_fmt,width,height,avg_frame_rate,"
                "nb_read_frames,duration_ts,time_base,duration,sample_rate,channels"
                ":stream_disposition=attached_pic",
                "-of",
                "json",
                str(output),
            ],
            log=spec.directory / "probe.log",
            stdout=probe,
            env=env,
            timeout=spec.check_timeout,
            cancel=cancel,
        )
        if not 0 < probe.stat().st_size <= 65536:
            raise LocalExportError("Media inspection exceeded the size policy")
        check_probe(spec, probe.read_bytes())
        return "ffprobe"
    verify = spec.directory / "verify.json"
    with verify.open("x", encoding="utf-8") as stream:
        json.dump(
            {
                "mode": "verify",
                "video": blender_path(output),
                "frames": spec.frames,
                "fps": spec.fps,
                "width": spec.width,
                "height": spec.height,
                "audio": spec.audio,
            },
            stream,
        )
    _child(
        [
            blender_path(spec.binary),
            "--quiet",
            "--offline-mode",
            "--factory-startup",
            "--disable-autoexec",
            "--background",
            "--python-exit-code",
            "1",
            "--python",
            blender_path(spec.worker),
            "--",
            blender_path(verify),
        ],
        log=spec.directory / "verify.log",
        env=env,
        timeout=spec.check_timeout,
        cancel=cancel,
    )
    measured = spec.directory / "measured.json"
    if measured.is_symlink() or not 0 < measured.stat().st_size <= 65536:
        raise LocalExportError("Blender verification output exceeded the size policy")
    check_blender(spec, measured.read_bytes())
    return "blender"


def render(spec, *, cancel=None, progress=None):
    """Render and verify an owned snapshot; keep staged output, logs and diagnostics.

    Exactly one ``output/film.mp4`` is accepted. Verification always inspects the
    container, then decodes with an installed ffprobe or, when absent, in a second
    offline Blender child. Media stamps must be unchanged before and after.
    """
    if not isinstance(spec, ExportSpec):
        raise TypeError("Use an approved Film export specification")
    cancel = cancel if cancel is not None else threading.Event()
    progress = progress if progress is not None else (lambda *_: None)
    snapshot = spec.directory / "snapshot.blend"
    output = spec.directory / "output"
    video = output / VIDEO_NAME
    # Validate every child-visible path before consuming this export's admission.
    child_paths = [
        blender_path(path)
        for path in (
            snapshot,
            spec.binary,
            spec.worker,
            spec.directory / "started.json",
            spec.directory / "verify.json",
            spec.directory / "measured.json",
            spec.directory / "decoded-1-1.png",
            video,
        )
    ]
    snapshot_argument, binary_argument, worker_argument, parameters_argument = child_paths[:4]
    if spec.directory.is_symlink() or not spec.directory.is_dir():
        raise LocalExportError("The owned export directory is unavailable")
    if digest(snapshot) != spec.snapshot_sha256:
        raise LocalExportError("The exported scene snapshot changed")
    if not spec.binary.is_file() or not spec.worker.is_file():
        raise LocalExportError("The Blender executable or bundled export worker is unavailable")
    receipts = _hash_media(spec, cancel, progress)
    with tempfile.TemporaryDirectory(prefix="worker-", dir=spec.directory) as owned:
        root = Path(owned)
        profile, temporary = root / "profile", root / "tmp"
        profile.mkdir()
        temporary.mkdir()
        env = _environment(profile, temporary)
        if cancel.is_set():
            raise RenderCancelled("Film export cancelled")
        with (spec.directory / "started.json").open("x", encoding="utf-8") as stream:
            json.dump(spec.parameters(), stream)
        output.mkdir(mode=0o700)
        log = spec.directory / "render.log"
        progress("render", 0, spec.frames)

        def poll():
            try:
                size = video.lstat().st_size
            except FileNotFoundError:
                size = 0
            if size > MAX_OUTPUT_BYTES:
                raise LocalExportError("Exported video exceeded the size policy")
            done = _progress_from_log(log, spec.frames)
            if done is not None:
                progress("render", done, spec.frames)

        _child(
            [
                binary_argument,
                "--quiet",
                "--offline-mode",
                "--factory-startup",
                "--disable-autoexec",
                "--background",
                snapshot_argument,
                "--python-exit-code",
                "1",
                "--python",
                worker_argument,
                "--",
                parameters_argument,
            ],
            log=log,
            env=env,
            timeout=spec.render_timeout,
            cancel=cancel,
            on_poll=poll,
        )
        if set(output.iterdir()) != {video} or video.is_symlink() or not video.is_file():
            raise LocalExportError("The export did not produce exactly one MP4 file")
        size = video.stat().st_size
        if not 0 < size <= MAX_OUTPUT_BYTES:
            raise LocalExportError("Exported video exceeded the size policy")
        progress("verify", 0, 1)
        try:
            summary = mp4_inspection.inspect(video, maximum=MAX_OUTPUT_BYTES)
        except (mp4_inspection.Mp4Error, OSError):
            raise LocalExportError("Exported file is not a complete MP4 movie") from None
        check_container(spec, summary)
        verification = _verify(spec, video, env, cancel)
        progress("verify", 1, 1)
    _check_media(spec)
    if cancel.is_set():
        raise RenderCancelled("Film export cancelled; staged output is retained")
    return StagedExport(
        spec.directory,
        video,
        digest(video, maximum=MAX_OUTPUT_BYTES),
        size,
        spec.frames,
        spec.fps,
        spec.width,
        spec.height,
        spec.audio,
        verification,
        receipts,
    )


def _fsync_directory(path):
    if os.name == "nt":
        return
    try:
        fd = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def publish(staged, destination, reservation=None, *, cancel=None, progress=None):
    """Copy verified bytes next to the destination, then atomically replace our placeholder.

    Failure or cancellation removes the partial copy and our own placeholder,
    keeps the staged output for another explicit publish and never overwrites.
    """
    if not isinstance(staged, StagedExport):
        raise TypeError("Use a verified staged export")
    cancel = cancel if cancel is not None else threading.Event()
    progress = progress if progress is not None else (lambda *_: None)
    destination = Path(destination)
    if reservation is None:
        # A copy-only publish reserves its new destination exclusively first.
        reservation = reserve(destination)
    elif not isinstance(reservation, Reservation) or reservation.path != destination:
        raise TypeError("Use this destination's placeholder reservation")
    partial = destination.parent / f".{destination.name}.scenario-{secrets.token_hex(6)}.partial"
    created = None
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        flags |= getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0)
        try:
            fd = os.open(partial, flags, 0o666)
        except OSError:
            raise ExportPublishError(
                "Cannot write next to the destination; check its folder", staged
            ) from None
        value, copied = hashlib.sha256(), 0
        with os.fdopen(fd, "wb") as target:
            info = os.fstat(target.fileno())
            created = (info.st_dev, info.st_ino)
            try:
                with open(staged.path, "rb") as source:
                    for chunk in iter(lambda: source.read(1024 * 1024), b""):
                        if cancel.is_set():
                            raise ExportPublishCancelled(
                                "Film export publishing cancelled; nothing was overwritten",
                                staged,
                            )
                        value.update(chunk)
                        copied += len(chunk)
                        if copied > staged.size:
                            break
                        target.write(chunk)
                        progress("publish", copied, staged.size)
                target.flush()
                os.fsync(target.fileno())
            except OSError:
                raise ExportPublishError(
                    "Could not copy the verified video to the destination", staged
                ) from None
        if (copied, value.hexdigest()) != (staged.size, staged.sha256):
            raise ExportPublishError("The staged video changed before publishing", staged)
        try:
            current = os.lstat(destination)
        except OSError:
            current = None
        if (
            current is None
            or not stat.S_ISREG(current.st_mode)
            or current.st_size != 0
            or (current.st_dev, current.st_ino) != (reservation.device, reservation.inode)
        ):
            raise ExportPublishError(
                "The destination changed during export; nothing was overwritten", staged
            )
        try:
            os.replace(partial, destination)
        except OSError:
            raise ExportPublishError(
                "Could not move the verified video into place", staged
            ) from None
        created = None
        _fsync_directory(destination.parent)
    except BaseException:
        if created is not None:
            try:
                info = os.lstat(partial)
                if (info.st_dev, info.st_ino) == created:
                    os.unlink(partial)
            except OSError:
                pass
        release(reservation)
        raise
    return PublishedExport(
        destination,
        staged.sha256,
        staged.size,
        staged.frames,
        staged.fps,
        staged.width,
        staged.height,
        staged.audio,
        staged.verification,
        staged.media,
    )


def discard_staging(directory):
    """Remove one private staging directory; never touches a published destination."""
    path = Path(directory)
    if path.is_symlink() or not path.is_dir() or not path.name.startswith("film-export-"):
        raise LocalExportError("Discard only an owned Film export staging directory")
    shutil.rmtree(path)
