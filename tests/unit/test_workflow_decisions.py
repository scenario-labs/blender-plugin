# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Decide waiting workflow steps through the actual SDK adapter, once, never replayed."""

import json
import logging
import re
import socket
import threading
from dataclasses import replace

import httpx
import pytest

from scenario.core.api.sdk_adapter import READ_RETRIES, AdapterError, Credentials, SDKAdapter
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
from scenario.core.jobs.workflow_nodes import BLOCKED, StepError, definition_links, pending_steps

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
    # Workflow definition reads, kept apart from `calls` (job reads and decisions).
    reads = []

    def create(
        replies,
        *,
        intent=INTENT,
        online=None,
        state=JobState.REMOTE,
        project=True,
        definition=None,
    ):
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
            if request.method == "GET" and request.url.path == "/v1/workflows/workflow":
                # SDK workflows.retrieve: the definition carries the step links.
                calls.pop()
                reads.append(request)
                value = definition(request) if callable(definition) else definition
                if isinstance(value, httpx.Response):
                    return value
                if value is None:
                    return httpx.Response(404, json={"message": "private fixture detail"})
                return httpx.Response(200, json={"workflow": value})
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

    create.reads = reads
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


# Live-shaped job flows: only the selection lists its inputs (see test_workflow_step_links).
CREATED = "2026-10-10T10:56:00.366Z"


def live_job(*flow, status="in-progress"):
    return {
        "jobId": "remote",
        "jobType": "workflow",
        "status": status,
        "createdAt": CREATED,
        "metadata": {"workflowId": "workflow", "flow": list(flow)},
    }


def live_selection(source, status="processing"):
    return {
        "id": "select1",
        "type": "user-selection",
        "status": status,
        "items": ["asset_a", "asset_b", "asset_c"],
        "inputs": [{"name": "images", "type": "file_array", "min": 2, "max": 2, "ref": source}],
    }


def live_definition(*flow):
    return {"id": "workflow", "updatedAt": "2026-10-10T10:23:21.000Z", "flow": list(flow)}


INTO_LOOP = live_definition(
    {
        "id": "select1",
        "type": "user-selection",
        "inputs": [
            {"name": "images", "type": "file_array", "ref": {"node": "workflow", "name": "x"}}
        ],
    },
    {
        "id": "loop1",
        "type": "for-each",
        "loopBodyNodeIds": ["cutout1"],
        "inputs": [{"name": "image0", "type": "file_array", "ref": {"node": "select1"}}],
    },
    {
        "id": "cutout1",
        "type": "custom-model",
        "inputs": [{"name": "image", "type": "file", "ref": {"node": "loop1", "name": "image0"}}],
    },
)
AFTER_LOOP = live_definition(
    {
        "id": "loop1",
        "type": "for-each",
        "loopBodyNodeIds": ["cutout1"],
        "inputs": [{"name": "image0", "type": "file_array", "ref": {"node": "workflow"}}],
    },
    {
        "id": "cutout1",
        "type": "custom-model",
        "inputs": [{"name": "image", "type": "file", "ref": {"node": "loop1", "name": "image0"}}],
    },
    {
        "id": "select1",
        "type": "user-selection",
        "inputs": [{"name": "images", "type": "file_array", "ref": {"node": "loop1"}}],
    },
    {
        "id": "grid1",
        "type": "custom-model",
        "inputs": [{"name": "images", "type": "file_array", "ref": {"node": "select1"}}],
    },
)
APPROVAL = live_definition(
    {"id": "cutout1", "type": "custom-model", "inputs": []},
    {"id": "approval1", "type": "user-approval", "dependsOn": ["cutout1"]},
)


def into_loop(status="processing", job_status="in-progress"):
    return live_job(
        live_selection({"node": "workflow", "name": "x"}, status),
        {"id": "loop1", "type": "for-each", "status": "pending"},
        {"id": "cutout1", "type": "custom-model", "status": "pending"},
        status=job_status,
    )


