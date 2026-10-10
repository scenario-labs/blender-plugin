# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Private previews of the assets a waiting workflow step asks a person to review.

A person asks for them explicitly with **Load previews** on a waiting step's
Jobs row or in Studio's Workflows page. The session's result preview scheduler
then fetches each asset's still on the dedicated preview lane: bounded, cached
under the extension user cache, bound to the saved workflow job, with Online
Access checked before each request and transient failures polled again within
its window. Opening **Review** sends nothing; the dialog shows what is loaded.

Everything here runs on Blender's main thread. The GUI pump calls `pump`, which
copies scheduler statuses into memory, verifies each newly cached still again
and decodes at most `DECODES_PER_TICK` of them into icons of at most 256 pixels
per side, never while a render job runs. Decoding goes through
`preview_decode`, in temporary Blender data freed before it returns: the open
file never gains or loses an image, so its dependency graph reports no update
and job origins captured in its scenes stay current. Icons are filled from
pixels, so Blender's file-thumbnail cache is never written. Drawing reads only
`get`, `summary` and `loading`, and never decodes, requests or changes a
property.

The cache is disposable, so a ready still's file can be evicted or deleted
after the lane verified it. The pump then fetches it again once, as part of the
request already made; after that, **Retry previews** does. Retry also sends a
still Blender could not decode through the lane again, which verifies its cache
entry and fetches it again only when that entry was lost or changed, then
decodes it again.
"""

import threading
from dataclasses import dataclass

import bpy
import bpy.utils.previews

from ..core.api.errors import ScenarioError
from ..core.jobs import result_previews as previews
from ..core.jobs import workflow_nodes
from ..core.jobs.results import ResultError
from . import preview_decode, runtime

State = previews.PreviewState
LOAD = "scenario.load_workflow_step_previews"
# A decoded icon fits this many pixels per side.
ICON_EDGE = previews.PREVIEW_EDGE
# Cached stills decoded per pump tick, so 50 images never stall one redraw.
DECODES_PER_TICK = 2
# Review assets tracked, and icons kept, at once; each icon is at most 256 KiB.
ICON_LIMIT = 128
# Icons a Jobs row or Studio Workflows entry draws per step, four to a row.
ROW_ICONS, ROW_WIDTH, ROW_SCALE = 8, 4, 3.0
LOADING, READY, OFFLINE, UNAVAILABLE = "loading", "ready", "offline", "unavailable"
_LOADING_STATES = frozenset({State.QUEUED, State.PENDING, State.DECODE})
_FAILED_STATES = frozenset({State.MISSING, State.FAILED, State.UNSUPPORTED})


def _main():
    if threading.current_thread() is not threading.main_thread():
        raise RuntimeError("Use workflow review previews on Blender's main thread")


def _rendering():
    """Whether a render job runs; decoding then waits until it ends."""
    running = getattr(bpy.app, "is_job_running", None)
    return bool(running is not None and running("RENDER"))


@dataclass(frozen=True)
class AssetPreview:
    """What drawing shows for one review asset: an icon, or why there is none."""

    state: str
    icon_id: int = 0
    reason: str = ""


@dataclass(frozen=True)
class Summary:
    """Counts over one step's review assets; `requested` excludes untracked ones."""

    total: int
    requested: int
    ready: int
    loading: int
    offline: int
    unavailable: int


