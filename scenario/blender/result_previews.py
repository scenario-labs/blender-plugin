# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Automatic previews of saved shared results in Jobs, Generations and Studio.

The session's preview scheduler (``core.jobs.preview_scheduler``) fetches
server stills of saved video, 3D and audio results on its preview lane and
issues private verified copies of saved images. This module is its Blender
side and runs on the main thread only, in its own timer, never while drawing:

- It requests one still for each of a few saved results of the jobs those
  panels show. It contacts nothing itself; the scheduler's lane reads
  Scenario's metadata and downloads server stills while Online Access allows.
- It decodes each issued image copy into a PNG of at most 256 pixels per side,
  which the lane validates and caches. The shared ``preview_decode`` helper
  loads the copy into a temporary ``bpy.data.temp_data()`` block, so the open
  file, its undo history and its dependency graph never see it.
- It builds preview icons from verified cache files only, rehashed against the
  cache entry right before the same temporary decode, in its own
  ``bpy.utils.previews`` collection. It never calls
  ``ImagePreviewCollection.load``, which writes a copy into the operating
  system's thumbnail cache.

Drawing reads only the tiles this controller precomputed. Nothing here
generates, downloads a result, applies, spends or changes the scene or the job
store, and a late status from a retired connection is never shown.
"""

import hashlib
import logging
import os
import stat
import textwrap
import threading
from collections import OrderedDict
from dataclasses import dataclass, replace
from pathlib import Path

import bpy
from bpy.app.handlers import persistent
from bpy.props import StringProperty

from ..core.jobs.result_previews import (
    PREVIEW_EDGE,
    ROLE_LABEL,
    STILL,
    STILL_MAX_BYTES,
    PreviewError,
    PreviewState,
    bounded_local_image,
    preview_kind,
)
from ..core.jobs.results import PREVIEW_STATES, ResultError
from ..core.jobs.workers import WorkerError
from . import runtime
from .preview_decode import PreviewDecodeError, decode

_log = logging.getLogger("scenario")
# Previews are kept for the first jobs of each list the panels draw: Jobs rows
# and the Generations rows, which list at most twelve.
JOB_LIMIT = 12
TILE_LIMIT = 4
ICON_LIMIT = 64
BUSY_INTERVAL = 0.1
IDLE_INTERVAL = 0.5
_SAVED_STATES = frozenset(state.value for state in PREVIEW_STATES)
KIND_ICON = {"image": "IMAGE_DATA", "video": "FILE_MOVIE", "3d": "MESH_DATA", "audio": "SPEAKER"}
KIND_LABEL = {"image": "Image", "video": "Video", "3d": "Model", "audio": "Audio"}
_PRIMARY_ROLES = frozenset({"base", "albedo"})
_SECONDARY_MODELS = frozenset({"model/obj"})
_LOADING = {
    PreviewState.QUEUED: "Preparing preview...",
    PreviewState.DECODE: "Decoding the saved image...",
}
_UNAVAILABLE = (PreviewState.MISSING, PreviewState.FAILED)
_OFFLINE = "Preview paused while online access is disabled"


class RetryRefused(ValueError):
    """A sanitized refusal of an explicit preview retry."""


def _main_thread():
    if threading.current_thread() is not threading.main_thread():
        raise RuntimeError("Result previews belong to Blender's main thread")


@dataclass(frozen=True)
class Tile:
    """One drawn preview: its icon when ready, otherwise the kind's placeholder.

    ``number`` is the result's 1-based position among the job's saved assets,
    as in its saved-job controls; ``label`` names its texture role or kind;
    ``asset_id`` is empty for a job-level note.
    """

    asset_id: str
    number: int
    label: str
    kind: str
    status: str  # "ready", "loading", "waiting", "offline" or "unavailable"
    message: str = ""
    icon_id: int = 0
    retry: bool = False

    @property
    def caption(self):
        """The result as status lines and saved-job controls name it: ``Albedo (3)``."""
        return f"{self.label} ({self.number})" if self.asset_id else self.label

    @property
    def title(self):
        """The text under the tile, number first: ``(3) Albedo``.

        Blender keeps the start of a label that does not fit, so a narrow
        column shortens the label and keeps the number of its controls.
        """
        return f"({self.number}) {self.label}"


@dataclass(frozen=True)
class _Target:
    asset_id: str
    number: int
    label: str
    kind: str


@dataclass(frozen=True)
class _Job:
    revision: int
    targets: tuple
    message: str = ""


def _verified(preview, root):
    """The cache file of a ready still, rehashed against its entry, or None."""
    path = preview.path
    try:
        if path is None or not Path(path).is_relative_to(root):
            return None
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0)
        descriptor = os.open(path, flags)
        with os.fdopen(descriptor, "rb") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                return None
            data = stream.read(STILL_MAX_BYTES + 1)
    except (OSError, ValueError, TypeError):
        return None
    if len(data) != preview.size or hashlib.sha256(data).hexdigest() != preview.sha256:
        return None
    return path


def _rank(item):
    """Primary results first: media, embedded models and base color maps."""
    kind = preview_kind(item.asset.media_type)
    role = item.asset.texture_role
    if kind == "image":
        return 0 if role is None or role in _PRIMARY_ROLES else 1
    if kind == "3d":
        return 1 if item.asset.media_type in _SECONDARY_MODELS else 0
    return 0


def _targets(record):
    """Previewed downloaded results of one saved record, numbered like its controls."""
    chosen = []
    for index, item in enumerate(record.results, 1):
        kind = preview_kind(item.asset.media_type)
        if item.receipt is None or kind is None:
            continue
        label = ROLE_LABEL.get(item.asset.texture_role) or KIND_LABEL[kind]
        target = _Target(item.asset.asset_id, index, label, kind)
        chosen.append((_rank(item), index, target))
    chosen.sort(key=lambda value: value[:2])
    return tuple(target for _, _, target in chosen[:TILE_LIMIT])


class PreviewController:
    """Main-thread preview requests, image decoding and icons for shared saved jobs.

    Drawing reads ``tiles`` only. Every status is read for the connection it
    was requested in; a connection, project or file change retires them.
    """

    def __init__(self):
        self.tiles = {}
        self.context_id = None
        self._session = None
        self._jobs = {}
        self._icons = OrderedDict()  # icon key -> icon id, least recently used first
        self._icon_failures = {}
        self._decoded = set()
        self._used = set()
        self._previews = None
        self._busy = False

    def interval(self):
        return BUSY_INTERVAL if self._busy else IDLE_INTERVAL

    # -- icons --------------------------------------------------------------

    def _collection(self):
        import bpy.utils.previews

        if self._previews is None:
            self._previews = bpy.utils.previews.new()
        return self._previews

    def _release_icons(self):
        if self._previews is not None:
            import bpy.utils.previews

            try:
                bpy.utils.previews.remove(self._previews)
            except (KeyError, RuntimeError):
                pass  # Already released with the extension's preview collections.
            self._previews = None
        self._icons.clear()

    def _icon(self, key, size, pixels):
        collection = self._collection()
        if key in collection:
            del collection[key]
        preview = collection.new(key)
        preview.image_size = size
        preview.image_pixels_float = pixels
        self._icons[key] = preview.icon_id
        return preview.icon_id

    def _trim_icons(self, used):
        """Release the least recently used icons beyond the limit, never drawn ones."""
        for key in tuple(self._icons):
            if len(self._icons) <= ICON_LIMIT:
                break
            if key in used:
                continue
            del self._icons[key]
            if self._previews is not None and key in self._previews:
                del self._previews[key]

    # -- polling ------------------------------------------------------------

    def _shown(self):
        """Shared saved views the Jobs and Generations panels draw first."""
        shown, active, settled = [], 0, 0
        for view in runtime.state.jobs_view:
            if view.is_terminal:
                settled += 1
                if settled > JOB_LIMIT:
                    continue
            else:
                active += 1
                if active > JOB_LIMIT:
                    continue
            meta = view.meta
            if meta.get("shared_job") and meta.get("saved_state") in _SAVED_STATES:
                if view.asset_ids and type(meta.get("saved_revision")) is int:
                    shown.append(view)
        return shown

    def _request(self, scheduler, store, views):
        changed = False
        jobs = {}
        for view in views:
            request_id, revision = view.local_id, view.meta["saved_revision"]
            job = self._jobs.get(request_id)
            if job is None or job.revision != revision:
                job = _Job(revision, ())
                try:
                    record = store.get(request_id)
                    targets = () if record is None else _targets(record)
                    if targets:
                        scheduler.request(
                            request_id,
                            asset_ids=[target.asset_id for target in targets],
                            renditions=(STILL,),
                        )
                    job = _Job(revision, targets)
                except PreviewError as error:
                    # Sanitized scheduler refusals, such as too many pending previews.
                    job = _Job(revision, (), str(error))
                except (ResultError, ValueError):
                    job = _Job(revision, ())
                except Exception:
                    _log.warning("Result preview request failed")
                    job = _Job(revision, (), "Previews could not be requested")
                changed = True
            jobs[request_id] = job
        changed |= jobs.keys() != self._jobs.keys()
        self._jobs = jobs
        return changed

    def _decode_one(self, scheduler):
        """Decode the oldest issued image copy into its PNG; one per tick."""
        requests = scheduler.decode_requests()
        self._decoded &= set(requests)
        if not requests:
            return False
        request = requests[0]
        if request not in self._decoded:
            try:
                decode(request.source, request.max_edge, bounded_local_image, output=request.output)
            except PreviewDecodeError as error:
                scheduler.discard_decode(request, reason=str(error))
                return True
            self._decoded.add(request)
        try:
            scheduler.finish_decode(request)
        except WorkerError:
            return False  # The lane is full; the decoded file waits for the next tick.
        self._decoded.discard(request)
        return True

    def _tile(self, scheduler, request_id, target, budget):
        """One tile from the scheduler's I/O-free status; may build one icon."""
        status = scheduler.status(request_id, target.asset_id)
        current = None if status is None else status.get(STILL)
        base = target.asset_id, target.number, target.label, target.kind
        if current is None:
            return Tile(*base, "loading", _LOADING[PreviewState.QUEUED]), budget
        state = current.state
        if state == PreviewState.READY:
            preview = current.preview
            key = f"{request_id}/{target.asset_id}/{preview.sha256}"
            self._used.add(key)
            if key in self._icons:
                self._icons.move_to_end(key)
                return Tile(*base, "ready", icon_id=self._icons[key]), budget
            failure = self._icon_failures.get(key)
            if failure is not None:
                return Tile(*base, "unavailable", failure, retry=True), budget
            if budget <= 0:
                return Tile(*base, "loading", "Loading preview..."), budget
            path = _verified(preview, scheduler.root)
            try:
                if path is None:
                    raise PreviewDecodeError("The cached preview changed or was removed; use Retry")
                size, pixels = decode(
                    path, PREVIEW_EDGE, lambda w, h: 1 <= w <= 4096 and 1 <= h <= 4096
                )
                icon_id = self._icon(key, size, pixels)
            except (PreviewDecodeError, RuntimeError, TypeError, ValueError) as error:
                message = (
                    str(error)
                    if isinstance(error, PreviewDecodeError)
                    else "The preview could not be displayed"
                )
                self._icon_failures[key] = message
                return Tile(*base, "unavailable", message, retry=True), budget - 1
            return Tile(*base, "ready", icon_id=icon_id), budget - 1
        if state in _LOADING:
            return Tile(*base, "loading", _LOADING[state]), budget
        if state == PreviewState.PENDING:
            reason = current.reason or "Waiting for Scenario to prepare the preview"
            return Tile(*base, "waiting", reason), budget
        if state == PreviewState.OFFLINE:
            return Tile(*base, "offline", _OFFLINE), budget
        if state in _UNAVAILABLE:
            reason = current.reason or "The preview could not be prepared; use Retry"
            return Tile(*base, "unavailable", reason, retry=True), budget
        return Tile(*base, "unavailable", "No preview is available for this format"), budget

    def _update_tiles(self, scheduler, budget):
        """Rebuild the drawn tiles; ``budget`` is how many icons this tick may decode."""
        self._used = set()
        tiles = {}
        for request_id, job in tuple(self._jobs.items()):
            built = []
            for target in job.targets:
                if scheduler.status(request_id, target.asset_id) is None:
                    # The scheduler forgot a settled entry to make room: request
                    # this job again on the next poll.
                    self._jobs[request_id] = replace(job, revision=-1)
                tile, budget = self._tile(scheduler, request_id, target, budget)
                built.append(tile)
            if built:
                tiles[request_id] = tuple(built)
            elif job.message:
                tiles[request_id] = (Tile("", 0, "Previews", "image", "unavailable", job.message),)
        self._trim_icons(self._used)
        self._icon_failures = {
            key: message for key, message in self._icon_failures.items() if key in self._used
        }
        self._busy = any(tile.status == "loading" for items in tiles.values() for tile in items)
        if tiles == self.tiles:
            return False
        self.tiles = tiles
        return True

    def poll(self):
        """Request, decode and build icons for the shown saved jobs; returns whether tiles changed."""
        _main_thread()
        state = runtime.state
        session, context = state.job_session, state.job_context_id
        changed = False
        if self.context_id is not None and (
            context != self.context_id or session is not self._session
        ):
            self.retire()
            changed = True
        if session is None or not session.active or state.job_store is None:
            self._busy = False
            return changed
        from .job_session import OriginUnavailable

        try:
            scheduler = session.result_previews
        except OriginUnavailable:
            self._busy = False
            return changed  # Previews are not configured for this connection.
        self.context_id, self._session = context, session
        changed |= self._request(scheduler, state.job_store, self._shown())
        decoded = self._decode_one(scheduler)
        # One main-thread decode per tick: an image copy or else an icon.
        changed |= self._update_tiles(scheduler, 0 if decoded else 1)
        self._busy |= decoded or bool(scheduler.decode_requests())
        return changed

    def retry(self, context_id, request_id, asset_id):
        """Prepare one saved result's preview again: clear its marker and icon failure."""
        _main_thread()
        state = runtime.state
        session = state.job_session
        if (
            not context_id
            or context_id != state.job_context_id
            or context_id != self.context_id
            or session is None
            or not session.active
        ):
            raise RetryRefused("The connection changed; inspect saved jobs again")
        job = self._jobs.get(request_id)
        if job is None or not any(target.asset_id == asset_id for target in job.targets):
            raise RetryRefused("This saved result is no longer shown; inspect saved jobs")
        prefix = f"{request_id}/{asset_id}/"
        for key in tuple(self._icon_failures):
            if key.startswith(prefix):
                del self._icon_failures[key]
        from .job_session import OriginUnavailable

        try:
            session.result_previews.retry(request_id, asset_id)
        except PreviewError as error:
            raise RetryRefused(str(error)) from None
        except OriginUnavailable:
            raise RetryRefused("Previews are unavailable for this connection") from None
        self._busy = True

    def retire(self):
        """Forget tiles, requests and icons of the current connection."""
        _main_thread()
        self._release_icons()
        self.tiles = {}
        self._jobs.clear()
        self._icon_failures.clear()
        self._decoded.clear()
        self.context_id, self._session = None, None
        self._busy = False


