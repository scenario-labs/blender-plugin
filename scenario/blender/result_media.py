# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Play, Stop and waveform controls for saved shared video and audio results.

The shared saved-job descriptors draw these controls. They never submit,
download, spend, apply or change the scene or the job store. **Play video** and
**Open in system player** open a private verified copy (``core.jobs.playback``)
in the system player, and **Play in Blender** opens a video copy in Blender's
animation player, a separate process. Both start without Scenario credentials,
Python start-up or proxy variables in their environment, never through
``wm.path_open``. **Play audio** plays an audio copy through Blender's audio
engine in an owned offline Blender process (``core.jobs.audio_player``), never
in this session, and **Stop audio** ends it. **Waveform** asks the session's
preview scheduler for the saved audio's envelope, which an owned offline
Blender process decodes on the preview lane, then draws it from cached state.

Copies are made on the preview lane; this module keeps their handles on
Blender's main thread, reuses an unchanged copy, keeps a bounded number and
removes them when the connection retires, a file loads or the extension
unregisters. At most one audio playback runs: another **Play audio**, Stop, a
connection, project or file change, and unregistering, including at Blender's
exit, stop it. No local MCP tool launches a player or plays audio.
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
from ..core.jobs import audio_player, playback
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
# While audio plays, Stop must reappear as Play soon after the sound ends.
PLAYING_INTERVAL = 0.25
IDLE_INTERVAL = 1.0
# Blender's output that never plays; Preferences > System > Sound > Audio Device.
NO_OUTPUT = "None"
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


def _listen_root():
    return runtime.paths().cache_dir / "audio-player"


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
    request_id: str = ""
    spec: object = None  # audio_player.PlayerSpec for LISTEN


