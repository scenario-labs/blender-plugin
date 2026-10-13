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
from scenario.core.jobs import failures, progress
from scenario.core.jobs.coordinator import (
    DuplicateRequestError,
    JobCoordinator,
    QuoteError,
    RecoveryError,
    SubmissionUncertain,
)
from scenario.core.jobs.store import (
    JobOrigin,
    JobScope,
    JobState,
    JobStore,
    StoreConflict,
    StoreError,
)

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
            if request.url.params.get("dryRun") == "true":
                return httpx.Response(200, content=QUOTE)
            if request.method == "GET" and respond:
                return respond(request)
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
        estimate = None
        if operation == "model":
            estimate = adapter.estimate_model(MODEL, {"prompt": "fixture"})
        elif operation == "workflow":
            estimate = adapter.estimate_workflow(
                {"id": "workflow", "inputs": MODEL["inputs"]}, {"prompt": "fixture"}
            )
        if operation in {"prompt", "translate"}:
            # The origin-bound command must not perform model/workflow discovery.
            parameters = {"prompt": "fixture"}
            if operation == "prompt":
                parameters["mode"] = "contextual"
            quote = getattr(coordinator, f"quote_{operation}")(parameters, origin=ORIGIN)
            prepared = coordinator.prepare_quote(quote)
        else:
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


def lost_submission(request):
    raise httpx.ReadTimeout("private fixture timeout", request=request)


def identical(coordinator, adapter, operation):
    """Quote and prepare the same request again; a prompt quote is origin-bound."""
    if operation == "model":
        return coordinator.prepare(adapter.estimate_model(MODEL, {"prompt": "fixture"}), ORIGIN)
    if operation == "workflow":
        estimate = adapter.estimate_workflow(
            {"id": "workflow", "inputs": MODEL["inputs"]}, {"prompt": "fixture"}
        )
        return coordinator.prepare(estimate, ORIGIN)
    quote = coordinator.quote_prompt({"prompt": "fixture", "mode": "contextual"}, origin=ORIGIN)
    return coordinator.prepare_quote(quote)


@pytest.mark.parametrize("operation", ["model", "workflow", "prompt"])
def test_an_unconfirmed_request_refuses_an_identical_one_until_reviewed(setup, operation):
    coordinator, store, prepared, requests, adapter = setup(lost_submission, operation=operation)
    with pytest.raises(SubmissionUncertain):
        submit(coordinator, prepared)
    earlier = store.get(prepared.intent.request_id)
    assert earlier.state == JobState.UNCERTAIN
    with pytest.raises(DuplicateRequestError) as refused:
        identical(coordinator, adapter, operation)
    assert refused.value.request_id == earlier.intent.request_id
    assert earlier.intent.request_id[:8] in str(refused.value)
    assert len(store.records()) == 1
    sent = len(requests)
    coordinator.mark_unconfirmed_reviewed(
        earlier.intent.request_id, expected_revision=earlier.revision
    )
    again = identical(coordinator, adapter, operation)
    assert store.get(again.intent.request_id).state == JobState.PREPARED
    assert len(requests) == sent + 1  # one more free dry run, nothing paid
    # The mark lasts for this session only; a new coordinator refuses again.
    fresh = JobCoordinator(adapter, store)
    with pytest.raises(DuplicateRequestError):
        identical(fresh, adapter, operation)


def test_a_claim_is_refused_when_an_identical_request_became_unconfirmed(setup):
    coordinator, store, first, requests, adapter = setup(lost_submission)
    second = identical(coordinator, adapter, "model")
    with pytest.raises(SubmissionUncertain):
        submit(coordinator, first)
    paid = [request for request in requests if request.url.params.get("dryRun") != "true"]
    with pytest.raises(DuplicateRequestError):
        submit(coordinator, second)
    assert [r for r in requests if r.url.params.get("dryRun") != "true"] == paid
    assert store.get(second.intent.request_id).state == JobState.PREPARED


def test_other_payloads_scopes_and_confirmed_jobs_do_not_block(setup, tmp_path):
    coordinator, store, prepared, _, adapter = setup(lost_submission)
    with pytest.raises(SubmissionUncertain):
        submit(coordinator, prepared)
    other = adapter.estimate_model(MODEL, {"prompt": "another"})
    assert coordinator.prepare(other, ORIGIN).intent.payload_sha256 != (
        prepared.intent.payload_sha256
    )
    # Another credential scope keeps its own records, even in the same database.
    elsewhere = replace(SCOPE, project_id="other-project")
    other_adapter = SDKAdapter(
        Credentials("selected", "secret"),
        online=lambda: True,
        base_url=elsewhere.service,
        account_id=elsewhere.account_id,
        project_id=elsewhere.project_id,
        team_id=elsewhere.team_id,
        transport=httpx.MockTransport(lambda r: httpx.Response(200, content=QUOTE)),
    )
    try:
        other_store = JobStore(tmp_path / "jobs.sqlite3", elsewhere)
        other_coordinator = JobCoordinator(other_adapter, other_store)
        estimate = other_adapter.estimate_model(MODEL, {"prompt": "fixture"})
        assert other_coordinator.prepare(estimate, ORIGIN).intent.payload_sha256 == (
            prepared.intent.payload_sha256
        )
    finally:
        other_adapter.close()


