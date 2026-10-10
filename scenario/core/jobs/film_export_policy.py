# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Film video export suggestions and the agent folder policy, without bpy.

``local_export.validate_destination`` remains the general destination policy;
these helpers only suggest a name and restrict agent-chosen destinations.
"""

import os
from pathlib import Path

from .local_export import _RESERVED_CHARACTERS, LocalExportError, portable_name


def default_name(title, mode):
    """Suggest a portable ``<title> - <Mode> Review.mp4`` name of at most 255 bytes.

    Control and reserved characters become hyphens; a title that cannot stay
    portable falls back to ``Film``. The suggestion is not an approval.
    """
    text = "".join(
        "-" if ord(c) < 32 or ord(c) == 127 or c in _RESERVED_CHARACTERS else c for c in str(title)
    )
    suffix = f" - {str(mode).title()} Review.mp4"
    text = " ".join(text.split()).strip(" .")
    while len((text + suffix).encode("utf-8")) > 255:
        text = text[:-1].rstrip(" .")
    name = (text or "Film") + suffix
    return name if portable_name(name) else "Film" + suffix


def require_within(destination, folder, *, create=None):
    """Accept a destination only when its resolved folder lies inside ``folder``.

    Both sides are resolved, so a link inside ``folder`` cannot send the export
    elsewhere. Unlike private-root refusal, the comparison never folds spellings,
    including on Windows where pathlib would: a resolved folder that differs only
    in case or composition is refused. Windows resolution itself returns an
    existing folder's on-disk spelling. ``create`` names the one folder that may
    be created, with its missing parents, when it is exactly the destination's
    missing folder. This is the agent policy; the session still applies
    ``validate_destination``.
    """
    raw = os.fspath(destination) if isinstance(destination, (str, os.PathLike)) else None
    if not isinstance(raw, str) or not raw or any(ord(c) < 32 or ord(c) == 127 for c in raw):
        raise LocalExportError("Choose a destination path without control characters")
    path, folder = Path(raw), Path(folder)
    if not path.is_absolute() or not folder.is_absolute():
        raise LocalExportError("Choose an absolute destination path inside the Output Folder")
    if (
        create is not None
        and os.path.normpath(path.parent) == os.path.normpath(create)
        and not os.path.lexists(path.parent)
    ):
        try:
            Path(create).mkdir(parents=True, exist_ok=True)
        except OSError:
            raise LocalExportError("Cannot create the Film folder in the Output Folder") from None
    try:
        root, parent = folder.resolve(strict=True), path.parent.resolve(strict=True)
    except (OSError, RuntimeError):
        raise LocalExportError(
            "The destination folder must already exist inside the Output Folder"
        ) from None
    if not inside(parent, root):
        raise LocalExportError("Agents may export videos only inside the Output Folder")
    return path


def inside(path, folder):
    """Whether ``path`` is ``folder`` or below it, comparing each part exactly.

    pathlib equality and ``is_relative_to`` fold case on Windows; this does not.
    """
    root = folder.parts
    return path.parts[: len(root)] == root