def after_loop():
    return live_job(
        {"id": "loop1", "type": "for-each", "status": "success"},
        {"id": "cutout1", "type": "custom-model", "status": "skipped"},
        *(
            {
                "id": f"cutout1__iter__{index}",
                "type": "custom-model",
                "status": "success",
                "assets": [{"assetId": f"asset_{index}", "url": SIGNED}],
            }
            for index in range(3)
        ),
        live_selection({"node": "loop1"}),
        {"id": "grid1", "type": "custom-model", "status": "pending"},
    )


def linked_step(node_id, value, workflow):
    links = None if workflow is None else definition_links(workflow, workflow_id="workflow")
    (item,) = (
        item
        for item in pending_steps(
            value, remote_job_id="remote", workflow_id="workflow", links=links
        )
        if item.node_id == node_id
    )
    return item


def test_polling_a_waiting_job_reads_its_workflow_definition_once(setup):
    waiting = into_loop()
    coordinator, _, calls, record = setup([waiting, waiting, into_loop()], definition=INTO_LOOP)
    first = coordinator.refresh_remote("request", expected_revision=record.revision)
    assert len(setup.reads) == 1
    assert setup.reads[0].url.path == "/v1/workflows/workflow"
    assert dict(setup.reads[0].url.params) == {"projectId": "project"}
    assert first.links == definition_links(INTO_LOOP, workflow_id="workflow")
    assert "Signature" not in repr(first) and "Signature" not in repr(first.links)
    (item,) = pending_steps(
        first.response, remote_job_id="remote", workflow_id="workflow", links=first.links
    )
    assert item.blocked == "loop" and item.links_complete
    second = coordinator.refresh_remote("request", expected_revision=record.revision)
    assert second.links == first.links and len(setup.reads) == 1
    assert [request.url.path for request in calls] == ["/v1/jobs/remote"] * 2


def test_jobs_without_a_waiting_step_read_no_definition(setup):
    coordinator, _, _, record = setup([job(), job("success")], definition=INTO_LOOP)
    assert coordinator.refresh_remote("request", expected_revision=record.revision).links is None
    finished = coordinator.refresh_remote("request", expected_revision=record.revision)
    assert finished.links is None and finished.record.state == JobState.SUCCEEDED
    assert setup.reads == []


def test_a_cached_definition_is_dropped_once_the_step_stops_waiting(setup):
    replies = [into_loop(), into_loop("success"), into_loop()]
    coordinator, _, _, record = setup(replies, definition=INTO_LOOP)
    for _ in replies:
        coordinator.refresh_remote("request", expected_revision=record.revision)
    assert len(setup.reads) == 2


@pytest.mark.parametrize(
    "definition",
    [
        None,
        httpx.Response(500, json={"message": "private fixture detail"}),
        {**INTO_LOOP, "id": "another"},
        {**INTO_LOOP, "flow": "unreadable"},
    ],
)
def test_an_unreadable_definition_blocks_choosing_and_is_read_again(setup, definition):
    waiting = into_loop()
    coordinator, _, calls, record = setup([waiting, waiting], definition=definition)
    snapshot = coordinator.refresh_remote("request", expected_revision=record.revision)
    assert snapshot.links is None
    (item,) = pending_steps(
        snapshot.response, remote_job_id="remote", workflow_id="workflow", links=snapshot.links
    )
    assert item.blocked == "unverified" and item.actions == ("reject",)
    coordinator.refresh_remote("request", expected_revision=record.revision)
    # A definition read is a workflow retrieve: the SDK retries a 5xx first.
    failed = isinstance(definition, httpx.Response)
    assert len(setup.reads) == 2 * (1 + READ_RETRIES if failed else 1) and len(calls) == 2