def test_a_confirmed_remote_job_does_not_block_an_identical_request(setup):
    coordinator, store, prepared, _, adapter = setup()
    submit(coordinator, prepared)
    assert store.get(prepared.intent.request_id).state == JobState.REMOTE
    assert identical(coordinator, adapter, "model").intent.payload_sha256 == (
        prepared.intent.payload_sha256
    )


def test_only_a_current_unconfirmed_record_can_be_marked_reviewed(setup):
    coordinator, store, prepared, _, adapter = setup()
    with pytest.raises(StoreConflict):  # prepared, not unconfirmed
        coordinator.mark_unconfirmed_reviewed(
            prepared.intent.request_id,
            expected_revision=store.get(prepared.intent.request_id).revision,
        )
    submit(coordinator, prepared)
    record = store.get(prepared.intent.request_id)
    with pytest.raises(StoreConflict):  # confirmed remote job
        coordinator.mark_unconfirmed_reviewed(
            record.intent.request_id, expected_revision=record.revision
        )


def test_a_stale_revision_cannot_mark_a_record_reviewed(setup):
    coordinator, store, prepared, _, _ = setup(lost_submission)
    stale = store.get(prepared.intent.request_id).revision
    with pytest.raises(SubmissionUncertain):
        submit(coordinator, prepared)
    with pytest.raises(StoreConflict):
        coordinator.mark_unconfirmed_reviewed(prepared.intent.request_id, expected_revision=stale)


@pytest.mark.parametrize("operation", ["model", "workflow", "prompt", "translate"])
def test_exact_intent_commits_before_single_scoped_submission(setup, operation):
    coordinator, store, prepared, requests, adapter = setup(operation=operation)
    assert len(requests) == 1
    assert store.get(prepared.intent.request_id).state == JobState.PREPARED
    result = submit(coordinator, prepared)
    assert len(requests) == 2
    assert dict(requests[-1].url.params) == {"projectId": "project"}
    assert (
        requests[-1].url.path
        == {
            "model": "/v1/generate/custom/model",
            "workflow": "/v1/workflows/workflow/run",
            "prompt": "/v1/generate/prompt",
            "translate": "/v1/generate/translate",
        }[operation]
    )
    assert json.loads(requests[-1].content) == {
        "prompt": "fixture",
        **({"mode": "contextual", "numResults": 1} if operation == "prompt" else {}),
    }
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
@pytest.mark.parametrize("operation", ["model", "prompt", "translate"])
def test_changed_payload_target_or_origin_cannot_claim_or_spend(setup, changed, operation):
    coordinator, store, prepared, requests, _ = setup(operation=operation)
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
@pytest.mark.parametrize("operation", ["model", "prompt", "translate"])
def test_failed_or_lost_receipt_is_durable_uncertainty_not_replay(setup, failure, operation):
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

    coordinator, store, prepared, requests, _ = setup(respond, operation=operation)
    with pytest.raises(SubmissionUncertain) as error:
        submit(coordinator, prepared)
    assert "private" not in str(error.value)
    assert store.get(prepared.intent.request_id).state == JobState.UNCERTAIN
    with pytest.raises(ValueError):
        submit(coordinator, prepared)
    assert len(requests) == 2


@pytest.mark.parametrize("operation", ["model", "prompt", "translate"])
def test_failed_claim_never_reaches_paid_transport(setup, monkeypatch, operation):
    coordinator, store, prepared, requests, _ = setup(operation=operation)

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


@pytest.mark.parametrize("operation", ["model", "workflow", "prompt", "translate"])
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


@pytest.mark.parametrize("operation", ["model", "workflow", "prompt", "translate"])
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


def test_active_refresh_yields_progress_without_changing_or_persisting_the_record(setup, tmp_path):
    def respond(request):
        return httpx.Response(
            200,
            json={
                "job": {
                    "jobId": "remote",
                    "jobType": "custom",
                    "status": "in-progress",
                    "progress": 0.4217,
                }
            },
        )

    coordinator, store, prepared, requests, _ = setup(respond)
    remote = submit(coordinator, prepared)
    snapshot = coordinator.refresh_remote(
        remote.intent.request_id, expected_revision=remote.revision
    )
    assert snapshot.record == remote == store.get(remote.intent.request_id)
    assert (requests[-1].method, requests[-1].url.path) == ("GET", "/v1/jobs/remote")
    reading = progress.observe(snapshot)
    assert (reading.status, reading.fraction, reading.percent) == ("in-progress", 0.4217, 42)
    assert (reading.remote_job_id, reading.revision) == ("remote", remote.revision)
    # The reading stays in memory; no database file holds the response or fraction.
    saved = b"".join(path.read_bytes() for path in tmp_path.glob("jobs.sqlite3*"))
    assert b"0.4217" not in saved and b"in-progress" not in saved


