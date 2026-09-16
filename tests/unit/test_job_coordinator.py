# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise durable spend ordering with the real SDK and no sockets."""

import hashlib
import json
import socket
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Event

import httpx
import pytest

from scenario.core.api.sdk_adapter import AdapterError, Credentials, SDKAdapter
from scenario.core.jobs.coordinator import JobCoordinator, QuoteError, SubmissionUncertain
from scenario.core.jobs.store import JobOrigin, JobScope, JobState, JobStore, StoreError

SCOPE = JobScope("https://service.example.invalid/v1", "account", "project", "team")
ORIGIN = JobOrigin("file", "scene", "revision", "object")
MODEL = {"id": "model", "type": "custom", "inputs": [{"name": "prompt", "type": "string"}]}
QUOTE = b'{"creativeUnitsCost":0.10000000000000001}'


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def deny(*args, **kwargs):
        pytest.fail("Coordinator tests must not open sockets")

    monkeypatch.setattr(socket.socket, "connect", deny)
    monkeypatch.setattr(socket.socket, "connect_ex", deny)
    monkeypatch.setattr(socket, "create_connection", deny)


@pytest.fixture
def setup(tmp_path):
    clients = []

    def create(respond=None, *, operation="model", online=lambda: True, clock=time.monotonic):
        requests = []
        store = JobStore(tmp_path / "jobs.sqlite3", SCOPE)

        def handler(request):
            requests.append(request)
            if request.url.params["dryRun"] == "true":
                return httpx.Response(200, content=QUOTE)
            # Reopen the actual database from the transport boundary. A cached
            # object is not proof that the submission claim committed.
            records = JobStore(tmp_path / "jobs.sqlite3", SCOPE).records()
            assert any(record.state == JobState.SUBMITTING for record in records)
            return (
                respond(request)
                if respond
                else httpx.Response(200, json={"job": {"jobId": "remote"}})
            )

        adapter = SDKAdapter(
            Credentials("selected", "secret"),
            online=online,
            base_url=SCOPE.service,
            account_id=SCOPE.account_id,
            project_id=SCOPE.project_id,
            team_id=SCOPE.team_id,
            transport=httpx.MockTransport(handler),
        )
        clients.append(adapter)
        coordinator = JobCoordinator(adapter, store, clock=clock)
        estimate = (
            adapter.estimate_model(MODEL, {"prompt": "fixture"})
            if operation == "model"
            else adapter.estimate_workflow(
                {"id": "workflow", "inputs": MODEL["inputs"]}, {"prompt": "fixture"}
            )
        )
        prepared = coordinator.prepare(estimate, ORIGIN)
        return coordinator, store, prepared, requests, adapter

    yield create
    for client in clients:
        client.close()


def submit(coordinator, prepared, **overrides):
    current = {
        "origin": ORIGIN,
        "operation": prepared.intent.operation,
        "target_id": prepared.intent.target_id,
        "payload": prepared.estimate.payload,
    }
    current.update(overrides)
    return coordinator.submit(prepared, **current)


@pytest.mark.parametrize("operation", ["model", "workflow"])
def test_exact_intent_commits_before_single_scoped_submission(setup, operation):
    coordinator, store, prepared, requests, adapter = setup(operation=operation)
    assert len(requests) == 1
    assert store.get(prepared.intent.request_id).state == JobState.PREPARED
    result = submit(coordinator, prepared)
    assert len(requests) == 2
    assert dict(requests[-1].url.params) == {"dryRun": "false", "projectId": "project"}
    assert requests[-1].url.path == (
        "/v1/generate/custom/model" if operation == "model" else "/v1/workflows/workflow/run"
    )
    assert json.loads(requests[-1].content) == {"prompt": "fixture"}
    assert result.state == JobState.REMOTE and result.remote_job_id == "remote"
    assert (
        result.intent.payload_sha256 == hashlib.sha256(prepared.estimate.payload_json).hexdigest()
    )
    assert result.intent.quote_sha256 == hashlib.sha256(QUOTE).hexdigest()
    assert result.intent.quote_cost == "0.10000000000000001"
    assert result.intent.origin == ORIGIN
    assert store.get(result.intent.request_id) == result
    assert not adapter.owns_estimate(prepared.estimate)
    with pytest.raises(ValueError):
        submit(coordinator, prepared)
    assert len(requests) == 2


