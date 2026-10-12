# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Automatic previews of saved shared results in Jobs, Generations and Studio.

The session's preview scheduler (``core.jobs.preview_scheduler``) fetches
server stills of saved video, 3D and audio results on its preview lane and
issues private verified copies of saved images. This module is its Blender
side and runs on the main thread only, in its own timer, never while drawing:

- It requests one still for each saved result on the drawn page of the jobs
  those panels show: four tiles at a time, which a pager steps through. It
  contacts nothing itself; the scheduler's lane reads Scenario's metadata and
  downloads server stills while Online Access allows.
- It decodes each issued image copy into a PNG of at most 256 pixels per side,
  which the lane validates and caches. The shared ``preview_decode`` helper
  loads the copy into a temporary ``bpy.data.temp_data()`` block, so the open
  file, its undo history and its dependency graph never see it.
- It builds preview icons from verified cache files only, rehashed against the
  cache entry right before the same temporary decode, in its own
  ``bpy.utils.previews`` collection. It never calls
  ``ImagePreviewCollection.load``, which writes a copy into the operating
  system's thumbnail cache.

Drawing reads only the tiles and pages this controller precomputed; a page
offset is transient state of this controller, changed only by the pager's
operator and reset when a job's results change. Nothing here generates, downloads a result, applies, spends or changes the scene or the job
store, and a late status from a retired connection is never shown.
"""

import hashlib
import logging
import os
import stat
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field, replace
from pathlib import Path

import bpy
from bpy.app.handlers import persistent
from bpy.props import EnumProperty, StringProperty

from ..core.jobs.result_previews import (
    PREVIEW_EDGE,
    ROLE_LABEL,
    STILL,
    STILL_MAX_BYTES,
    PreviewError,
    PreviewState,
    bounded_local_image,
    in_cache,
    preview_kind,
)
from ..core.jobs.results import PREVIEW_STATES, ResultError
from ..core.jobs.workers import WorkerError
from ..core.ui import preview_pages
from ..core.ui.text_wrap import NO_BREAK
from . import label_wrap, runtime
from .preview_decode import PreviewDecodeError, decode

_log = logging.getLogger("scenario")
# Previews are kept for the first jobs of each list the panels draw: Jobs rows
# and the Generations rows, which list at most twelve.
JOB_LIMIT = 12
# Tiles drawn at once; a pager steps through a job's other previewable results.
TILE_LIMIT = preview_pages.SIZE
ICON_LIMIT = 64
BUSY_INTERVAL = 0.1
IDLE_INTERVAL = 0.5
# Seconds before a job whose preview request was refused, for example by a full
# scheduler, is requested again; the last delay repeats.
REQUEST_RETRY = (5.0, 10.0, 20.0, 40.0, 60.0)
# Interface units of the sidebar that a status line under the tiles cannot use:
# from the region's left edge to the text after the line's icon (panel and job
# box) and from the job box's right content edge past the category tabs,
# measured as 90 on Blender 5.1.2, plus a few units of slack.
TEXT_INSET = 96
# The pager's arrows: one interface unit wide each, about 24 units with spacing,
# as tall as the tiles' icons.
ARROW_UNITS = 1.0
ARROW_WIDTH = 24
PREVIOUS_ARROW, NEXT_ARROW = "\u2039", "\u203a"
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


class PageRefused(ValueError):
    """A sanitized refusal of the pager's previous or next page."""


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
    """One shown job's previewable targets, ranked, or why its request was refused.

    ``requested`` holds the asset IDs already requested, those of the pages
    drawn so far. A refused request is made again at ``retry_at`` (monotonic
    seconds), after ``attempts`` refusals in a row; meanwhile the targets
    already read stay, so ready tiles and the page offset survive it.
    """

    revision: int
    targets: tuple
    message: str = ""
    retry_at: float = field(default=0.0, compare=False)
    attempts: int = field(default=0, compare=False)
    requested: frozenset = field(default=frozenset(), compare=False)


def _verified(preview, root):
    r"""The cache file of a ready still, rehashed against its entry, or None.

    ``root`` is the scheduler's configured root; the cache spells ``path`` from
    its canonical root, the extended ``\\?\`` namespace on Windows.
    """
    path = preview.path
    try:
        if path is None or not in_cache(Path(path), Path(root)):
            return None
        # Nonblocking: a named pipe in its place would otherwise block the
        # main-thread timer until a writer opens it.
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0)
        flags |= getattr(os, "O_NONBLOCK", 0)
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
    """Every previewable downloaded result of one saved record, ranked and numbered
    like its controls; the pager draws them ``TILE_LIMIT`` at a time."""
    chosen = []
    for index, item in enumerate(record.results, 1):
        kind = preview_kind(item.asset.media_type)
        if item.receipt is None or kind is None:
            continue
        label = ROLE_LABEL.get(item.asset.texture_role) or KIND_LABEL[kind]
        target = _Target(item.asset.asset_id, index, label, kind)
        chosen.append((_rank(item), index, target))
    chosen.sort(key=lambda value: value[:2])
    return tuple(target for _, _, target in chosen)


