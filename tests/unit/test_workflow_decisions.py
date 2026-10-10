# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Decide waiting workflow steps through the actual SDK adapter, once, never replayed."""

import json
import socket
import threading
from dataclasses import replace

import httpx
import pytest

from scenario.core.api.sdk_adapter import AdapterError, Credentials, SDKAdapter
from scenario.core.jobs.coordinator import (
    DecisionRefused,
    DecisionSnapshot,
    DecisionUncertain,
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
)
from scenario.core.jobs.workers import JobWorkers
from scenario.core.jobs.workflow_nodes import StepError, pending_steps

SCOPE = JobScope("https://service.example.invalid/v1", "account", "project", "team")
INTENT = JobIntent(
    "request",
    SCOPE,
    JobOrigin("file", "scene", "revision"),
    "workflow",
    "workflow",
    "a" * 64,
    "b" * 64,
    "1",
)
SIGNED = "https://cdn.example.invalid/a?X-Signature=private-signature"


def flow(*waiting, status="processing"):
    nodes = [
        {
            "id": "render",
            "type": "model",
            "status": "success",
            "assets": [{"assetId": "asset_a", "url": SIGNED}],
        }
    ]
    if "approve" in waiting:
        nodes.append(
            {"id": "approve", "type": "user-approval", "status": status, "dependsOn": ["render"]}
        )
    if "pick" in waiting or "looped" in waiting:
        nodes.append(
            {
                "id": "pick",
                "type": "user-selection",
                "status": status,
                "items": ["asset_a", "asset_b", "asset_c"],
                "inputs": [{"name": "choices", "type": "file_array", "min": 1, "max": 2}],
            }
        )
    if "looped" in waiting:
        nodes.append(
            {
                "id": "loop",
                "type": "for-each",
                "status": "pending",
                "inputs": [{"name": "items", "ref": {"node": "pick"}}],
            }
        )
    return nodes


def job(status="in-progress", *waiting, node_status="processing"):
    return {
        "jobId": "remote",
        "jobType": "workflow",
        "status": status,
        "metadata": {"workflowId": "workflow", "flow": flow(*waiting, status=node_status)},
    }


def step(node_id, value):
    return next(
        item
        for item in pending_steps(value, remote_job_id="remote", workflow_id="workflow")
        if item.node_id == node_id
    )


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def deny(*args, **kwargs):
        pytest.fail("Decision contracts must not access the network")

    monkeypatch.setattr(socket.socket, "connect", deny)
    monkeypatch.setattr(socket.socket, "connect_ex", deny)
    monkeypatch.setattr(socket, "create_connection", deny)


@pytest.fixture
def setup(tmp_path):
    adapters = []

    def create(replies, *, intent=INTENT, online=None, state=JobState.REMOTE, project=True):
        replies = list(replies)
        calls = []
        scope = SCOPE if project else replace(SCOPE, project_id=None)
        store = JobStore(tmp_path / f"jobs-{len(adapters)}.sqlite3", scope)
        intent = replace(intent, scope=scope)
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
            expected = {"projectId": "project"} if project else {}
            assert dict(request.url.params) == expected
            assert request.headers["Authorization"] == Credentials("key", "secret").authorization()
            if request.method == "GET":
                assert request.url.path == "/v1/jobs/remote"
            else:
                assert request.method == "PUT"
                assert request.url.path in (
                    "/v1/workflows/workflow/user-approval",
                    "/v1/workflows/workflow/user-selection",
                )
            value = replies.pop(0)
            if callable(value):
                value = value(request)
            if isinstance(value, httpx.Response):
                return value
            return httpx.Response(200, json={"job": value})

        adapter = SDKAdapter(
            Credentials("key", "secret"),
            online=online or (lambda: True),
            base_url=SCOPE.service,
            account_id=SCOPE.account_id,
            project_id=SCOPE.project_id if project else None,
            team_id=SCOPE.team_id,
            transport=httpx.MockTransport(handler),
        )
        adapters.append(adapter)
        return JobCoordinator(adapter, store), store, calls, record

    yield create
    for adapter in adapters:
        adapter.close()


def decide(coordinator, record, node_id, value, action, picks=None, review=None):
    return coordinator.decide_workflow_node(
        "request",
        expected_revision=record.revision,
        node_id=node_id,
        review_id=review if review is not None else step(node_id, value).review_id,
        action=action,
        selected_indices=picks,
    )