@pytest.mark.parametrize(
    "changed",
    [
        {"payload": {"prompt": "changed"}},
        {"operation": "other"},
        {"target_id": "other"},
        {"origin": replace(ORIGIN, file_id="other")},
        {"origin": replace(ORIGIN, scene_id="other")},
        {"origin": replace(ORIGIN, target_id="other")},
        {"origin": replace(ORIGIN, revision="other")},
    ],
)
def test_changed_payload_target_or_origin_cannot_claim_or_spend(setup, changed):
    coordinator, store, prepared, requests, _ = setup()
    with pytest.raises(QuoteError):
        submit(coordinator, prepared, **changed)
    assert len(requests) == 1
    assert store.get(prepared.intent.request_id).state == JobState.PREPARED


@pytest.mark.parametrize("point", ["prepare", "submit"])
def test_expiry_is_measured_from_estimate_issuance_not_preparation(setup, point):
    offset = [0]
    coordinator, store, prepared, requests, _ = setup(clock=lambda: time.monotonic() + offset[0])
    offset[0] = 121
    with pytest.raises(QuoteError, match="expired"):
        if point == "prepare":
            coordinator.prepare(prepared.estimate, ORIGIN)
        else:
            submit(coordinator, prepared)
    assert len(requests) == 1 and len(store.records()) == 1


@pytest.mark.parametrize("failure", ["timeout", "malformed", "no-id", 307, 429, 503])
def test_failed_or_lost_receipt_is_durable_uncertainty_not_replay(setup, failure):
    def respond(request):
        if failure == "timeout":
            raise httpx.ReadTimeout("private signed URL", request=request)
        if failure == "malformed":
            return httpx.Response(200, content=b"not JSON")
        if failure == "no-id":
            return httpx.Response(200, json={"job": {"status": "success"}})
        return httpx.Response(
            failure,
            json={"error": "private response"},
            headers={"Location": "https://private.invalid/secret", "Retry-After": "0"},
        )

    coordinator, store, prepared, requests, _ = setup(respond)
    with pytest.raises(SubmissionUncertain) as error:
        submit(coordinator, prepared)
    assert "private" not in str(error.value)
    assert store.get(prepared.intent.request_id).state == JobState.UNCERTAIN
    with pytest.raises(ValueError):
        submit(coordinator, prepared)
    assert len(requests) == 2


def test_failed_claim_never_reaches_paid_transport(setup, monkeypatch):
    coordinator, store, prepared, requests, _ = setup()

    def fail(*args, **kwargs):
        raise StoreError("fixture persistence failure")

    monkeypatch.setattr(store, "transition", fail)
    with pytest.raises(StoreError):
        submit(coordinator, prepared)
    assert len(requests) == 1
    assert store.get(prepared.intent.request_id).state == JobState.PREPARED


def test_failed_receipt_commit_keeps_inflight_record_and_consumed_quote(setup, monkeypatch):
    coordinator, store, prepared, requests, _ = setup()
    transition = store.transition

    def fail_receipt(*args, **kwargs):
        if kwargs["state"] == JobState.REMOTE:
            raise StoreError("fixture failed receipt commit")
        return transition(*args, **kwargs)

    monkeypatch.setattr(store, "transition", fail_receipt)
    with pytest.raises(StoreError):
        submit(coordinator, prepared)
    assert store.get(prepared.intent.request_id).state == JobState.SUBMITTING
    with pytest.raises(ValueError):
        submit(coordinator, prepared)
    assert len(requests) == 2


@pytest.mark.parametrize("kind", ["estimate", "prepared"])
def test_copied_or_modified_tokens_are_not_issued_tokens(setup, kind):
    coordinator, store, prepared, requests, _ = setup()
    with pytest.raises(QuoteError):
        if kind == "estimate":
            coordinator.prepare(replace(prepared.estimate, payload_json=b"{}"), ORIGIN)
        else:
            submit(coordinator, replace(prepared))
    assert len(requests) == 1


def test_same_quote_cannot_spend_twice_through_different_prepared_requests(setup):
    coordinator, store, prepared, requests, adapter = setup()
    other = JobCoordinator(adapter, store)
    other_prepared = other.prepare(prepared.estimate, ORIGIN)
    with ThreadPoolExecutor(max_workers=2) as workers:

        def attempt(pair):
            try:
                return submit(*pair)
            except ValueError:
                return None

        results = list(workers.map(attempt, [(coordinator, prepared), (other, other_prepared)]))
    assert sum(result is not None for result in results) == 1
    assert len(requests) == 2


