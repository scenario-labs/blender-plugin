# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Catalog choices and each schema become available before slow warmup completes."""

import threading
from concurrent.futures import Future

import httpx
import pytest

from scenario.core.api.errors import ScenarioError
from scenario.core.jobs.manager import JobManager
from tests.unit.test_sdk_catalog import catalog


@pytest.mark.parametrize("privacy", ["public", "private"])
@pytest.mark.parametrize("malformed", [{"capabilities": [17]}, {"tags": 17}])
def test_malformed_shared_refresh_preserves_cache_and_delivers_catalog_failures(
    monkeypatch, privacy, malformed
):
    entered, release, waiting = (threading.Event() for _ in range(3))
    calls = []
    refresh = False

    class ObservedFuture(Future):
        def result(self, timeout=None):
            waiting.set()
            return super().result(timeout)

    monkeypatch.setattr("scenario.core.api.sdk_catalog.Future", ObservedFuture)

    def respond(request):
        calls.append(request)
        if not refresh:
            return httpx.Response(200, json={"models": [{"id": "saved"}]})
        if "paginationToken" not in request.url.params:
            entered.set()
            assert release.wait(5)
            return httpx.Response(
                200, json={"models": [{"id": "partial"}], "nextPaginationToken": "next"}
            )
        return httpx.Response(200, json={"models": [{"id": "invalid", **malformed}]})

    context, _ = catalog(respond)
    manager = JobManager(None, None, None)
    try:
        context.fetch_list(privacy)
        refresh = True
        manager.fetch_catalog(context, privacy)
        try:
            assert entered.wait(5)
            manager.fetch_catalog(context, privacy)
            assert waiting.wait(5)
        finally:
            release.set()
            manager.join(5)
        assert not manager.has_active()
        assert [record.id for record in context.load_list_cached(privacy)] == ["saved"]
        assert manager.drain() == []
        assert (
            manager.drain_catalog()
            == [
                (
                    "catalog_failed",
                    {"catalog": context, "error": "Scenario returned an invalid model catalog"},
                )
            ]
            * 2
        )
        assert len(calls) == 3
        refresh = False
        manager.fetch_catalog(context, privacy)
        manager.join(5)
        assert not manager.has_active()
        assert [name for name, _ in manager.drain_catalog()] == ["catalog", "catalog"]
        assert len(calls) == 4
    finally:
        release.set()
        manager.join(5)
        context.close()


def test_catalog_and_completed_schema_are_published_before_slow_detail():
    entered, release = threading.Event(), threading.Event()

    class Catalog:
        def fetch_list(self, privacy):
            return ["listed-model"]

        def get(self, model_id, refresh=False):
            if model_id == "slow":
                entered.set()
                assert release.wait(5)
                raise ScenarioError(503, "fixture unavailable")
            return model_id

    context = Catalog()
    manager = JobManager(None, None, None)
    manager.fetch_catalog(context, model_ids=("first", "slow", "last"))
    try:
        assert entered.wait(5)
        available = manager.drain_catalog()
        assert [name for name, _ in available] == ["catalog", "models"]
        assert available[0][1]["records"] == ["listed-model"]
        assert available[0][1]["warmup"] is True
        assert available[1][1]["detailed"] == ["first"]
        assert available[1][1]["mark_dirty"] is False
        assert all(payload["catalog"] is context for _, payload in available)
        assert manager.has_active()
        manager.fetch_models(context, ["selected"])
        name, selected = manager.catalog_events.get(timeout=5)
        assert name == "models" and selected["detailed"] == ["selected"]
        assert selected["catalog"] is context
        assert selected["mark_dirty"] is True
        assert not release.is_set()
    finally:
        release.set()
        manager.join(5)
    assert not manager.has_active()
    later = manager.drain_catalog()
    assert [name for name, _ in later] == ["models", "catalog"]
    assert later[0][1]["detailed"] == ["last"]
    assert later[1][1]["detailed"] == ["first", "last"]
    assert not later[1][1].get("warmup", False)
    assert all(payload["catalog"] is context for _, payload in later)


def test_shutdown_stops_schema_warmup_after_current_request():
    entered, release = threading.Event(), threading.Event()
    requested = []

    class Catalog:
        def fetch_list(self, privacy):
            return []

        def get(self, model_id):
            requested.append(model_id)
            entered.set()
            assert release.wait(5)
            return model_id

    manager = JobManager(None, None, None)
    manager.fetch_catalog(Catalog(), model_ids=("first", "must-not-start"))
    try:
        assert entered.wait(5)
        manager.shutdown()
    finally:
        release.set()
        manager.join(5)
    assert requested == ["first"]
    assert not manager.has_active()


def test_background_schema_request_keeps_its_quote_intent():
    class Catalog:
        def get(self, model_id, refresh=False):
            return model_id

    manager = JobManager(None, None, None)
    manager.fetch_models(Catalog(), ["background"], mark_dirty=False)
    manager.join(5)
    assert not manager.has_active()
    name, payload = manager.catalog_events.get(timeout=5)
    assert name == "models"
    assert payload["detailed"] == ["background"]
    assert payload["mark_dirty"] is False
