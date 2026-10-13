# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Saved audio played through Blender's audio engine in an owned offline process, without bpy.

Playing a saved audio result never decodes generated media in the user's
Blender. Blender's audio module holds Python's global interpreter lock while it
decodes (see ``audio_decode``), its ffmpeg readers would parse a generated file
inside the session that holds unsaved work, and an output device opened there
would stay with the session. Instead, ``start`` runs the standalone
``audio_player_worker.py`` in a separate factory-startup Blender started with
``--offline-mode``, ``--disable-autoexec``, ``--background`` and ``-noaudio``,
the scrubbed environment and disposable profile of ``local_render``, and a
private ``listen-*`` directory for its request, profile, temporary files and
reports. That child checks the private copy decodes, opens the one output
device the request names and plays the copy from its start.

An ``AudioPlayer`` owns one child. Its owner polls it, normally from a timer on
Blender's main thread: no method blocks except ``wait``, which is bounded and
meant for unregistering. ``stop`` closes the child's standard input, which the
child treats as its stop signal, and terminates it; a child still running
``STOP_GRACE`` seconds later is killed on the next poll. Because the parent
never writes to that pipe, a parent that exits or crashes also stops it. A child
must report playback or a failure within its start timeout, and is stopped
``END_GRACE`` seconds after the duration it reported, or its limit. Its
directory is removed once it has exited; a day-old sweep removes directories
a crash left behind. Errors name no path and carry no output of the child.
"""

import json
import math
import os
import shutil
import stat
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from ..audio_waveform import MAX_SECONDS
from .local_render import LocalRenderError, _environment, blender_path
from .playback import PlaybackError, playback_root
from .transfers import TransferError, _root
from .upload_sources import _open

FORMAT = 1
PREFIX = "listen-"
START_TIMEOUT = 60.0
END_GRACE = 10.0
STOP_GRACE = 3.0
STALE_SECONDS = 24 * 60 * 60
REPORT_MAX_BYTES = 256
DEVICE_NAME_LENGTH = 64
# The child's phases. STARTING and PLAYING hold the output; the others are final.
STARTING, PLAYING, ENDED, STOPPED, FAILED = "STARTING", "PLAYING", "ENDED", "STOPPED", "FAILED"
ACTIVE = frozenset({STARTING, PLAYING})
_ERRORS = {
    "unreadable": "Blender could not decode this audio",
    "unsupported": "This audio's sample rate or channel count is not supported",
    "empty": "This audio contains no samples",
    "too_long": "This audio is longer than Blender plays here; open it in the system player",
    "device": "Blender could not play through the audio output chosen in Preferences",
}
_UNKNOWN = "Blender could not play this audio"


class AudioPlayerError(RuntimeError):
    """A sanitized refusal before a child starts; nothing was played."""


@dataclass(frozen=True)
class PlayerSpec:
    """The Blender executable, bundled worker and output device, resolved on the main thread."""

    binary: Path
    worker: Path
    device: str
    start_timeout: float = START_TIMEOUT
    max_seconds: int = MAX_SECONDS

    def __post_init__(self):
        if any(
            not isinstance(path, Path) or not path.is_absolute()
            for path in (self.binary, self.worker)
        ):
            raise ValueError("Use absolute Blender executable and audio player paths")
        if (
            not isinstance(self.device, str)
            or not 0 < len(self.device) <= DEVICE_NAME_LENGTH
            or not self.device.isprintable()
        ):
            raise ValueError("Name one audio output device")
        if (
            isinstance(self.start_timeout, bool)
            or not isinstance(self.start_timeout, (int, float))
            or not math.isfinite(self.start_timeout)
            or not 0 < self.start_timeout <= 600
        ):
            raise ValueError("Use a finite start timeout of at most 600 seconds")
        if type(self.max_seconds) is not int or not 1 <= self.max_seconds <= MAX_SECONDS:
            raise ValueError("Use a playback limit of at most 600 seconds")


def _report(path):
    """One small JSON report the child published, or None while it is absent or invalid."""
    try:
        stream, info = _open(path)
        with stream:
            if info.st_size > REPORT_MAX_BYTES:
                return None
            value = json.loads(stream.read(REPORT_MAX_BYTES + 1))
    except (OSError, TransferError, ValueError):
        return None
    return value if isinstance(value, dict) and value.get("format") == FORMAT else None


def _seconds(value, limit):
    """The duration the child reported, within ``limit``, or None when it declared none."""
    seconds = value.get("seconds")
    if type(seconds) not in (int, float) or not math.isfinite(seconds) or seconds <= 0:
        return None
    return min(float(seconds), float(limit))


def _remove(root, directory):
    """Remove one ``listen-*`` directory directly below ``root``; leave anything else."""
    if not directory.name.startswith(PREFIX) or directory.parent != root:
        return
    try:
        if stat.S_ISDIR(directory.lstat().st_mode):
            shutil.rmtree(directory, ignore_errors=True)
    except OSError:
        pass  # Already gone, or still held on Windows: the age sweep removes it.


class AudioPlayer:
    """One owned playback child, polled by its owner; see the module documentation."""

    def __init__(self, process, root, directory, spec, clock):
        self._process = process
        self._root = root
        self.directory = directory
        self._spec = spec
        self._clock = clock
        self.phase = STARTING
        self.reason = ""
        self.seconds = None
        self._deadline = clock() + spec.start_timeout
        self._kill_at = None
        self._removed = False

    @property
    def active(self):
        """Whether the child is starting or playing, as far as the last poll knows."""
        return self.phase in ACTIVE

    @property
    def exited(self):
        return self._process.poll() is not None

    def _finish(self, phase, reason=""):
        self.phase, self.reason = phase, reason
        self._halt()

    def _close_input(self):
        stream = self._process.stdin
        if stream is not None:
            try:
                stream.close()
            except OSError:
                pass  # The child already exited and its end of the pipe is gone.

    def _halt(self):
        """Close the lifeline and terminate a running child; the next poll kills it if needed."""
        self._close_input()
        if self._process.poll() is None and self._kill_at is None:
            try:
                self._process.terminate()
            except OSError:
                pass  # It exited between the poll and the signal.
            self._kill_at = self._clock() + STOP_GRACE

    def _reap(self):
        if (
            self._kill_at is not None
            and self._process.poll() is None
            and self._clock() >= self._kill_at
        ):
            try:
                self._process.kill()
            except OSError:
                pass

    def _failure(self):
        value = _report(self.directory / "output" / "error.json")
        code = None if value is None else value.get("error")
        return _ERRORS.get(code, _UNKNOWN) if isinstance(code, str) else _UNKNOWN

    def poll(self):
        """Advance the phase from the child's reports, exit and deadlines; True when it changed."""
        if not self.active:
            self._reap()
            return False
        code = self._process.poll()
        now = self._clock()
        if self.phase == STARTING:
            report = _report(self.directory / "output" / "playing.json")
            if report is not None:
                self.phase = PLAYING
                self.seconds = _seconds(report, self._spec.max_seconds)
                limit = self._spec.max_seconds if self.seconds is None else self.seconds
                self._deadline = now + limit + END_GRACE
                return True
            if code is not None:
                self._finish(FAILED, self._failure())
            elif now >= self._deadline:
                self._finish(FAILED, "Blender's audio engine did not start in time")
            else:
                return False
            return True
        if code is not None:
            # A child that crashed while playing reports nothing more useful.
            self._finish(ENDED if code == 0 else FAILED, "" if code == 0 else _UNKNOWN)
            return True
        if now >= self._deadline:
            self._finish(ENDED)
            return True
        return False

    def stop(self):
        """Stop playback now: close the lifeline and terminate the child; never blocks."""
        if self.active:
            self.phase = STOPPED
        self._halt()

    def wait(self, timeout=STOP_GRACE):
        """Stop and wait for the child to exit, killing it after ``timeout``; for unregistering."""
        self.stop()
        try:
            self._process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            try:
                self._process.kill()
            except OSError:
                pass
            try:
                self._process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                return False
        return True

    def release(self):
        """Remove the child's directory once it has exited; True when nothing remains to do."""
        if self._removed:
            return True
        if self._process.poll() is None:
            return False
        _remove(self._root, self.directory)
        self._removed = True
        return True