controller = PreviewController()


def _redraw():
    from . import pump, studio

    pump.redraw()
    studio.redraw_popups()


def _tick():
    try:
        changed = controller.poll()
    except Exception:
        # Never log statuses or paths: they can identify private results.
        _log.warning("Result preview update failed")
        changed = False
    if changed:
        _redraw()
    return controller.interval()


@persistent
def _file_load(_):
    controller.retire()


class SCENARIO_OT_retry_result_preview(bpy.types.Operator):
    bl_idname = "scenario.retry_result_preview"
    bl_label = "Retry result preview"
    bl_description = (
        "Prepare this saved result's preview again from Scenario's preview or the "
        "verified saved file; nothing is generated, applied, spent or changed in the scene"
    )
    context_id: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    request_id: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    asset_id: StringProperty(options={"HIDDEN", "SKIP_SAVE"})

    def execute(self, context):
        try:
            controller.retry(self.context_id, self.request_id, self.asset_id)
        except RetryRefused as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        except Exception:
            self.report({"ERROR"}, "Could not retry the preview; inspect saved jobs again")
            return {"CANCELLED"}
        _redraw()
        return {"FINISHED"}


_builtin_icons = {}


def _builtin(name):
    """The icon value of a built-in icon, for drawing a placeholder at preview size."""
    value = _builtin_icons.get(name)
    if value is None:
        items = bpy.types.UILayout.bl_rna.functions["label"].parameters["icon"].enum_items
        value = _builtin_icons[name] = items[name].value
    return value


