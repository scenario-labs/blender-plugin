# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Cancel through the actual SDK without trusting acknowledgements or replaying."""

import json
import socket
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import httpx
import pytest

from scenario.core.api.sdk_adapter import AdapterError, Credentials, SDKAdapter
from scenario.core.jobs.coordinator import (
    CancellationUncertain,
    JobCoordinator,
    RecoveryAction,
    RecoveryError,
)
from scenario.core.jobs.store import (
    JobIntent,
    JobOrigin,
    JobScope,
    JobState,
    JobStore,
    StoreConflict,
    StoreError,
)
from scenario.core.jobs.workers import JobWorkers, WorkerError

SCOPE = JobScope("https://service.example.invalid/v1", "account", "project", "team")
INTENT = JobIntent(
    "request",
    SCOPE,
    JobOrigin("file", "scene", "revision"),
    "model",
    "model",
    "a" * 64,
    "b" * 64,
    "1",
)


def response(status="in-progress", **fields):
    return {"jobId": "remote", "jobType": "inference", "status": status, **fields}


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def deny(*args, **kwargs):
        pytest.fail("Cancellation contracts must not access the network")

    monkeypatch.setattr(socket.socket, "connect", deny)
    monkeypatch.setattr(socket.socket, "connect_ex", deny)
    monkeypatch.setattr(socket, "create_connection", deny)


@pytest.fixture
def setup(tmp_path):
    adapters = []

    def create(replies=None, *, intent=INTENT, online=None, state=JobState.REMOTE):
        replies = list(
            replies
            if replies is not None
            else [response(), response("canceled"), response("success")]
        )
        calls = []
        store = JobStore(tmp_path / "jobs.sqlite3", SCOPE)
        record = store.create(intent)
        for next_state in (JobState.SUBMITTING, state):
            if state == JobState.PREPARED:
                break
            record = store.transition(
                intent.request_id,
                expected_revision=record.revision,
                state=next_state,
                remote_job_id="remote" if next_state == JobState.REMOTE else None,
            )

        def handler(request):
            calls.append(request)
            assert request.url.path == "/v1/jobs/remote" + (
                "/action" if request.method == "POST" else ""
            )
            assert dict(request.url.params) == {"projectId": "project"}
            assert request.headers["Authorization"] == Credentials("key", "secret").authorization()
            if request.method == "POST":
                assert json.loads(request.content) == {"action": "cancel"}
            value = replies.pop(0)
            if callable(value):
                return value(request)
            if isinstance(value, httpx.Response):
                return value
            return httpx.Response(200, json={"job": value})

        adapter = SDKAdapter(
            Credentials("key", "secret"),
            online=online or (lambda: True),
            base_url=SCOPE.service,
            account_id=SCOPE.account_id,
            project_id=SCOPE.project_id,
            team_id=SCOPE.team_id,
            transport=httpx.MockTransport(handler),
        )
        adapters.append(adapter)
        coordinator = JobCoordinator(adapter, store)
        return coordinator, store, calls, record, adapter

    yield create
    for adapter in adapters:
        adapter.close()


@pytest.mark.parametrize("ack", ["in-progress", "canceled", "success", "future-status"])
@pytest.mark.parametrize(
    "observed,expected",
    [
        ("in-progress", JobState.REMOTE),
        ("canceled", JobState.CANCELED),
        ("success", JobState.SUCCEEDED),
        ("failure", JobState.FAILED),
    ],
)
def test_only_retrieval_decides_state_and_restart_does_not_replay(
    setup, ack, observed, expected, tmp_path
):
    coordinator, store, calls, record, adapter = setup(
        [response(), response(ack), response(observed)]
    )
    snapshot = coordinator.cancel_remote("request", expected_revision=record.revision)
    assert [r.method for r in calls] == ["GET", "POST", "GET"]
    assert snapshot.record.state == expected
    assert snapshot.response == response(observed)
    assert snapshot.record.intent == INTENT and snapshot.record.remote_job_id == "remote"
    reopened = JobStore(tmp_path / "jobs.sqlite3", SCOPE)
    fresh = JobCoordinator(adapter, reopened)
    assert fresh.recovery_plan()[0].record == snapshot.record
    assert len(calls) == 3
    if expected == JobState.REMOTE:
        assert fresh.recovery_plan()[0].action == RecoveryAction.POLL_REMOTE


