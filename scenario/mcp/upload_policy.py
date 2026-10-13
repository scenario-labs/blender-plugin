# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Which local files a connected agent may upload. No bpy: the Blender glue supplies the
extension's own folders and the files the user chose; this module resolves and compares.

An agent may upload a file only when the extension produced it in its private user folders,
or when the user chose it in one of the extension's file fields during this Blender session.
Every other path is refused before the file is opened, copied or sent. Paths are compared
after expanding ``~`` and following every link, so a link inside an allowed folder that
points elsewhere is judged by its target.
"""

import os
from collections import OrderedDict
from pathlib import Path

# One message for a missing file and a file outside the allowlist: a separate "not found"
# answer would tell an agent which files exist anywhere on the disk.
REFUSED = (
    "An agent can upload only an existing file that the extension saved in its own "
    "folders, or a file the user chose in Blender during this session. Ask the user to choose "
    "it in Blender, or capture the scene with capture_reference. Nothing was read or sent."
)


class UploadRefused(ValueError):
    """The path is not on the allowlist; raised before the file is read or sent."""

    def __init__(self, message=REFUSED):
        super().__init__(message)


def resolve_file(raw):
    """The existing regular file ``raw`` names after ``~`` and every link, or None."""
    if not isinstance(raw, (str, os.PathLike)):
        return None
    try:
        if not os.fspath(raw):
            return None
        path = Path(raw).expanduser().resolve(strict=True)
        return path if path.is_file() else None
    except (OSError, RuntimeError, ValueError):
        # Missing, unreadable folder, link loop, undeterminable home or an embedded NUL.
        return None


def _resolve_folder(raw):
    try:
        path = Path(raw).expanduser().resolve(strict=True)
        return path if path.is_dir() else None
    except (OSError, RuntimeError, TypeError, ValueError):
        return None


class ChosenFiles:
    """Resolved paths of files the user chose in Blender this session (main thread only).

    The oldest choices are forgotten past ``limit``; forgetting only refuses more.
    """

    def __init__(self, limit=256):
        self._paths = OrderedDict()
        self._limit = limit

    def record(self, raw):
        """Remember the file ``raw`` names; return its resolved path, or None if no file."""
        path = resolve_file(raw)
        if path is None:
            return None
        self._paths.pop(path, None)
        self._paths[path] = None
        while len(self._paths) > self._limit:
            self._paths.popitem(last=False)
        return path

    def __contains__(self, path):
        return path in self._paths

    def __len__(self):
        return len(self._paths)


def allowed_upload(raw, *, roots, chosen):
    """Return the resolved file an agent may upload, or raise UploadRefused.

    ``roots`` are the extension's private folders; a file anywhere inside one is allowed.
    ``chosen`` holds the resolved files the user chose this session. Only metadata is read
    here; the caller opens the returned path, not ``raw``.
    """
    path = resolve_file(raw)
    if path is None:
        raise UploadRefused()
    if path in chosen:
        return path
    for root in roots:
        folder = _resolve_folder(root)
        if folder is not None and path.is_relative_to(folder):
            return path
    raise UploadRefused()