def draw(layout, record):
    """Preview tiles of one shared saved view; only precomputed tiles are read."""
    tiles = controller.tiles.get(record.local_id)
    if (
        not tiles
        or not record.meta.get("shared_job")
        or controller.context_id is None
        or controller.context_id != runtime.state.job_context_id
    ):
        return
    context = bpy.context
    # The custom-interface multiplier already includes the resolution scale;
    # background Blender reports 0.
    scale = context.preferences.system.ui_scale or 1.0
    width = (context.region.width if context.region is not None else 300) / scale
    shown = [tile for tile in tiles if tile.asset_id]
    if shown:
        icon_scale = max(2.5, min(5.0, (width - 60) / (22 * len(shown))))
        row = layout.row(align=False)
        for tile in shown:
            column = row.column(align=True)
            column.template_icon(
                icon_value=tile.icon_id or _builtin(KIND_ICON[tile.kind]), scale=icon_scale
            )
            column.label(text=tile.title)
    columns = max(12, int((width - 60) / 7))
    pending = {}
    for tile in tiles:
        if tile.status == "ready":
            continue
        if tile.retry:
            message = f"{tile.caption}: {tile.message}" if tile.asset_id else tile.message
            for index, line in enumerate(textwrap.wrap(message, width=columns)):
                layout.label(text=line, icon="ERROR" if index == 0 else "BLANK1")
            retry = layout.operator(
                "scenario.retry_result_preview",
                text=f"Retry preview ({tile.number})",
                icon="FILE_REFRESH",
            )
            retry.context_id, retry.request_id = controller.context_id, record.local_id
            retry.asset_id = tile.asset_id
        else:
            pending.setdefault(tile.message, []).append(tile.caption)
    for message, captions in pending.items():
        label = f"{', '.join(captions)}: {message}"
        for index, line in enumerate(textwrap.wrap(label, width=columns)):
            layout.label(text=line, icon="INFO" if index == 0 else "BLANK1")


CLASSES = (SCENARIO_OT_retry_result_preview,)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    if _file_load not in bpy.app.handlers.load_pre:
        bpy.app.handlers.load_pre.append(_file_load)
    if not bpy.app.background and not bpy.app.timers.is_registered(_tick):
        # Persistent: saved jobs inspected after a file load get previews too.
        bpy.app.timers.register(_tick, first_interval=IDLE_INTERVAL, persistent=True)


def unregister():
    try:
        controller.retire()
    finally:
        if bpy.app.timers.is_registered(_tick):
            bpy.app.timers.unregister(_tick)
        if _file_load in bpy.app.handlers.load_pre:
            bpy.app.handlers.load_pre.remove(_file_load)
        for cls in reversed(CLASSES):
            bpy.utils.unregister_class(cls)
