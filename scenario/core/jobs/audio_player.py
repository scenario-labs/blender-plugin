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

An ``AudioPlayer`` owns one child and one watcher thread. Only the watcher
touches the child's files: it reads its reports and exit status, applies the
deadlines, sweeps directories a crash left behind more than a day ago and
removes the child's directory once it has exited. Its owner, normally a timer on
Blender's main thread, reads the phase from memory; no owner method touches the
file system or blocks, except ``wait``, which is bounded and meant for
unregistering. ``stop`` closes the child's standard input, which the child
treats as its stop signal, and terminates it; the watcher kills a child still
running ``STOP_GRACE`` seconds later. Because the parent never writes to that
pipe, a parent that exits or crashes also stops it. A child must report playback
or a failure within its start timeout, and is stopped ``END_GRACE`` seconds
after the duration it reported, or its limit. Errors name no path and carry no
output of the child.
"""

import json
import logging
import math
import os
import shutil
import stat
import subprocess
import tempfile
import threading
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
# How often the watcher reads the child's reports and exit status.
POLL_SECONDS = 0.05
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
_log = logging.getLogger("scenario")


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
    """One owned playback child and its watcher thread; see the module documentation.

    The watcher thread alone reads the child's reports and exit status, applies
    the deadlines, kills a child that outlives its grace period, sweeps stale
    directories and removes this child's directory once it has exited. The
    owner's methods read and write only memory, except ``stop``, which closes
    the lifeline pipe and signals the child, and ``wait``, which joins the
    watcher and is meant for unregistering.
    """

    def __init__(self, process, root, directory, spec, clock, *, watch=True):
        self._process = process
        self._root = root
        self.directory = directory
        self._spec = spec
        self._clock = clock
        self._lock = threading.Lock()
        self._phase = STARTING
        self._reason = ""
        self._seconds = None
        self._reported = STARTING  # The phase ``poll`` last returned.
        self._deadline = clock() + spec.start_timeout
        self._kill_at = None
        self._swept = False
        self._wake = threading.Event()
        self._released = threading.Event()
        self._thread = None
        if watch:
            self._thread = threading.Thread(
                target=self._watch, name="ScenarioAudioPlayer", daemon=True
            )
            self._thread.start()

    # -- the owner's side: memory only, except stop and wait ----------------

    @property
    def phase(self):
        with self._lock:
            return self._phase

    @property
    def reason(self):
        with self._lock:
            return self._reason

    @property
    def seconds(self):
        with self._lock:
            return self._seconds

    @property
    def active(self):
        """Whether the child is starting or playing, as far as its watcher knows."""
        return self.phase in ACTIVE

    @property
    def released(self):
        """Whether the child has exited and its watcher removed its directory."""
        return self._released.is_set()

    @property
    def exited(self):
        return self._process.poll() is not None

    def poll(self):
        """Whether the phase changed since the last poll; reads memory only."""
        with self._lock:
            changed = self._phase != self._reported
            self._reported = self._phase
        return changed

    def stop(self):
        """Stop playback now: close the lifeline and terminate the child; never blocks."""
        with self._lock:
            if self._phase in ACTIVE:
                # The owner asked for it, so poll does not report it as news.
                self._phase = self._reported = STOPPED
        self._halt()
        self._wake.set()

    def wait(self, timeout=STOP_GRACE):
        """Stop, then wait for the watcher to see the child exit and remove its directory.

        Kills the child if it outlives ``timeout``, and waits ``timeout`` again.
        Returns False when the child is still running or its directory is still
        being removed; the watcher keeps trying, so the caller must keep the player.
        """
        self.stop()
        if self._thread is None:
            # Unwatched players, for tests that drive ``step`` themselves.
            if not self.step():
                self._kill()
                self.step()
            return self.released
        self._thread.join(timeout)
        if self._thread.is_alive():
            self._kill()
            self._wake.set()
            self._thread.join(timeout)
        return self.released

    # -- the watcher's side --------------------------------------------------

    def _watch(self):
        while True:
            try:
                if self.step():
                    return
            except Exception:
                # Never log paths or the child's output; stop it and keep watching.
                _log.warning("Audio playback watcher failed; stopping the child")
                self._finish(FAILED, _UNKNOWN)
            self._wake.wait(POLL_SECONDS)
            self._wake.clear()

    def _finish(self, phase, reason=""):
        with self._lock:
            if self._phase in ACTIVE:
                self._phase, self._reason = phase, reason
        self._halt()

    def _close_input(self):
        stream = self._process.stdin
        if stream is not None:
            try:
                stream.close()
            except OSError:
                pass  # The child already exited and its end of the pipe is gone.

    def _halt(self):
        """Close the lifeline and terminate a running child; the watcher kills it if needed."""
        with self._lock:
            self._close_input()
            if self._process.poll() is None and self._kill_at is None:
                try:
                    self._process.terminate()
                except OSError:
                    pass  # It exited between the poll and the signal.
                self._kill_at = self._clock() + STOP_GRACE

    def _kill(self):
        if self._process.poll() is None:
            try:
                self._process.kill()
            except OSError:
                pass  # It exited between poll() and kill(); nothing is left to stop.

    def _failure(self):
        value = _report(self.directory / "output" / "error.json")
        code = None if value is None else value.get("error")
        return _ERRORS.get(code, _UNKNOWN) if isinstance(code, str) else _UNKNOWN

    def _advance(self, code, now):
        """Apply the child's reports, exit status and deadlines to an active phase."""
        phase = self.phase
        if phase == STARTING:
            report = _report(self.directory / "output" / "playing.json")
            if report is not None:
                seconds = _seconds(report, self._spec.max_seconds)
                limit = self._spec.max_seconds if seconds is None else seconds
                with self._lock:
                    if self._phase == STARTING:
                        self._phase, self._seconds = PLAYING, seconds
                        self._deadline = now + limit + END_GRACE
                return
            if code is not None:
                self._finish(FAILED, self._failure())
            elif now >= self._deadline:
                self._finish(FAILED, "Blender's audio engine did not start in time")
        elif phase == PLAYING:
            if code is not None:
                # A child that crashed while playing reports nothing more useful.
                self._finish(ENDED if code == 0 else FAILED, "" if code == 0 else _UNKNOWN)
            elif now >= self._deadline:
                self._finish(ENDED)

    def step(self):
        """One watch on the watcher thread; True once the child exited and its directory is gone.

        Called by the watcher thread, or directly by a test of an unwatched player.
        """
        if self._released.is_set():
            return True
        if not self._swept:
            # Directories a crash left behind; a running child's are younger.
            sweep(self._root, keep=(self.directory,))
            self._swept = True
        now = self._clock()
        self._advance(self._process.poll(), now)
        with self._lock:
            overdue = self._kill_at is not None and now >= self._kill_at
        if overdue:
            self._kill()
        code = self._process.poll()
        if code is None:
            return False
        # It may have exited after this step read its reports: read them again,
        # from starting to playing to a final phase at most.
        for _ in range(2):
            if self.active:
                self._advance(code, now)
        _remove(self._root, self.directory)
        self._released.set()
        return True


def start(source, root, spec, *, popen=None, clock=None, watch=True):
    """Start one owned child that plays the private copy ``source`` on ``spec.device``.

    ``root`` is the private directory the caller owns for playback children;
    this call creates one ``listen-*`` directory in it. The caller binds
    ``source`` to its bytes, for example with a receipt-checked private copy,
    and polls and stops the returned player, whose watcher thread removes the
    directory. ``watch=False`` leaves the watching to a test that calls ``step``.
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
    return AudioPlayer(process, root, directory, spec, clock, watch=watch)


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
