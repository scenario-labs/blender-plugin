# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Composition drafts read durable scoped tasks without writing or spending."""

import copy
from dataclasses import replace
from fractions import Fraction
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from scenario.core.jobs.film_finishing import (
    composition_sources,
    prepare_composition,
    validate_composition_draft,
)
from scenario.core.jobs.film_tasks import _task_context, model_task_request, upload_task_reference
from scenario.core.jobs.store import (
    JobIntent,
    JobOrigin,
    JobScope,
    JobState,
    JobStore,
    ResultAsset,
    StoreConflict,
)
from scenario.core.jobs.upload_store import UploadIntent, UploadState, UploadStore
from scenario.core.scene.film_finish import AudioDuration
from scenario.core.scene.film_scene_plan import local_plan


def saved_model(e, task_id, *, kind="video", count=1, state=JobState.SUCCEEDED):
    binding, tasks, *_ = _task_context(
        e.store, e.recipe, production_id="production", task_id=task_id, kind="model"
    )
    row = e.store.create(
        JobIntent(
            task_id,
            e.store.scope,
            e.origin,
            "model",
            tasks[task_id]["model"],
            "a" * 64,
            "b" * 64,
            "1",
            film_task=binding,
        )
    )
    for target in (JobState.SUBMITTING, JobState.REMOTE, JobState.SUCCEEDED):
        if row.state == state:
            return row
        row = e.store.transition(
            task_id,
            expected_revision=row.revision,
            state=target,
            remote_job_id="remote-" + task_id if target == JobState.REMOTE else None,
        )
    if count == 0:
        return row
    return e.store.set_results(
        task_id,
        tuple(
            ResultAsset(f"asset-{task_id}-{i}", f"source-{i}.bin", kind + "/mp4")
            for i in range(count)
        ),
        expected_revision=row.revision,
    )


def saved_upload(e, *, kind="audio"):
    row = e.uploads.create(
        UploadIntent(
            "score",
            e.store.scope,
            e.origin,
            kind,
            "score.wav",
            "audio/wav",
            4,
            "c" * 64,
            4,
            ("c" * 64,),
        )
    )
    for state in (UploadState.INITIALIZING, UploadState.UPLOADING, UploadState.IMPORTED):
        row = e.uploads.transition(
            "score",
            expected_revision=row.revision,
            state=state,
            upload_id="upload-score" if state == UploadState.UPLOADING else None,
            asset_id="asset-score" if state == UploadState.IMPORTED else None,
        )
    reference = upload_task_reference(
        e.store,
        e.recipe,
        production_id="production",
        task_id="score",
        inspect_upload=e.uploads.get,
        request_id="score",
        expected_revision=row.revision,
    )
    e.store.bind_film_upload(reference)
    return row


@pytest.fixture
def env(tmp_path):
    scope = JobScope("https://fixture.invalid/v1", "account")
    recipe = {
        "title": "Composition",
        "fps": 30,
        "shots": [
            {"id": "shot", "title": "Shot", "duration": 4, "scene": local_plan("studio", "", 4)}
        ],
        "tasks": [
            {
                "id": "shot-video",
                "title": "Shot",
                "kind": "model",
                "model": "model",
                "parameters": {"prompt": "fixture"},
            },
            {"id": "score", "title": "Score", "kind": "upload"},
        ],
    }
    return SimpleNamespace(
        store=JobStore(tmp_path / "jobs.sqlite3", scope),
        uploads=UploadStore(tmp_path / "uploads.sqlite3", scope),
        origin=JobOrigin("file", "scene", "revision"),
        recipe=recipe,
    )


def prepare(e):
    return prepare_composition(
        e.store,
        e.recipe,
        production_id="production",
        inspect_upload=e.uploads.get,
        audio_durations={"score": AudioDuration(e.store.scope, "asset-score", Fraction(2))},
    )


def test_source_resolution_computes_dependency_identities_once(env):
    from scenario.core.jobs import film_tasks

    shot = env.recipe["shots"][0]
    task = env.recipe["tasks"][0]
    env.recipe["shots"] = [dict(shot, id=f"shot{i}") for i in range(10)]
    env.recipe["tasks"] = [dict(task, id=f"shot{i}-video") for i in range(10)] + [
        env.recipe["tasks"][1]
    ]
    for i in range(10):
        saved_model(env, f"shot{i}-video")
    saved_upload(env)
    with (
        patch.object(
            film_tasks, "validate_film_plan", wraps=film_tasks.validate_film_plan
        ) as validate,
        patch.object(film_tasks, "_digest", wraps=film_tasks._digest) as digest,
    ):
        sources = composition_sources(
            env.store, env.recipe, production_id="production", inspect_upload=env.uploads.get
        )
    assert len(sources) == 11
    validate.assert_called_once()
    assert digest.call_count == len(env.recipe["tasks"])