@pytest.mark.parametrize("status", ["success", "failure", "canceled"])
def test_preflight_completion_avoids_cancel(setup, status):
    coordinator, store, calls, record, _ = setup([response(status)])
    result = coordinator.cancel_remote("request", expected_revision=record.revision)
    assert result.record.state != JobState.REMOTE and len(calls) == 1
    assert store.get("request") == result.record


@pytest.mark.parametrize("kind", [None, "workflow", "training", [], "Inference"])
def test_only_verified_inference_is_cancelable(setup, kind):
    coordinator, store, calls, record, _ = setup([response(jobType=kind)])
    with pytest.raises(RecoveryError, match="verified inference"):
        coordinator.cancel_remote("request", expected_revision=record.revision)
    assert store.get("request") == record and len(calls) == 1


def test_workflows_and_lost_id_never_send_cancellation(setup):
    coordinator, _, calls, record, _ = setup(intent=replace(INTENT, operation="workflow"))
    with pytest.raises(RecoveryError, match="workflow"):
        coordinator.cancel_remote("request", expected_revision=record.revision)
    assert calls == []


@pytest.mark.parametrize("state", [JobState.PREPARED, JobState.UNCERTAIN])
def test_no_remote_id_cannot_be_canceled(setup, state):
    coordinator, _, calls, record, _ = setup(state=state)
    with pytest.raises(StoreConflict):
        coordinator.cancel_remote("request", expected_revision=record.revision)
    assert calls == []


@pytest.mark.parametrize("phase", ["preflight", "action", "observation"])
@pytest.mark.parametrize("failure", ["timeout", 429, 503, "malformed"])
def test_failure_never_retries_and_keeps_known_id_recoverable(setup, phase, failure):
    def fail(request):
        if failure == "timeout":
            raise httpx.ReadTimeout("private signed-url secret", request=request)
        if failure == "malformed":
            return httpx.Response(200, json={"wrong": "private secret"})
        return httpx.Response(failure, json={"secret": "private"}, headers={"Retry-After": "0"})

    replies = {
        "preflight": [fail],
        "action": [response(), fail],
        "observation": [response(), response(), fail],
    }[phase]
    coordinator, store, calls, record, _ = setup(replies)
    with pytest.raises(AdapterError if phase == "preflight" else CancellationUncertain) as error:
        coordinator.cancel_remote("request", expected_revision=record.revision)
    assert "private" not in str(error.value) and "secret" not in str(error.value)
    assert store.get("request") == record
    assert len(calls) == len(replies)
    assert coordinator.recovery_plan()[0].action == RecoveryAction.POLL_REMOTE


def test_post_action_invalid_identity_never_updates_local_state(setup):
    coordinator, store, calls, record, _ = setup(
        [response(), response(), response("canceled", jobId="other")]
    )
    with pytest.raises(RecoveryError, match="identity"):
        coordinator.cancel_remote("request", expected_revision=record.revision)
    assert store.get("request") == record and len(calls) == 3


def test_offline_is_checked_again_before_action(setup):
    online = True

    def preflight(request):
        nonlocal online
        online = False
        return httpx.Response(200, json={"job": response()})

    coordinator, store, calls, record, _ = setup([preflight], online=lambda: online)
    with pytest.raises(CancellationUncertain):
        coordinator.cancel_remote("request", expected_revision=record.revision)
    assert len(calls) == 1 and store.get("request") == record