def test_an_unreadable_definition_logs_only_its_error_type_once_until_read(setup, caplog):
    # Not found, a server error the SDK's read retry recovers from with the readable
    # definition, then another workflow's definition.
    answers = iter(
        [None, httpx.Response(500, json={"message": "private fixture detail"}), INTO_LOOP]
        + [{**INTO_LOOP, "id": "another"}] * 2
    )
    waiting = into_loop()
    # The step stops waiting after the read, so the next waiting period reads again.
    replies = [waiting] * 3 + [into_loop("success")] + [waiting] * 2
    coordinator, _, _, record = setup(replies, definition=lambda _: next(answers))
    with caplog.at_level(logging.WARNING, logger="scenario"):
        for _ in replies:
            coordinator.refresh_remote("request", expected_revision=record.revision)
    messages = [
        record.getMessage()
        for record in caplog.records
        if record.getMessage().startswith("Workflow step links unavailable")
    ]
    assert len(setup.reads) == 5
    # One line per unreadable stretch: the type name only, never the response, URL or IDs.
    assert len(messages) == 2
    assert all(re.fullmatch(r"Workflow step links unavailable \(\w+\)", item) for item in messages)
    assert "private fixture detail" not in caplog.text and "Signature" not in caplog.text


@pytest.mark.parametrize("definition", [INTO_LOOP, None])
def test_a_selection_the_flow_does_not_link_is_never_chosen_into_a_loop(setup, definition):
    # The live defect: the job flow alone showed no link from the selection to the loop.
    waiting = into_loop()
    coordinator, store, calls, record = setup([waiting], definition=definition)
    review = linked_step("select1", waiting, definition).review_id
    with pytest.raises(StepError) as error:
        decide(coordinator, record, "select1", waiting, "select", [0, 2], review=review)
    assert str(error.value) == BLOCKED["loop" if definition else "unverified"]
    assert [request.method for request in calls] == ["GET"]
    assert store.get("request") == record


def test_rejecting_an_unverified_selection_is_still_sent(setup):
    waiting = into_loop()
    rejected = into_loop("rejected", "canceled")
    coordinator, _, calls, record = setup([waiting, {"jobId": "remote"}, rejected])
    review = linked_step("select1", waiting, None).review_id
    snapshot = decide(coordinator, record, "select1", waiting, "reject", review=review)
    assert snapshot.sent and snapshot.record.state == JobState.CANCELED
    assert json.loads(calls[1].content)["action"] == "reject"


def test_a_selection_after_a_loop_is_sent_with_the_definition(setup):
    waiting = after_loop()
    coordinator, _, calls, record = setup(
        [waiting, {"jobId": "remote"}, live_job(status="in-progress")], definition=AFTER_LOOP
    )
    review = linked_step("select1", waiting, AFTER_LOOP).review_id
    # A projection without the definition is a different review.
    assert review != linked_step("select1", waiting, None).review_id
    snapshot = decide(coordinator, record, "select1", waiting, "select", [0, 2], review=review)
    assert snapshot.sent and len(puts(calls)) == 1
    assert json.loads(calls[1].content)["selectedIndices"] == [0, 2]
    assert len(setup.reads) == 1


def test_a_review_made_with_links_conflicts_when_the_definition_is_now_unreadable(setup):
    waiting = after_loop()
    coordinator, store, calls, record = setup([waiting], definition=None)
    review = linked_step("select1", waiting, AFTER_LOOP).review_id
    with pytest.raises(StoreConflict, match="step changed"):
        decide(coordinator, record, "select1", waiting, "select", [0, 2], review=review)
    assert [request.method for request in calls] == ["GET"]


def test_an_approval_decision_is_bound_to_its_linked_review_assets(setup):
    waiting = live_job(
        {"id": "approval1", "type": "user-approval", "status": "processing"},
        {
            "id": "cutout1",
            "type": "custom-model",
            "status": "success",
            "assets": [{"assetId": "asset_cut", "url": SIGNED}],
        },
    )
    coordinator, _, calls, record = setup(
        [waiting, {"jobId": "remote"}, live_job(status="in-progress")], definition=APPROVAL
    )
    step = linked_step("approval1", waiting, APPROVAL)
    assert step.review_asset_ids == ("asset_cut",) and step.depends_on == ("cutout1",)
    snapshot = decide(coordinator, record, "approval1", waiting, "approve", review=step.review_id)
    assert snapshot.sent and json.loads(calls[1].content)["action"] == "approve"
    # The step no longer waits after the decision, so no links are kept.
    assert snapshot.links is None and coordinator._step_links_cache == {}
    assert len(setup.reads) == 1