@dataclass(eq=False)
class Listening:
    """One owned audio playback child and the private copy it reads, until it is released."""

    context_id: str
    session: object
    request_id: str
    asset_id: str
    label: str
    copy: object = field(repr=False)
    player: object = field(repr=False)


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
    or opened after a credential, project or file change, and a late copy never
    starts audio. At most one audio playback is active: starting another stops
    it first.
    """

    def __init__(self):
        self.selection = None
        self._play = None
        self._copies = OrderedDict()  # PreviewKey -> PlaybackCopy, oldest first
        self._players = []  # (process, PlaybackCopy) for Blender animation players
        self._openers = []  # (process, PlaybackCopy) for system player launchers
        # Audio playback children until they exit and are released, oldest
        # first; at most the last one is active.
        self._listeners = []
        self._abandoned = []  # lane tasks whose copies must be removed once done
        # (lane task, copy) evicted for a Play whose command discards it first;
        # tracked until that task ends, since deactivation cancels a queued one.
        self._evicted = []
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
        # A child that starts, or has stopped but not yet exited, is polled quickly.
        if self.loading or any(
            item.player.phase != audio_player.PLAYING for item in self._listeners
        ):
            return LOADING_INTERVAL
        if self._listeners:
            return PLAYING_INTERVAL
        if self.selection is not None or self._players or self._openers:
            return IDLE_INTERVAL
        return None

    def listening(self, request_id):
        """The saved audio asset of ``request_id`` that plays or prepares to play, or None.

        Reads only this controller's memory, so drawing may call it.
        """
        pending = self._play
        if (
            pending is not None
            and pending.player == "LISTEN"
            and pending.request_id == request_id
            and pending.context_id == runtime.state.job_context_id
        ):
            return pending.key.asset_id
        for item in self._listeners:
            if (
                item.player.active
                and item.request_id == request_id
                and item.context_id == runtime.state.job_context_id
            ):
                return item.asset_id
        return None

    def _pinned(self, copy):
        if any(item.copy is copy for item in self._listeners):
            return True
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
        """Remove the oldest unpinned copies while the cache exceeds its budgets.

        The copy the pending Play reuses stays: the lane may already have
        handed it back for the timer to open.
        """
        total = sum(copy.size for copy in self._copies.values())
        reused = None if self._play is None else self._play.reuse
        for key, copy in tuple(self._copies.items()):
            if len(self._copies) <= COPY_LIMIT and total <= COPY_BYTES:
                break
            if self._pinned(copy) or copy is reused:
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
        """Queue a private copy for one saved result; the timer opens or plays it when ready.

        ``player`` is SYSTEM (the system player), BLENDER (Blender's animation
        player, video only) or LISTEN (Blender's audio engine in an owned
        offline process, audio only). LISTEN stops any audio playing now.
        """
        _main_thread()
        if player not in ("SYSTEM", "BLENDER", "LISTEN"):
            raise MediaError("Choose the system player or one of Blender's players")
        kinds = {"BLENDER": ("video",), "LISTEN": ("audio",)}.get(player, ("video", "audio"))
        session, store, item, index = _admit(
            context_id, request_id, expected_revision, asset_id, kinds
        )
        binary = spec = None
        # Exited players and launchers no longer pin their copies.
        self._reap()
        if player == "BLENDER":
            binary = _blender_binary()
            if binary is None:
                raise MediaError("Play in Blender needs Blender's executable")
            if len(self._players) >= PLAYER_LIMIT:
                raise MediaError("Close an open Blender animation player first")
        elif player == "LISTEN":
            device = runtime.audio_device()
            if not device or device == NO_OUTPUT:
                raise MediaError(
                    "Blender's audio output is None; choose a device in Preferences > "
                    "System > Sound, or open the system player"
                )
            spec = runtime.audio_player_spec(device)
            if spec is None:
                raise MediaError("Playing audio needs Blender's executable")
        self._bind(context_id)
        key = PreviewKey.for_result(store.scope, request_id, item)
        reuse = self._copies.get(key)
        evicted = self._evictions(key, item.receipt.size)
        keep = [copy.directory for copy in self._copies.values()]
        keep += [copy.directory for _, copy in (*self._players, *self._openers)]
        keep += [listener.copy.directory for listener in self._listeners]
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
            self._evicted.append((task, self._copies.pop(cached)))
        if self._play is not None:
            self._abandon(self._play)
        if player == "LISTEN":
            # The previous sound stops now, not when the new copy is ready.
            self._stop_listeners()
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
            request_id,
            spec,
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
        if request.player == "LISTEN":
            self._listen(copy, request)
            return
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

    def _collect_evicted(self):
        """Discard evicted copies once their lane task ends, usually already removed.

        A command canceled before it ran, or refused before its discards, left
        them in place.
        """
        remaining = []
        for task, copy in self._evicted:
            if task.done():
                _discard(copy)
            else:
                remaining.append((task, copy))
        self._evicted = remaining

    # -- audio playback ---------------------------------------------------

    def _listen(self, copy, request):
        """Start Blender's audio engine on a ready copy; any other playback already stopped."""
        self._stop_listeners()
        try:
            # The player's watcher thread, not this one, sweeps directories a
            # crash left behind and removes this child's once it exits.
            player = audio_player.start(copy.path, _listen_root(), request.spec)
        except audio_player.AudioPlayerError as error:
            runtime.set_message(str(error))
            return
        except Exception:
            runtime.set_message("Blender's audio engine could not start")
            return
        self._listeners.append(
            Listening(
                request.context_id,
                request.session,
                copy.request_id,
                copy.asset_id,
                request.label,
                copy,
                player,
            )
        )
        runtime.set_message(f"Starting saved {request.label} in Blender's audio engine...")

    def _stop_listeners(self):
        """Stop every active playback at once; their children are released as they exit."""
        stopped = False
        for listener in self._listeners:
            if listener.player.active:
                listener.player.stop()
                stopped = True
        return stopped

    def stop_listening(self, context_id, request_id, asset_id):
        """Stop this saved audio result's playback, or its preparation; never blocks.

        Returns whether anything was stopped. A Stop drawn for a result that no
        longer plays does nothing, so it never stops another result's audio.
        """
        _main_thread()
        stopped = None
        pending = self._play
        if (
            pending is not None
            and pending.player == "LISTEN"
            and pending.context_id == context_id
            and pending.request_id == request_id
            and pending.key.asset_id == asset_id
        ):
            self._abandon(pending)
            self._play = None
            stopped = pending.label
        for listener in self._listeners:
            if (
                listener.player.active
                and listener.context_id == context_id
                and listener.request_id == request_id
                and listener.asset_id == asset_id
            ):
                listener.player.stop()
                stopped = listener.label
        if stopped is not None:
            runtime.set_message(f"Stopped saved {stopped}")
        self._release_listeners()
        return stopped is not None

    def _poll_listeners(self):
        changed = False
        for listener in self._listeners:
            player = listener.player
            if player.active and not self._current(listener.context_id, listener.session):
                # A retired connection's audio never keeps playing.
                player.stop()
                changed = True
            if not player.poll():
                continue
            changed = True
            if player.phase == audio_player.PLAYING:
                runtime.set_message(f"Playing saved {listener.label} in Blender's audio engine")
            elif player.phase == audio_player.ENDED:
                runtime.set_message(f"Saved {listener.label} finished playing")
            elif player.phase == audio_player.FAILED:
                runtime.set_message(player.reason)
        return self._release_listeners() or changed

    def _release_listeners(self):
        """Forget children whose watcher saw them exit and removed their directory.

        Reads only the players' memory; their copies are unpinned here.
        """
        remaining, released = [], []
        for listener in self._listeners:
            if listener.player.active or not listener.player.released:
                remaining.append(listener)
            else:
                released.append(listener)
        if not released:
            return False
        self._listeners = remaining
        for listener in released:
            copy = listener.copy
            if not self._cached(copy) and not self._pinned(copy):
                _discard(copy)
        self._trim()
        return True

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
        previous, key = self.selection, (request_id, asset_id)
        if previous is not None and (previous.request_id, previous.asset_id) != key:
            # Only one waveform shows: an unfinished decode of the one it
            # replaces would hold the preview lane until it ends.
            self.cancel_waveform()
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
        changed |= self._poll_listeners()
        self._collect_abandoned()
        self._collect_evicted()
        changed |= self._update_waveform()
        return changed

    def retire(self):
        """Forget the selection and pending play, stop audio; remove copies nothing uses."""
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
        # Audio stops now. On a file load or connection change, cleanup is
        # guaranteed without blocking: each child's watcher thread removes its
        # directory once it exits, and the persistent timer then releases it
        # with its copy.
        self._stop_listeners()
        self._release_listeners()
        for copy in self._copies.values():
            if not self._pinned(copy):
                _discard(copy)
        self._copies.clear()
        # Deactivation cancels a queued command before it discards what its
        # Play evicted; a running one may discard them too, which is harmless.
        for _, copy in self._evicted:
            _discard(copy)
        self._evicted.clear()
        self._context = None

    def shutdown(self):
        """On unregister and Blender's exit: retire, end audio and leave external players running.

        Cleanup here is synchronous: each audio child is stopped and waited for,
        killed if it outlives the grace period, and its watcher removes its
        directory before it is released with its copy. A child that survives
        even the kill is kept, with a warning, rather than dropped: its watcher
        thread keeps reaping it and removes its directory if it exits later. A
        running animation player or system player launcher keeps its copy; the
        age sweep removes it later.
        """
        self.retire()
        for listener in self._listeners:
            try:
                stopped = listener.player.wait()
            except Exception:
                stopped = False
            if not stopped:
                # Never log process details; the next child still has to stop.
                _log.warning("An audio playback process did not exit; it is still being stopped")
        # Survivors stay listed, so nothing loses track of a running child.
        self._release_listeners()
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
    # Blender unregisters a timer that raises, which would leave players unreaped
    # and a loading waveform frozen until the next Play or Waveform.
    try:
        changed = controller.poll()
    except Exception:
        # Never log task outcomes: they can hold private paths.
        _log.warning("Saved media update failed")
        changed = False
    if changed:
        try:
            _redraw()
        except Exception:
            _log.warning("Saved media redraw failed")
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
            "Open a verified private copy of this saved result in the system's default "
            "app, outside Blender; nothing is generated, downloaded or changed in the scene"
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


