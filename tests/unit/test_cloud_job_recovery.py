# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Cloud results enter durable recovery without counterfeit submission evidence."""

import hashlib
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from dataclasses import asdict, replace
from threading import Barrier

import httpx
import pytest

from scenario.core.api.sdk_adapter import AdapterError, Credentials, SDKAdapter
from scenario.core.jobs.coordinator import JobCoordinator, QuoteError, RecoveryError
from scenario.core.jobs.store import (
    CloudJobIntent,
    JobIntent,
    JobOrigin,
    JobScope,
    JobState,
    JobStore,
    StoreConflict,
    StoreError,
)
from scenario.core.jobs.workers import JobWorkers

SCOPE = JobScope("https://service.example.invalid/v1", "selected-account", "selected-project")
ORIGIN = JobOrigin("local-file", "local-scene", "local-revision")


@pytest.fixture
def setup(tmp_path):
    store = JobStore(tmp_path / "jobs.sqlite3", SCOPE)
    calls = []
    job = {
        "jobId": "remote",
        "jobType": "custom",
        "status": "success",
        "metadata": {
            "input": {"modelId": "model", "prompt": "private text"},
            "assetIds": ["asset-one"],
        },
    }
    state = {"online": True, "status": 200, "after": None}

    def respond(request):
        calls.append(request)
        assert request.method == "GET"
        assert request.headers["Authorization"] == "Basic c2VsZWN0ZWQ6c2VjcmV0"
        assert dict(request.url.params) == {"projectId": "selected-project"}
        if state["after"]:
            state["after"]()
        if request.url.path == "/v1/jobs/remote":
            return httpx.Response(state["status"], json={"job": job})
        assert request.url.path == "/v1/assets/asset-one"
        return httpx.Response(
            200,
            json={
                "asset": {
                    "id": "asset-one",
                    "status": "success",
                    "mimeType": "image/png",
                    "properties": {"size": 3},
                }
            },
        )

    adapter = SDKAdapter(
        Credentials("selected", "secret"),
        online=lambda: state["online"],
        base_url=SCOPE.service,
        account_id=SCOPE.account_id,
        project_id=SCOPE.project_id,
        transport=httpx.MockTransport(respond),
    )
    coordinator = JobCoordinator(adapter, store)
    yield coordinator, store, calls, job, state
    coordinator.close()


def adopt(coordinator, **options):
    return coordinator.adopt_cloud_job(
        "remote", origin=ORIGIN, expected_model_id="model", **options
    )


def test_adoption_is_read_only_and_never_invents_a_quote(setup, tmp_path):
    coordinator, store, calls, _, _ = setup
    record = adopt(coordinator)
    assert record.state == JobState.SUCCEEDED
    assert record.revision == 0 and record.remote_job_id == "remote"
    assert isinstance(record.intent, CloudJobIntent)
    assert record.intent.quote_cost is None and record.intent.mesh_sources == ()
    assert record.intent.operation == "model" and record.intent.origin == ORIGIN
    assert set(asdict(record.intent)) == {"request_id", "scope", "origin", "target_id", "source"}
    assert len(calls) == 1
    assert JobStore(tmp_path / "jobs.sqlite3", SCOPE).records() == (record,)
    assert "private text" not in (tmp_path / "jobs.sqlite3").read_bytes().decode(errors="ignore")
    with pytest.raises(ValueError):
        store.create(record.intent)
    with pytest.raises(QuoteError):
        coordinator.submit(record, origin=ORIGIN, operation="model", target_id="model", payload={})
    assert len(calls) == 1
    for state in (JobState.PREPARED, JobState.SUBMITTING, JobState.REMOTE, JobState.CANCELED):
        with pytest.raises(ValueError):
            store.transition(record.intent.request_id, expected_revision=0, state=state)


def test_repeated_reads_keep_identity_origin_and_existing_manifest(setup):
    coordinator, store, calls, _, _ = setup
    record = adopt(coordinator)
    loaded = coordinator.load_results(record.intent.request_id, expected_revision=record.revision)
    again = coordinator.adopt_cloud_job(
        "remote", origin=replace(ORIGIN, scene_id="other"), expected_model_id="model"
    )
    assert again == loaded
    assert again.intent.origin == ORIGIN
    assert len(again.results) == 1 and not again.results[0].receipt
    assert len(store.records()) == 1
    assert all(request.method == "GET" for request in calls)


@pytest.mark.parametrize(
    "change",
    [
        {"jobId": "other"},
        {"status": "in-progress"},
        {"status": "failure"},
        {"jobType": "upload"},
        {"jobType": []},
        {"metadata": []},
        {"metadata": {"input": {"modelId": "other"}, "assetIds": ["asset-one"]}},
        {"metadata": {"input": {"modelId": "model"}, "assetIds": []}},
        {"metadata": {"input": {"modelId": "model"}, "assetIds": ["asset-one", "asset-one"]}},
        {"metadata": {"input": {"modelId": "model"}, "assetIds": ["https://private.invalid/file"]}},
        {"metadata": {"input": {"modelId": "model"}, "assetIds": ["asset"] * 129}},
    ],
)
def test_invalid_or_unfinished_remote_evidence_never_creates_local_record(setup, change):
    coordinator, store, calls, job, _ = setup
    job.update(change)
    with pytest.raises(RecoveryError):
        adopt(coordinator)
    assert store.records() == () and len(calls) == 1


