# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Origin changes invalidate queued quotes before the durable spend boundary."""

import threading
from dataclasses import replace

import httpx
import pytest

from scenario.core.api.sdk_adapter import Credentials, SDKAdapter
from scenario.core.jobs.coordinator import JobCoordinator, QuoteError
from scenario.core.jobs.origins import OriginRevisions
from scenario.core.jobs.store import JobScope, JobState, JobStore
from scenario.core.jobs.workers import JobWorkers


def test_origin_revisions_isolate_scenes_and_file_sessions():
    origins = OriginRevisions()
    first = origins.capture("scene", "object")
    other = origins.capture("other-scene")
    assert origins.current(first) and origins.current(other)
    assert origins.capture("scene", "object") == first
    assert not origins.current(replace(first, revision="wrong"))
    origins.invalidate("scene")
    assert not origins.current(first) and origins.current(other)
    fresh = origins.capture("scene", "object")
    assert fresh != first and origins.current(fresh)
    origins.reset()
    assert not origins.current(fresh) and not origins.current(other)
    assert origins.capture("scene", "object").file_id != first.file_id
    assert not OriginRevisions().current(first)


@pytest.mark.parametrize("change", ["scene", "file", "other-scene"])
def test_queued_origin_rechecked_before_paid_dispatch(tmp_path, change):
    origins = OriginRevisions()
    entered, release = threading.Event(), threading.Event()
    paid = []
    scope = JobScope("https://fixture.invalid/v1", "fixture-account")
    store = JobStore(tmp_path / "jobs.sqlite3", scope)

    def respond(request):
        if request.url.params["dryRun"] == "true":
            return httpx.Response(200, json={"creativeUnitsCost": 1})
        paid.append(request)
        entered.set()
        assert release.wait(5)
        return httpx.Response(200, json={"job": {"jobId": f"remote-{len(paid)}"}})

    with SDKAdapter(
        Credentials("key", "secret"),
        online=lambda: True,
        account_id=scope.account_id,
        base_url=scope.service,
        transport=httpx.MockTransport(respond),
    ) as adapter:
        coordinator = JobCoordinator(adapter, store, origin_guard=origins.guard)
        owner = JobWorkers(coordinator, workers=1)
        origin = origins.capture("scene", "target")

        def prepare():
            quote = adapter.estimate_workflow({"id": "workflow", "inputs": []}, {})
            return coordinator.prepare(quote, origin)

        first, second = prepare(), prepare()

        def submit(prepared):
            return owner.submit(
                prepared, origin=origin, operation="workflow", target_id="workflow", payload={}
            )

        try:
            running = submit(first)
            assert entered.wait(2)
            queued = submit(second)
            if change == "file":
                origins.reset()
            else:
                origins.invalidate(change)
            release.set()
            assert running.result(2).state == JobState.REMOTE
            if change == "other-scene":
                assert queued.result(2).state == JobState.REMOTE
                assert len(paid) == 2
            else:
                with pytest.raises(QuoteError, match="Origin changed"):
                    queued.result(2)
                assert len(paid) == 1
                assert store.get(second.intent.request_id).state == JobState.PREPARED
        finally:
            release.set()
            owner.shutdown()


def test_origin_guard_covers_storage_claim_but_not_http(tmp_path, monkeypatch):
    from contextlib import contextmanager

    origins = OriginRevisions()
    origin = origins.capture("scene")
    held = False
    scope = JobScope("https://fixture.invalid/v1", "fixture-account")
    store = JobStore(tmp_path / "jobs.sqlite3", scope)
    transitions = []

    @contextmanager
    def guard(value):
        nonlocal held
        with origins.guard(value) as current:
            held = True
            try:
                yield current
            finally:
                held = False

    def respond(request):
        assert not held, "Origin invalidation must not wait for HTTP"
        if request.url.params["dryRun"] == "true":
            return httpx.Response(200, json={"creativeUnitsCost": 1})
        return httpx.Response(200, json={"job": {"jobId": "remote"}})

    original = store.transition

    def transition(*args, **kwargs):
        transitions.append((kwargs["state"], held))
        return original(*args, **kwargs)

    monkeypatch.setattr(store, "transition", transition)
    with SDKAdapter(
        Credentials("key", "secret"),
        online=lambda: True,
        account_id=scope.account_id,
        base_url=scope.service,
        transport=httpx.MockTransport(respond),
    ) as adapter:
        coordinator = JobCoordinator(adapter, store, origin_guard=guard)
        quote = adapter.estimate_workflow({"id": "workflow", "inputs": []}, {})
        prepared = coordinator.prepare(quote, origin)
        result = coordinator.submit(
            prepared, origin=origin, operation="workflow", target_id="workflow", payload={}
        )
        assert result.state == JobState.REMOTE
    assert transitions == [(JobState.SUBMITTING, True), (JobState.REMOTE, False)]


def test_invalidation_waits_for_an_existing_origin_claim():
    from concurrent.futures import ThreadPoolExecutor

    origins = OriginRevisions()
    origin = origins.capture("scene")
    started = threading.Event()
    finished = threading.Event()

    def invalidate():
        started.set()
        origins.invalidate("scene")
        finished.set()

    with ThreadPoolExecutor(max_workers=1) as pool:
        with origins.guard(origin) as valid:
            assert valid
            future = pool.submit(invalidate)
            assert started.wait(2)
            assert not finished.is_set()
        future.result(2)
    assert finished.is_set() and not origins.current(origin)
