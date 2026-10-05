# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Owned local Blender/ffmpeg processes, without bpy, service calls or another queue.

The PNG/playblast workflow adapts the selected first-party Studio scene.py and
render_worker.py; see docs/STUDIO_ADOPTION.md. The caller owns approval and storage.
"""

import hashlib
import json
import math
import os
import shutil
import struct
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

from .upload_sources import _open


class LocalRenderError(RuntimeError):
    """Local frames/logs may remain; failure never authorizes upload or generation."""


class RenderCancelled(LocalRenderError):
    pass


def digest(path, *, maximum=1024**3):
    stream, info = _open(Path(path))
    with stream:
        if not 1 <= info.st_size <= maximum:
            raise LocalRenderError("Local render file exceeds the size policy")
        value = hashlib.sha256()
        for chunk in iter(lambda: stream.read(65536), b""):
            value.update(chunk)
    return value.hexdigest()


@dataclass(frozen=True)
class RenderSpec:
    directory: Path
    binary: Path
    worker: Path
    scene_name: str
    snapshot_sha256: str
    frame_start: int
    frame_end: int
    fps: float
    width: int
    height: int
    kind: str = "VIDEO"
    color_type: str = "MATERIAL"
    timeout: float = 1800
    encode_timeout: float = 300

    def __post_init__(self):
        if any(
            not isinstance(p, Path) or not p.is_absolute()
            for p in (self.directory, self.binary, self.worker)
        ):
            raise ValueError("Use absolute owned render paths")
        if not isinstance(self.scene_name, str) or not self.scene_name or "\0" in self.scene_name:
            raise ValueError("Choose a named local scene")
        if (
            not isinstance(self.snapshot_sha256, str)
            or len(self.snapshot_sha256) != 64
            or any(c not in "0123456789abcdef" for c in self.snapshot_sha256)
        ):
            raise ValueError("Bind the exact scene snapshot")
        if (
            type(self.frame_start) is not int
            or type(self.frame_end) is not int
            or not 1 <= self.frame_start <= self.frame_end <= 1048574
            or not 1 <= self.frame_end - self.frame_start + 1 <= 1800
        ):
            raise ValueError("Capture one to 1800 exact positive frames")
        if (
            isinstance(self.fps, bool)
            or not isinstance(self.fps, (int, float))
            or not math.isfinite(self.fps)
            or not 1 <= self.fps <= 120
        ):
            raise ValueError("Use a finite frame rate from 1 to 120")
        if any(type(n) is not int or not 64 <= n <= 4096 for n in (self.width, self.height)):
            raise ValueError("Use capture dimensions from 64 to 4096 pixels")
        if self.kind not in {"STILL", "VIDEO"} or self.color_type not in {
            "MATERIAL",
            "TEXTURE",
            "OBJECT",
        }:
            raise ValueError("Choose a still/video capture and a supported Workbench color mode")
        if self.kind == "STILL" and self.frame_start != self.frame_end:
            raise ValueError("A still captures exactly one selected frame")
        if self.kind == "VIDEO" and (self.width % 2 or self.height % 2):
            raise ValueError("MP4 dimensions must be even; implicit padding is not supported")
        if any(
            isinstance(n, bool)
            or not isinstance(n, (int, float))
            or not math.isfinite(n)
            or not 0 < n <= 7200
            for n in (self.timeout, self.encode_timeout)
        ):
            raise ValueError("Use finite positive bounded process timeouts")

    @property
    def frames(self):
        return self.frame_end - self.frame_start + 1

    def parameters(self):
        return {
            "scene_name": self.scene_name,
            "frame_start": self.frame_start,
            "frame_end": self.frame_end,
            "fps": self.fps,
            "width": self.width,
            "height": self.height,
            "color_type": self.color_type,
        }


@dataclass(frozen=True)
class RenderedMedia:
    path: Path
    sha256: str
    size: int
    content_type: str
    frames: int
    fps: float
    width: int
    height: int


def media_tools():
    """Optional installed tools only: never fetch a binary or alter PATH."""
    ffmpeg, ffprobe = shutil.which("ffmpeg"), shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        raise LocalRenderError(
            "MP4 capture requires ffmpeg and ffprobe on PATH; still capture remains available"
        )
    return Path(ffmpeg).resolve(), Path(ffprobe).resolve()


def _environment(profile, temporary):
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.upper().startswith(("SCENARIO_", "BLENDER_", "PYTHON"))
        and key.upper() not in {"HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY"}
    }
    env.update(
        BLENDER_USER_RESOURCES=str(profile), PYTHONNOUSERSITE="1", PYTHONDONTWRITEBYTECODE="1"
    )
    for key in ("TMPDIR", "TMP", "TEMP"):
        env[key] = str(temporary)
    return env


def _run(command, *, log, env, timeout, cancel, stdout=None):
    """Reap the owned child on cancellation, timeout, log overflow and exceptions."""
    if cancel.is_set():
        raise RenderCancelled("Local capture cancelled")
    with log.open("xb") as errors:
        output = stdout.open("xb") if stdout is not None else errors
        try:
            process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=output,
                stderr=errors if stdout is not None else subprocess.STDOUT,
                env=env,
                cwd=log.parent,
            )
            try:
                deadline = time.monotonic() + timeout
                while process.poll() is None:
                    if cancel.is_set():
                        raise RenderCancelled("Local capture cancelled; inspect retained frames")
                    if time.monotonic() >= deadline:
                        raise LocalRenderError("Local capture timed out; inspect retained frames")
                    if log.stat().st_size > 8 * 1024**2 or (
                        stdout is not None and stdout.stat().st_size > 65536
                    ):
                        raise LocalRenderError("Local render diagnostics exceeded the size policy")
                    cancel.wait(0.1)
                if process.returncode:
                    raise LocalRenderError("Local media process failed; inspect its retained log")
            finally:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
        finally:
            if stdout is not None:
                output.close()


def _png(path, width, height):
    stream, _ = _open(path)
    with stream:
        header = stream.read(24)
    if (
        len(header) != 24
        or header[:16] != b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        or struct.unpack(">II", header[16:24]) != (width, height)
    ):
        raise LocalRenderError("A rendered PNG has unexpected dimensions or header")


def render(spec, *, cancel=None):
    """Render an immutable owned snapshot; preserve outputs/logs and remove child profiles."""
    if not isinstance(spec, RenderSpec):
        raise TypeError("Use an approved local render specification")
    cancel = cancel if cancel is not None else threading.Event()
    tools = media_tools() if spec.kind == "VIDEO" else None
    snapshot = spec.directory / "snapshot.blend"
    if spec.directory.is_symlink() or not spec.directory.is_dir():
        raise LocalRenderError("The owned capture directory is unavailable")
    if digest(snapshot) != spec.snapshot_sha256:
        raise LocalRenderError("The captured scene snapshot changed")
    if not spec.binary.is_file() or not spec.worker.is_file():
        raise LocalRenderError("The Blender executable or bundled render worker is unavailable")
    # Exclusive admission prevents a repeated caller from overwriting/replaying this capture.
    with (spec.directory / "started.json").open("x", encoding="utf-8") as stream:
        json.dump(spec.parameters(), stream)
    frames = spec.directory / "frames"
    frames.mkdir(mode=0o700)
    with tempfile.TemporaryDirectory(prefix="worker-", dir=spec.directory) as owned:
        root = Path(owned)
        profile, temporary = root / "profile", root / "tmp"
        profile.mkdir()
        temporary.mkdir()
        env = _environment(profile, temporary)
        _run(
            [
                str(spec.binary),
                "--offline-mode",
                "--factory-startup",
                "--disable-autoexec",
                "--background",
                str(snapshot),
                "--python-exit-code",
                "1",
                "--python",
                str(spec.worker),
                "--",
                str(spec.directory / "started.json"),
            ],
            log=spec.directory / "render.log",
            env=env,
            timeout=spec.timeout,
            cancel=cancel,
        )
        expected = [frames / f"Frame-{index:06d}.png" for index in range(1, spec.frames + 1)]
        if set(frames.iterdir()) != set(expected):
            raise LocalRenderError("The render did not produce the exact requested frame sequence")
        for path in expected:
            _png(path, spec.width, spec.height)
        if spec.kind == "STILL":
            output, content_type = expected[0], "image/png"
        else:
            output, content_type = spec.directory / "capture.mp4", "video/mp4"
            ffmpeg, ffprobe = tools
            _run(
                [
                    str(ffmpeg),
                    "-hide_banner",
                    "-loglevel",
                    "warning",
                    "-nostdin",
                    "-n",
                    "-framerate",
                    str(spec.fps),
                    "-start_number",
                    "1",
                    "-i",
                    str(frames / "Frame-%06d.png"),
                    "-frames:v",
                    str(spec.frames),
                    "-c:v",
                    "libx264",
                    "-preset",
                    "fast",
                    "-crf",
                    "19",
                    "-pix_fmt",
                    "yuv420p",
                    "-an",
                    "-movflags",
                    "+faststart",
                    str(output),
                ],
                log=spec.directory / "encode.log",
                env=env,
                timeout=spec.encode_timeout,
                cancel=cancel,
            )
            probe = spec.directory / "probe.json"
            _run(
                [
                    str(ffprobe),
                    "-v",
                    "error",
                    "-select_streams",
                    "v:0",
                    "-count_frames",
                    "-show_entries",
                    "stream=width,height,nb_read_frames,avg_frame_rate",
                    "-of",
                    "json",
                    str(output),
                ],
                log=spec.directory / "probe.log",
                stdout=probe,
                env=env,
                timeout=30,
                cancel=cancel,
            )
            if probe.stat().st_size > 65536:
                raise LocalRenderError("Media inspection exceeded the size policy")
            try:
                streams = json.loads(probe.read_text(encoding="utf-8"))["streams"]
                stream = streams[0]
                valid = (
                    len(streams) == 1
                    and stream["width"] == spec.width
                    and stream["height"] == spec.height
                    and int(stream["nb_read_frames"]) == spec.frames
                    and abs(float(Fraction(stream["avg_frame_rate"])) - spec.fps) < 0.0001
                )
            except (ValueError, KeyError, IndexError, TypeError, ZeroDivisionError):
                valid = False
            if not valid:
                raise LocalRenderError(
                    "Encoded video does not match the requested frames, size or frame rate"
                )
    if cancel.is_set():
        raise RenderCancelled("Local capture cancelled; inspect retained output")
    return RenderedMedia(
        output,
        digest(output),
        output.stat().st_size,
        content_type,
        spec.frames,
        spec.fps,
        spec.width,
        spec.height,
    )