def puts(calls):
    return [request for request in calls if request.method == "PUT"]


@pytest.mark.parametrize("project", [True, False])
def test_approval_is_sent_once_then_the_job_is_retrieved(setup, project):
    waiting = job("in-progress", "approve")
    coordinator, store, calls, record = setup(
        [waiting, {"jobId": "remote", "status": "in-progress"}, job()], project=project
    )
    snapshot = decide(coordinator, record, "approve", waiting, "approve")
    assert [request.method for request in calls] == ["GET", "PUT", "GET"]
    assert json.loads(calls[1].content) == {
        "nodeId": "approve",
        "workflowJobId": "remote",
        "action": "approve",
    }
    assert isinstance(snapshot, DecisionSnapshot) and snapshot.sent
    assert snapshot.record == store.get("request")
    assert snapshot.record.state == JobState.REMOTE and snapshot.record.revision == record.revision
    assert snapshot.response == job()


def test_selection_sends_ordered_picks_through_the_selection_extension(setup):
    waiting = job("in-progress", "pick")
    coordinator, _, calls, record = setup([waiting, {"jobId": "remote"}, job()])
    snapshot = decide(coordinator, record, "pick", waiting, "select", [2, 0])
    assert calls[1].url.path == "/v1/workflows/workflow/user-selection"
    assert json.loads(calls[1].content) == {
        "action": "select",
        "nodeId": "pick",
        "workflowJobId": "remote",
        "selectedIndices": [2, 0],
    }
    assert snapshot.sent and len(puts(calls)) == 1


@pytest.mark.parametrize("node_id,path", [("approve", "approval"), ("pick", "selection")])
def test_reject_followed_by_a_canceled_retrieval_persists_canceled(setup, node_id, path):
    waiting = job("in-progress", node_id)
    rejected = job("canceled", node_id, node_status="rejected")
    coordinator, store, calls, record = setup([waiting, {"jobId": "remote"}, rejected])
    snapshot = decide(coordinator, record, node_id, waiting, "reject")
    assert calls[1].url.path.endswith(f"/user-{path}")
    assert json.loads(calls[1].content)["action"] == "reject"
    assert "selectedIndices" not in json.loads(calls[1].content)
    assert snapshot.sent and snapshot.record.state == JobState.CANCELED
    reopened = JobCoordinator(coordinator._adapter, JobStore(store._path, SCOPE))
    (item,) = reopened.recovery_plan()
    assert item.record.state == JobState.CANCELED and item.action == RecoveryAction.FINISHED
    assert len(calls) == 3


@pytest.mark.parametrize(
    "status,state",
    [
        ("success", JobState.SUCCEEDED),
        ("canceled", JobState.CANCELED),
        ("failure", JobState.FAILED),
    ],
)
def test_a_finished_job_is_committed_without_sending(setup, status, state):
    waiting = job("in-progress", "approve")
    coordinator, store, calls, record = setup([job(status)])
    snapshot = decide(coordinator, record, "approve", waiting, "approve")
    assert isinstance(snapshot, DecisionSnapshot) and not snapshot.sent
    assert snapshot.record.state == state == store.get("request").state
    assert [request.method for request in calls] == ["GET"]


def test_changed_or_finished_steps_conflict_before_sending(setup):
    waiting = job("in-progress", "approve")
    changed = job("in-progress", "approve")
    changed["metadata"]["flow"][0]["assets"].append({"assetId": "asset_b", "url": SIGNED})
    for reply in (changed, job("in-progress", "approve", node_status="success"), job()):
        coordinator, store, calls, record = setup([reply])
        with pytest.raises(StoreConflict, match="step changed"):
            decide(coordinator, record, "approve", waiting, "approve")
        assert [request.method for request in calls] == ["GET"]
        assert store.get("request") == record


def test_wrong_review_identity_or_node_never_sends(setup):
    waiting = job("in-progress", "approve")
    for node_id, review in (("approve", "0" * 64), ("approve", None), ("missing", "0" * 64)):
        coordinator, _, calls, record = setup([waiting])
        with pytest.raises(StoreConflict, match="step changed"):
            coordinator.decide_workflow_node(
                "request",
                expected_revision=record.revision,
                node_id=node_id,
                review_id=review,
                action="approve",
            )
        assert len(calls) == 1 and not puts(calls)


