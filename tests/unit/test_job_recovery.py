# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Scoped read-only restart inspection and known-ID reconciliation."""

import socket
from dataclasses import replace

import httpx
import pytest

from scenario.core.api.sdk_adapter import AdapterError, Credentials, SDKAdapter
from scenario.core.jobs.coordinator import JobCoordinator, RecoveryAction, RecoveryError
from scenario.core.jobs.store import (
    JobIntent,
    JobOrigin,
    JobScope,
    JobState,
    JobStore,
    StoreConflict,
    StoreError,
)

SCOPE = JobScope("https://service.example.invalid/v1", "account", "project")
INTENT = JobIntent(
    "request",
    SCOPE,
    JobOrigin("file", "scene", "revision"),
    "model",
    "model",
    "a" * 64,
    "b" * 64,
    "0.1",
)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def deny(*args, **kwargs):
        pytest.fail("Recovery tests must not open sockets")

    monkeypatch.setattr(socket.socket, "connect", deny)
    monkeypatch.setattr(socket.socket, "connect_ex", deny)
    monkeypatch.setattr(socket, "create_connection", deny)


@pytest.fixture
def setup(tmp_path):
    clients = []

    def create(response=None, *, online=True):
        calls = []
        store = JobStore(tmp_path / "jobs.sqlite3", SCOPE)

        def handler(request):
            calls.append(request)
            assert request.method == "GET"
            assert request.url.path == "/v1/jobs/remote"
            assert dict(request.url.params) == {"projectId": "project"}
            if callable(response):
                return response(request)
            return httpx.Response(
                200, json={"job": response or {"jobId": "remote", "status": "success"}}
            )

        adapter = SDKAdapter(
            Credentials("key", "secret"),
            online=lambda: online,
            base_url=SCOPE.service,
            account_id=SCOPE.account_id,
            project_id=SCOPE.project_id,
            transport=httpx.MockTransport(handler),
        )
        clients.append(adapter)
        return JobCoordinator(adapter, store), store, calls

    yield create
    for client in clients:
        client.close()


def advance(store, record, state):
    return store.transition(
        record.intent.request_id,
        expected_revision=record.revision,
        state=state,
        remote_job_id="remote" if state == JobState.REMOTE else None,
    )


def remote_record(store):
    record = advance(store, store.create(INTENT), JobState.SUBMITTING)
    return advance(store, record, JobState.REMOTE)


@pytest.mark.parametrize(
    "states,action",
    [
        ([], RecoveryAction.REVIEW_QUOTE),
        ([JobState.SUBMITTING], RecoveryAction.RECONCILE_UNKNOWN),
        ([JobState.SUBMITTING, JobState.UNCERTAIN], RecoveryAction.RECONCILE_UNKNOWN),
        ([JobState.SUBMITTING, JobState.REMOTE], RecoveryAction.POLL_REMOTE),
        (
            [JobState.SUBMITTING, JobState.REMOTE, JobState.SUCCEEDED],
            RecoveryAction.DOWNLOAD_RESULT,
        ),
        (
            [JobState.SUBMITTING, JobState.REMOTE, JobState.SUCCEEDED, JobState.DOWNLOADING],
            RecoveryAction.REVIEW_DOWNLOAD,
        ),
        (
            [
                JobState.SUBMITTING,
                JobState.REMOTE,
                JobState.SUCCEEDED,
                JobState.DOWNLOADING,
                JobState.DOWNLOAD_FAILED,
            ],
            RecoveryAction.REVIEW_DOWNLOAD,
        ),
        (
            [
                JobState.SUBMITTING,
                JobState.REMOTE,
                JobState.SUCCEEDED,
                JobState.DOWNLOADING,
                JobState.READY,
            ],
            RecoveryAction.REVIEW_APPLICATION,
        ),
        (
            [
                JobState.SUBMITTING,
                JobState.REMOTE,
                JobState.SUCCEEDED,
                JobState.DOWNLOADING,
                JobState.READY,
                JobState.APPLYING,
            ],
            RecoveryAction.REVIEW_APPLICATION,
        ),
        (
            [
                JobState.SUBMITTING,
                JobState.REMOTE,
                JobState.SUCCEEDED,
                JobState.DOWNLOADING,
                JobState.READY,
                JobState.APPLYING,
                JobState.APPLY_FAILED,
            ],
            RecoveryAction.REVIEW_APPLICATION,
        ),
        (
            [
                JobState.SUBMITTING,
                JobState.REMOTE,
                JobState.SUCCEEDED,
                JobState.DOWNLOADING,
                JobState.READY,
                JobState.APPLYING,
                JobState.APPLIED,
            ],
            RecoveryAction.FINISHED,
        ),
        ([JobState.CANCELED], RecoveryAction.FINISHED),
        ([JobState.SUBMITTING, JobState.REMOTE, JobState.FAILED], RecoveryAction.FINISHED),
    ],
)
def test_restart_plan_has_no_network_or_state_changes(setup, states, action):
    _, store, calls = setup()
    record = store.create(INTENT)
    for state in states:
        record = advance(store, record, state)
    reopened, other_store, other_calls = setup()
    plan = reopened.recovery_plan()
    assert len(plan) == 1 and plan[0].record == record and plan[0].action == action
    assert other_store.get(INTENT.request_id) == record
    assert calls == other_calls == []