class ReviewPreviews:
    """Main-thread owner of one job context's review preview icons.

    The runtime replaces it when the job context changes and clears it when
    jobs retire, so icons never cross a credential or project selection.
    """

    def __init__(self, context_id):
        _main()
        self.context_id = context_id
        # (request ID, asset ID) -> AssetPreview, in request order.
        self._tracked = {}
        # (request ID, asset ID) -> (cached digest, icon name) of a decoded icon.
        self._icons = {}
        # (request ID, asset ID) -> (cached digest, reason) of a failed decode.
        self._failed = {}
        # (request ID, asset ID) of lost cached stills already fetched again once.
        self._refetched = set()
        self._collection = None
        self._serial = 0

    # Requests.

    def request(
        self, jobs, scheduler, request_id, expected_revision, node_id, review_id, *, retry=False
    ):
        """Track one waiting step's review assets; `retry` fetches failed ones again.

        A retry sends through the lane again each still it failed or found
        missing, and each ready still whose cached file was lost or changed or
        that Blender could not decode. The lane verifies the cache entry again
        and fetches the still when the entry no longer verifies. Returns the
        number of assets requested. Checks the step binding and Online Access
        first; nothing is queued when either fails.
        """
        _main()
        assets = jobs.review_assets(request_id, expected_revision, node_id, review_id)
        if not assets:
            raise ScenarioError(0, "This step lists no assets to preview")
        if not runtime.online():
            raise ScenarioError(0, "Allow Online Access before loading previews")
        try:
            scheduler.request_review(request_id, assets)
            if retry:
                for asset_id in assets:
                    if self._refetch(scheduler, (request_id, asset_id)):
                        scheduler.retry(request_id, asset_id, review=True)
        except (previews.PreviewError, ResultError) as error:
            raise ScenarioError(0, str(error)) from None
        for asset_id in assets:
            key = (request_id, asset_id)
            if retry:
                self._failed.pop(key, None)
                self._refetched.discard(key)
            value = self._tracked.pop(key, AssetPreview(LOADING, reason="Loading preview"))
            self._tracked[key] = value
        while len(self._tracked) > ICON_LIMIT:
            self._forget(next(iter(self._tracked)))
        return len(assets)

    def _refetch(self, scheduler, key):
        """Whether Retry previews fetches this asset's still again."""
        status = scheduler.status(*key, review=True)
        still = status.get(previews.STILL) if status is not None else None
        if still is None:
            return False
        if still.state in _FAILED_STATES:
            return True
        failed = self._failed.get(key)
        return (
            still.state == State.READY
            and still.preview is not None
            and failed is not None
            and failed[0] == still.preview.sha256
        )

    # Main-thread maintenance.

    def pump(self):
        """Copy statuses and decode new icons; returns whether drawing changes."""
        _main()
        if not self._tracked:
            return False
        session, jobs = runtime.state.job_session, runtime.state.model_jobs
        scheduler = None
        if (
            runtime.state.job_context_id == self.context_id
            and session is not None
            and session.active
            and jobs is not None
        ):
            try:
                scheduler = session.result_previews
            except Exception:
                scheduler = None
        if scheduler is None:
            self.clear()
            return True
        changed = False
        current = self._current(jobs)
        for key in tuple(self._tracked):
            if key not in current:
                # The step was decided, changed or left the projection.
                self._forget(key)
                changed = True
        decodes = 0 if not _rendering() else DECODES_PER_TICK
        for key in tuple(self._tracked):
            status = scheduler.status(*key, review=True)
            still = status.get(previews.STILL) if status is not None else None
            value, decoded = self._project(scheduler, key, still, decodes < DECODES_PER_TICK)
            decodes += decoded
            if value != self._tracked[key]:
                self._tracked[key] = value
                changed = True
        return changed

    def _current(self, jobs):
        """Review assets of the tracked jobs' currently projected waiting steps."""
        current = set()
        for request_id in {request_id for request_id, _ in self._tracked}:
            for step in jobs.steps(request_id):
                current.update((request_id, asset) for asset in workflow_nodes.preview_assets(step))
        return current

    def _project(self, scheduler, key, still, may_decode):
        """The drawable value for one scheduler status; decodes a ready still once."""
        if still is None:
            icon = self._icons.get(key)
            if icon is not None:
                return self._tracked[key], 0
            return AssetPreview(UNAVAILABLE, reason="Load previews again"), 0
        if still.state in _LOADING_STATES:
            return AssetPreview(LOADING, reason=still.reason or "Loading preview"), 0
        if still.state == State.OFFLINE:
            return AssetPreview(OFFLINE, reason="Online Access is disabled"), 0
        if still.state != State.READY or still.preview is None:
            return AssetPreview(UNAVAILABLE, reason=still.reason or "No preview is available"), 0
        digest = still.preview.sha256
        icon = self._icons.get(key)
        if icon is not None and icon[0] == digest:
            return AssetPreview(READY, self._collection[icon[1]].icon_id), 0
        failed = self._failed.get(key)
        if failed is not None and failed[0] == digest:
            return AssetPreview(UNAVAILABLE, reason=failed[1]), 0
        if not may_decode:
            return AssetPreview(LOADING, reason="Preparing preview"), 0
        self._release_icon(key)
        try:
            path = previews.check_still(still.preview)
        except previews.PreviewError as error:
            return self._lost(scheduler, key, digest, str(error)), 1
        try:
            name, icon_id = self._decode(path, still.preview)
        except previews.PreviewError as error:
            self._failed[key] = (digest, str(error))
            return AssetPreview(UNAVAILABLE, reason=str(error)), 1
        except (OSError, RuntimeError, TypeError, ValueError):
            reason = "Blender could not decode this preview"
            self._failed[key] = (digest, reason)
            return AssetPreview(UNAVAILABLE, reason=reason), 1
        self._refetched.discard(key)
        self._icons[key] = (digest, name)
        return AssetPreview(READY, icon_id), 1

    def _lost(self, scheduler, key, digest, reason):
        """A ready still whose cached file vanished or changed before it was decoded.

        Cache eviction, or a person deleting the cache, can remove it after the
        lane verified it. The first time, the still is fetched again at once,
        as part of the request already made; after that, Retry previews does it.
        """
        if key not in self._refetched:
            self._refetched.add(key)
            try:
                scheduler.retry(*key, review=True)
            except previews.PreviewError:
                pass
            else:
                return AssetPreview(LOADING, reason="Fetching preview again")
        self._failed[key] = (digest, reason)
        return AssetPreview(UNAVAILABLE, reason=reason)

    def _decode(self, path, preview):
        """Decode one verified cached still into a new icon of at most ICON_EDGE pixels.

        ``preview_decode`` reads it in temporary Blender data freed before it
        returns, never through ``bpy.data``: loading and removing an image
        there would make the next dependency graph evaluation report scene and
        object updates, which invalidate every job origin captured in that
        scene. Blender must read the dimensions the lane verified. Pixels are
        RGBA display values, as the icon shows them.
        """
        expected = (preview.width, preview.height)
        read = []

        def limit(width, height):
            read.append((width, height))
            return (width, height) == expected

        try:
            size, pixels = preview_decode.decode(path, ICON_EDGE, limit)
        except preview_decode.PreviewDecodeError as error:
            if read and read[-1] != expected:
                raise previews.PreviewError(
                    "Blender read different dimensions for this preview"
                ) from None
            raise previews.PreviewError(str(error)) from None
        if self._collection is None:
            self._collection = bpy.utils.previews.new()
        name = f"review-{self._serial}"
        self._serial += 1
        icon = self._collection.new(name)
        icon.image_size = size
        icon.image_pixels_float.foreach_set(pixels)
        return name, icon.icon_id

    def _release_icon(self, key):
        icon = self._icons.pop(key, None)
        if icon is not None and self._collection is not None and icon[1] in self._collection:
            del self._collection[icon[1]]

    def _forget(self, key):
        self._tracked.pop(key, None)
        self._failed.pop(key, None)
        self._refetched.discard(key)
        self._release_icon(key)

    def clear(self):
        """Forget every tracked asset and release all icons; the disk cache stays."""
        _main()
        self._tracked.clear()
        self._icons.clear()
        self._failed.clear()
        self._refetched.clear()
        if self._collection is not None:
            bpy.utils.previews.remove(self._collection)
            self._collection = None

    # Read-only accessors for drawing.

    def get(self, request_id, asset_id):
        """The drawable value of one tracked review asset, or None; memory only."""
        return self._tracked.get((request_id, asset_id))

    def summary(self, request_id, asset_ids):
        """Counts over one step's review assets; memory only."""
        values = [self._tracked.get((request_id, asset_id)) for asset_id in asset_ids]
        states = [value.state for value in values if value is not None]
        return Summary(
            total=len(values),
            requested=len(states),
            ready=states.count(READY),
            loading=states.count(LOADING),
            offline=states.count(OFFLINE),
            unavailable=states.count(UNAVAILABLE),
        )

    def loading(self, request_id, asset_ids):
        """Whether any of these assets is still loading or waiting for Online Access."""
        return any(
            value is not None and value.state in (LOADING, OFFLINE)
            for value in (self._tracked.get((request_id, asset_id)) for asset_id in asset_ids)
        )


