# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Insert one receipt-bound media snapshot into an explicitly selected scene."""

import hashlib
import os
import shutil
import stat
import tempfile
import threading
from dataclasses import dataclass, field
from pathlib import Path

import bpy

MAX_MEDIA_BYTES = 512 * 1024 * 1024
MEDIA_TYPES = {
    "video/mp4": ("video", ".mp4"),
    "video/webm": ("video", ".webm"),
    "audio/mpeg": ("audio", ".mp3"),
    "audio/wav": ("audio", ".wav"),
    "audio/x-wav": ("audio", ".wav"),
    "audio/ogg": ("audio", ".ogg"),
}


class MediaApplicationError(RuntimeError):
    """No media mutation remains after a failed application."""


@dataclass(frozen=True)
class MediaApplication:
    strip: object = field(repr=False)
    path: Path = field(repr=False)
    kind: str
    frame: int


def _container_matches(data, suffix):
    if suffix == ".mp4":
        return len(data) >= 12 and data[4:8] == b"ftyp"
    if suffix == ".webm":
        return data.startswith(b"\x1a\x45\xdf\xa3")
    if suffix == ".wav":
        return data[:4] == b"RIFF" and data[8:12] == b"WAVE"
    if suffix == ".ogg":
        return data.startswith(b"OggS")
    return data.startswith(b"ID3") or (
        len(data) >= 2 and data[0] == 0xFF and data[1] & 0xE6 == 0xE2
    )


def _snapshot(item, path, directory, suffix):
    receipt, path = item.receipt, Path(path)
    if (
        receipt is None
        or path.name != receipt.name
        or not 0 < receipt.size <= MAX_MEDIA_BYTES
        or path.is_symlink()
    ):
        raise MediaApplicationError("Use a supported saved media receipt")
    snapshot = directory / ("media" + suffix)
    flags = (
        os.O_RDONLY
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
        | getattr(os, "O_BINARY", 0)
    )
    digest, size = hashlib.sha256(), 0
    with os.fdopen(os.open(path, flags), "rb") as source, snapshot.open("xb") as target:
        if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
            raise MediaApplicationError("The saved media is not a regular file")
        while chunk := source.read(min(1024 * 1024, receipt.size - size + 1)):
            if size == 0 and not _container_matches(chunk, suffix):
                raise MediaApplicationError("Media contents do not match the saved type")
            size += len(chunk)
            if size > receipt.size:
                raise MediaApplicationError("The saved media changed")
            digest.update(chunk)
            target.write(chunk)
        target.flush()
        os.fsync(target.fileno())
    if size != receipt.size or digest.hexdigest() != receipt.sha256:
        raise MediaApplicationError("The saved media no longer matches its receipt")
    return snapshot


def _insert(editor, path, kind, frame):
    occupied = {strip.channel for strip in editor.strips}
    occupied.update(
        index for index, channel in enumerate(editor.channels) if channel.lock or channel.mute
    )
    channel = next((value for value in range(1, 129) if value not in occupied), None)
    if channel is None:
        raise MediaApplicationError("No unused sequencer channel is available")
    options = dict(
        name="Scenario " + kind.title(), filepath=str(path), channel=channel, frame_start=frame
    )
    if kind == "video":
        strip = editor.strips.new_movie(**options, fit_method="FIT")
        if (
            not strip.elements
            or strip.elements[0].orig_width <= 0
            or strip.elements[0].orig_height <= 0
        ):
            raise MediaApplicationError("Blender could not decode the video")
    else:
        strip = editor.strips.new_sound(**options)
        if strip.sound is None:
            raise MediaApplicationError("Blender could not decode the sound")
    if strip.frame_duration <= 0:
        raise MediaApplicationError("Blender could not decode the media duration")
    return strip


def apply_media(scene, item, path, *, frame):
    """Keep an independent verified file for the strip; never change timing settings."""
    if threading.current_thread() is not threading.main_thread():
        raise MediaApplicationError("Apply media on Blender's main thread")
    if scene not in tuple(bpy.data.scenes) or scene.library is not None or type(frame) is not int:
        raise MediaApplicationError("Choose an editable scene and explicit frame")
    kind_suffix = MEDIA_TYPES.get(item.asset.media_type)
    if kind_suffix is None:
        raise MediaApplicationError("Choose a supported saved video or sound asset")
    kind, suffix = kind_suffix
    package = __package__.rsplit(".", 1)[0]
    root = bpy.utils.extension_path_user(package, path="media-import", create=True)
    directory = Path(tempfile.mkdtemp(prefix="result-", dir=root))
    previous_editor = scene.sequence_editor
    editor = previous_editor
    before = {strip.as_pointer() for strip in editor.strips} if editor else set()
    sounds = set(bpy.data.sounds)
    try:
        snapshot = _snapshot(item, path, directory, suffix)
        editor = editor or scene.sequence_editor_create()
        strip = _insert(editor, snapshot, kind, frame)
        strip["scenario_asset"] = item.asset.asset_id
        return MediaApplication(strip, snapshot, kind, frame)
    except Exception:
        # Rollback failures deliberately escape as uncertainty: do not delete a
        # snapshot that might still be referenced by a partially inserted strip.
        if editor is not None:
            for strip in list(editor.strips):
                if strip.as_pointer() not in before:
                    editor.strips.remove(strip)
            if previous_editor is None and not editor.strips:
                scene.sequence_editor_clear()
        for sound in set(bpy.data.sounds) - sounds:
            if sound.users:
                raise RuntimeError("Media rollback needs inspection") from None
            bpy.data.sounds.remove(sound)
        shutil.rmtree(directory)
        raise MediaApplicationError(
            "Could not insert verified media; saved downloads are preserved"
        ) from None
