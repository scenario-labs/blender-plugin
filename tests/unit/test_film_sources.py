# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Film hero selections require exact saved scope, task, revision and GLB metadata."""

import copy
from dataclasses import replace
from types import SimpleNamespace

import pytest

from scenario.core.jobs.film_sources import select_shot_sources, shot_records
from scenario.core.jobs.film_tasks import _task_context
from scenario.core.jobs.store import (
    JobIntent,
    JobOrigin,
    JobScope,
    JobState,
    JobStore,
    ResultAsset,
)
from scenario.core.jobs.transfers import DownloadedResult
from scenario.core.scene.film_scene_plan import local_plan


@pytest.fixture
def env(tmp_path):
    raw = {
        "title": "Fixture",
        "fps": 30,
        "heroes": {
            "hero": {"name": "Hero", "description": "Fixture", "mesh": "mesh", "reference": "ref"}
        },
        "tasks": [
            {
                "id": "mesh",
                "title": "Mesh",
                "kind": "model",
                "model": "model",
                "parameters": {"prompt": "fixture"},
            }
        ],
        "shots": [
            {
                "id": "shot",
                "title": "Shot",
                "duration": 4,
                "scene": local_plan("studio", "", 4),
                "actors": [{"hero": "hero", "name": "Actor", "location": [0, 0, 0]}],
            }
        ],
    }
    store = JobStore(tmp_path / "jobs.sqlite3", JobScope("https://fixture.invalid/v1", "account"))
    origin = JobOrigin("file", "scene", "revision")
    binding, *_ = _task_context(
        store, raw, production_id="production", task_id="mesh", kind="model"
    )
    row = store.create(
        JobIntent(
            "request",
            store.scope,
            origin,
            "model",
            "model",
            "a" * 64,
            "b" * 64,
            "1",
            film_task=binding,
        )
    )
    for state in (JobState.SUBMITTING, JobState.REMOTE, JobState.SUCCEEDED):
        row = store.transition(
            "request",
            expected_revision=row.revision,
            state=state,
            remote_job_id="remote" if state == JobState.REMOTE else None,
        )
    row = store.set_results(
        "request",
        (ResultAsset("asset", "hero.glb", "model/gltf-binary"),),
        expected_revision=row.revision,
    )
    row = store.transition("request", expected_revision=row.revision, state=JobState.DOWNLOADING)
    row = store.record_download(
        "request",
        "asset",
        DownloadedResult("hero.glb", 4, "c" * 64),
        expected_revision=row.revision,
    )
    row = store.transition("request", expected_revision=row.revision, state=JobState.READY)
    return SimpleNamespace(
        store=store,
        raw=raw,
        row=row,
        choice={"hero": {"request_id": "request", "revision": row.revision, "asset_id": "asset"}},
    )


def select(e, **options):
    return select_shot_sources(
        e.store, e.raw, production_id="production", shot_id="shot", selections=e.choice, **options
    )


def test_default_project_scope_and_explicit_output_selection(env):
    before = env.store.records()
    result = select(env)
    assert result[0].record == env.row
    assert result[0].hero_id == "hero"
    assert result[0].result == env.row.results[0]
    assert env.store.records() == before


@pytest.mark.parametrize(
    "field,value",
    [("request_id", "other"), ("revision", 0), ("revision", True), ("asset_id", "other")],
)
def test_stale_or_foreign_observation_rejected(env, field, value):
    env.choice["hero"][field] = value
    with pytest.raises(ValueError):
        select(env)


@pytest.mark.parametrize("selection", [{}, {"hero": {}}, {"extra": {}}, {"hero": None}, []])
def test_complete_explicit_selection_required(env, selection):
    env.choice = selection
    with pytest.raises(ValueError):
        select(env)


def test_unrelated_editorial_change_preserves_exact_task_reuse(env):
    env.raw["title"] = "New editorial title"
    assert select(env)[0].record == env.row


def test_changed_model_payload_rejects_old_task_output(env):
    env.raw["tasks"][0]["parameters"]["prompt"] = "different"
    with pytest.raises(ValueError, match="matching"):
        select(env)


def test_transitive_dependency_change_rejects_output(env, tmp_path):
    # Rebind the synthetic saved task to the original dependency-aware digest.
    dep = {
        "id": "ref",
        "title": "Ref",
        "kind": "model",
        "model": "model",
        "parameters": {"prompt": "first"},
    }
    env.raw["tasks"].insert(0, dep)
    env.raw["tasks"][1]["parameters"] = {"prompt": "$ref"}
    binding, *_ = _task_context(
        env.store, env.raw, production_id="production", task_id="mesh", kind="model"
    )
    saved = replace(env.row, intent=replace(env.row.intent, film_task=binding))
    proxy = SimpleNamespace(scope=env.store.scope, film_job=lambda *_: saved)
    assert select_shot_sources(
        proxy, env.raw, production_id="production", shot_id="shot", selections=env.choice
    )
    dep["parameters"]["prompt"] = "changed"
    with pytest.raises(ValueError, match="matching"):
        select_shot_sources(
            proxy, env.raw, production_id="production", shot_id="shot", selections=env.choice
        )


@pytest.mark.parametrize(
    "field,value", [("account_id", "other"), ("project_id", "other"), ("team_id", "other")]
)
def test_foreign_scope_cannot_supply_a_matching_named_job(env, field, value):
    row = replace(
        env.row,
        intent=replace(env.row.intent, scope=replace(env.row.intent.scope, **{field: value})),
    )
    env.store = SimpleNamespace(scope=env.store.scope, film_job=lambda *_: row)
    with pytest.raises(ValueError, match="matching"):
        select(env)


@pytest.mark.parametrize(
    "state", [JobState.SUCCEEDED, JobState.DOWNLOADING, JobState.DOWNLOAD_FAILED, JobState.APPLYING]
)
def test_incomplete_or_uncertain_result_is_not_eligible(env, state):
    row = replace(env.row, state=state)
    env.store = SimpleNamespace(scope=env.store.scope, film_job=lambda *_: row)
    with pytest.raises(ValueError, match="matching"):
        select(env)


def test_multiple_actors_share_one_explicit_hero_selection(env):
    env.raw["shots"][0]["actors"].append({"hero": "hero", "name": "Second", "location": [3, 0, 0]})
    assert len(select(env)) == 1


def test_no_hero_shot_needs_no_result_or_discovery(env):
    env.raw["shots"][0]["actors"] = []
    env.choice = {}
    assert select(env) == ()


def test_recipe_project_override_must_match_selected_scope(env):
    env.raw["project_id"] = "other"
    with pytest.raises(ValueError, match="project"):
        select(env)


def test_missing_model_task_and_wrong_shot_rejected(env):
    raw = copy.deepcopy(env.raw)
    raw["heroes"]["hero"]["mesh"] = "absent"
    with pytest.raises(ValueError):
        shot_records(env.store, raw, production_id="production", shot_id="shot")
    with pytest.raises(ValueError):
        shot_records(env.store, env.raw, production_id="production", shot_id="absent")
