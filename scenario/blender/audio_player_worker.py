# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Standalone owned Blender process that plays one audio file through Blender's audio engine.

``core.jobs.audio_player`` starts it with ``--offline-mode``,
``--factory-startup``, ``--disable-autoexec``, ``--background`` and
``-noaudio``, so Blender opens no output of its own. It does not import or
register the extension. Blender's audio module opens the file named in the
request and decodes its first quarter second to confirm it holds audio; the
duration it declares must be within the request's limit. Only then does it
open the output device the request names, the one chosen in the user's
Preferences, and play the file from its start, at most that limit long.

``playing.json`` appears once the sound plays, and a failure is reported as a
fixed code in ``error.json``; the parent never reads this process's output.
The process ends when the sound ends, when its standard input reaches its end
or when the parent terminates it. The parent never writes to standard input:
its end means that the parent closed it to stop playback, or exited or crashed.
"""

import json
import math
import os
import sys
import threading
from pathlib import Path

FORMAT = 1
MAX_REQUEST_BYTES = 4096
MAX_RATE = 192_000
MAX_CHANNELS = 8
# Seconds decoded before playing, to fail on a file that names audio but holds none.
HEAD_SECONDS = 0.25
POLL_SECONDS = 0.05
DEVICE_NAME_LENGTH = 64


class PlayFailure(Exception):
    """A reportable failure; ``code`` belongs to the parent's fixed vocabulary."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


def _request(path):
    if path.stat().st_size > MAX_REQUEST_BYTES:
        raise ValueError("Playback request is too large")
    value = json.loads(path.read_text(encoding="utf-8"))
    names = {"format", "source", "output", "device", "max_seconds"}
    if not isinstance(value, dict) or set(value) != names or value["format"] != FORMAT:
        raise ValueError("Use an owned playback request")
    source, output = Path(value["source"]), Path(value["output"])
    if not source.is_absolute() or not output.is_absolute():
        raise ValueError("Use absolute playback paths")
    if output.is_symlink() or not output.is_dir() or any(output.iterdir()):
        raise ValueError("The owned playback output directory must be empty")
    device = value["device"]
    if (
        not isinstance(device, str)
        or not 0 < len(device) <= DEVICE_NAME_LENGTH
        or not device.isprintable()
    ):
        raise ValueError("Name one audio output device")
    limit = value["max_seconds"]
    if type(limit) is not int or limit < 1:
        raise ValueError("Use a positive playback limit")
    return source, output, device, limit


def _write(output, name, value):
    """Publish one small report; a reader sees it whole or not at all."""
    partial = output / (name + ".partial")
    with partial.open("x", encoding="utf-8") as stream:
        json.dump(value, stream)
    os.replace(partial, output / name)


def lifeline(stop, descriptor=0):
    """Set ``stop`` once ``descriptor`` reaches its end; the parent never writes to it.

    A raw read holds no lock of ``sys.stdin``, which interpreter shutdown would
    otherwise wait for while this daemon thread still reads.
    """

    def watch():
        try:
            while os.read(descriptor, 4096):
                pass
        except OSError:
            pass  # A closed or invalid standard input also means stop.
        stop.set()

    threading.Thread(target=watch, name="ScenarioPlaybackLifeline", daemon=True).start()


def prepare(source, max_seconds, aud):
    """The sound to play, limited to ``max_seconds``, and its declared duration or None."""
    try:
        sound = aud.Sound(str(source))
        rate, channels = sound.specs
        length = sound.length
    except aud.error:
        raise PlayFailure("unreadable") from None
    if (
        not math.isfinite(rate)
        or rate != int(rate)
        or not 1 <= int(rate) <= MAX_RATE
        or not 1 <= channels <= MAX_CHANNELS
    ):
        raise PlayFailure("unsupported")
    rate = int(rate)
    if length > max_seconds * rate:
        raise PlayFailure("too_long")
    try:
        head = sound.limit(0, HEAD_SECONDS).data()
    except aud.error:
        raise PlayFailure("unreadable") from None
    if head.ndim != 2 or head.shape[1] != channels:
        raise PlayFailure("unsupported")
    if not head.shape[0]:
        raise PlayFailure("empty")
    # Containers without a declared length still stop at the limit.
    seconds = length / rate if length > 0 else None
    return sound.limit(0, max_seconds), seconds


def play(sound, device_name, stop, aud, started):
    """Play ``sound`` on the named output until it ends or ``stop`` is set."""
    if stop.is_set():
        return
    try:
        device = aud.Device(device_name)
        handle = device.play(sound)
    except aud.error:
        raise PlayFailure("device") from None
    if handle.status != aud.STATUS_PLAYING:
        # Blender's None output accepts the sound but never plays it.
        raise PlayFailure("device")
    try:
        started()
        while handle.status == aud.STATUS_PLAYING and not stop.wait(POLL_SECONDS):
            pass
    finally:
        handle.stop()


def main():
    import aud

    arguments = sys.argv[sys.argv.index("--") + 1 :]
    if len(arguments) != 1:
        raise ValueError("Provide the owned playback request")
    source, output, device, max_seconds = _request(Path(arguments[0]))
    stop = threading.Event()
    lifeline(stop)
    try:
        sound, seconds = prepare(source, max_seconds, aud)
        play(
            sound,
            device,
            stop,
            aud,
            lambda: _write(output, "playing.json", {"format": FORMAT, "seconds": seconds}),
        )
    except PlayFailure as failure:
        _write(output, "error.json", {"format": FORMAT, "error": failure.code})
        raise


if __name__ == "__main__":
    main()