@pytest.mark.parametrize(
    "node_id,action,picks,message",
    [
        ("approve", "select", [0], "decision this workflow step accepts"),
        ("approve", "approve", [0], "Only a selection"),
        ("pick", "approve", None, "decision this workflow step accepts"),
        ("pick", "select", [0, 1, 2], "Select 1 to 2 items"),
        ("pick", "select", [3], "listed candidates"),
        ("pick", "select", None, "list of indices"),
    ],
)
def test_invalid_decisions_are_refused_locally(setup, node_id, action, picks, message):
    waiting = job("in-progress", node_id)
    coordinator, store, calls, record = setup([waiting])
    with pytest.raises(StepError, match=message):
        decide(coordinator, record, node_id, waiting, action, picks)
    assert not puts(calls) and store.get("request") == record


def test_selection_feeding_a_loop_is_blocked_but_rejection_is_sent(setup):
    waiting = job("in-progress", "looped")
    coordinator, _, calls, record = setup([waiting])
    with pytest.raises(StepError, match="ForEach loop"):
        decide(coordinator, record, "pick", waiting, "select", [0])
    assert not puts(calls)
    coordinator, _, calls, record = setup(
        [waiting, {"jobId": "remote"}, job("canceled", "looped", node_status="rejected")]
    )
    snapshot = decide(coordinator, record, "pick", waiting, "reject")
    assert snapshot.record.state == JobState.CANCELED and len(puts(calls)) == 1


@pytest.mark.parametrize("status", [400, 401, 403, 404, 409, 429])
def test_service_refusal_is_definitive_and_rereads_once(setup, status):
    waiting = job("in-progress", "approve")
    refusal = httpx.Response(
        status, json={"message": "private detail"}, headers={"Retry-After": "0"}
    )
    coordinator, store, calls, record = setup([waiting, refusal, job()])
    with pytest.raises(DecisionRefused) as error:
        decide(coordinator, record, "approve", waiting, "approve")
    assert error.value.status_code == status
    assert str(error.value).startswith("Scenario refused this decision: ")
    assert "private" not in str(error.value)
    assert error.value.snapshot is not None and error.value.snapshot.record == record
    assert [request.method for request in calls] == ["GET", "PUT", "GET"]
    assert store.get("request") == record


@pytest.mark.parametrize("failure", ["timeout", 500, 503, "malformed", "mismatch"])
def test_lost_or_unclear_outcomes_are_uncertain_and_never_replayed(setup, failure):
    waiting = job("in-progress", "approve")

    def fail(request):
        if failure == "timeout":
            raise httpx.ReadTimeout("private signed-url secret", request=request)
        if failure == "malformed":
            return httpx.Response(200, json={"wrong": "private"})
        if failure == "mismatch":
            return httpx.Response(200, json={"job": {"jobId": "another"}})
        return httpx.Response(failure, json={"secret": "private"}, headers={"Retry-After": "0"})

    coordinator, store, calls, record = setup([waiting, fail, job()])
    with pytest.raises(DecisionUncertain) as error:
        decide(coordinator, record, "approve", waiting, "approve")
    assert "private" not in str(error.value) and "secret" not in str(error.value)
    assert "do not repeat" in str(error.value)
    assert len(puts(calls)) == 1 and calls[-1].method == "GET"
    assert error.value.snapshot is not None
    assert store.get("request") == record


def test_lost_reject_whose_retrieval_shows_canceled_persists_it(setup):
    waiting = job("in-progress", "approve")

    def lose(request):
        raise httpx.ReadTimeout("lost", request=request)

    rejected = job("canceled", "approve", node_status="rejected")
    coordinator, store, calls, record = setup([waiting, lose, rejected])
    with pytest.raises(DecisionUncertain) as error:
        decide(coordinator, record, "approve", waiting, "reject")
    assert error.value.snapshot.record.state == JobState.CANCELED
    assert store.get("request").state == JobState.CANCELED and len(puts(calls)) == 1


def test_failed_retrieval_after_refusal_keeps_the_saved_job(setup):
    waiting = job("in-progress", "approve")
    lost = httpx.Response(503)
    coordinator, store, calls, record = setup([waiting, httpx.Response(409), lost])
    with pytest.raises(DecisionRefused) as error:
        decide(coordinator, record, "approve", waiting, "approve")
    assert error.value.snapshot is None and store.get("request") == record
    assert len(puts(calls)) == 1