def test_offline_permission_failure_and_retirement_leave_storage_untouched(setup):
    coordinator, store, calls, _, state = setup
    state["online"] = False
    with pytest.raises(AdapterError, match="Online access"):
        adopt(coordinator)
    assert not calls and not store.records()
    state.update(online=True, status=403)
    with pytest.raises(AdapterError, match="HTTP 403"):
        adopt(coordinator)
    assert len(calls) == 1 and not store.records()
    state.update(status=200, after=coordinator.deactivate)
    with pytest.raises(QuoteError):
        adopt(coordinator)
    assert len(calls) == 2 and not store.records()


@pytest.mark.parametrize("initially_current", [True, False])
def test_changed_origin_before_or_during_read_preserves_metadata_provenance(
    setup, initially_current
):
    coordinator, store, _, _, state = setup
    current = [initially_current]
    coordinator._origin_guard = lambda origin: nullcontext(current[0])
    state["after"] = lambda: current.__setitem__(0, False)
    record = adopt(coordinator)
    assert store.records() == (record,)
    assert record.intent.origin == ORIGIN
    assert record.application_origin is None
    assert record.state == JobState.SUCCEEDED and not record.results


def test_retired_coordinator_rejects_cloud_read_before_dispatch(setup):
    coordinator, store, calls, _, _ = setup
    coordinator.deactivate()
    with pytest.raises(QuoteError):
        adopt(coordinator)
    assert not calls and not store.records()


def test_existing_generation_intent_wins_without_losing_quote_or_state(setup):
    coordinator, store, _, _, _ = setup
    original = JobIntent("original", SCOPE, ORIGIN, "model", "model", "a" * 64, "b" * 64, "7.25")
    store.create(original)
    store.transition("original", expected_revision=0, state=JobState.SUBMITTING)
    remote = store.transition(
        "original", expected_revision=1, state=JobState.REMOTE, remote_job_id="remote"
    )
    assert adopt(coordinator) == remote
    assert store.records() == (remote,)
    assert remote.intent.quote_cost == "7.25"


def test_atomic_cloud_creation_across_two_store_owners_and_scope_isolation(setup, tmp_path):
    _, store, _, _, _ = setup
    other = JobStore(tmp_path / "jobs.sqlite3", SCOPE)
    intent = CloudJobIntent("cloud-request", SCOPE, ORIGIN, "model")
    barrier = Barrier(2)

    def save(owner):
        barrier.wait(timeout=3)
        return owner.adopt_cloud_job(intent, "remote")

    with ThreadPoolExecutor(max_workers=2) as workers:
        values = list(workers.map(save, (store, other)))
    assert values[0] == values[1]
    assert store.records() == (values[0],)
    alternate = JobStore(tmp_path / "jobs.sqlite3", replace(SCOPE, project_id="another-project"))
    assert not alternate.records()
    with pytest.raises(ValueError):
        alternate.adopt_cloud_job(intent, "remote")


def test_duplicate_remote_ambiguity_and_local_identity_collision_fail_closed(setup):
    coordinator, store, _, _, _ = setup
    base = JobIntent("first", SCOPE, ORIGIN, "model", "model", "a" * 64, "b" * 64, "1")
    for identifier in ("first", "second"):
        store.create(replace(base, request_id=identifier))
        store.transition(identifier, expected_revision=0, state=JobState.SUBMITTING)
        store.transition(
            identifier, expected_revision=1, state=JobState.REMOTE, remote_job_id="remote"
        )
    with pytest.raises(StoreConflict):
        adopt(coordinator)
    with pytest.raises(StoreConflict):
        store.adopt_cloud_job(CloudJobIntent("first", SCOPE, ORIGIN, "model"), "different-remote")
    assert len(store.records()) == 2


def test_failed_commit_preserves_database_and_safe_read_retry(setup, monkeypatch, tmp_path):
    coordinator, store, calls, _, _ = setup
    path = tmp_path / "jobs.sqlite3"
    before = path.read_bytes()
    connect = sqlite3.connect

    class FailCommit(sqlite3.Connection):
        def commit(self):
            raise sqlite3.OperationalError("synthetic commit failure")

    with monkeypatch.context() as patch:
        patch.setattr(sqlite3, "connect", lambda *a, **k: connect(*a, **k, factory=FailCommit))
        with pytest.raises(StoreError):
            adopt(coordinator)
    assert path.read_bytes() == before and not store.records()
    assert adopt(coordinator).state == JobState.SUCCEEDED
    assert len(calls) == 2


@pytest.mark.parametrize("damage", ["state", "quote", "source", "target"])
def test_corrupt_cloud_records_are_not_loaded_as_submittable_intents(setup, tmp_path, damage):
    coordinator, store, _, _, _ = setup
    record = adopt(coordinator)
    value = asdict(record)
    if damage == "state":
        value.update(state="prepared", remote_job_id=None)
    elif damage == "quote":
        value["intent"]["quote_cost"] = "0"
    elif damage == "source":
        value["intent"]["source"] = "submitted"
    else:
        value["intent"]["origin"]["target_id"] = "unverified-object"
    with sqlite3.connect(tmp_path / "jobs.sqlite3") as connection:
        connection.execute("UPDATE jobs SET record=?", (json.dumps(value),))
    with pytest.raises(StoreError):
        store.records()


def test_worker_command_uses_existing_owner_and_returns_one_durable_result(setup):
    coordinator, store, calls, _, _ = setup
    workers = JobWorkers(coordinator, workers=1)
    try:
        task = workers.adopt_cloud_job("remote", expected_model_id="model", origin=ORIGIN)
        record = task.result(3)
        assert store.records() == (record,)
        assert record.intent.request_id == "cloud-" + hashlib.sha256(b"remote").hexdigest()
        assert len(calls) == 1
    finally:
        workers.shutdown()
