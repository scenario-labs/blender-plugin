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
    from . import mcp_service, studio

    changed = generation.process_catalog_events()
    mcp_service.process_pending()
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
    now = props.clock()
    for scene in bpy.data.scenes:
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
    if changed:
        redraw()
    studio.redraw_popups()


def _job_row(row):
    # Offered actions are deliberately absent: they empty while each automatic
    # two-second refresh is in flight, and redrawing on that would make the
    # saved-job controls blink. A completed refresh that changes the reading or
    # saved state redraws after its drain has restored them.
    reading = row.meta.get("remote")
    return (
        row.local_id,
        row.status,
        row.error,
        row.progress,
        len(row.files),
        row.meta.get("saved_revision"),
        None if reading is None else (reading.status, reading.percent, reading.stale),
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
        tuple(_job_row(row) for row in runtime.state.jobs_view),
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
