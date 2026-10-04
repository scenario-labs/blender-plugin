# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Film identity, dependency, restart and spend ordering through shared SDK jobs."""

import copy
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, replace
from threading import Barrier, Event
from types import SimpleNamespace

import httpx
import pytest

from scenario.core.api.sdk_adapter import Credentials, SDKAdapter
from scenario.core.jobs.coordinator import JobCoordinator, QuoteError, SubmissionUncertain
from scenario.core.jobs.film_tasks import model_task_request
from scenario.core.jobs.origins import OriginRevisions
from scenario.core.jobs.store import (
    CloudJobIntent,
    FilmTaskBinding,
    JobScope,
    JobState,
    JobStore,
    ResultAsset,
    StoreConflict,
    StoreError,
)
from scenario.core.jobs.workers import JobWorkers
from scenario.core.scene.film_scene_plan import local_plan


def model_task(identifier, prompt="fixture"):
    return {
        "id": identifier,
        "title": identifier,
        "kind": "model",
        "model": "model",
        "parameters": {"prompt": prompt},
    }


def recipe():
    return {
        "title": "Fixture production",
        "shots": [
            {"id": "shot", "title": "Shot", "duration": 4, "scene": local_plan("studio", "", 4)}
        ],
        "tasks": [
            model_task("design"),
            model_task("motion", "$design:1"),
            model_task("final", "$motion"),
        ],
    }


@pytest.fixture
def env(tmp_path):
    scope = JobScope("https://fixture.invalid/v1", "fixture-account")
    revisions = OriginRevisions()
    store = JobStore(tmp_path / "jobs.sqlite3", scope)
    e = SimpleNamespace(
        scope=scope,
        store=store,
        revisions=revisions,
        origin=revisions.capture("scene"),
        calls=[],
        hook=None,
        recipe=recipe(),
    )

    def handler(request):
        e.calls.append(request)
        if e.hook:
            e.hook(request)
        if request.method == "GET":
            return httpx.Response(
                200,
                json={
                    "model": {
                        "id": "model",
                        "type": "custom",
                        "inputs": [{"name": "prompt", "type": "string", "required": True}],
                    }
                },
            )
        if request.url.params.get("dryRun") == "true":
            return httpx.Response(200, content=b'{"creativeUnitsCost":0.10000000000000001}')
        # Observe committed identity from a separate DB connection before spending.
        saved = JobStore(tmp_path / "jobs.sqlite3", scope).records()
        assert any(
            row.state == JobState.SUBMITTING and row.intent.film_task is not None for row in saved
        )
        return httpx.Response(200, json={"job": {"jobId": "remote-" + str(len(e.calls))}})

    adapter = SDKAdapter(
        Credentials("fixture", "fixture-secret"),
        online=lambda: True,
        base_url=scope.service,
        account_id=scope.account_id,
        transport=httpx.MockTransport(handler),
    )
    e.coordinator = JobCoordinator(adapter, store, origin_guard=revisions.guard)
    yield e
    e.coordinator.close()


def quote(e, task="design", production="production", raw=None):
    return e.coordinator.quote_film_task(
        e.recipe if raw is None else raw, production_id=production, task_id=task, origin=e.origin
    )


def submit(e, prepared):
    return e.coordinator.submit(
        prepared,
        origin=e.origin,
        operation="model",
        target_id="model",
        payload=prepared.estimate.payload,
    )


def complete(e, task="design"):
    prepared = e.coordinator.prepare_quote(quote(e, task))
    row = submit(e, prepared)
    row = e.store.transition(
        row.intent.request_id, expected_revision=row.revision, state=JobState.SUCCEEDED
    )
    return e.store.set_results(
        row.intent.request_id,
        tuple(ResultAsset(f"{task}-{i}", f"result-{i}.png", "image/png") for i in range(2)),
        expected_revision=row.revision,
    )


