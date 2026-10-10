# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Private verified copies of saved video and audio results for desktop players, without bpy.

A desktop player opens a file by its name and extension, so it never receives
the saved result's own path, whose name came from a download. On the preview
lane, one downloaded receipt is streamed into a new private ``play-*``
directory and rehashed against the receipt while copying. The copy's container
signature must match its saved MIME type, and it is named ``media`` plus that
type's canonical suffix, read-only. Copies are disposable: their Blender owner
discards them, and an age sweep on the lane removes any left behind, for
example by a crash or by a player that still held one open on Windows.
"""

import os
import shutil
import stat
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

from .local_render import RenderCancelled
from .media_probe import FORMATS, MAX_BYTES, MediaProbeError, _snapshot
from .result_previews import _AUDIO_CHECKS, PreviewKey, PreviewTarget, _iso_media, _matroska
from .transfers import TransferError, _root
from .upload_sources import _stamp

PREFIX = "play-"
STALE_SECONDS = 24 * 60 * 60
# One allowlist with Film media inspection: saved MIME type -> (kind, suffix).
PLAYBACK_TYPES = {media_type: (kind, suffix) for media_type, (kind, suffix, _) in FORMATS.items()}
# Variables a player never needs: credentials, Python start-up and proxies.
_PROXIES = frozenset({"HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY"})


def _avi(head):
    return head[:4] == b"RIFF" and head[8:12] == b"AVI "


_CHECKS = {
    ".mp4": _iso_media,
    ".mov": _iso_media,
    ".webm": _matroska,
    ".mkv": _matroska,
    ".avi": _avi,
    **_AUDIO_CHECKS,
}


class PlaybackError(RuntimeError):
    """Sanitized playback copy failure; never a reason to download or generate again."""


class PlaybackCanceled(PlaybackError):
    """The lane task was canceled; any partial copy was removed."""


def kind(media_type):
    """``video`` or ``audio`` for a playable saved MIME type, else None."""
    value = PLAYBACK_TYPES.get(media_type) if isinstance(media_type, str) else None
    return None if value is None else value[0]


@dataclass(frozen=True, eq=False)
class PlaybackCopy:
    """One private read-only copy, bound to the exact saved receipt by ``key``."""

    key: PreviewKey
    request_id: str
    asset_id: str
    media_type: str
    kind: str
    size: int
    path: Path = field(repr=False)
    directory: Path = field(repr=False)
    stamp: tuple = field(repr=False)


def playback_root(root):
    """The canonical private root for copies, created when its parent exists."""
    path = Path(root)
    if path.is_absolute():
        try:
            path.mkdir(mode=0o700)
        except FileExistsError:
            pass  # The usual case: the root survives between copies.
        except OSError:
            raise PlaybackError("Playback storage is unavailable") from None
    try:
        return _root(path)
    except TransferError:
        raise PlaybackError("Playback storage is unavailable") from None


def _head(path):
    flags = (
        os.O_RDONLY
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
        | getattr(os, "O_BINARY", 0)
    )
    descriptor = os.open(path, flags)
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise PlaybackError("Playback copies must be regular local files")
        return os.read(descriptor, 16)
    finally:
        os.close(descriptor)


def make_copy(root, target, source, cancel):
    """Copy one downloaded receipt for a player; the copy is removed on any failure."""
    if not isinstance(target, PreviewTarget) or kind(target.media_type) is None:
        raise PlaybackError("Choose one saved video or audio result")
    if not 0 < target.receipt.size <= MAX_BYTES:
        raise PlaybackError("The saved result is too large to play")
    media_kind, suffix = PLAYBACK_TYPES[target.media_type]
    root = playback_root(root)
    try:
        # Only the name comes from mkdtemp, which normalizes the path it returns
        # on Python 3.12 and later; keep the canonical root's spelling.
        directory = root / Path(tempfile.mkdtemp(prefix=PREFIX, dir=root)).name
    except OSError:
        raise PlaybackError("Playback storage is unavailable") from None
    try:
        path = directory / ("media" + suffix)
        _snapshot(Path(source), target.receipt, path, cancel)
        if not _CHECKS[suffix](_head(path)):
            raise PlaybackError("The saved result contents do not match its type")
        os.chmod(path, 0o400)
        info = os.lstat(path)
        return PlaybackCopy(
            target.key,
            target.request_id,
            target.asset_id,
            target.media_type,
            media_kind,
            target.receipt.size,
            path,
            directory,
            _stamp(info),
        )
    except RenderCancelled:
        discard(root, directory)
        raise PlaybackCanceled("Playback preparation was canceled") from None
    except PlaybackError:
        discard(root, directory)
        raise
    except (OSError, ValueError, MediaProbeError, TransferError):
        discard(root, directory)
        raise PlaybackError("The saved result no longer matches its receipt") from None
    except BaseException:
        discard(root, directory)
        raise


def unchanged(copy):
    """Whether a copy is still the regular file this lane wrote; metadata only."""
    if not isinstance(copy, PlaybackCopy):
        return False
    try:
        info = os.lstat(copy.path)
    except OSError:
        return False
    return stat.S_ISREG(info.st_mode) and _stamp(info) == copy.stamp


def _unlink(path):
    try:
        os.unlink(path)
    except PermissionError:
        # Windows refuses to delete a read-only file; clear the flag first.
        os.chmod(path, stat.S_IREAD | stat.S_IWRITE)
        os.unlink(path)


def discard(root, directory):
    """Remove one ``play-*`` directory directly below ``root``; leave anything else.

    Errors are ignored: Windows refuses to delete a file a player holds open,
    and the age sweep removes it later.
    """
    directory = Path(directory)
    try:
        # Copies use the canonical root's spelling: on Windows, the \\?\ namespace.
        root = _root(Path(root))
    except TransferError:
        return
    if not directory.name.startswith(PREFIX) or directory.parent != root:
        return
    try:
        if not stat.S_ISDIR(directory.lstat().st_mode):
            return
        for child in tuple(directory.iterdir()):
            if stat.S_ISDIR(child.lstat().st_mode):
                shutil.rmtree(child, ignore_errors=True)
            else:
                _unlink(child)
        directory.rmdir()
    except OSError:
        pass


def sweep(root, *, keep=(), now=None, older_than=STALE_SECONDS):
    """Remove stale ``play-*`` directories that no live copy or player still uses."""
    now = time.time() if now is None else now
    kept = {Path(path).name for path in keep}
    try:
        children = tuple(_root(Path(root)).iterdir())
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
            discard(root, child)


def player_environment(environ=None):
    """The launching environment without credentials, Python start-up or proxies.

    Blender variables stay, so an animation player uses the same Blender
    configuration as the session that launched it.
    """
    environ = os.environ if environ is None else environ
    return {
        key: value
        for key, value in environ.items()
        if not key.upper().startswith(("SCENARIO_", "PYTHON")) and key.upper() not in _PROXIES
    }
