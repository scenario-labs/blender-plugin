# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Selected local audio previews; workers never access Blender or service state."""

import array
import queue
import textwrap
import threading
from dataclasses import dataclass
from pathlib import Path
from time import monotonic

import bpy
from bpy.app.handlers import persistent
from bpy.props import IntProperty, StringProperty

from ..core import audio_waveform
from . import runtime

MAX_READERS = 2
READ_TIMEOUT = 30.0
LOADING_INTERVAL = 0.1
IDLE_INTERVAL = 1.0


@dataclass
class Selection:
    token: object
    manager: object
    record: object
    index: int
    path: str
    scene: object
    window: object
    area: object
    credentials: object
    deadline: float
    status: str = "LOADING"
    message: str = "Loading local waveform..."
    waveform: object = None
    icon_id: int = 0


@dataclass
class Reader:
    thread: threading.Thread
    cancel: threading.Event


def _main_thread():
    if threading.current_thread() is not threading.main_thread():
        raise RuntimeError("Audio preview state belongs to Blender's main thread")


def _read(token, path, cancel, outcomes):
    try:
        waveform = audio_waveform.read_waveform(path, cancel)
        pixels = audio_waveform.raster(waveform)
        if audio_waveform.stamp(Path(path).lstat()) != waveform.source_stamp:
            raise audio_waveform.WaveformError("Audio changed while preparing its preview")
        if cancel.is_set():
            raise audio_waveform.WaveformCanceled("Waveform preview canceled")
        result = (token, waveform, pixels, "")
    except audio_waveform.WaveformError as error:
        result = (token, None, None, str(error))
    except Exception:
        result = (token, None, None, "Could not prepare this local waveform")
    outcomes.put(result)


class PreviewController:
    """Bounded tracked readers plus one replaceable request, never an unbounded backlog.

    A canceled OS read cannot be killed safely, so a spare reader lets a new
    selection proceed. Both live readers remain tracked even after file load.
    """

    def __init__(self):
        self.selection = None
        self._pending = None
        self._readers = []
        self._outcomes = queue.SimpleQueue()
        self._previews = None

    def _release_icon(self):
        if self._previews is not None:
            import bpy.utils.previews

            bpy.utils.previews.remove(self._previews)
            self._previews = None

    def clear(self):
        _main_thread()
        for reader in self._readers:
            reader.cancel.set()
        self._pending = self.selection = None
        self._release_icon()

    def cancel(self):
        _main_thread()
        if self.selection is None or self.selection.status != "LOADING":
            return
        for reader in self._readers:
            reader.cancel.set()
        self._pending = None
        self.selection.status = "CANCELED"
        self.selection.message = "Waveform preview canceled"

    def select(self, context, local_id, index):
        _main_thread()
        manager = runtime.state.manager
        record = manager.registry.by_local_id(local_id) if manager is not None else None
        if (
            record is None
            or record.kind != "audio"
            or not record.is_success
            or type(index) is not int
            or not 0 <= index < len(record.files)
        ):
            raise ValueError("Select an available downloaded audio result")
        self.clear()
        self.selection = Selection(
            object(),
            manager,
            record,
            index,
            record.files[index],
            context.scene,
            context.window,
            context.area,
            runtime.credentials(),
            monotonic() + READ_TIMEOUT,
        )
        self._pending = self.selection
        self.poll()

    def _valid(self, selected):
        try:
            return (
                runtime.state.manager is selected.manager
                and selected.record.kind == "audio"
                and selected.record.is_success
                and runtime.credentials() == selected.credentials
                and selected.manager.registry.by_local_id(selected.record.local_id)
                is selected.record
                and selected.index < len(selected.record.files)
                and selected.record.files[selected.index] == selected.path
                and bpy.data.scenes.get(selected.scene.name) == selected.scene
                and (
                    selected.window is None
                    or selected.window in tuple(bpy.context.window_manager.windows)
                    and selected.window.scene == selected.scene
                    and (
                        selected.area is None
                        or selected.area in tuple(selected.window.screen.areas)
                        and selected.area.type == "VIEW_3D"
                    )
                )
            )
        except (ReferenceError, AttributeError):
            return False

    def poll(self):
        _main_thread()
        self._readers = [reader for reader in self._readers if reader.thread.is_alive()]
        changed = False
        selected = self.selection
        if selected is not None and not self._valid(selected):
            self.clear()
            selected = None
            changed = True
        if (
            selected is not None
            and selected.status == "LOADING"
            and monotonic() >= selected.deadline
        ):
            saturated = self._pending is not None and len(self._readers) >= MAX_READERS
            self.cancel()
            selected.status = "ERROR"
            selected.message = (
                "Audio readers are still occupied; retry when they finish or restart Blender"
                if saturated
                else "Waveform preview timed out; try another file"
            )
            changed = True
        while True:
            try:
                token, waveform, pixels, error = self._outcomes.get_nowait()
            except queue.Empty:
                break
            if selected is None or token is not selected.token or selected.status != "LOADING":
                continue
            changed = True
            if waveform is not None:
                try:
                    import bpy.utils.previews

                    self._previews = bpy.utils.previews.new()
                    preview = self._previews.new("waveform")
                    preview.image_size = (256, 96)
                    preview.image_pixels_float = array.array("f", (v / 255 for v in pixels))
                    selected.icon_id, selected.waveform = preview.icon_id, waveform
                    selected.status = "READY"
                    selected.message = f"{waveform.seconds:.2f} s · {'Mono' if waveform.channels == 1 else 'Stereo'} · Snapshot"
                except (OSError, ValueError, RuntimeError):
                    self._release_icon()
                    error = "The captured preview could not be displayed"
            if error:
                selected.status, selected.message = "ERROR", error
        if self._pending is not None and len(self._readers) < MAX_READERS:
            selected, self._pending = self._pending, None
            cancel = threading.Event()
            thread = threading.Thread(
                target=_read,
                args=(selected.token, selected.path, cancel, self._outcomes),
                name="scenario-audio-preview",
                daemon=True,
            )
            try:
                thread.start()
            except (OSError, RuntimeError):
                selected.status = "ERROR"
                selected.message = "Could not start the waveform reader; try again"
                changed = True
            else:
                self._readers.append(Reader(thread, cancel))
        return changed