def test_deactivation_during_preflight_prevents_action(setup):
    def preflight(request):
        coordinator.deactivate()
        return httpx.Response(200, json={"job": response()})

    coordinator, store, calls, record, _ = setup([preflight])
    with pytest.raises(RecoveryError, match="inactive"):
        coordinator.cancel_remote("request", expected_revision=record.revision)
    assert len(calls) == 1 and store.get("request") == record


def test_deactivation_after_action_keeps_late_evidence_in_original_scope(setup, tmp_path):
    def ack(request):
        coordinator.deactivate()
        return httpx.Response(200, json={"job": response("canceled")})

    coordinator, store, calls, record, _ = setup([response(), ack, response("success")])
    result = coordinator.cancel_remote("request", expected_revision=record.revision)
    assert result.record.state == JobState.SUCCEEDED and len(calls) == 3
    assert JobStore(tmp_path / "jobs.sqlite3", replace(SCOPE, account_id="other")).records() == ()
    assert store.get("request").intent == INTENT


def test_write_failure_is_visible_without_false_cancellation(setup, monkeypatch):
    coordinator, store, calls, record, _ = setup(
        [response(), response("canceled"), response("canceled")]
    )

    def fail(*args, **kwargs):
        raise StoreError("fixture disk failure")

    monkeypatch.setattr(store, "transition", fail)
    with pytest.raises(StoreError):
        coordinator.cancel_remote("request", expected_revision=record.revision)
    assert store.get("request") == record and len(calls) == 3


def test_competing_terminal_result_cannot_be_overwritten(setup):
    def observed(request):
        store.transition("request", expected_revision=record.revision, state=JobState.SUCCEEDED)
        return httpx.Response(200, json={"job": response("canceled")})

    coordinator, store, calls, record, _ = setup([response(), response(), observed])
    with pytest.raises(StoreConflict):
        coordinator.cancel_remote("request", expected_revision=record.revision)
    assert store.get("request").state == JobState.SUCCEEDED and len(calls) == 3


def test_concurrent_requests_share_inflight_exclusion_and_worker_shutdown(setup):
    entered, release = threading.Event(), threading.Event()

    def ack(request):
        entered.set()
        assert release.wait(5)
        return httpx.Response(200, json={"job": response("canceled")})

    coordinator, store, calls, record, _ = setup([response(), ack, response("canceled")])
    owner = JobWorkers(coordinator, workers=1)
    task = owner.cancel_remote("request", expected_revision=record.revision)
    try:
        assert entered.wait(2)
        with pytest.raises(StoreConflict, match="already"):
            coordinator.cancel_remote("request", expected_revision=record.revision)
        with ThreadPoolExecutor() as pool:
            shutdown = pool.submit(owner.shutdown)
            release.set()
            assert task.result(3).record.state == JobState.CANCELED
            shutdown.result(3)
        assert len(calls) == 3 and store.get("request").state == JobState.CANCELED
        with pytest.raises(WorkerError):
            owner.cancel_remote("request", expected_revision=record.revision)
    finally:
        release.set()
        owner.shutdown()


@pytest.mark.parametrize("ack", [{}, {"jobId": "other"}])
def test_wrong_acknowledgement_identity_stays_uncertain(setup, ack):
    coordinator, store, calls, record, _ = setup([response(), ack])
    with pytest.raises(CancellationUncertain):
        coordinator.cancel_remote("request", expected_revision=record.revision)
    assert store.get("request") == record and len(calls) == 2


@pytest.mark.parametrize("reason", ["offline", "inactive", "stale"])
def test_ineligible_request_never_reaches_service(setup, reason):
    coordinator, store, calls, record, _ = setup(online=lambda: reason != "offline")
    if reason == "inactive":
        coordinator.deactivate()
    expected_revision = record.revision - 1 if reason == "stale" else record.revision
    with pytest.raises((AdapterError, RecoveryError, StoreConflict)):
        coordinator.cancel_remote("request", expected_revision=expected_revision)
    assert store.get("request") == record and calls == []