def test_deactivation_rejects_queued_work_and_late_receipt_keeps_original_origin(setup):
    entered, release = Event(), Event()

    def respond(request):
        entered.set()
        assert release.wait(timeout=5)
        return httpx.Response(200, json={"job": {"jobId": "late-remote"}})

    coordinator, store, prepared, requests, _ = setup(respond)
    with ThreadPoolExecutor(max_workers=1) as worker:
        result = worker.submit(submit, coordinator, prepared)
        assert entered.wait(timeout=5)
        coordinator.deactivate()
        release.set()
        record = result.result(timeout=5)
    assert record.intent.origin == ORIGIN and record.intent.scope == SCOPE
    assert record.remote_job_id == "late-remote"
    with pytest.raises(ValueError):
        submit(coordinator, prepared)
    assert len(requests) == 2


def test_offline_before_claim_preserves_prepared_state(setup):
    online = [True]
    coordinator, store, prepared, requests, _ = setup(online=lambda: online[0])
    online[0] = False
    with pytest.raises(AdapterError, match="Online access"):
        submit(coordinator, prepared)
    assert len(requests) == 1
    assert store.get(prepared.intent.request_id).state == JobState.PREPARED


@pytest.mark.parametrize(
    "change",
    [
        {"account_id": "other"},
        {"project_id": None},
        {"team_id": "other"},
        {"service": "https://other.invalid/v1"},
    ],
)
def test_connection_and_store_scope_must_match(setup, tmp_path, change):
    _, _, _, requests, adapter = setup()
    other = JobStore(tmp_path / "other.sqlite3", replace(SCOPE, **change))
    with pytest.raises(ValueError, match="scopes differ"):
        JobCoordinator(adapter, other)
    assert len(requests) == 1


def test_coordinator_requires_explicit_account_identity_before_network(tmp_path):
    def unexpected(request):
        pytest.fail("Missing account identity must fail before network access")

    store = JobStore(tmp_path / "jobs.sqlite3", SCOPE)
    with SDKAdapter(
        Credentials("selected", "secret"),
        online=lambda: True,
        base_url=SCOPE.service,
        project_id=SCOPE.project_id,
        team_id=SCOPE.team_id,
        transport=httpx.MockTransport(unexpected),
    ) as adapter:
        with pytest.raises(ValueError, match="account_id"):
            JobCoordinator(adapter, store)
    assert store.records() == ()


@pytest.mark.parametrize("operation", ["model", "workflow"])
@pytest.mark.parametrize(
    "remote_id",
    ["r" * 257, "remote\u00a0id", "remote\u2003id"],
    ids=["too-long", "no-break-space", "em-space"],
)
def test_unpersistable_receipt_identity_is_uncertain_without_replay(
    setup, tmp_path, operation, remote_id
):
    def respond(request):
        return httpx.Response(200, json={"job": {"jobId": remote_id}})

    coordinator, store, prepared, requests, adapter = setup(respond, operation=operation)
    with pytest.raises(SubmissionUncertain) as error:
        submit(coordinator, prepared)
    assert remote_id not in str(error.value)
    record = JobStore(tmp_path / "jobs.sqlite3", SCOPE).get(prepared.intent.request_id)
    assert record.state == JobState.UNCERTAIN and record.remote_job_id is None
    assert not adapter.owns_estimate(prepared.estimate)
    with pytest.raises(ValueError):
        submit(coordinator, prepared)
    assert len(requests) == 2


@pytest.mark.parametrize("operation", ["model", "workflow"])
def test_receipt_identity_limit_is_accepted(setup, operation):
    remote_id = "r" * 256
    coordinator, store, prepared, requests, _ = setup(
        lambda request: httpx.Response(200, json={"job": {"jobId": remote_id}}),
        operation=operation,
    )
    record = submit(coordinator, prepared)
    assert record.state == JobState.REMOTE and record.remote_job_id == remote_id
    assert store.get(prepared.intent.request_id) == record and len(requests) == 2


def test_malformed_receipt_persistence_failure_stays_unreplayable(setup, monkeypatch):
    coordinator, store, prepared, requests, adapter = setup(
        lambda request: httpx.Response(200, json={"job": {"jobId": "r" * 257}})
    )
    transition = store.transition

    def fail_uncertainty(*args, **kwargs):
        if kwargs["state"] == JobState.UNCERTAIN:
            raise StoreError("fixture failed uncertainty commit")
        return transition(*args, **kwargs)

    monkeypatch.setattr(store, "transition", fail_uncertainty)
    with pytest.raises(StoreError, match="uncertainty commit"):
        submit(coordinator, prepared)
    assert store.get(prepared.intent.request_id).state == JobState.SUBMITTING
    assert not adapter.owns_estimate(prepared.estimate)
    with pytest.raises(ValueError):
        submit(coordinator, prepared)
    assert len(requests) == 2
