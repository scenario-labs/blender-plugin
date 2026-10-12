# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Play and waveform controls for saved shared video and audio results.

The shared saved-job descriptors draw these controls. They never submit,
download, spend, apply or change the scene or the job store. **Play** opens a
private verified copy (``core.jobs.playback``) in the system player, and **Play
in Blender** opens one in Blender's animation player, a separate process. Both
start without Scenario credentials, Python start-up or proxy variables in their
environment, never through ``wm.path_open``. **Waveform** asks the session's preview
scheduler for the saved audio's envelope, which an owned offline Blender
process decodes on the preview lane, then draws it from cached state.

Copies are made on the preview lane; this module keeps their handles on
Blender's main thread, reuses an unchanged copy, keeps a bounded number and
removes them when the connection retires, a file loads or the extension
unregisters. No local MCP tool launches a player.
"""

import array
import logging
import subprocess
import threading
from collections import OrderedDict
from concurrent.futures import CancelledError
from dataclasses import dataclass, field
from pathlib import Path

import bpy
from bpy.app.handlers import persistent
from bpy.props import EnumProperty, IntProperty, StringProperty

from ..core import audio_waveform
from ..core.jobs import playback
from ..core.jobs.local_render import LocalRenderError, blender_path
from ..core.jobs.result_previews import (
    ENVELOPE,
    PreviewCanceled,
    PreviewError,
    PreviewKey,
    PreviewState,
)
from ..core.jobs.results import PREVIEW_STATES, ResultError
from ..core.jobs.workers import WorkerError
from ..core.ui.text_wrap import NO_BREAK
from . import label_wrap, runtime

_log = logging.getLogger("scenario")
# At most this many copies and bytes stay for reuse; player-pinned ones stay too.
COPY_LIMIT = 4
COPY_BYTES = 1024**3
PLAYER_LIMIT = 2
LOADING_INTERVAL = 0.1
IDLE_INTERVAL = 1.0
WAVEFORM_SIZE = (256, 96)
# Interface units of the sidebar that the waveform box's status text cannot use:
# from the region's left edge to the first line's text (panel, job box, this box
# and the icon) and from this box's right content edge past the category tabs,
# measured as 100 on Blender 5.1.2, plus a few units of slack. Labels clip text
# wider than their row.
TEXT_INSET = 106
_WAITING = {
    PreviewState.QUEUED: "Waiting for the preview lane...",
    PreviewState.DECODE: "Decoding the verified saved audio in an offline Blender process...",
}
_FAILED = frozenset({PreviewState.FAILED, PreviewState.MISSING, PreviewState.UNSUPPORTED})
_UNAVAILABLE = "The connection changed; inspect saved jobs again"


class MediaError(ValueError):
    """A sanitized refusal before any copy, decode or player starts."""


def _main_thread():
    if threading.current_thread() is not threading.main_thread():
        raise RuntimeError("Saved media controls belong to Blender's main thread")


def _blender_binary():
    """This Blender's executable for the animation player, or None without one."""
    binary = bpy.app.binary_path
    if not binary:
        return None
    try:
        path = Path(binary).resolve()
        return path if path.is_file() else None
    except (OSError, ValueError):
        return None


def _system_open(path):
    """The operating system's default application on a private copy, without credentials."""
    return playback.system_open(path)