def test_exact_bound_intent_is_saved_before_paid_request_and_reopens(env, tmp_path):
    q = quote(env)
    assert env.store.records() == ()
    assert q.estimate.payload == {"prompt": "fixture"}
    prepared = env.coordinator.prepare_quote(q)
    assert prepared.intent.film_task == q.film_task
    result = submit(env, prepared)
    saved = JobStore(tmp_path / "jobs.sqlite3", env.scope).film_job("production", "design")
    assert saved == result
    assert saved.intent.quote_cost == "0.10000000000000001"
    assert [dict(r.url.params) for r in env.calls] == [{}, {"dryRun": "true"}, {}]
    assert "film" not in env.calls[-1].content.decode()
    assert '"prompt"' not in json.dumps(asdict(saved))
    assert env.recipe["title"] not in json.dumps(asdict(saved))
    with pytest.raises(ValueError):
        submit(env, prepared)


@pytest.mark.parametrize(
    "stage", ["prepared", "canceled", "uncertain", "remote", "failed", "succeeded"]
)
def test_saved_take_blocks_new_quotes_even_after_restart_or_recipe_edit(env, tmp_path, stage):
    prepared = env.coordinator.prepare_quote(quote(env))
    row = env.store.get(prepared.intent.request_id)
    if stage == "canceled":
        row = env.coordinator.cancel_prepared(row.intent.request_id, expected_revision=row.revision)
    elif stage != "prepared":
        row = env.store.transition(
            row.intent.request_id, expected_revision=row.revision, state=JobState.SUBMITTING
        )
        row = env.store.transition(
            row.intent.request_id,
            expected_revision=row.revision,
            state=JobState.UNCERTAIN if stage == "uncertain" else JobState.REMOTE,
            **({} if stage == "uncertain" else {"remote_job_id": "remote"}),
        )
        if stage in {"failed", "succeeded"}:
            row = env.store.transition(
                row.intent.request_id, expected_revision=row.revision, state=JobState(stage)
            )
    changed = copy.deepcopy(env.recipe)
    changed["tasks"][0]["parameters"]["prompt"] = "changed"
    before = len(env.calls)
    with pytest.raises(StoreConflict, match="already"):
        quote(env, raw=changed)
    reopened = JobStore(tmp_path / "jobs.sqlite3", env.scope)
    with pytest.raises(StoreConflict):
        model_task_request(reopened, changed, production_id="production", task_id="design")
    assert reopened.film_job("production", "design") == row
    assert len(env.calls) == before


def test_uncertain_sdk_submission_preserves_task_and_never_retries(env):
    prepared = env.coordinator.prepare_quote(quote(env))

    def fail(request):
        raise httpx.ReadTimeout("synthetic private error", request=request)

    env.hook = fail
    with pytest.raises(SubmissionUncertain):
        submit(env, prepared)
    assert len(env.calls) == 3
    assert env.store.film_job("production", "design").state == JobState.UNCERTAIN
    with pytest.raises(StoreConflict):
        quote(env)
    assert len(env.calls) == 3


def test_two_quotes_and_competing_connections_reserve_one_take(env, tmp_path):
    first, second = quote(env), quote(env)
    seed = env.coordinator.prepare_quote(first).intent
    with pytest.raises(StoreConflict):
        env.coordinator.prepare_quote(second)
    assert len(env.store.records()) == 1
    barrier = Barrier(2)

    def create(number):
        store = JobStore(tmp_path / "jobs.sqlite3", env.scope)
        intent = replace(
            seed,
            request_id=f"racer-{number}",
            film_task=replace(seed.film_task, task_id="take-two", recipe_sha256=str(number) * 64),
        )
        barrier.wait(5)
        try:
            return store.create(intent)
        except StoreConflict:
            return None

    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(create, [1, 2]))
    assert sum(row is not None for row in results) == 1
    assert len(env.store.records()) == 2
    assert all(r.url.params.get("dryRun") == "true" or r.method == "GET" for r in env.calls)


def test_commit_failure_leaves_no_task_reservation_and_sends_nothing(env, monkeypatch):
    q = quote(env)
    original = sqlite3.connect

    class FailCommit(sqlite3.Connection):
        def commit(self):
            raise sqlite3.OperationalError("fixture")

    with monkeypatch.context() as patch:
        patch.setattr(sqlite3, "connect", lambda *a, **k: original(*a, **k, factory=FailCommit))
        with pytest.raises(StoreError):
            env.coordinator.prepare_quote(q)
    assert env.store.records() == ()
    assert len(env.calls) == 2


