# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Local record of the panel's invitations to share usage data. No bpy.

One small JSON file in the extension's user directory, beside the usage install ID,
records that an invitation was answered. It is never sent: an answer, No thanks above
all, stays on this computer. A missing, unreadable or malformed file reads as nothing
answered, and an unknown or malformed entry is ignored. Each update rereads the file and
replaces it atomically, so Blender processes sharing the directory keep each other's
answers.
"""

import json
import os
import pathlib

PROMPTS_FILE = "prompts.json"
ANSWERED = "answered"
# Each entry and the values it may hold; anything else in the file is ignored.
_VALID = {"usage_card": lambda value: value == ANSWERED}


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
    directory = pathlib.Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    saved = {**read(directory), **entries}
    temporary = directory / f".{PROMPTS_FILE}.{os.getpid()}.tmp"
    temporary.write_text(json.dumps(saved, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(directory / PROMPTS_FILE)
    return saved