def _launch(binary, copy):
    """Blender's animation player on a private copy, without credentials or Python start-up."""
    return subprocess.Popen(
        [blender_path(binary), "-a", blender_path(copy.path)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=blender_path(copy.directory),
        env=playback.player_environment(),
    )


def _root():
    return runtime.paths().cache_dir / "media-playback"


def _discard(copy):
    # Copies live directly below the canonical root they were made in.
    playback.discard(copy.directory.parent, copy.directory)


def _channels(count):
    return "Mono" if count == 1 else "Stereo" if count == 2 else f"{count}{NO_BREAK}channels"


def _duration(seconds):
    if seconds < 10:
        return f"{seconds:.2f}{NO_BREAK}s"
    if seconds < 60:
        return f"{seconds:.1f}{NO_BREAK}s"
    whole = round(seconds)
    return f"{whole // 60}:{whole % 60:02d}"


def summary(envelope):
    """One status line for a decoded envelope, from cached values only.

    No-break spaces keep each value with its unit, and each separator with the
    part before it, so a wrapped line never starts with a unit or a separator.
    """
    parts = [
        "Verified saved audio",
        _duration(envelope.seconds),
        _channels(envelope.channels),
        f"{envelope.sample_rate / 1000:g}{NO_BREAK}kHz",
    ]
    if envelope.silent:
        parts.append("Silent")
    return f"{NO_BREAK}· ".join(parts)


def _admit(context_id, request_id, expected_revision, asset_id, kinds):
    """The current session, store, saved result and its 1-based position, or MediaError."""
    state = runtime.state
    session, store = state.job_session, state.job_store
    if (
        not context_id
        or context_id != state.job_context_id
        or session is None
        or not session.active
        or store is None
    ):
        raise MediaError(_UNAVAILABLE)
    try:
        record = store.get(request_id)
    except Exception:
        raise MediaError("Could not read the saved job; inspect saved jobs again") from None
    if (
        record is None
        or type(expected_revision) is not int
        or record.revision != expected_revision
        or record.state not in PREVIEW_STATES
    ):
        raise MediaError("The saved job changed; inspect saved jobs again")
    for index, item in enumerate(record.results, 1):
        if item.asset.asset_id == asset_id:
            if item.receipt is not None and playback.kind(item.asset.media_type) in kinds:
                return session, store, item, index
            break
    if kinds == ("video",):
        raise MediaError("Choose a downloaded saved video result")
    if kinds == ("audio",):
        raise MediaError("Choose a downloaded saved audio result")
    raise MediaError("Choose a downloaded saved video or audio result")


def _reason(error):
    if isinstance(error, (playback.PlaybackError, ResultError)):
        return str(error)
    return "Could not prepare a private copy; inspect saved jobs and try again"


@dataclass(eq=False)
class PlayRequest:
    context_id: str
    session: object
    key: PreviewKey
    task: object
    player: str
    label: str
    binary: Path | None = None
    reuse: object = None


@dataclass(eq=False)
class Waveform:
    context_id: str
    session: object
    request_id: str
    asset_id: str
    label: str
    status: str = "LOADING"
    message: str = "Waiting for the preview lane..."
    envelope: object = field(default=None, repr=False)
    icon_id: int = 0


class MediaController:
    """Main-thread playback and waveform state; never reads files while drawing.

    Only the latest Play request is honored. The waveform selection follows the
    preview scheduler's status for one saved audio result. Every result checks
    the context it was requested in, so a late copy or envelope is never shown
    or opened after a credential, project or file change.
    """

    def __init__(self):
        self.selection = None
        self._play = None
        self._copies = OrderedDict()  # PreviewKey -> PlaybackCopy, oldest first
        self._players = []  # (process, PlaybackCopy) for Blender animation players
        self._openers = []  # (process, PlaybackCopy) for system player launchers
        self._abandoned = []  # lane tasks whose copies must be removed once done
        self._context = None
        self._previews = None

    # -- state ------------------------------------------------------------

    @property
    def loading(self):
        return (
            self._play is not None
            or bool(self._abandoned)
            or (self.selection is not None and self.selection.status == "LOADING")
        )

    def interval(self):
        if self.loading:
            return LOADING_INTERVAL
        if self.selection is not None or self._players or self._openers:
            return IDLE_INTERVAL
        return None

    def _pinned(self, copy):
        return any(pinned is copy for _, pinned in (*self._players, *self._openers))

    def _cached(self, copy):
        return any(cached is copy for cached in self._copies.values())

    def _release_icon(self):
        if self._previews is not None:
            import bpy.utils.previews

            try:
                bpy.utils.previews.remove(self._previews)
            except (KeyError, RuntimeError):
                pass  # Already released with the extension's preview collections.
            self._previews = None

    def _bind(self, context_id):
        if self._context is not None and self._context != context_id:
            self.retire()
        self._context = context_id

    def _current(self, context_id, session):
        return (
            context_id == runtime.state.job_context_id
            and session is runtime.state.job_session
            and session.active
        )

    # -- play -------------------------------------------------------------

    def _trim(self):
        """Remove the oldest unpinned copies while the cache exceeds its budgets."""
        total = sum(copy.size for copy in self._copies.values())
        for key, copy in tuple(self._copies.items()):
            if len(self._copies) <= COPY_LIMIT and total <= COPY_BYTES:
                break
            if self._pinned(copy):
                continue
            del self._copies[key]
            total -= copy.size
            _discard(copy)

    def _evictions(self, key, size):
        """Oldest unpinned copies that make room for one more within the budgets."""
        if key in self._copies:
            return []
        count = len(self._copies)
        total = sum(copy.size for copy in self._copies.values())
        evicted = []
        for cached_key, copy in self._copies.items():
            if count < COPY_LIMIT and total + size <= COPY_BYTES:
                break
            if self._pinned(copy):
                continue
            evicted.append(cached_key)
            count -= 1
            total -= copy.size
        return evicted

    def play(self, context_id, request_id, expected_revision, asset_id, player):
        """Queue a private copy for one saved result; the timer opens it when ready."""
        _main_thread()
        if player not in ("SYSTEM", "BLENDER"):
            raise MediaError("Choose the system player or Blender's animation player")
        kinds = ("video",) if player == "BLENDER" else ("video", "audio")
        session, store, item, index = _admit(
            context_id, request_id, expected_revision, asset_id, kinds
        )
        binary = None
        # Exited players and launchers no longer pin their copies.
        self._reap()
        if player == "BLENDER":
            binary = _blender_binary()
            if binary is None:
                raise MediaError("Play in Blender needs Blender's executable")
            if len(self._players) >= PLAYER_LIMIT:
                raise MediaError("Close an open Blender animation player first")
        self._bind(context_id)
        key = PreviewKey.for_result(store.scope, request_id, item)
        reuse = self._copies.get(key)
        evicted = self._evictions(key, item.receipt.size)
        keep = [copy.directory for copy in self._copies.values()]
        keep += [copy.directory for _, copy in (*self._players, *self._openers)]
        try:
            task = session.prepare_playback(
                request_id,
                expected_revision=expected_revision,
                asset_id=asset_id,
                root=_root(),
                reuse=reuse,
                discard=[self._copies[cached].directory for cached in evicted],
                keep=keep,
            )
        except WorkerError:
            raise MediaError("Previews are busy; try again shortly") from None
        for cached in evicted:
            del self._copies[cached]
        if self._play is not None:
            self._abandon(self._play)
        kind = playback.kind(item.asset.media_type)
        self._play = PlayRequest(
            context_id,
            session,
            key,
            task,
            player,
            f"{kind} ({index})",
            binary,
            reuse,
        )
        return task

    def _abandon(self, request):
        try:
            request.session.cancel_playback(request.task)
        except Exception:
            pass  # A retired session already signaled its lane.
        self._abandoned.append(request.task)

    def _finish_play(self):
        request = self._play
        if request is None or not request.task.done():
            return False
        self._play = None
        try:
            copy = request.task.result()
        except (CancelledError, PreviewCanceled, playback.PlaybackCanceled):
            return True
        except Exception as error:
            runtime.set_message(_reason(error))
            return True
        if not self._current(request.context_id, request.session) or copy.key != request.key:
            if not self._cached(copy) and not self._pinned(copy):
                _discard(copy)
            return True
        previous = self._copies.pop(copy.key, None)
        if previous is not None and previous is not copy and not self._pinned(previous):
            _discard(previous)
        self._copies[copy.key] = copy
        self._open(copy, request)
        return True

    def _open(self, copy, request):
        try:
            if request.player == "BLENDER":
                self._players.append((_launch(request.binary, copy), copy))
                message = f"Opened saved {request.label} in Blender's animation player"
            else:
                self._openers.append((_system_open(blender_path(copy.path)), copy))
                message = f"Opened saved {request.label} in the system player"
        except (OSError, RuntimeError, ValueError, LocalRenderError):
            message = "The player could not open the private copy"
        runtime.set_message(message)

    def _reap(self):
        """Forget exited players and launchers; their copies leave unless cached or shared.

        A system player launcher exits once the default application has the
        copy; a failed one is reported, since nothing else would show it.
        """
        running, exited, failed = [], [], False
        for process, copy in self._players:
            if process.poll() is None:
                running.append((process, copy))
            else:
                exited.append(copy)
        opening = []
        for process, copy in self._openers:
            code = process.poll()
            if code is None:
                opening.append((process, copy))
            else:
                exited.append(copy)
                failed |= code != 0
        if not exited:
            return False
        self._players, self._openers = running, opening
        if failed:
            runtime.set_message("The system player could not open the private copy")
        for copy in exited:
            if not self._cached(copy) and not self._pinned(copy):
                _discard(copy)
        self._trim()
        return True

    def _collect_abandoned(self):
        remaining = []
        for task in self._abandoned:
            if not task.done():
                remaining.append(task)
                continue
            try:
                copy = task.result()
            except Exception:
                continue  # A failed or canceled copy was removed on the lane.
            if not self._cached(copy) and not self._pinned(copy):
                _discard(copy)
        self._abandoned = remaining

    # -- waveform ---------------------------------------------------------

    def select_waveform(self, context_id, request_id, expected_revision, asset_id):
        """Show one saved audio result's envelope, requesting it if needed."""
        _main_thread()
        session, _, item, index = _admit(
            context_id, request_id, expected_revision, asset_id, ("audio",)
        )
        if runtime.waveform_spec() is None:
            raise MediaError("Audio waveforms need Blender's executable")
        from .job_session import OriginUnavailable

        try:
            previews = session.result_previews
            statuses = previews.request(request_id, asset_ids=(asset_id,), renditions=(ENVELOPE,))
            current = statuses[0].get(ENVELOPE) if statuses else None
            if current is not None and current.state in _FAILED:
                previews.retry(request_id, asset_id)
        except PreviewError as error:
            # Sanitized scheduler refusals, such as too many pending previews.
            raise MediaError(str(error)) from None
        except (OriginUnavailable, ResultError, ValueError):
            raise MediaError("Waveforms are unavailable for this connection") from None
        self._bind(context_id)
        self._release_icon()
        self.selection = Waveform(context_id, session, request_id, asset_id, f"Audio ({index})")
        self._update_waveform()

    def _icon(self, envelope):
        import bpy.utils.previews

        width, height = WAVEFORM_SIZE
        pixels = audio_waveform.raster(envelope, width=width, height=height)
        self._release_icon()
        self._previews = bpy.utils.previews.new()
        preview = self._previews.new("waveform")
        preview.image_size = WAVEFORM_SIZE
        preview.image_pixels_float = array.array("f", (value / 255 for value in pixels))
        return preview.icon_id

    def _update_waveform(self):
        selected = self.selection
        if selected is None or selected.status != "LOADING":
            return False
        from .job_session import OriginUnavailable

        try:
            status = selected.session.result_previews.status(selected.request_id, selected.asset_id)
        except OriginUnavailable:
            status = None
        current = None if status is None else status.get(ENVELOPE)
        if current is None:
            selected.status, selected.message = "ERROR", "Select Waveform again"
        elif current.state == PreviewState.READY:
            envelope = current.preview.envelope
            try:
                selected.icon_id = self._icon(envelope)
            except (audio_waveform.WaveformError, RuntimeError, ValueError, TypeError):
                self._release_icon()
                selected.status = "ERROR"
                selected.message = "The waveform could not be displayed"
                return True
            selected.envelope = envelope
            selected.status, selected.message = "READY", summary(envelope)
        elif current.state in _FAILED:
            selected.status = "ERROR"
            selected.message = current.reason or "The waveform could not be prepared; use Retry"
        else:
            message = _WAITING.get(current.state, "Preparing the waveform...")
            if message == selected.message:
                return False
            selected.message = message
        return True

    def cancel_waveform(self):
        _main_thread()
        selected = self.selection
        if selected is None or selected.status != "LOADING":
            return
        selected.status, selected.message = "CANCELED", "Waveform canceled"
        try:
            selected.session.result_previews.cancel(selected.request_id, selected.asset_id)
        except Exception:
            pass  # A retired session already stopped its lane work.

    def close_waveform(self):
        _main_thread()
        self.cancel_waveform()
        self.selection = None
        self._release_icon()

    # -- lifecycle --------------------------------------------------------

    def poll(self):
        """Advance play, players and the waveform; returns whether drawing changed."""
        _main_thread()
        changed = self._reap()
        if self._context is not None and self._context != runtime.state.job_context_id:
            self.retire()
            changed = True
        selected = self.selection
        if selected is not None and not self._current(selected.context_id, selected.session):
            self.selection = None
            self._release_icon()
            changed = True
        changed |= self._finish_play()
        self._collect_abandoned()
        changed |= self._update_waveform()
        return changed

    def retire(self):
        """Forget the selection and pending play; remove copies no running player uses."""
        _main_thread()
        # A player or launcher that exited since the last timer tick no longer
        # pins its copy, so that copy is removed here too.
        self._reap()
        if self.selection is not None:
            self.cancel_waveform()
            self.selection = None
        self._release_icon()
        if self._play is not None:
            self._abandon(self._play)
            self._play = None
        for copy in self._copies.values():
            if not self._pinned(copy):
                _discard(copy)
        self._copies.clear()
        self._context = None

    def shutdown(self):
        """On unregister: retire, collect finished lane tasks and leave players running.

        A running player or launcher keeps its copy; the age sweep removes it later.
        """
        self.retire()
        self._collect_abandoned()
        self._abandoned.clear()
        self._players.clear()
        self._openers.clear()


controller = MediaController()


def _redraw():
    from . import pump, studio

    pump.redraw()
    studio.redraw_popups()


def _tick():
    try:
        changed = controller.poll()
    except Exception:
        # Never log task outcomes: they can hold private paths.
        _log.warning("Saved media update failed")
        changed = False
    if changed:
        _redraw()
    return controller.interval()


def _start_timer():
    if bpy.app.background:
        return
    # A terminal state may have left a one-second timer pending; restart it at
    # the loading cadence. Persistent: a file load would otherwise drop the
    # timer while an animation player still runs, and its copy would outlive it.
    if bpy.app.timers.is_registered(_tick):
        bpy.app.timers.unregister(_tick)
    bpy.app.timers.register(_tick, first_interval=LOADING_INTERVAL, persistent=True)


@persistent
def _file_load(_):
    controller.retire()


class SCENARIO_OT_play_saved_media(bpy.types.Operator):
    bl_idname = "scenario.play_saved_media"
    bl_label = "Play saved media"
    bl_description = (
        "Open a verified private copy of this saved result in a player; "
        "nothing is generated, downloaded or changed in the scene"
    )
    context_id: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    request_id: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    expected_revision: IntProperty(min=0, options={"HIDDEN", "SKIP_SAVE"})
    asset_id: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    player: EnumProperty(
        items=(
            ("SYSTEM", "System player", "The operating system's default application"),
            ("BLENDER", "Blender", "Blender's animation player in a separate process"),
        ),
        options={"HIDDEN", "SKIP_SAVE"},
    )

    @classmethod
    def poll(cls, context):
        return not bpy.app.background

    @classmethod
    def description(cls, context, properties):
        if properties.player == "BLENDER":
            return (
                "Open a verified private copy of this saved video in Blender's animation "
                "player, without Scenario credentials; nothing is generated, downloaded "
                "or changed in the scene"
            )
        return (
            "Open a verified private copy of this saved result in the system player; "
            "nothing is generated, downloaded or changed in the scene"
        )

    def execute(self, context):
        try:
            controller.play(
                self.context_id, self.request_id, self.expected_revision, self.asset_id, self.player
            )
        except MediaError as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        except Exception:
            self.report({"ERROR"}, "Could not prepare a private copy; inspect saved jobs again")
            return {"CANCELLED"}
        runtime.set_message("Preparing a verified private copy...")
        _start_timer()
        _redraw()
        return {"FINISHED"}


class SCENARIO_OT_preview_saved_waveform(bpy.types.Operator):
    bl_idname = "scenario.preview_saved_waveform"
    bl_label = "Show saved audio waveform"
    bl_description = (
        "Show this saved audio's waveform, decoded from its verified local file in an "
        "offline Blender process, without playback or a service request"
    )
    context_id: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    request_id: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    expected_revision: IntProperty(min=0, options={"HIDDEN", "SKIP_SAVE"})
    asset_id: StringProperty(options={"HIDDEN", "SKIP_SAVE"})

    def execute(self, context):
        try:
            controller.select_waveform(
                self.context_id, self.request_id, self.expected_revision, self.asset_id
            )
        except MediaError as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        except Exception:
            self.report({"ERROR"}, "Could not show the waveform; inspect saved jobs again")
            return {"CANCELLED"}
        _start_timer()
        _redraw()
        return {"FINISHED"}


class SCENARIO_OT_cancel_saved_waveform(bpy.types.Operator):
    bl_idname = "scenario.cancel_saved_waveform"
    bl_label = "Cancel waveform"
    bl_description = "Stop decoding this waveform; the saved result and its controls stay unchanged"

    @classmethod
    def poll(cls, context):
        selected = controller.selection
        return selected is not None and selected.status == "LOADING"

    def execute(self, context):
        controller.cancel_waveform()
        _redraw()
        return {"FINISHED"}


class SCENARIO_OT_close_saved_waveform(bpy.types.Operator):
    bl_idname = "scenario.close_saved_waveform"
    bl_label = "Close waveform"
    bl_description = "Hide this waveform and stop decoding it; the saved result stays unchanged"

    def execute(self, context):
        controller.close_waveform()
        _redraw()
        return {"FINISHED"}


def draw(layout, record):
    """The selected waveform for this view; only cached state is read here."""
    selected = controller.selection
    if (
        selected is None
        or record.local_id != selected.request_id
        or not record.meta.get("shared_job")
        or selected.context_id != runtime.state.job_context_id
    ):
        return
    context = bpy.context
    box = layout.box()
    header = box.row(align=True)
    header.label(text=f"Waveform: {selected.label}", icon="SOUND")
    header.operator("scenario.close_saved_waveform", text="", icon="X", emboss=False)
    icon = "ERROR" if selected.status == "ERROR" else "INFO"
    for index, line in enumerate(label_wrap.label_lines(context, selected.message, TEXT_INSET)):
        box.label(text=line, icon=icon if index == 0 else "NONE")
    if selected.status == "LOADING":
        box.operator("scenario.cancel_saved_waveform", text="Cancel", icon="CANCEL")
    elif selected.status == "READY":
        width = label_wrap.region_width(context) / label_wrap.ui_scale(context)
        box.template_icon(icon_value=selected.icon_id, scale=max(3.0, min(8.0, (width - 80) / 20)))
    elif "saved_revision" in record.meta:
        retry = box.operator("scenario.preview_saved_waveform", text="Retry", icon="FILE_REFRESH")
        retry.context_id, retry.request_id = selected.context_id, selected.request_id
        retry.expected_revision = record.meta["saved_revision"]
        retry.asset_id = selected.asset_id


CLASSES = (
    SCENARIO_OT_play_saved_media,
    SCENARIO_OT_preview_saved_waveform,
    SCENARIO_OT_cancel_saved_waveform,
    SCENARIO_OT_close_saved_waveform,
)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    if _file_load not in bpy.app.handlers.load_pre:
        bpy.app.handlers.load_pre.append(_file_load)


def unregister():
    try:
        controller.shutdown()
    finally:
        if bpy.app.timers.is_registered(_tick):
            bpy.app.timers.unregister(_tick)
        if _file_load in bpy.app.handlers.load_pre:
            bpy.app.handlers.load_pre.remove(_file_load)
        for cls in reversed(CLASSES):
            bpy.utils.unregister_class(cls)