def test_committed_but_unacknowledged_preparation_cannot_create_second_take(env, monkeypatch):
    q = quote(env)
    create = env.store.create

    def committed(intent):
        create(intent)
        raise StoreError("lost acknowledgement")

    monkeypatch.setattr(env.store, "create", committed)
    with pytest.raises(StoreError):
        env.coordinator.prepare_quote(q)
    with pytest.raises(StoreConflict):
        quote(env)
    with pytest.raises(StoreConflict):
        env.coordinator.prepare_quote(q)
    assert len(env.store.records()) == 1
    assert len(env.calls) == 2


def test_saved_ordered_outputs_resolve_without_download_and_changed_dependencies_fail(env):
    complete(env)
    q = quote(env, "motion")
    assert q.estimate.payload == {"prompt": "design-1"}
    prepared = env.coordinator.prepare_quote(q)
    row = submit(env, prepared)
    row = env.store.transition(
        row.intent.request_id, expected_revision=row.revision, state=JobState.SUCCEEDED
    )
    env.store.set_results(
        row.intent.request_id,
        (ResultAsset("motion-output", "motion.mp4", "video/mp4"),),
        expected_revision=row.revision,
    )
    assert quote(env, "final").estimate.payload == {"prompt": "motion-output"}
    changed = copy.deepcopy(env.recipe)
    changed["tasks"][0]["parameters"]["prompt"] = "different ancestor"
    before = len(env.calls)
    with pytest.raises(ValueError, match="matching completed"):
        quote(env, "final", raw=changed)
    assert len(env.calls) == before


def test_appended_take_preserves_unchanged_dependency_and_new_recipe_digest(env):
    saved = complete(env)
    env.recipe["tasks"].append(model_task("take-two", "$design"))
    q = quote(env, "take-two")
    assert q.estimate.payload == {"prompt": "design-0"}
    assert q.film_task.recipe_sha256 != saved.intent.film_task.recipe_sha256
    prepared = env.coordinator.prepare_quote(q)
    assert prepared.intent.film_task.task_id == "take-two"
    assert env.store.film_job("production", "design") == saved


@pytest.mark.parametrize(
    "change",
    [
        {"account_id": "other"},
        {"project_id": "other"},
        {"team_id": "other"},
        {"service": "https://other.invalid/v1"},
    ],
)
def test_foreign_scope_cannot_resolve_outputs_and_has_independent_reservations(
    env, tmp_path, change
):
    saved = complete(env)
    store = JobStore(tmp_path / "jobs.sqlite3", replace(env.scope, **change))
    assert store.film_job("production", "design") is None
    with pytest.raises(ValueError, match="completed"):
        model_task_request(store, env.recipe, production_id="production", task_id="motion")
    store.create(replace(saved.intent, scope=store.scope))
    assert env.store.film_job("production", "design") == saved


@pytest.mark.parametrize(
    "damage",
    ["missing", "pending", "manifest", "other-production", "cloud", "index", "task-changed"],
)
def test_unverified_or_mismatched_dependencies_fail_before_any_service_call(env, damage):
    if damage != "missing":
        if damage == "cloud":
            env.store.adopt_cloud_job(
                CloudJobIntent("cloud", env.scope, env.origin, "model"), "remote"
            )
        elif damage in {"pending", "manifest"}:
            prepared = env.coordinator.prepare_quote(quote(env))
            if damage == "manifest":
                row = submit(env, prepared)
                env.store.transition(
                    row.intent.request_id, expected_revision=row.revision, state=JobState.SUCCEEDED
                )
        else:
            complete(env)
    if damage == "index":
        env.recipe["tasks"][1]["parameters"]["prompt"] = "$design:9"
    if damage == "task-changed":
        env.recipe["tasks"][0]["model"] = "different-model"
    before = len(env.calls)
    with pytest.raises(ValueError):
        quote(
            env, "motion", production="different" if damage == "other-production" else "production"
        )
    assert len(env.calls) == before