class SCENARIO_OT_play_saved_audio(bpy.types.Operator):
    bl_idname = "scenario.play_saved_audio"
    bl_label = "Play saved audio"
    bl_description = (
        "Play a verified private copy of this saved audio through Blender's audio engine, "
        "in a separate offline Blender process; no other app opens, and nothing is "
        "generated, downloaded or changed in the scene"
    )
    context_id: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    request_id: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    expected_revision: IntProperty(min=0, options={"HIDDEN", "SKIP_SAVE"})
    asset_id: StringProperty(options={"HIDDEN", "SKIP_SAVE"})

    @classmethod
    def poll(cls, context):
        return not bpy.app.background

    def execute(self, context):
        try:
            controller.play(
                self.context_id, self.request_id, self.expected_revision, self.asset_id, "LISTEN"
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


class SCENARIO_OT_stop_saved_audio(bpy.types.Operator):
    bl_idname = "scenario.stop_saved_audio"
    bl_label = "Stop saved audio"
    bl_description = (
        "Stop playing this saved audio; the saved result and its controls stay unchanged"
    )
    context_id: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    request_id: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    asset_id: StringProperty(options={"HIDDEN", "SKIP_SAVE"})

    def execute(self, context):
        controller.stop_listening(self.context_id, self.request_id, self.asset_id)
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
    SCENARIO_OT_play_saved_audio,
    SCENARIO_OT_stop_saved_audio,
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
