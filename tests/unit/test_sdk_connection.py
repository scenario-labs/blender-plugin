# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Bounded selected-credential connection checks through the published SDK."""

import threading
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest

from scenario.core.api.errors import ScenarioError
from scenario.core.jobs.manager import JobManager
from tests.unit.test_sdk_catalog import catalog


def test_probe_is_one_fresh_read_and_does_not_replace_the_catalog(monkeypatch):
    monkeypatch.setenv("SCENARIO_CUSTOM_HEADERS", "Authorization: Bearer wrong")
    calls = []

    def respond(request):
        calls.append(request)
        if request.url.params["pageSize"] == "1":
            return httpx.Response(200, json={"models": [], "nextPaginationToken": "not-followed"})
        return httpx.Response(200, json={"models": [{"id": "cached-model"}]})

    context, pools = catalog(respond)
    try:
        context.fetch_list()
        assert context.check_connection() is None
        assert context.check_connection() is None
        assert len(calls) == 3
        assert len(pools) == 1
        assert [r.id for r in context.load_list_cached()] == ["cached-model"]
        for call in calls[1:]:
            assert (call.method, call.url.path) == ("GET", "/v1/models")
            assert dict(call.url.params) == {"privacy": "public", "pageSize": "1"}
            assert call.headers["Authorization"] == "Basic c2VsZWN0ZWQta2V5OnNlbGVjdGVkLXNlY3JldA=="
    finally:
        context.close()


@pytest.mark.parametrize(
    "status,page", [(401, {}), (403, {}), (503, {}), (200, {}), (200, {"models": [None]})]
)
def test_failed_probe_delivers_safe_error_without_retrying(status, page):
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(status, json={**page, "private": "do-not-expose"})

    context, _ = catalog(respond)
    manager = JobManager(None, None, None)
    key = object()
    try:
        manager.check_connection(context, key)
        manager.join(5)
        assert not manager.has_active()
        assert manager.drain() == []
        [(name, payload)] = manager.drain_catalog()
        assert name == "connection" and payload["key"] is key and payload["catalog"] is context
        assert payload["error"] and "do-not-expose" not in payload["error"]
        assert len(calls) == 1
    finally:
        context.close()


def test_probe_respects_online_gate_without_touching_transport():
    context, _ = catalog(lambda r: pytest.fail("Offline probe reached the service"))
    context.update_online(False)
    try:
        with pytest.raises(ScenarioError, match="Online"):
            context.check_connection()
    finally:
        context.close()


def test_retired_probe_cannot_report_success():
    entered, release = threading.Event(), threading.Event()

    def respond(request):
        entered.set()
        assert release.wait(5)
        return httpx.Response(200, json={"models": []})

    context, pools = catalog(respond)
    with ThreadPoolExecutor(max_workers=1) as worker:
        result = worker.submit(context.check_connection)
        try:
            assert entered.wait(5)
            context.close()
            assert not pools[0]._closed
        finally:
            release.set()
        with pytest.raises(ScenarioError, match="connection changed"):
            result.result(5)
    assert pools[0]._closed
