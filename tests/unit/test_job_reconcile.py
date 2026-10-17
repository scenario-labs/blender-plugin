# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Uncertain submissions: read-only cloud candidates and explicit verified links (#494).

The real pinned SDK runs against a fake service with no sockets. No test sends
a second paid submission: every listing and retrieval is a GET.
"""

import json
import socket
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import httpx
import pytest

from scenario.core.api.sdk_adapter import AdapterError, Credentials, SDKAdapter
from scenario.core.jobs import reconcile
from scenario.core.jobs.coordinator import (
    DuplicateRequestError,
    JobCoordinator,
    RecoveryError,
    SubmissionUncertain,
)
from scenario.core.jobs.store import (
    JobOrigin,
    JobScope,
    JobState,
    JobStore,
    StoreConflict,
)

SCOPE = JobScope("https://service.example.invalid/v1", "account", "project", "team")
ORIGIN = JobOrigin("file", "scene", "revision", "object")
CLOUD_ORIGIN = JobOrigin("file", "scene", "revision")
MODEL = {"id": "model", "type": "custom", "inputs": [{"name": "prompt", "type": "string"}]}
QUOTE = b'{"creativeUnitsCost":0.25}'
# 2026-10-14T21:18:11.000Z, the fake wall clock at the submission claim.
CLAIMED_SECONDS = 1792012691.0
CLAIMED = "2026-10-14T21:18:11.000Z"
SUBMIT_PATHS = {
    "/v1/generate/custom/model",
    "/v1/workflows/workflow/run",
    "/v1/generate/prompt",
    "/v1/generate/translate",
}


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def deny(*args, **kwargs):
        pytest.fail("Reconciliation tests must not open sockets")

    monkeypatch.setattr(socket.socket, "connect", deny)
    monkeypatch.setattr(socket.socket, "connect_ex", deny)
    monkeypatch.setattr(socket, "create_connection", deny)


def job(identifier, operation="model", *, created="2026-10-14T21:18:12.500Z", **changes):
    value = {
        "jobId": identifier,
        "jobType": {
            "model": "custom",
            "workflow": "workflow",
            "prompt": "generate-prompt",
            "translate": "translate",
        }[operation],
        "status": "success",
        "createdAt": created,
        "updatedAt": created,
        "ownerId": "project",
        "metadata": {"input": {"prompt": "a weathered  copper\nkettle"}},
        "billing": {"cuCost": 0.25, "cuDiscount": 0},
    }
    if operation == "model":
        value["metadata"]["input"]["modelId"] = "model"
    if operation == "workflow":
        value["metadata"]["workflowId"] = "workflow"
    value.update(changes)
    return value


class Service:
    """A fake Scenario: lost submissions, one listing, retrievals by ID."""

    def __init__(self):
        self.requests = []
        self.listing = []
        self.jobs = {}
        self.pages = None

    def __call__(self, request):
        self.requests.append(request)
        if request.url.params.get("dryRun") == "true":
            return httpx.Response(200, content=QUOTE)
        if request.url.path in SUBMIT_PATHS:
            raise httpx.ReadTimeout("fixture lost response", request=request)
        assert request.method == "GET", "reconciliation must never send a write"
        if request.url.path == "/v1/jobs":
            if self.pages is not None:
                index = len([r for r in self.requests if r.url.path == "/v1/jobs"]) - 1
                return httpx.Response(200, json=self.pages[index])
            return httpx.Response(200, json={"jobs": self.listing})
        identifier = request.url.path.rsplit("/", 1)[-1]
        if identifier not in self.jobs:
            return httpx.Response(404, json={"error": "not found"})
        return httpx.Response(200, json={"job": self.jobs[identifier]})

    def paid(self):
        return [
            r for r in self.requests if r.url.path in SUBMIT_PATHS and "dryRun" not in r.url.params
        ]


@pytest.fixture
def setup(tmp_path):
    clients = []

    def create(operation="model", *, online=lambda: True):
        service = Service()
        store = JobStore(tmp_path / "jobs.sqlite3", SCOPE)
        adapter = SDKAdapter(
            Credentials("selected", "secret"),
            online=online,
            base_url=SCOPE.service,
            account_id=SCOPE.account_id,
            project_id=SCOPE.project_id,
            team_id=SCOPE.team_id,
            transport=httpx.MockTransport(service),
        )
        clients.append(adapter)
        coordinator = JobCoordinator(adapter, store, wall_clock=lambda: CLAIMED_SECONDS)
        if operation == "model":
            prepared = coordinator.prepare(adapter.estimate_model(MODEL, {"prompt": "x"}), ORIGIN)
        elif operation == "workflow":
            estimate = adapter.estimate_workflow(
                {"id": "workflow", "inputs": MODEL["inputs"]}, {"prompt": "x"}
            )
            prepared = coordinator.prepare(estimate, ORIGIN)
        else:
            parameters = {"prompt": "x"} | ({"mode": "contextual"} if operation == "prompt" else {})
            quote = getattr(coordinator, f"quote_{operation}")(parameters, origin=ORIGIN)
            prepared = coordinator.prepare_quote(quote)
        with pytest.raises(SubmissionUncertain):
            coordinator.submit(
                prepared,
                origin=ORIGIN,
                operation=prepared.intent.operation,
                target_id=prepared.intent.target_id,
                payload=prepared.estimate.payload,
            )
        record = store.get(prepared.intent.request_id)
        assert record.state == JobState.UNCERTAIN
        return coordinator, store, record, service, adapter

    yield create
    for client in clients:
        client.close()


def test_submission_claim_saves_the_wall_clock_time(setup):
    _, store, record, service, _ = setup()
    assert record.claimed_at == CLAIMED
    assert len(service.paid()) == 1


@pytest.mark.parametrize(
    ("operation", "query"),
    [
        ("model", {"types": "custom,inference"}),
        ("workflow", {"workflowId": "workflow"}),
        ("prompt", {"types": "generate-prompt,image-prompt-editing"}),
        ("translate", {"types": "translate"}),
    ],
)
def test_zero_candidates_list_nothing_and_change_nothing(setup, operation, query):
    coordinator, store, record, service, _ = setup(operation)
    found = coordinator.unconfirmed_candidates(
        record.intent.request_id, expected_revision=record.revision
    )
    assert (found.candidates, found.complete, found.record) == ((), True, record)
    listing = [r for r in service.requests if r.url.path == "/v1/jobs"]
    assert len(listing) == 1
    params = dict(listing[0].url.params)
    assert {key: params[key] for key in query} == query
    assert params["projectId"] == "project"
    assert store.get(record.intent.request_id) == record
    assert len(service.paid()) == 1


def test_one_candidate_is_described_relative_to_the_claim(setup):
    coordinator, store, record, service, _ = setup()
    service.listing = [job("job-one")]
    found = coordinator.unconfirmed_candidates(
        record.intent.request_id, expected_revision=record.revision
    )
    (candidate,) = found.candidates
    assert candidate == reconcile.CloudCandidate(
        "job-one",
        "custom",
        "success",
        "2026-10-14T21:18:12.500Z",
        1.5,
        "a weathered copper kettle",
        "0.25",
    )
    assert store.get(record.intent.request_id) == record


def test_many_candidates_are_never_picked_and_are_ordered_by_distance_to_the_claim(setup):
    coordinator, store, record, service, _ = setup()
    service.listing = [
        job("later", created="2026-10-14T21:28:11.000Z"),
        job("closest", created="2026-10-14T21:18:11.400Z"),
        job("before", created="2026-10-14T21:17:11.000Z"),
        job("too-early", created="2026-10-14T20:00:00.000Z"),
        job("too-late", created="2026-10-14T23:00:00.000Z"),
        job("other-model", metadata={"input": {"modelId": "another"}}),
        job("other-type", jobType="upload"),
        job("other-project", ownerId="another-project"),
        job("unknown-state", status="exploded"),
    ]
    found = coordinator.unconfirmed_candidates(
        record.intent.request_id, expected_revision=record.revision
    )
    assert [item.job_id for item in found.candidates] == ["closest", "before", "later"]
    assert [item.seconds_after_claim for item in found.candidates] == [0.4, -60.0, 600.0]
    assert store.get(record.intent.request_id).state == JobState.UNCERTAIN


def test_saved_jobs_in_this_scope_are_not_candidates(setup):
    coordinator, store, record, service, adapter = setup()
    adopted = job("adopted", metadata={"input": {"modelId": "model"}, "assetIds": ["asset"]})
    service.jobs["adopted"] = adopted
    coordinator.adopt_cloud_job("adopted", expected_model_id="model", origin=CLOUD_ORIGIN)
    service.listing = [adopted, job("free")]
    found = coordinator.unconfirmed_candidates(
        record.intent.request_id, expected_revision=record.revision
    )
    assert [item.job_id for item in found.candidates] == ["free"]


def test_an_unknown_claim_time_lists_the_newest_first_and_a_truncated_window(setup, tmp_path):
    coordinator, store, record, service, _ = setup()
    # A schema 11 row has no claim time; nothing narrows by time then.
    with sqlite3.connect(tmp_path / "jobs.sqlite3") as connection:
        (raw,) = connection.execute("SELECT record FROM jobs").fetchone()
        value = json.loads(raw) | {"claimed_at": None}
        connection.execute("UPDATE jobs SET record=?", (json.dumps(value),))
    record = store.get(record.intent.request_id)
    service.pages = [
        {"jobs": [job("old", created="2026-01-01T00:00:00.000Z")], "nextPaginationToken": "a"},
        {"jobs": [job("new", created="2026-10-01T00:00:00.000Z")], "nextPaginationToken": "b"},
    ]
    found = coordinator.unconfirmed_candidates(
        record.intent.request_id, expected_revision=record.revision
    )
    assert [item.job_id for item in found.candidates] == ["new", "old"]
    assert {item.seconds_after_claim for item in found.candidates} == {None}
    assert found.complete is False


def test_candidates_are_capped(setup):
    coordinator, _, record, service, _ = setup()
    service.listing = [job(f"job-{index:02}") for index in range(30)]
    found = coordinator.unconfirmed_candidates(
        record.intent.request_id, expected_revision=record.revision
    )
    assert len(found.candidates) == reconcile.CANDIDATE_LIMIT


@pytest.mark.parametrize("operation", ["model", "workflow", "prompt", "translate"])
def test_a_confirmed_link_saves_the_verified_job_and_polls_it_as_a_normal_job(setup, operation):
    coordinator, store, record, service, adapter = setup(operation)
    service.jobs["chosen"] = job("chosen", operation, status="in-progress")
    linked = coordinator.link_unconfirmed(
        record.intent.request_id, expected_revision=record.revision, remote_job_id="chosen"
    )
    assert (linked.state, linked.remote_job_id) == (JobState.REMOTE, "chosen")
    assert linked.claimed_at == CLAIMED
    service.jobs["chosen"]["status"] = "success"
    snapshot = coordinator.refresh_remote(
        record.intent.request_id, expected_revision=linked.revision
    )
    assert snapshot.record.state == JobState.SUCCEEDED
    assert len(service.paid()) == 1
    # A confirmed job no longer blocks an identical request.
    if operation == "model":
        coordinator.prepare(adapter.estimate_model(MODEL, {"prompt": "x"}), ORIGIN)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"jobType": "upload"}, "different kind"),
        ({"metadata": {"input": {"modelId": "another"}}}, "another model"),
        ({"ownerId": "another-project"}, "another project"),
        ({"createdAt": "2026-10-14T20:00:00.000Z"}, "before the request"),
        ({"status": "exploded"}, "unrecognized"),
    ],
)
def test_a_link_to_a_job_that_cannot_be_this_request_is_refused(setup, changes, message):
    coordinator, store, record, service, _ = setup()
    service.jobs["chosen"] = job("chosen", **changes)
    with pytest.raises(reconcile.LinkRefused, match=message):
        coordinator.link_unconfirmed(
            record.intent.request_id, expected_revision=record.revision, remote_job_id="chosen"
        )
    assert store.get(record.intent.request_id) == record


@pytest.mark.parametrize(
    "metadata",
    [
        {"workflowId": "another"},
        {"input": {"workflowId": "another"}},
        {},
        {"workflowId": "workflow", "workflowJobId": "parent-run"},
    ],
)
def test_a_link_to_another_workflow_or_a_step_is_refused(setup, metadata):
    coordinator, store, record, service, _ = setup("workflow")
    service.jobs["chosen"] = job("chosen", "workflow", metadata=metadata)
    with pytest.raises(reconcile.LinkRefused, match="workflow"):
        coordinator.link_unconfirmed(
            record.intent.request_id, expected_revision=record.revision, remote_job_id="chosen"
        )
    assert store.get(record.intent.request_id) == record


def test_a_job_outside_the_selected_project_is_refused(setup):
    coordinator, store, record, service, _ = setup()
    with pytest.raises(RecoveryError, match="this project"):
        coordinator.link_unconfirmed(
            record.intent.request_id, expected_revision=record.revision, remote_job_id="missing"
        )
    assert store.get(record.intent.request_id) == record


def test_a_job_already_saved_here_cannot_be_linked_again(setup):
    coordinator, store, record, service, _ = setup()
    adopted = job("adopted", metadata={"input": {"modelId": "model"}, "assetIds": ["asset"]})
    service.jobs["adopted"] = adopted
    coordinator.adopt_cloud_job("adopted", expected_model_id="model", origin=CLOUD_ORIGIN)
    with pytest.raises(StoreConflict, match="already saved"):
        coordinator.link_unconfirmed(
            record.intent.request_id, expected_revision=record.revision, remote_job_id="adopted"
        )
    assert store.get(record.intent.request_id) == record


def test_a_stale_revision_or_confirmed_record_cannot_list_or_link(setup):
    coordinator, store, record, service, _ = setup()
    service.jobs["chosen"] = job("chosen")
    before = len(service.requests)
    for command, extra in (
        (coordinator.unconfirmed_candidates, {}),
        (coordinator.link_unconfirmed, {"remote_job_id": "chosen"}),
    ):
        with pytest.raises(StoreConflict):
            command(record.intent.request_id, expected_revision=record.revision + 1, **extra)
    assert len(service.requests) == before
    coordinator.link_unconfirmed(
        record.intent.request_id, expected_revision=record.revision, remote_job_id="chosen"
    )
    current = store.get(record.intent.request_id)
    with pytest.raises(StoreConflict):
        coordinator.link_unconfirmed(
            record.intent.request_id, expected_revision=current.revision, remote_job_id="chosen"
        )
    with pytest.raises(StoreConflict):
        coordinator.unconfirmed_candidates(
            record.intent.request_id, expected_revision=current.revision
        )


def test_offline_lookup_and_link_send_nothing_and_change_nothing(setup):
    online = [True]
    coordinator, store, record, service, _ = setup(online=lambda: online[0])
    service.jobs["chosen"] = job("chosen")
    online[0] = False
    before = len(service.requests)
    with pytest.raises(AdapterError, match="Online access"):
        coordinator.unconfirmed_candidates(
            record.intent.request_id, expected_revision=record.revision
        )
    with pytest.raises(AdapterError, match="Online access"):
        coordinator.link_unconfirmed(
            record.intent.request_id, expected_revision=record.revision, remote_job_id="chosen"
        )
    assert len(service.requests) == before
    assert store.get(record.intent.request_id) == record


def test_an_inactive_context_cannot_list_or_link(setup):
    coordinator, store, record, service, _ = setup()
    service.jobs["chosen"] = job("chosen")
    coordinator.deactivate()
    with pytest.raises(RecoveryError):
        coordinator.unconfirmed_candidates(
            record.intent.request_id, expected_revision=record.revision
        )
    with pytest.raises(RecoveryError):
        coordinator.link_unconfirmed(
            record.intent.request_id, expected_revision=record.revision, remote_job_id="chosen"
        )
    assert store.get(record.intent.request_id) == record


def test_a_request_still_being_sent_cannot_be_listed_or_linked(tmp_path):
    entered, release = Event(), Event()
    service = Service()

    def handler(request):
        if request.url.path in SUBMIT_PATHS and "dryRun" not in request.url.params:
            entered.set()
            release.wait(5)
            return httpx.Response(200, json={"job": {"jobId": "real"}})
        return service(request)

    store = JobStore(tmp_path / "jobs.sqlite3", SCOPE)
    with SDKAdapter(
        Credentials("selected", "secret"),
        online=lambda: True,
        base_url=SCOPE.service,
        account_id=SCOPE.account_id,
        project_id=SCOPE.project_id,
        team_id=SCOPE.team_id,
        transport=httpx.MockTransport(handler),
    ) as adapter:
        coordinator = JobCoordinator(adapter, store)
        prepared = coordinator.prepare(adapter.estimate_model(MODEL, {"prompt": "x"}), ORIGIN)
        with ThreadPoolExecutor(1) as pool:
            future = pool.submit(
                coordinator.submit,
                prepared,
                origin=ORIGIN,
                operation="model",
                target_id="model",
                payload=prepared.estimate.payload,
            )
            assert entered.wait(5)
            record = store.get(prepared.intent.request_id)
            assert record.state == JobState.SUBMITTING
            service.jobs["real"] = job("real")
            for command, extra in (
                (coordinator.unconfirmed_candidates, {}),
                (coordinator.link_unconfirmed, {"remote_job_id": "real"}),
            ):
                with pytest.raises(StoreConflict, match="still being sent"):
                    command(record.intent.request_id, expected_revision=record.revision, **extra)
            release.set()
            assert future.result(5).remote_job_id == "real"


def test_a_link_clears_the_session_review_and_identical_requests_follow_the_saved_job(setup):
    coordinator, store, record, service, adapter = setup()
    with pytest.raises(DuplicateRequestError):
        coordinator.prepare(adapter.estimate_model(MODEL, {"prompt": "x"}), ORIGIN)
    service.jobs["chosen"] = job("chosen")
    coordinator.link_unconfirmed(
        record.intent.request_id, expected_revision=record.revision, remote_job_id="chosen"
    )
    assert not coordinator.unconfirmed_reviewed(record.intent.request_id)
    again = coordinator.prepare(adapter.estimate_model(MODEL, {"prompt": "x"}), ORIGIN)
    assert again.intent.request_id != record.intent.request_id
    assert len(service.paid()) == 1


def test_a_refused_link_keeps_the_users_review_mark(setup):
    coordinator, store, record, service, adapter = setup()
    adopted = job("adopted", metadata={"input": {"modelId": "model"}, "assetIds": ["asset"]})
    service.jobs["adopted"] = adopted
    coordinator.adopt_cloud_job("adopted", expected_model_id="model", origin=CLOUD_ORIGIN)
    coordinator.mark_unconfirmed_reviewed(
        record.intent.request_id, expected_revision=record.revision
    )
    service.jobs["other-model"] = job("other-model", metadata={"input": {"modelId": "another"}})
    for remote_job_id, error in (
        ("adopted", StoreConflict),
        ("other-model", reconcile.LinkRefused),
        ("missing", RecoveryError),
    ):
        with pytest.raises(error):
            coordinator.link_unconfirmed(
                record.intent.request_id,
                expected_revision=record.revision,
                remote_job_id=remote_job_id,
            )
        assert coordinator.unconfirmed_reviewed(record.intent.request_id)
    # The mark still lets an identical request through; nothing was linked.
    coordinator.prepare(adapter.estimate_model(MODEL, {"prompt": "x"}), ORIGIN)
    assert store.get(record.intent.request_id) == record
