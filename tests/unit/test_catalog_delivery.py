# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Catalog choices and each schema become available before slow warmup completes."""

import threading

from scenario.core.api.errors import ScenarioError
from scenario.core.jobs.manager import JobManager


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
        assert available[1][1]["detailed"] == ["first"]
        assert available[1][1]["mark_dirty"] is False
        assert all(payload["catalog"] is context for _, payload in available)
        assert manager.has_active()
        manager.fetch_models(context, ["selected"])
        name, selected = manager.catalog_events.get(timeout=5)
        assert name == "models" and selected["detailed"] == ["selected"]
        assert selected["catalog"] is context
        assert not release.is_set()
    finally:
        release.set()
        manager.join(5)
    assert not manager.has_active()
    later = manager.drain_catalog()
    assert [name for name, _ in later] == ["models", "catalog"]
    assert later[0][1]["detailed"] == ["last"]
    assert later[1][1]["detailed"] == ["first", "last"]
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