def test_acknowledged_decision_without_retrieval_is_uncertain(setup):
    waiting = job("in-progress", "approve")
    coordinator, store, calls, record = setup([waiting, {"jobId": "remote"}, httpx.Response(503)])
    with pytest.raises(DecisionUncertain, match="acknowledged the decision"):
        decide(coordinator, record, "approve", waiting, "approve")
    assert len(puts(calls)) == 1 and store.get("request") == record


def test_only_current_remote_workflow_records_can_be_decided(setup):
    waiting = job("in-progress", "approve")
    coordinator, _, calls, record = setup([], intent=replace(INTENT, operation="model"))
    with pytest.raises(RecoveryError, match="Only workflow jobs"):
        decide(coordinator, record, "approve", waiting, "approve")
    for state in (JobState.PREPARED, JobState.UNCERTAIN):
        coordinator, _, calls, record = setup([], state=state)
        with pytest.raises(StoreConflict, match="current known remote workflow"):
            decide(coordinator, record, "approve", waiting, "approve")
    coordinator, _, calls, record = setup([])
    with pytest.raises(StoreConflict):
        coordinator.decide_workflow_node(
            "request",
            expected_revision=record.revision + 1,
            node_id="approve",
            review_id=step("approve", waiting).review_id,
            action="approve",
        )
    coordinator.deactivate()
    with pytest.raises(RecoveryError, match="inactive"):
        decide(coordinator, record, "approve", waiting, "approve")
    assert calls == []


def test_deactivation_after_the_retrieval_sends_nothing(setup):
    waiting = job("in-progress", "approve")
    holder = []

    def retrieve(request):
        holder[0].deactivate()
        return httpx.Response(200, json={"job": waiting})

    coordinator, _, calls, record = setup([retrieve])
    holder.append(coordinator)
    with pytest.raises(RecoveryError, match="inactive"):
        decide(coordinator, record, "approve", waiting, "approve")
    assert not puts(calls)


def test_offline_preflight_sends_nothing(setup):
    waiting = job("in-progress", "approve")
    coordinator, store, calls, record = setup([], online=lambda: False)
    with pytest.raises(AdapterError, match="Online access is disabled"):
        decide(coordinator, record, "approve", waiting, "approve")
    assert calls == [] and store.get("request") == record


def test_a_concurrent_second_decision_is_refused_locally(setup):
    waiting = job("in-progress", "approve")
    entered, release = threading.Event(), threading.Event()

    def hold(request):
        entered.set()
        assert release.wait(5)
        return httpx.Response(200, json={"job": {"jobId": "remote"}})

    coordinator, _, calls, record = setup([waiting, hold, job()])
    outcome = []
    first = threading.Thread(
        target=lambda: outcome.append(decide(coordinator, record, "approve", waiting, "approve"))
    )
    first.start()
    try:
        assert entered.wait(5)
        with pytest.raises(StoreConflict, match="already being sent"):
            decide(coordinator, record, "approve", waiting, "reject")
    finally:
        release.set()
        first.join(5)
    assert outcome and outcome[0].sent and len(puts(calls)) == 1
    # The guard is released once the first decision finishes.
    assert "request" not in coordinator._deciding


def test_a_restarted_coordinator_decides_from_a_fresh_retrieval(setup):
    waiting = job("in-progress", "approve")
    coordinator, store, calls, record = setup([waiting, {"jobId": "remote"}, job()])
    restarted = JobCoordinator(coordinator._adapter, JobStore(store._path, SCOPE))
    snapshot = decide(restarted, record, "approve", waiting, "approve")
    assert snapshot.sent and len(puts(calls)) == 1


def test_workers_run_decisions_with_an_immutable_selection(setup):
    waiting = job("in-progress", "pick")
    coordinator, _, calls, record = setup([waiting, {"jobId": "remote"}, job()])
    workers = JobWorkers(coordinator, workers=1, pending_limit=2)
    try:
        picks = [1]
        task = workers.decide_workflow_node(
            "request",
            expected_revision=record.revision,
            node_id="pick",
            review_id=step("pick", waiting).review_id,
            action="select",
            selected_indices=picks,
        )
        picks.append(2)
        snapshot = task.result(5)
    finally:
        workers.shutdown()
    assert snapshot.sent
    assert json.loads(puts(calls)[0].content)["selectedIndices"] == [1]
