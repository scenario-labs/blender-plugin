# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Credential-bound cloud history delivery for UI and local MCP."""

import uuid

from ..core import history as core_history
from ..core.api.catalog import LANE_KIND as KIND_BY_LANE
from . import runtime


def _kinds():
    """model_id -> kind, most specific lane first so Patina reads as material."""
    kinds = {}
    for lane in (
        "material",
        "3d",
        "edit3d",
        "audio",
        "video",
        "render_video",
        "image",
        "render_image",
    ):
        kind = KIND_BY_LANE.get(lane)
        for record in runtime.state.lane_models.get(lane, []):
            kinds.setdefault(record.id, kind)
    return kinds


def _request(catalog, token, append):
    manager = runtime.ensure_manager()
    key = uuid.uuid4().hex
    runtime.state.history_request = key
    runtime.state.history_loading = True
    runtime.state.history_error = ""
    manager.fetch_history(catalog, key, token, append=append)
    return manager


def refresh():
    catalog = runtime.ensure_catalog()
    if runtime.state.history_loading:
        return runtime.state.manager
    return _request(catalog, None, False)


def older():
    catalog = runtime.ensure_catalog()
    token = runtime.state.history_token
    if not token or runtime.state.history_loading:
        return False
    _request(catalog, token, True)
    return True


def on_history_event(payload):
    runtime.sync_catalog_context()
    if (
        payload.get("catalog") is not runtime.state.catalog
        or runtime.state.catalog is None
        or payload.get("key") != runtime.state.history_request
    ):
        return
    runtime.state.history_request = None
    runtime.state.history_loading = False
    error = payload.get("error")
    cursors = set(runtime.state.history_cursors) if payload.get("append") else set()
    if payload.get("cursor"):
        cursors.add(payload["cursor"])
    if payload.get("token") in cursors:
        error = "Scenario repeated a history cursor; refresh history"
    if not error:
        try:
            manager = runtime.ensure_manager()
            entries = core_history.entries_from_jobs(
                payload["jobs"], manager.registry.all(), kinds=_kinds()
            )
        except (AttributeError, TypeError, ValueError, KeyError):
            error = "Scenario returned an invalid history page"
    if error:
        runtime.state.history_error = error
        runtime.set_message(f"Could not load history: {error}")
        return
    if payload.get("append"):
        known = {e.job_id for e in runtime.state.history}
        runtime.state.history.extend(e for e in entries if e.job_id not in known)
    else:
        runtime.state.history = entries
    runtime.state.history_token = payload.get("token")
    runtime.state.history_cursors = cursors
    runtime.state.history_loaded = True
    runtime.state.history_error = ""