def start(source, root, spec, *, popen=None, clock=None):
    """Start one owned child that plays the private copy ``source`` on ``spec.device``.

    ``root`` is the private directory the caller owns for playback children;
    this call creates one ``listen-*`` directory in it. The caller binds
    ``source`` to its bytes, for example with a receipt-checked private copy,
    and polls, stops and releases the returned player.
    """
    if not isinstance(spec, PlayerSpec):
        raise TypeError("Use an audio player specification")
    source = Path(source)
    if not source.is_absolute():
        raise AudioPlayerError("Play only an absolute private copy")
    if not spec.binary.is_file() or not spec.worker.is_file():
        raise AudioPlayerError("Playing audio needs Blender's executable and bundled player")
    try:
        root = playback_root(root)
        # Only the name comes from mkdtemp, which normalizes the path it returns
        # on Python 3.12 and later; keep the canonical root's spelling.
        directory = root / Path(tempfile.mkdtemp(prefix=PREFIX, dir=root)).name
    except (OSError, PlaybackError):
        raise AudioPlayerError("Audio playback storage is unavailable") from None
    clock = time.monotonic if clock is None else clock
    try:
        profile, temporary, output = directory / "profile", directory / "tmp", directory / "output"
        for path in (profile, temporary, output):
            path.mkdir(mode=0o700)
        request = directory / "request.json"
        with request.open("x", encoding="utf-8") as stream:
            os.chmod(request, 0o600)
            json.dump(
                {
                    "format": FORMAT,
                    "source": blender_path(source),
                    "output": blender_path(output),
                    "device": spec.device,
                    "max_seconds": spec.max_seconds,
                },
                stream,
            )
        command = [
            blender_path(spec.binary),
            "--offline-mode",
            "--factory-startup",
            "--disable-autoexec",
            "--background",
            "-noaudio",
            "--python-exit-code",
            "1",
            "--python",
            blender_path(spec.worker),
            "--",
            blender_path(request),
        ]
        process = (subprocess.Popen if popen is None else popen)(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=_environment(profile, temporary),
            cwd=blender_path(directory),
        )
    except (OSError, ValueError, LocalRenderError):
        _remove(root, directory)
        raise AudioPlayerError("Blender's audio engine could not start") from None
    except BaseException:
        _remove(root, directory)
        raise
    return AudioPlayer(process, root, directory, spec, clock)


def sweep(root, *, keep=(), now=None, older_than=STALE_SECONDS):
    """Remove stale ``listen-*`` directories that no running child still uses."""
    now = time.time() if now is None else now
    kept = {Path(path).name for path in keep}
    try:
        root = _root(Path(root))
        children = tuple(root.iterdir())
    except (OSError, TransferError):
        return
    for child in children:
        try:
            info = child.lstat()
        except OSError:
            continue
        if (
            child.name.startswith(PREFIX)
            and child.name not in kept
            and stat.S_ISDIR(info.st_mode)
            and now - info.st_mtime > older_than
        ):
            _remove(root, child)