def test_failed_refresh_commits_the_state_and_reads_the_reason_without_persisting_it(
    setup, tmp_path
):
    message = "An internal error occurred. Please contact support and provide this id: error_Zx81"
    hint = "Try a mesh under 30,000 faces."

    def respond(request):
        return httpx.Response(
            200,
            json={
                "job": {
                    "jobId": "remote",
                    "jobType": "custom",
                    "status": "failure",
                    "progress": 0.1,
                    "metadata": {"input": {"modelId": "model"}, "error": message, "hint": hint},
                }
            },
        )

    coordinator, store, prepared, requests, _ = setup(respond)
    remote = submit(coordinator, prepared)
    snapshot = coordinator.refresh_remote(
        remote.intent.request_id, expected_revision=remote.revision
    )
    saved = store.get(remote.intent.request_id)
    assert snapshot.record == saved and saved.state == JobState.FAILED
    assert (requests[-1].method, requests[-1].url.path) == ("GET", "/v1/jobs/remote")
    assert failures.observe(snapshot) == failures.RemoteFailure(
        "remote", saved.revision, f"{message}. {hint}"
    )
    # Display only: the database keeps neither the message nor its support id.
    raw = b"".join(path.read_bytes() for path in tmp_path.glob("jobs.sqlite3*"))
    assert b"internal error" not in raw and b"error_Zx81" not in raw and b"faces" not in raw


def test_prompt_restart_observes_known_id_without_resubmission_or_cancellation(setup, tmp_path):
    def respond(request):
        return httpx.Response(
            200,
            json={"job": {"jobId": "remote", "jobType": "generate-prompt", "status": "success"}},
        )

    coordinator, store, prepared, requests, adapter = setup(respond, operation="prompt")
    remote = submit(coordinator, prepared)
    reopened_store = JobStore(tmp_path / "jobs.sqlite3", SCOPE)
    restarted = JobCoordinator(adapter, reopened_store)
    with pytest.raises(RecoveryError, match="Only model-job"):
        restarted.cancel_remote(remote.intent.request_id, expected_revision=remote.revision)
    assert len(requests) == 2
    snapshot = restarted.refresh_remote(remote.intent.request_id, expected_revision=remote.revision)
    assert snapshot.record.state == JobState.SUCCEEDED
    assert snapshot.record.intent == prepared.intent
    assert requests[-1].method == "GET"
    assert requests[-1].url.path == "/v1/jobs/remote"
    assert len(requests) == 3


def organization_owner(tmp_path):
    from organization_service import URL, OrganizationService, asset

    service = OrganizationService(assets=[asset("asset-a"), asset("asset-b")])
    adapter = service.adapter()
    scope = JobScope(URL, "account", "project")
    coordinator = JobCoordinator(adapter, JobStore(tmp_path / "organization.sqlite3", scope))
    return service, adapter, coordinator


def test_organization_rejects_other_scope_and_issued_snapshots_apply_once(tmp_path):
    from dataclasses import replace

    from scenario.core.jobs.organization import (
        OrganizationError,
        OrganizationNotSent,
        build_request,
    )

    service, adapter, coordinator = organization_owner(tmp_path)
    with adapter:
        other = replace(coordinator.scope, project_id="another-project")
        foreign = build_request(other, "update_tags", asset_ids=["asset-a"], add_tags=["x"])
        with pytest.raises(OrganizationError, match="selected connection"):
            coordinator.organization_snapshot(foreign)
        assert service.requests == []
        built = build_request(
            coordinator.scope, "update_tags", asset_ids=["asset-a"], add_tags=["x"]
        )
        snapshot = coordinator.organization_snapshot(built)
        forged = replace(snapshot)
        with pytest.raises(OrganizationNotSent):
            coordinator.organize(forged)
        assert coordinator.organize(snapshot).state.value == "VERIFIED"
        with pytest.raises(OrganizationNotSent):
            coordinator.organize(snapshot)
        assert len(service.writes) == 1


def test_deactivation_stops_later_organization_writes_and_clears_uncertain_names(tmp_path):
    from scenario.core.jobs.organization import Outcome, build_request

    service, adapter, coordinator = organization_owner(tmp_path)
    with adapter:
        built = build_request(
            coordinator.scope, "update_tags", asset_ids=["asset-a", "asset-b"], add_tags=["x"]
        )
        snapshot = coordinator.organization_snapshot(built)
        coordinator._organization._mark_uncertain("Earlier name")

        def deactivate_during_first_write(request):
            if request.method == "PUT":
                coordinator.deactivate()

        service.gate = deactivate_during_first_write
        result = coordinator.organize(snapshot)
        assert [outcome.state for outcome in result.outcomes] == [
            Outcome.VERIFIED,
            Outcome.NOT_SENT,
        ]
        assert len(service.writes) == 1
        assert not coordinator._organization._uncertain("Earlier name")
        with pytest.raises(QuoteError, match="inactive"):
            coordinator.organization_snapshot(built)
