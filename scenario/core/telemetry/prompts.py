# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Local record of the panel's invitations to share usage data and send feedback. No bpy.

One small JSON file in the extension's user directory, beside the usage install ID,
records which invitations were answered, how many generations succeeded up to
RATING_AFTER, and until when feedback prompts stay quiet. It is never sent: an answer,
No thanks above all, stays on this computer. A missing, unreadable or malformed file
reads as nothing answered, and an unknown or malformed entry is ignored. Each update
rereads the file and replaces it atomically while it holds the record's lock, so Blender
processes sharing the directory keep each other's answers and counts.
"""

import json
import math
import os
import pathlib
import time
from contextlib import contextmanager

PROMPTS_FILE = "prompts.json"
# The record's lock: a directory, which every platform creates atomically or not at all.
LOCK = ".prompts.lock"
LOCK_WAIT = 1.0  # seconds an update waits for another Blender's
LOCK_STALE = 10.0  # seconds after which a lock was left by a Blender that stopped
ANSWERED = "answered"
# Successful generations before the rating prompt is offered.
RATING_AFTER = 10
# Acting on a feedback prompt keeps every feedback prompt away for this long.
QUIET_PERIOD = 7 * 24 * 3600.0
# Each entry and the values it may hold; anything else in the file is ignored.
_VALID = {
    "usage_card": lambda value: value == ANSWERED,
    "rating_prompt": lambda value: value == ANSWERED,
    "generations": lambda value: type(value) is int and 0 <= value <= RATING_AFTER,
    "quiet_until": lambda value: (
        type(value) in (int, float) and math.isfinite(value) and value >= 0
    ),
}


def read(directory):
    """The valid entries of the saved record, or an empty dict."""
    try:
        text = (pathlib.Path(directory) / PROMPTS_FILE).read_text(encoding="utf-8")
        data = json.loads(text)
    except (OSError, ValueError):  # ValueError covers undecodable bytes and invalid JSON
        return {}
    if not isinstance(data, dict):
        return {}
    return {key: value for key, value in data.items() if key in _VALID and _VALID[key](value)}


def update(directory, **entries):
    """Save `entries` over the saved record and return the record; an OSError raises."""
    for key, value in entries.items():
        if key not in _VALID or not _VALID[key](value):
            raise ValueError(f"Not a prompt record entry: {key}")
    with _locked(directory) as directory:
        return _write(directory, {**read(directory), **entries})


def count_generation(directory):
    """Count one successful generation, up to RATING_AFTER, and return the record."""
    with _locked(directory) as directory:
        saved = read(directory)
        return _write(
            directory, {**saved, "generations": min(RATING_AFTER, saved.get("generations", 0) + 1)}
        )


def _write(directory, saved):
    temporary = directory / f".{PROMPTS_FILE}.{os.getpid()}.tmp"
    temporary.write_text(json.dumps(saved, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(directory / PROMPTS_FILE)
    return saved


@contextmanager
def _locked(directory):
    """Hold the record's lock for one read and write; TimeoutError, an OSError, if busy.

    A lock older than LOCK_STALE was left by a Blender that stopped while holding it, and
    is removed. Holding it lasts one small file write, far less than either delay.
    """
    directory = pathlib.Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    lock = directory / LOCK
    deadline = time.monotonic() + LOCK_WAIT
    while True:
        try:
            lock.mkdir()
            break
        except FileExistsError:
            try:
                stale = time.time() - lock.stat().st_mtime > LOCK_STALE
            except FileNotFoundError:
                continue  # released meanwhile
            if stale:
                _release(lock)
            elif time.monotonic() >= deadline:
                raise TimeoutError("The prompt record is locked by another Blender") from None
            else:
                time.sleep(0.02)
    try:
        yield directory
    finally:
        _release(lock)


def _release(lock):
    try:
        lock.rmdir()
    except OSError:  # already removed: released as stale by another Blender
        pass


def quiet(saved, now):
    """Whether feedback prompts stay away at `now`, after one was acted on."""
    return now < saved.get("quiet_until", 0)


def rating_due(saved):
    """Whether enough generations succeeded and the rating prompt is still unanswered."""
    return saved.get("rating_prompt") != ANSWERED and saved.get("generations", 0) >= RATING_AFTER
