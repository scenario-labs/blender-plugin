# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Main-thread pump: drains the job manager's event queue from a bpy.app.timers callback."""

import logging

import bpy

from . import generation, handlers, props, runtime

log = logging.getLogger("scenario.pump")
ESTIMATE_DEBOUNCE = 0.7
ACTIVE_INTERVAL = 0.25
IDLE_INTERVAL = 0.6
_running = False
_job_rows = None  # what job views last drew; compared each tick, never persisted
_failures = {}  # step -> the last exception type it reported


def start():
    global _running
    if bpy.app.background or _running:
        return
    bpy.app.timers.register(_tick, first_interval=0.5, persistent=True)
    _running = True


def stop():
    global _running
    if _running:
        try:
            bpy.app.timers.unregister(_tick)
        except ValueError:
            pass
    _running = False


def _tick():
    try:
        _process()
    except Exception:  # an exception here would silently kill the timer
        log.exception("pump tick failed")
    manager = runtime.state.manager
    return ACTIVE_INTERVAL if manager is not None and manager.has_active() else IDLE_INTERVAL


def _process():
    from . import file_state, mcp_service, model_picker, studio

    changed = generation.process_catalog_events()
    mcp_service.process_pending()
    # A change delivered during a sculpt or paint stroke is marked once it ends.
    file_state.flush()
    manager = runtime.state.manager
    if manager is not None:
        for event in manager.drain():
            changed = True
            try:
                handlers.dispatch(event)
            except Exception:  # one bad event must not drop the rest of the batch
                log.exception("event %s failed", event[0] if event else event)
    if (
        not runtime.state.catalog_loaded
        and not runtime.state.catalog_loading
        and not runtime.state.catalog_error
        and runtime.credentials().valid
    ):
        generation.request_catalog()
    from . import trained_defaults

    # Forms without an explicit choice take the scope's project default before any price.
    try:
        changed |= trained_defaults.apply_pending()
        _failures.pop("defaults", None)  # a failure that comes back after this is new
    except Exception as error:  # never let it stop pricing; report each new failure once
        # Other forms may have taken their default before the failure was raised,
        # and the failing one shows its wait: redraw, at most once per timer tick.
        changed = True
        if type(error).__name__ != _failures.get("defaults"):
            _failures["defaults"] = type(error).__name__
            log.exception("applying project defaults failed")
    now = props.clock()
    # A quote binds to the selected scene, and the job session refuses any
    # other origin. Other scenes keep their pending request until selected.
    current = bpy.context.scene
    for scene in (current,) if current is not None else ():
        visible = props.active_lane(scene)
        for lane in props.GENERATION_LANES:
            if lane != visible:
                continue  # only the visible lane is priced; the others are quoted when shown
            lane_state = scene.scenario.lane_state(lane)
            if (
                lane_state.estimate_state == "PENDING"
                and lane_state.estimate_dirty_at
                and now - lane_state.estimate_dirty_at >= ESTIMATE_DEBOUNCE
            ):
                if runtime.credentials().valid and runtime.online():
                    lane_state.estimate_dirty_at = 0.0
                    generation.request_estimate(scene, lane)
                    changed = True
    if _jobs_changed():
        changed = True
    # Review previews decode verified cached stills here, never while drawing.
    previews = runtime.state.review_previews
    if previews is not None and previews.pump():
        changed = True
    if changed:
        redraw()
    studio.redraw_popups()
    # The model picker is a dialog with OK: it is refreshed only when what it shows changes,
    # here once new thumbnails are cached (model_picker._dialogs explains why).
    model_picker.refresh_thumbnails()


def _job_row(row, jobs):
    # Offered actions are deliberately absent: they empty while each automatic
    # two-second refresh is in flight, and redrawing on that would make the
    # saved-job controls blink. A completed refresh that changes the reading or
    # saved state redraws after its drain has restored them. Waiting workflow
    # steps change without either, so their review IDs, a decision in flight
    # and the last decision error are compared too.
    reading = row.meta.get("remote")
    steps = None
    if jobs is not None and row.kind == "workflow" and jobs.views.get(row.local_id) is row:
        view = jobs.step_view(row.local_id)
        steps = (
            view.revision,
            tuple(step.review_id for step in view.steps),
            view.deciding,
            view.error,
        )
    return (
        row.local_id,
        row.status,
        row.error,
        row.progress,
        len(row.files),
        row.meta.get("saved_revision"),
        None if reading is None else (reading.status, reading.percent, reading.stale),
        steps,
    )


def _jobs_changed():
    """Report whether drawn job rows changed since the last tick.

    Shared job projections change in context maintenance, not in a manager
    event, so this one comparison is what redraws Jobs, Generations and the
    viewport when progress or saved state moves. Online access is compared too,
    because shared rows draw an offline line. Unchanged ticks never redraw.
    """
    global _job_rows
    rows = (
        runtime.state.job_context_id,
        runtime.online(),
        tuple(_job_row(row, runtime.state.model_jobs) for row in runtime.state.jobs_view),
    )
    if rows == _job_rows:
        return False
    _job_rows = rows
    return True


def redraw():
    wm = bpy.context.window_manager
    if wm is None:
        return
    for window in wm.windows:
        for area in window.screen.areas:
            if area.type in ("VIEW_3D", "PREFERENCES"):
                for region in area.regions:
                    if region.type in ("UI", "HEADER", "WINDOW"):
                        region.tag_redraw()
