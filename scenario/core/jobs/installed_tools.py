# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Find optional installed media tools, ffmpeg and ffprobe, without bpy.

Blender opened from the macOS Dock or Finder gets launchd's PATH
(``/usr/bin:/bin:/usr/sbin:/sbin``), not the shell's, so Homebrew and MacPorts
tools are not on it. Lookup checks the current PATH first, then a fixed list of
well-known absolute install folders for the platform; Windows uses PATH only.
It never changes the environment, downloads or runs anything, and never
searches the working directory or a relative PATH entry. Every caller uses this
one lookup, so a dialog and the work it describes agree on which tool runs.
"""

import os
import shutil
import sys
from pathlib import Path

FFMPEG, FFPROBE = "ffmpeg", "ffprobe"

# Checked after PATH, in order. Only fixed absolute folders belong here.
DIRECTORIES = {
    # Homebrew on Apple silicon; Homebrew on Intel and manual installs; MacPorts.
    "darwin": ("/opt/homebrew/bin", "/usr/local/bin", "/opt/local/bin"),
    # Not /snap/bin: a strictly confined snap cannot read the hidden extension
    # storage or the host temporary folder that inspection and capture use.
    "linux": ("/usr/local/bin", "/usr/bin"),
}


def _platform():
    return "linux" if sys.platform.startswith("linux") else sys.platform


def _on_path(name):
    path = os.environ.get("PATH")
    if path is not None:
        # An empty or relative entry names the working directory; skip it.
        path = os.pathsep.join(entry for entry in path.split(os.pathsep) if os.path.isabs(entry))
    found = shutil.which(name, path=path)
    # Windows can search the working directory first; never use that result.
    return found if found and os.path.isabs(found) else None


def find(name):
    """Resolved absolute path of an installed tool, or None when it is absent."""
    if not name or os.path.basename(name) != name or name in (os.curdir, os.pardir):
        raise ValueError("Look up a bare tool name")
    found = _on_path(name)
    if found:
        return Path(found).resolve()
    for directory in DIRECTORIES.get(_platform(), ()):
        candidate = Path(directory, name)
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate.resolve()
    return None


def missing(names, purpose):
    """Readable text naming absent tools, where lookup searched and, on macOS, why."""
    directories = DIRECTORIES.get(_platform(), ())
    where = "on PATH"
    if directories:
        listed = ", ".join(directories[:-1])
        where += f" or in {listed} or {directories[-1]}" if listed else f" or in {directories[0]}"
    text = f"Install {' and '.join(names)} {purpose}: not found {where}."
    if _platform() == "darwin":
        text += " Apps opened from the Dock or Finder do not inherit the shell PATH."
    return text