class PreviewController:
    """Main-thread preview requests, image decoding and icons for shared saved jobs.

    Drawing reads ``tiles`` and ``pages`` only. Every status is read for the
    connection it was requested in; a connection, project or file change
    retires them, page offsets included.
    """

    def __init__(self):
        self.tiles = {}
        self.pages = {}  # request ID -> preview_pages.Page, for jobs with a pager
        self._offsets = preview_pages.PageOffsets()
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

    def _visible(self, request_id, targets):
        """The job's drawn targets and its page, or None as the page when all fit."""
        results = tuple(target.asset_id for target in targets)
        offset = self._offsets.offset(request_id, results)
        return preview_pages.visible(targets, offset), preview_pages.page(results, offset)

    def _request(self, scheduler, store, views):
        changed = False
        jobs = {}
        now = time.monotonic()
        for view in views:
            request_id, revision = view.local_id, view.meta["saved_revision"]
            previous = job = self._jobs.get(request_id)
            refused = job is not None and job.revision == revision and bool(job.message)
            fresh = job is None or job.revision != revision or (refused and now >= job.retry_at)
            if fresh or not refused:
                message = ""
                try:
                    if fresh:
                        record = store.get(request_id)
                        job = _Job(revision, () if record is None else _targets(record))
                    # Only the drawn page is requested; the pager requests others.
                    visible, _ = self._visible(request_id, job.targets)
                    missing = [
                        target.asset_id
                        for target in visible
                        if target.asset_id not in job.requested
                    ]
                    if missing:
                        scheduler.request(request_id, asset_ids=missing, renditions=(STILL,))
                        job = replace(job, requested=job.requested | frozenset(missing))
                except PreviewError as error:
                    # Sanitized scheduler refusals, such as too many pending previews.
                    message = str(error)
                except (ResultError, ValueError):
                    job = _Job(revision, ())
                except Exception:
                    _log.warning("Result preview request failed")
                    message = "Previews could not be requested"
                if message:
                    # Ask again later: a refusal such as a full scheduler is transient.
                    attempts = previous.attempts + 1 if refused else 1
                    delay = REQUEST_RETRY[min(attempts, len(REQUEST_RETRY)) - 1]
                    if job is None or job.revision != revision:
                        job = _Job(revision, ())  # Its saved record was not read.
                    job = replace(job, message=message, retry_at=now + delay, attempts=attempts)
                changed |= job != previous
            jobs[request_id] = job
        changed |= jobs.keys() != self._jobs.keys()
        self._jobs = jobs
        return changed

    def _decode_one(self, scheduler):
        """Decode the oldest issued image copy into its PNG; one per tick.

        Returns whether this tick decoded or handed a copy to the lane, so the
        tick decodes no icon as well.
        """
        requests = scheduler.decode_requests()
        self._decoded &= set(requests)
        if not requests:
            return False
        request = requests[0]
        decoded = request not in self._decoded
        if decoded:
            try:
                decode(request.source, request.max_edge, bounded_local_image, output=request.output)
            except PreviewDecodeError as error:
                scheduler.discard_decode(request, reason=str(error))
                return True
            self._decoded.add(request)
        try:
            scheduler.finish_decode(request)
        except WorkerError:
            # The lane is full; the decoded file waits for the next tick, which
            # retries only the hand-off.
            return decoded
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
        """Rebuild the drawn tiles and pages; ``budget`` is how many icons this tick may decode."""
        self._used = set()
        tiles, pages, results = {}, {}, {}
        for request_id, job in tuple(self._jobs.items()):
            results[request_id] = tuple(target.asset_id for target in job.targets)
            visible, page = self._visible(request_id, job.targets)
            built = []
            for target in visible:
                if scheduler.status(request_id, target.asset_id) is None:
                    if job.message:
                        # Its request was refused; the job asks again when due.
                        base = target.asset_id, target.number, target.label, target.kind
                        built.append(Tile(*base, "waiting", job.message))
                        continue
                    # The scheduler forgot a settled entry to make room: request
                    # this job again on the next poll.
                    self._jobs[request_id] = replace(job, revision=-1)
                tile, budget = self._tile(scheduler, request_id, target, budget)
                built.append(tile)
            if built:
                tiles[request_id] = tuple(built)
                if page is not None:
                    pages[request_id] = page
            elif job.message:
                tiles[request_id] = (Tile("", 0, "Previews", "image", "unavailable", job.message),)
        # A job no longer shown, or whose results changed, starts on its first page.
        self._offsets.prune(results)
        self._trim_icons(self._used)
        self._icon_failures = {
            key: message for key, message in self._icon_failures.items() if key in self._used
        }
        self._busy = any(tile.status == "loading" for items in tiles.values() for tile in items)
        if tiles == self.tiles and pages == self.pages:
            return False
        self.tiles, self.pages = tiles, pages
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

    def page(self, context_id, request_id, direction):
        """Show one job's previous (-1) or next (1) tiles; returns whether the page moved.

        The new page's previews are requested at once and its tiles rebuilt
        from status and icons already built; the timer builds the other icons.
        """
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
            raise PageRefused("The connection changed; inspect saved jobs again")
        job = self._jobs.get(request_id)
        if job is None:
            raise PageRefused("This saved job's previews are no longer shown; inspect saved jobs")
        results = tuple(target.asset_id for target in job.targets)
        before = self._offsets.offset(request_id, results)
        if self._offsets.move(request_id, results, direction) == before:
            return False
        from .job_session import OriginUnavailable

        try:
            scheduler = session.result_previews
        except OriginUnavailable:
            raise PageRefused("Previews are unavailable for this connection") from None
        self._request(scheduler, state.job_store, self._shown())
        self._update_tiles(scheduler, 0)
        self._busy = True
        return True

    def retire(self):
        """Forget tiles, pages, requests and icons of the current connection."""
        _main_thread()
        self._release_icons()
        self.tiles = {}
        self.pages = {}
        self._offsets.clear()
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
    # Blender unregisters a timer that raises, and only enabling the extension
    # registers this one: no failure may escape it.
    try:
        changed = controller.poll()
    except Exception:
        # Never log statuses or paths: they can identify private results.
        _log.warning("Result preview update failed")
        changed = False
    if changed:
        try:
            _redraw()
        except Exception:
            _log.warning("Result preview redraw failed")
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


