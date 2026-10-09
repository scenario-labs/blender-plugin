# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Main-thread scene snapshots for the owned local render and export workers.

The caller owns scene/credential approval and eventual attachment/upload.
No file save, render, SDK request or job submission is implicit in drawing.
"""

import os
import shutil
import tempfile
import threading
from pathlib import Path

import bpy

from ..core.jobs.local_export import MAX_MEDIA, ExportSpec, LocalExportError, media_stamp
from ..core.jobs.local_render import RenderSpec, blender_path, digest, media_tools
from ..core.jobs.transfers import _root

# Scene strips render another scene's 3D data, clips need tracking data and
# masks need their own datablock; none belong in a saved-media review export.
BLOCKED_STRIPS = frozenset({"SCENE", "MOVIECLIP", "MASK"})


def _write_snapshot(scene, root, prefix):
    """Write only this scene and its dependencies into a new private directory."""
    private = Path(tempfile.mkdtemp(prefix=prefix, dir=root))
    previous = bpy.data.filepath
    try:
        path = private / "snapshot.blend"
        bpy.data.libraries.write(blender_path(path), {scene}, path_remap="ABSOLUTE", compress=True)
        os.chmod(path, 0o600)
        if bpy.data.filepath != previous:
            raise RuntimeError("Snapshot unexpectedly changed the working file")
        return private, digest(path)
    except BaseException:
        shutil.rmtree(private)
        raise


def snapshot(
    scene,
    directory,
    *,
    frame_start,
    frame_end,
    kind="VIDEO",
    width=1280,
    height=720,
    color_type="MATERIAL",
    timeout=1800,
    encode_timeout=300,
):
    """Export only the selected scene/dependencies without changing the working file.

    External resources keep absolute references; inspect the resulting media
    before upload. This freezes the .blend bytes, not arbitrary linked resources.
    """
    if threading.current_thread() is not threading.main_thread():
        raise RuntimeError("Capture scene snapshots on Blender's main thread")
    if scene not in tuple(bpy.data.scenes) or scene.library or scene.override_library:
        raise ValueError("Choose a live local scene")
    if scene.camera is None or scene.camera not in tuple(scene.objects):
        raise ValueError("Capture requires a camera in the selected scene")
    if bpy.context.mode != "OBJECT":
        raise ValueError("Capture snapshots in Object Mode")
    # Validate before creating files, then bind the actual exported bytes below.
    root = _root(directory)
    parameters = {
        "directory": root,
        "binary": Path(bpy.app.binary_path).resolve(),
        "worker": Path(__file__).with_name("render_worker.py").resolve(),
        "scene_name": scene.name,
        "snapshot_sha256": "0" * 64,
        "frame_start": frame_start,
        "frame_end": frame_end,
        "fps": scene.render.fps / scene.render.fps_base,
        "width": width,
        "height": height,
        "kind": kind,
        "color_type": color_type,
        "timeout": timeout,
        "encode_timeout": encode_timeout,
    }
    RenderSpec(**parameters)
    if kind == "VIDEO":
        media_tools()
    private, sha256 = _write_snapshot(scene, root, "capture-")
    try:
        parameters.update(directory=private, snapshot_sha256=sha256)
        return RenderSpec(**parameters)
    except BaseException:
        shutil.rmtree(private)
        raise


def _export_media(scene):
    """Stamp every external file the sequencer reads; packed data is in the snapshot."""
    paths = []
    for strip in scene.sequence_editor.strips_all:
        if strip.type in BLOCKED_STRIPS:
            raise ValueError("Export only movie, sound, image, text and effect strips")
        if strip.type == "MOVIE":
            paths.append(strip.filepath)
        elif strip.type == "SOUND" and strip.sound is not None:
            if strip.sound.packed_file is None:
                paths.append(strip.sound.filepath)
        elif strip.type == "IMAGE":
            paths.extend(os.path.join(strip.directory, item.filename) for item in strip.elements)
        elif strip.type == "TEXT" and strip.font is not None:
            if strip.font.packed_file is None and strip.font.filepath != "<builtin>":
                paths.append(strip.font.filepath)
        if len(paths) > MAX_MEDIA:
            raise LocalExportError("Export at most 2,000 media files")
    stamps = {}
    for raw in paths:
        path = Path(bpy.path.abspath(raw))
        if not path.is_absolute():
            raise LocalExportError("Export media must use absolute or saved-file-relative paths")
        stamps.setdefault(path, media_stamp(path))
    return tuple(stamps.values())


def _muted(editor, strip):
    """Mirror the sequencer: a strip, its channel or any enclosing meta strip mutes it."""
    while strip is not None:
        parent = strip.parent_meta()
        if strip.mute or (parent or editor).channels[strip.channel].mute:
            return True
        strip = parent
    return False


def _audible(scene):
    editor = scene.sequence_editor
    return any(
        strip.type == "SOUND" and strip.sound is not None and not _muted(editor, strip)
        for strip in editor.strips_all
    )


def export_snapshot(
    scene,
    directory,
    *,
    frame_start=None,
    frame_end=None,
    width=None,
    height=None,
    audio=None,
    timeout=None,
    verify_timeout=None,
):
    """Snapshot one local sequencer scene for an offline MP4 export.

    Defaults follow the scene's frame range, output dimensions and audible sound
    strips, honoring strip, channel and enclosing meta strip mutes. External
    media keep absolute references and are stamped so a change before or during
    rendering rejects the export. The working file, selected scene and frame are
    unchanged. The caller owns the returned staging directory.
    """
    if threading.current_thread() is not threading.main_thread():
        raise RuntimeError("Snapshot Film exports on Blender's main thread")
    if scene not in tuple(bpy.data.scenes) or scene.library or scene.override_library:
        raise ValueError("Choose a live local scene")
    if scene.sequence_editor is None or not tuple(scene.sequence_editor.strips_all):
        raise ValueError("Export a scene with sequencer strips")
    if bpy.context.mode != "OBJECT":
        raise ValueError("Export video in Object Mode")
    if not bpy.app.ffmpeg.supported:
        raise LocalExportError("This Blender build cannot encode video")
    render = scene.render
    if render.fps_base != 1 or not 1 <= render.fps <= 120:
        raise ValueError("Export scenes with an integer frame rate from 1 to 120")
    scale = render.resolution_percentage / 100
    parameters = {
        "directory": _root(directory),
        "binary": Path(bpy.app.binary_path).resolve(),
        "worker": Path(__file__).with_name("film_export_worker.py").resolve(),
        "scene_name": scene.name,
        "snapshot_sha256": "0" * 64,
        "frame_start": scene.frame_start if frame_start is None else frame_start,
        "frame_end": scene.frame_end if frame_end is None else frame_end,
        "fps": render.fps,
        "width": round(render.resolution_x * scale) if width is None else width,
        "height": round(render.resolution_y * scale) if height is None else height,
        "audio": _audible(scene) if audio is None else audio,
        "media": _export_media(scene),
        "timeout": timeout,
        "verify_timeout": verify_timeout,
    }
    # Validate before creating files, then bind the actual exported bytes below.
    ExportSpec(**parameters)
    # New inactive scenes need synchronized layer data before library copies
    # on Blender 5.2; this updates only the exported scene's own view layers.
    for layer in scene.view_layers:
        layer.update()
    private, sha256 = _write_snapshot(scene, parameters["directory"], "film-export-")
    try:
        parameters.update(directory=private, snapshot_sha256=sha256)
        return ExportSpec(**parameters)
    except BaseException:
        shutil.rmtree(private)
        raise