def owner():
    """The current job context's previews, or None; memory only, so drawing may call it."""
    value = runtime.state.review_previews
    if value is None or value.context_id != runtime.state.job_context_id:
        return None
    return value


def get(request_id, asset_id):
    value = owner()
    return None if value is None else value.get(request_id, asset_id)


def status_text(value):
    """One short line for an asset without an icon; memory only."""
    if value is None:
        return "No preview loaded"
    if value.state == READY:
        return "Preview ready"
    if value.state == LOADING:
        return value.reason or "Loading preview"
    return f"No preview: {value.reason}" if value.reason else "No preview"


def _steps(view):
    """The view's projected waiting steps for its saved revision, or ()."""
    jobs = runtime.state.model_jobs
    if jobs is None or view.kind != "workflow" or jobs.views.get(view.local_id) is not view:
        return ()
    projection = jobs.step_view(view.local_id)
    if projection.revision is None or projection.revision != view.meta.get("saved_revision"):
        return ()
    return projection.steps


def _operator(layout, view, step, text, icon, retry):
    operator = layout.operator(LOAD, text=text, icon=icon)
    operator.context_id = runtime.state.job_context_id or ""
    operator.request_id = view.local_id
    operator.expected_revision = view.meta.get("saved_revision")
    operator.node_id = step.node_id
    operator.review_id = step.review_id
    operator.retry = retry


