# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Main-thread scene snapshot for the owned local render worker.

The caller owns scene/credential approval and eventual attachment/upload.
No file save, render, SDK request or job submission is implicit in drawing.
"""

import os
import shutil
import tempfile
import threading
from pathlib import Path

import bpy

from ..core.jobs.local_render import RenderSpec, digest, media_tools
from ..core.jobs.transfers import _root


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
    private = Path(tempfile.mkdtemp(prefix="capture-", dir=root))
    previous = bpy.data.filepath
    try:
        path = private / "snapshot.blend"
        bpy.data.libraries.write(str(path), {scene}, path_remap="ABSOLUTE", compress=True)
        os.chmod(path, 0o600)
        if bpy.data.filepath != previous:
            raise RuntimeError("Capture unexpectedly changed the working file")
        parameters.update(directory=private, snapshot_sha256=digest(path))
        return RenderSpec(**parameters)
    except BaseException:
        shutil.rmtree(private)
        raise