controller = PreviewController()


def _redraw():
    from .pump import redraw

    redraw()


def _tick():
    if controller.poll():
        _redraw()
    selected = controller.selection
    if selected is None:
        return None
    # Completed previews still need to retire when credentials, scene or window
    # change. Keep that guard without a permanent 10 Hz loading timer.
    return LOADING_INTERVAL if selected.status == "LOADING" else IDLE_INTERVAL


@persistent
def _file_load(_):
    controller.clear()


class SCENARIO_OT_preview_audio(bpy.types.Operator):
    bl_idname = "scenario.preview_audio"
    bl_label = "Preview waveform"
    bl_description = "Preview this downloaded PCM WAV locally without playback or a service request"

    local_id: StringProperty()
    file_index: IntProperty(default=0, min=0)

    def execute(self, context):
        try:
            controller.select(context, self.local_id, self.file_index)
        except ValueError as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        if not bpy.app.background:
            # A terminal preview may have left a one-second timer pending.
            # Restart it so this selection immediately gets the loading cadence.
            if bpy.app.timers.is_registered(_tick):
                bpy.app.timers.unregister(_tick)
            bpy.app.timers.register(_tick, first_interval=LOADING_INTERVAL)
        _redraw()
        return {"FINISHED"}


class SCENARIO_OT_cancel_audio_preview(bpy.types.Operator):
    bl_idname = "scenario.cancel_audio_preview"
    bl_label = "Cancel preview"
    bl_description = (
        "Cancel the local waveform preview and leave playback and result files unchanged"
    )

    @classmethod
    def poll(cls, context):
        return controller.selection is not None and controller.selection.status == "LOADING"

    def execute(self, context):
        controller.cancel()
        _redraw()
        return {"FINISHED"}


def draw(layout, record, index):
    """Only cached state is read here; admission, decoding and icons are outside draw."""
    selected = controller.selection
    if selected is None or selected.record is not record or selected.index != index:
        return
    context = bpy.context
    if selected.scene != context.scene or selected.window != context.window:
        return
    box = layout.box()
    box.label(text=Path(selected.path).name, icon="SOUND")
    scale = context.preferences.view.ui_scale * context.preferences.system.pixel_size
    width = context.region.width if context.region is not None else 300
    columns = max(12, int((width / scale - 80) / 7))
    for line in textwrap.wrap(selected.message, width=columns):
        box.label(text=line, icon="ERROR" if selected.status == "ERROR" else "INFO")
    if selected.status == "LOADING":
        box.operator("scenario.cancel_audio_preview", text="Cancel", icon="CANCEL")
    elif selected.status == "READY":
        box.template_icon(
            icon_value=selected.icon_id, scale=max(3.0, min(8.0, (width / scale - 80) / 20))
        )


CLASSES = (SCENARIO_OT_preview_audio, SCENARIO_OT_cancel_audio_preview)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.app.handlers.load_pre.append(_file_load)


def unregister():
    controller.clear()
    if bpy.app.timers.is_registered(_tick):
        bpy.app.timers.unregister(_tick)
    if _file_load in bpy.app.handlers.load_pre:
        bpy.app.handlers.load_pre.remove(_file_load)
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