@pytest.mark.parametrize(
    "damage", ["self", "forward", "missing", "invalid", "upload", "project", "unknown-task"]
)
def test_invalid_plan_and_unsupported_upload_binding_fail_before_io(env, damage):
    if damage in {"self", "forward", "missing", "invalid"}:
        env.recipe["tasks"][0]["parameters"]["prompt"] = {
            "self": "$design",
            "forward": "$motion",
            "missing": "$absent",
            "invalid": "$design:-1",
        }[damage]
    elif damage == "upload":
        env.recipe["tasks"][0] = {"id": "design", "title": "Upload", "kind": "upload"}
    elif damage == "project":
        env.recipe["project_id"] = "other"
    with pytest.raises(ValueError):
        quote(
            env,
            "absent" if damage == "unknown-task" else "motion" if damage == "upload" else "design",
        )
    assert env.calls == []


def test_worker_copies_recipe_and_origin_guard_rejects_late_quote(env):
    entered, release = Event(), Event()

    def wait(request):
        if request.method == "GET":
            entered.set()
            assert release.wait(5)

    env.hook = wait
    workers = JobWorkers(env.coordinator, workers=1)
    try:
        task = workers.quote_film_task(
            env.recipe, production_id="production", task_id="design", origin=env.origin
        )
        assert entered.wait(5)
        env.recipe["tasks"][0]["parameters"]["prompt"] = "edited"
        release.set()
        q = task.result(5)
        assert q.estimate.payload == {"prompt": "fixture"}
        env.revisions.invalidate("scene")
        with pytest.raises(QuoteError):
            env.coordinator.prepare_quote(q)
        assert env.store.records() == ()
    finally:
        release.set()
        workers.shutdown()


@pytest.mark.parametrize("damage", ["missing", "list", "truncated", "digest", "task", "operation"])
def test_corrupt_current_binding_fails_closed(env, damage):
    prepared = env.coordinator.prepare_quote(quote(env))
    path = env.store._path
    with sqlite3.connect(path) as connection:
        raw = json.loads(connection.execute("SELECT record FROM jobs").fetchone()[0])
        intent = raw["intent"]
        if damage == "missing":
            del intent["film_task"]
        elif damage == "list":
            intent["film_task"] = []
        elif damage == "truncated":
            del intent["film_task"]["task_sha256"]
        elif damage == "digest":
            intent["film_task"]["recipe_sha256"] = "bad"
        elif damage == "task":
            intent["film_task"]["task_id"] = "bad/task"
        else:
            intent["operation"] = "workflow"
        connection.execute("UPDATE jobs SET record=?", (json.dumps(raw),))
    with pytest.raises(StoreError):
        env.store.get(prepared.intent.request_id)


def test_duplicate_task_records_fail_inspection_instead_of_selecting_one(env):
    prepared = env.coordinator.prepare_quote(quote(env))
    row = env.store.get(prepared.intent.request_id)
    second = replace(row, intent=replace(row.intent, request_id="duplicate"))
    with sqlite3.connect(env.store._path) as connection:
        connection.execute(
            "INSERT INTO jobs VALUES (?, ?, ?, ?)",
            (env.store._key, "duplicate", 0, json.dumps(asdict(second))),
        )
    with pytest.raises(StoreError, match="multiple"):
        env.store.film_job("production", "design")


@pytest.mark.parametrize(
    "change",
    [
        {"production_id": "bad/path"},
        {"task_id": ""},
        {"task_id": "x" * 97},
        {"recipe_sha256": "x" * 64},
        {"task_sha256": None},
    ],
)
def test_invalid_identity_cannot_be_persisted(change):
    with pytest.raises(ValueError):
        FilmTaskBinding(
            **(
                {
                    "production_id": "production",
                    "task_id": "task",
                    "recipe_sha256": "a" * 64,
                    "task_sha256": "b" * 64,
                }
                | change
            )
        )