def test_draft_reads_scoped_saved_sources_and_resolves_through_existing_film_command(env):
    saved_model(env, "shot-video")
    saved_upload(env)
    before, jobs, uploads = copy.deepcopy(env.recipe), env.store.records(), env.uploads.records()
    draft = prepare(env)
    assert env.recipe == before and env.store.records() == jobs and env.uploads.records() == uploads
    fresh = validate_composition_draft(env.store, draft, inspect_upload=env.uploads.get)
    fresh["title"] = "mutable caller copy"
    assert draft.recipe["title"] == "Composition"
    binding, model, params = model_task_request(
        env.store,
        draft.recipe,
        production_id="production",
        task_id="final-master",
        inspect_upload=env.uploads.get,
    )
    assert binding.task_id == "final-master" and model == "model_scenario-compose-video"
    assert [layer["source"] for layer in params["layers"]] == [
        "asset-shot-video-0",
        "asset-score",
        "asset-score",
    ]
    assert env.store.film_job("production", "final-master") is None


@pytest.mark.parametrize(
    "kind,count,state",
    [
        ("image", 1, JobState.SUCCEEDED),
        ("video", 2, JobState.SUCCEEDED),
        ("video", 0, JobState.SUCCEEDED),
        ("video", 1, JobState.PREPARED),
        ("video", 1, JobState.REMOTE),
    ],
)
def test_wrong_ambiguous_missing_or_unfinished_model_outputs_are_rejected(env, kind, count, state):
    saved_model(env, "shot-video", kind=kind, count=count, state=state)
    saved_upload(env)
    with pytest.raises(ValueError):
        prepare(env)


def test_changed_task_or_transitive_dependency_cannot_reuse_old_outputs(env):
    env.recipe["tasks"].insert(
        0,
        {
            "id": "design",
            "title": "Design",
            "kind": "model",
            "model": "model",
            "parameters": {"prompt": "old"},
        },
    )
    env.recipe["tasks"][1]["parameters"]["prompt"] = "$design"
    saved_model(env, "shot-video")
    saved_upload(env)
    env.recipe["tasks"][0]["parameters"]["prompt"] = "new"
    with pytest.raises(ValueError):
        prepare(env)


def test_upload_kind_and_revision_are_current_before_reuse(env):
    saved_model(env, "shot-video")
    saved_upload(env, kind="image")
    with pytest.raises(ValueError):
        prepare(env)


def test_changed_saved_revision_invalidates_existing_draft(env):
    row = saved_model(env, "shot-video")
    saved_upload(env)
    draft = prepare(env)
    env.store.transition(
        row.intent.request_id, expected_revision=row.revision, state=JobState.DOWNLOADING
    )
    with pytest.raises(ValueError, match="changed"):
        validate_composition_draft(env.store, draft, inspect_upload=env.uploads.get)


@pytest.mark.parametrize("dimension", ["service", "account_id", "project_id", "team_id"])
def test_draft_cannot_move_between_scopes_even_with_identical_asset_names(env, tmp_path, dimension):
    saved_model(env, "shot-video")
    saved_upload(env)
    draft = prepare(env)
    foreign = replace(
        env.store.scope,
        **{dimension: "https://other.invalid" if dimension == "service" else "other"},
    )
    other = JobStore(tmp_path / "jobs.sqlite3", foreign)
    with pytest.raises(ValueError):
        validate_composition_draft(other, draft, inspect_upload=env.uploads.get)


def test_reserved_master_blocks_draft_without_creating_a_second_job(env):
    saved_model(env, "shot-video")
    saved_upload(env)
    draft = prepare(env)
    env.recipe = draft.recipe
    saved_model(env, "final-master", state=JobState.PREPARED)
    with pytest.raises(StoreConflict):
        validate_composition_draft(env.store, draft, inspect_upload=env.uploads.get)
    env.recipe["tasks"].pop()
    with pytest.raises(StoreConflict):
        prepare(env)


def test_upload_evidence_changed_after_draft_cannot_authorize_reuse(env):
    saved_model(env, "shot-video")
    row = saved_upload(env)
    draft = prepare(env)
    with patch.object(env.uploads, "get", return_value=replace(row, revision=row.revision + 1)):
        with pytest.raises(ValueError):
            validate_composition_draft(env.store, draft, inspect_upload=env.uploads.get)


def test_model_store_must_return_matching_scope_production_and_model(env):
    row = saved_model(env, "shot-video")
    saved_upload(env)
    for intent in (
        replace(row.intent, scope=replace(env.store.scope, account_id="foreign")),
        replace(row.intent, film_task=replace(row.intent.film_task, production_id="foreign")),
        replace(row.intent, target_id="another-model"),
    ):
        original = env.store.film_job

        def read(production, task_id, intent=intent, original=original):
            return (
                replace(row, intent=intent)
                if task_id == "shot-video"
                else original(production, task_id)
            )

        with patch.object(env.store, "film_job", side_effect=read):
            with pytest.raises(ValueError):
                prepare(env)