def draw_step_previews(layout, view):
    """Load control, loaded icons and status of each waiting step's review assets.

    For Jobs rows and Studio's Workflows page. Reads memory only: it never
    requests, decodes or changes a property.
    """
    steps = [
        step
        for step in _steps(view)
        if step.blocked != "unidentified" and workflow_nodes.preview_assets(step)
    ]
    if not steps:
        return
    previews_owner = owner()
    for step in steps:
        assets = workflow_nodes.preview_assets(step)
        column = layout.column(align=True)
        if len(steps) > 1:
            column.label(text=f"Previews of {step.node_id}", icon="IMAGE_DATA")
        counts = (
            previews_owner.summary(view.local_id, assets) if previews_owner is not None else None
        )
        if counts is None or counts.requested == 0:
            _operator(column, view, step, f"Load previews ({len(assets)})", "IMAGE_DATA", False)
            continue
        icons = [
            value.icon_id
            for value in (previews_owner.get(view.local_id, asset) for asset in assets)
            if value is not None and value.state == READY and value.icon_id
        ][:ROW_ICONS]
        for start in range(0, len(icons), ROW_WIDTH):
            row = column.row(align=True)
            for icon_id in icons[start : start + ROW_WIDTH]:
                row.template_icon(icon_value=icon_id, scale=ROW_SCALE)
        text = f"Previews: {counts.ready} of {counts.total} ready"
        if counts.loading:
            text += f", {counts.loading} loading"
        if counts.offline:
            text += f", {counts.offline} waiting for Online Access"
        if counts.unavailable:
            text += f", {counts.unavailable} unavailable"
        column.label(text=text, icon="IMAGE_DATA")
        if counts.ready > len(icons):
            column.label(text=f"Review shows all {counts.ready} loaded previews")
        if counts.unavailable or counts.requested < counts.total:
            _operator(column, view, step, "Retry previews", "FILE_REFRESH", True)