class SCENARIO_OT_page_result_previews(bpy.types.Operator):
    bl_idname = "scenario.page_result_previews"
    bl_label = "Show other result previews"
    bl_description = (
        "Show the previous or next previews of this saved job's results; nothing is "
        "downloaded, applied, spent or changed in the scene"
    )
    context_id: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    request_id: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    direction: EnumProperty(
        items=(
            ("PREVIOUS", "Previous", "The previous previews of this saved job"),
            ("NEXT", "Next", "The next previews of this saved job"),
        ),
        options={"HIDDEN", "SKIP_SAVE"},
    )

    @classmethod
    def description(cls, context, properties):
        which = "previous" if properties.direction == "PREVIOUS" else "next"
        return (
            f"Show this saved job's {which} result previews; nothing is downloaded, "
            "applied, spent or changed in the scene"
        )

    def execute(self, context):
        direction = -1 if self.direction == "PREVIOUS" else 1
        try:
            moved = controller.page(self.context_id, self.request_id, direction)
        except PageRefused as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        except Exception:
            self.report({"ERROR"}, "Could not show other previews; inspect saved jobs again")
            return {"CANCELLED"}
        if not moved:
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


def _named(caption):
    """A tile's caption, such as "Model (2)", that a wrapped status line keeps whole."""
    return caption.replace(" ", NO_BREAK)


def _arrow(row, record, text, direction, enabled, height):
    """One pager arrow beside the tiles, as tall as their icons; disabled at an end."""
    column = row.column(align=True)
    column.enabled = enabled
    column.ui_units_x = ARROW_UNITS
    column.scale_y = height
    arrow = column.operator("scenario.page_result_previews", text=text)
    arrow.context_id, arrow.request_id = controller.context_id, record.local_id
    arrow.direction = direction


def draw(layout, record):
    """Preview tiles of one shared saved view; only precomputed tiles and pages are read."""
    tiles = controller.tiles.get(record.local_id)
    if (
        not tiles
        or not record.meta.get("shared_job")
        or controller.context_id is None
        or controller.context_id != runtime.state.job_context_id
    ):
        return
    context = bpy.context
    width = label_wrap.region_width(context) / label_wrap.ui_scale(context)
    shown = [tile for tile in tiles if tile.asset_id]
    page = controller.pages.get(record.local_id)
    if shown:
        arrows = 0 if page is None else 2 * ARROW_WIDTH
        icon_scale = max(2.5, min(5.0, (width - 60 - arrows) / (22 * len(shown))))
        row = layout.row(align=False)
        if page is not None:
            _arrow(row, record, PREVIOUS_ARROW, "PREVIOUS", page.previous, icon_scale)
        for tile in shown:
            column = row.column(align=True)
            column.template_icon(
                icon_value=tile.icon_id or _builtin(KIND_ICON[tile.kind]), scale=icon_scale
            )
            column.label(text=tile.title)
        if page is not None:
            _arrow(row, record, NEXT_ARROW, "NEXT", page.next, icon_scale)
            layout.label(text=page.label)
    pending = {}
    for tile in tiles:
        if tile.status == "ready":
            continue
        if tile.retry:
            message = f"{_named(tile.caption)}: {tile.message}" if tile.asset_id else tile.message
            for index, line in enumerate(label_wrap.label_lines(context, message, TEXT_INSET)):
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
        label = f"{', '.join(_named(caption) for caption in captions)}: {message}"
        for index, line in enumerate(label_wrap.label_lines(context, label, TEXT_INSET)):
            layout.label(text=line, icon="INFO" if index == 0 else "BLANK1")


CLASSES = (SCENARIO_OT_retry_result_preview, SCENARIO_OT_page_result_previews)


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
