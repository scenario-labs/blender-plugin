# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Video results: remember the file, offer playback."""

import subprocess
import threading
from pathlib import Path

import bpy
from bpy.props import IntProperty, StringProperty

from . import runtime

VIDEO_EXTS = {".mp4", ".mov", ".webm", ".mkv", ".avi", ".m4v"}


def on_video_result(rec):
    if rec.files:
        runtime.set_message(f"Video ready: {rec.files[0].rsplit('/', 1)[-1]}")
    return list(rec.files)


def play_with_os(path):
    bpy.ops.wm.path_open(filepath=path)


def play_with_blender(path):
    subprocess.Popen([bpy.app.binary_path, "-a", path])


def _load_movie(editor, path, channel, frame):
    return editor.strips.new_movie(
        name=path.stem[:60],
        filepath=str(path),
        channel=channel,
        frame_start=frame,
        fit_method="FIT",
    )


def add_to_sequencer(scene, path):
    """Insert picture frames on an unused channel without changing scene settings."""
    if threading.current_thread() is not threading.main_thread():
        raise RuntimeError("Video insertion belongs to Blender's main thread")
    path = Path(bpy.path.abspath(path)).expanduser().resolve()
    if not path.is_file() or path.suffix.lower() not in VIDEO_EXTS:
        raise ValueError("Select an available downloaded video file")
    if scene.library is not None:
        raise ValueError("Select an editable scene for the video strip")
    existing_editor = scene.sequence_editor
    editor = existing_editor or scene.sequence_editor_create()
    before = {strip.as_pointer() for strip in editor.strips}
    try:
        occupied = {strip.channel for strip in editor.strips}
        occupied.update(
            index for index, channel in enumerate(editor.channels) if channel.lock or channel.mute
        )
        channel = next((n for n in range(1, 129) if n not in occupied), None)
        if channel is None:
            raise ValueError("No unused sequencer channel is available; free a channel first")
        strip = _load_movie(editor, path, channel, scene.frame_current)
        if (
            not strip.elements
            or strip.elements[0].orig_width <= 0
            or strip.elements[0].orig_height <= 0
            or strip.frame_duration <= 0
        ):
            raise ValueError("Blender could not decode this video file")
        return strip
    except Exception:
        for strip in list(editor.strips):
            if strip.as_pointer() not in before:
                editor.strips.remove(strip)
        if existing_editor is None and not editor.strips:
            scene.sequence_editor_clear()
        raise


class SCENARIO_OT_video_to_sequencer(bpy.types.Operator):
    bl_idname = "scenario.video_to_sequencer"
    bl_label = "Add video strip"
    bl_description = (
        "Add picture frames at the current frame on an unused sequencer channel; "
        "keep the scene frame rate and omit embedded audio"
    )
    bl_options = {"REGISTER", "UNDO"}

    local_id: StringProperty(options={"HIDDEN"})
    file_index: IntProperty(default=0, min=0, options={"HIDDEN"})

    def execute(self, context):
        manager = runtime.state.manager
        record = manager.registry.by_local_id(self.local_id) if manager is not None else None
        if (
            record is None
            or record.kind != "video"
            or not record.is_success
            or not 0 <= self.file_index < len(record.files)
        ):
            self.report({"ERROR"}, "Select an available downloaded video result")
            return {"CANCELLED"}
        try:
            strip = add_to_sequencer(context.scene, record.files[self.file_index])
        except (OSError, RuntimeError, ValueError) as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        runtime.set_message(f"Video strip added at frame {strip.frame_final_start:g}")
        return {"FINISHED"}


def register():
    bpy.utils.register_class(SCENARIO_OT_video_to_sequencer)


def unregister():
    bpy.utils.unregister_class(SCENARIO_OT_video_to_sequencer)
