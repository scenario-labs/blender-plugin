# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Credential-bound cloud history delivery for UI and local MCP."""

import uuid

from ..core import history as core_history
from ..core.api.catalog import model_kind
from ..core.api.errors import ScenarioError
from ..core.jobs.store import StoreError
from . import runtime


def saved_records():
    """Read current scoped storage, independently of the displayed cloud page."""
    try:
        records = runtime.ensure_job_store().records()
    except (StoreError, OSError):
        runtime.state.history_saved_ids = None
        raise ScenarioError(
            0, "Could not inspect saved jobs; preserve storage for recovery"
        ) from None
    runtime.state.history_saved_ids = frozenset(
        record.remote_job_id for record in records if record.remote_job_id
    )
    return records


def saved_matches(reference):
    return tuple(
        record
        for record in saved_records()
        if reference in (record.intent.request_id, record.remote_job_id)
    )


def _catalog_kind(model_id):
    """Read the loaded catalog, not the mode-filtered lane lists a picker shows."""
    record = runtime.state.records.get(model_id) if model_id else None
    return model_kind(record) if record is not None else None


def _kinds(jobs):
    """model_id -> catalog kind for one page; missing until the catalog loads."""
    kinds = {}
    for job in jobs:
        model_id = ((job.get("metadata") or {}).get("input") or {}).get("modelId")
        kind = _catalog_kind(model_id) if isinstance(model_id, str) else None
        if kind:
            kinds[model_id] = kind
    return kinds


def entry_kind(entry):
    """A row's kind, completed from a catalog that loaded after its page."""
    if entry.kind != core_history.UNKNOWN_KIND:
        return entry.kind
    return _catalog_kind(entry.model_id) or core_history.UNKNOWN_KIND


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
                payload["jobs"],
                manager.registry.all(),
                kinds=_kinds(payload["jobs"]),
                shared_records=saved_records(),
            )
        except ScenarioError:
            error = "Could not inspect saved jobs; preserve storage for recovery"
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