@pytest.mark.parametrize(
    "status,expected",
    [
        ("pending", JobState.REMOTE),
        ("queued", JobState.REMOTE),
        ("warming-up", JobState.REMOTE),
        ("in-progress", JobState.REMOTE),
        ("finalizing", JobState.REMOTE),
        ("success", JobState.SUCCEEDED),
        ("failure", JobState.FAILED),
        ("canceled", JobState.CANCELED),
    ],
)
def test_polling_known_id_preserves_result_and_origin(setup, status, expected):
    response = {
        "jobId": "remote",
        "status": status,
        "metadata": {"assetIds": ["asset"], "future": True},
    }
    coordinator, store, calls = setup(response)
    current = remote_record(store)
    snapshot = coordinator.refresh_remote(INTENT.request_id, expected_revision=current.revision)
    assert len(calls) == 1
    assert snapshot.record.state == expected
    assert snapshot.record.intent == INTENT and snapshot.record.remote_job_id == "remote"
    assert snapshot.response == response
    snapshot.response["metadata"]["assetIds"].append("changed")
    assert snapshot.response == response
    assert store.get(INTENT.request_id) == snapshot.record


@pytest.mark.parametrize(
    "response",
    [
        {"jobId": "wrong", "status": "success"},
        {"jobId": "remote", "status": "new-unknown"},
        {"jobId": "remote", "status": []},
        {"status": "success"},
    ],
)
def test_untrusted_remote_evidence_never_changes_state(setup, response):
    coordinator, store, calls = setup(response)
    current = remote_record(store)
    with pytest.raises(RecoveryError):
        coordinator.refresh_remote(INTENT.request_id, expected_revision=current.revision)
    assert store.get(INTENT.request_id) == current and len(calls) == 1


def test_lost_id_cannot_be_polled_or_rebound_from_guesses(setup):
    coordinator, store, calls = setup()
    current = advance(store, store.create(INTENT), JobState.SUBMITTING)
    for state in (JobState.SUBMITTING, JobState.UNCERTAIN):
        if state == JobState.UNCERTAIN:
            current = advance(store, current, state)
        with pytest.raises(StoreConflict):
            coordinator.refresh_remote(INTENT.request_id, expected_revision=current.revision)
    assert calls == []


def test_local_cancellation_only_accepts_unclaimed_intent(setup):
    coordinator, store, calls = setup()
    prepared = store.create(INTENT)
    canceled = coordinator.cancel_prepared(INTENT.request_id, expected_revision=prepared.revision)
    assert canceled.state == JobState.CANCELED and calls == []
    with pytest.raises(StoreConflict):
        coordinator.cancel_prepared(INTENT.request_id, expected_revision=prepared.revision)
    other = store.create(replace(INTENT, request_id="other"))
    other = advance(store, other, JobState.SUBMITTING)
    with pytest.raises(StoreConflict):
        coordinator.cancel_prepared("other", expected_revision=other.revision)
    assert calls == []


@pytest.mark.parametrize("failure", ["timeout", 404, 503])
def test_poll_failure_preserves_recoverable_remote_identity(setup, failure):
    def handler(request):
        if failure == "timeout":
            raise httpx.ReadTimeout("secret URL", request=request)
        return httpx.Response(failure, json={"private": True})

    coordinator, store, calls = setup(handler)
    current = remote_record(store)
    with pytest.raises(AdapterError):
        coordinator.refresh_remote(INTENT.request_id, expected_revision=current.revision)
    assert store.get(INTENT.request_id) == current and len(calls) == 1


def test_scope_switch_hides_records_and_inactive_context_does_not_poll(setup, tmp_path):
    coordinator, store, calls = setup()
    record = remote_record(store)
    other = JobStore(tmp_path / "jobs.sqlite3", replace(SCOPE, account_id="other"))
    assert other.records() == ()
    coordinator.deactivate()
    with pytest.raises(RecoveryError):
        coordinator.recovery_plan()
    with pytest.raises(RecoveryError):
        coordinator.refresh_remote(INTENT.request_id, expected_revision=record.revision)
    assert calls == []


def test_newer_state_cannot_be_overwritten_by_stale_poll(setup):
    store = None

    def handler(request):
        current = store.get(INTENT.request_id)
        store.transition(
            INTENT.request_id, expected_revision=current.revision, state=JobState.CANCELED
        )
        return httpx.Response(200, json={"job": {"jobId": "remote", "status": "success"}})

    coordinator, store, _ = setup(handler)
    current = remote_record(store)
    with pytest.raises(StoreConflict):
        coordinator.refresh_remote(INTENT.request_id, expected_revision=current.revision)
    assert store.get(INTENT.request_id).state == JobState.CANCELED


def test_duplicate_success_observation_is_idempotent(setup):
    store = None

    def handler(request):
        current = store.get(INTENT.request_id)
        store.transition(
            INTENT.request_id, expected_revision=current.revision, state=JobState.SUCCEEDED
        )
        return httpx.Response(200, json={"job": {"jobId": "remote", "status": "success"}})

    coordinator, store, _ = setup(handler)
    current = remote_record(store)
    result = coordinator.refresh_remote(INTENT.request_id, expected_revision=current.revision)
    assert result.record == store.get(INTENT.request_id)
    assert result.record.state == JobState.SUCCEEDED


def test_failed_status_commit_does_not_report_terminal_success(setup, monkeypatch):
    coordinator, store, calls = setup()
    current = remote_record(store)

    def fail(*args, **kwargs):
        raise StoreError("fixture disk failure")

    monkeypatch.setattr(store, "transition", fail)
    with pytest.raises(StoreError):
        coordinator.refresh_remote(INTENT.request_id, expected_revision=current.revision)
    assert store.get(INTENT.request_id) == current and len(calls) == 1


def test_offline_recovery_plan_is_local_but_polling_is_forbidden(setup):
    coordinator, store, calls = setup(online=False)
    current = remote_record(store)
    assert coordinator.recovery_plan()[0].action == RecoveryAction.POLL_REMOTE
    with pytest.raises(AdapterError, match="Online access"):
        coordinator.refresh_remote(INTENT.request_id, expected_revision=current.revision)
    assert calls == []
