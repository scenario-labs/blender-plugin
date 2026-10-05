# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Read and recheck scoped Film composition inputs without reserving or sending work."""

import json
from dataclasses import dataclass

from ..scene.film_finish import compose_recipe, required_sources
from ..scene.film_plan import TaskAssets, validate_film_plan
from .film_tasks import _recipe_context, _upload_evidence
from .store import JobScope, JobState, StoreConflict, StoredJob, _identity, _json


@dataclass(frozen=True)
class CompositionSource:
    task_id: str
    scope: JobScope
    request_id: str
    revision: int
    asset_id: str
    kind: str
    task_sha256: str


@dataclass(frozen=True)
class CompositionDraft:
    production_id: str
    mode: str
    score_task_id: str
    recipe_json: str
    sources: tuple[CompositionSource, ...]

    @property
    def recipe(self):
        return json.loads(self.recipe_json)


def composition_sources(
    store, recipe, *, production_id, mode="final", score_task_id="score", inspect_upload=None
):
    """Observe exact typed outputs; metadata is not local file verification."""
    _identity(production_id)
    _, tasks, digests, _ = _recipe_context(store, recipe)
    observed = []
    for task_id, media_kind in required_sources(
        recipe, mode=mode, score_task_id=score_task_id
    ).items():
        kind = tasks[task_id]["kind"]
        task_sha256 = digests[task_id]
        if kind == "upload":
            attached = store.film_upload(production_id, task_id)
            if attached is None or attached.film_task.task_sha256 != task_sha256:
                raise ValueError("Choose a matching imported Film upload")
            current = _upload_evidence(
                inspect_upload,
                attached.film_task,
                store.scope,
                attached.upload_request_id,
                attached.upload_revision,
            )
            if current != attached or current.kind != media_kind:
                raise ValueError("The Film upload scope, revision or media kind changed")
            request_id, revision, asset_id = (
                current.upload_request_id,
                current.upload_revision,
                current.asset_id,
            )
        else:
            saved = store.film_job(production_id, task_id)
            if (
                not isinstance(saved, StoredJob)
                or saved.intent.scope != store.scope
                or saved.intent.operation != "model"
                or saved.intent.film_task is None
                or saved.intent.film_task.production_id != production_id
                or saved.intent.film_task.task_id != task_id
                or saved.intent.film_task.task_sha256 != task_sha256
                or saved.intent.target_id != tasks[task_id]["model"]
                or saved.state
                not in {
                    JobState.SUCCEEDED,
                    JobState.DOWNLOADING,
                    JobState.DOWNLOAD_FAILED,
                    JobState.READY,
                    JobState.APPLYING,
                    JobState.APPLY_FAILED,
                    JobState.APPLIED,
                }
                or len(saved.results) != 1
                or not saved.results[0].asset.media_type.startswith(media_kind + "/")
            ):
                raise ValueError(
                    "Choose one matching completed Film output of the expected media kind"
                )
            request_id, revision, asset_id = (
                saved.intent.request_id,
                saved.revision,
                saved.results[0].asset.asset_id,
            )
        observed.append(
            CompositionSource(
                task_id,
                store.scope,
                request_id,
                revision,
                asset_id,
                media_kind,
                task_sha256,
            )
        )
    return tuple(observed)


def _unused_master(store, recipe, production_id, mode):
    master = validate_film_plan(recipe)[mode + "_master_task"]
    if store.film_job(production_id, master) or store.film_upload(production_id, master):
        raise StoreConflict("Master task already has saved work; name a new take")


def prepare_composition(
    store,
    recipe,
    *,
    production_id,
    mode="final",
    score_task_id="score",
    audio_durations=None,
    inspect_upload=None,
):
    """Produce immutable review data; never change a recipe, claim a job or quote."""
    sources = composition_sources(
        store,
        recipe,
        production_id=production_id,
        mode=mode,
        score_task_id=score_task_id,
        inspect_upload=inspect_upload,
    )
    _unused_master(store, recipe, production_id, mode)
    draft = compose_recipe(
        recipe,
        {s.task_id: TaskAssets(s.scope, (s.asset_id,)) for s in sources},
        scope=store.scope,
        mode=mode,
        score_task_id=score_task_id,
        audio_durations=audio_durations,
    )
    return CompositionDraft(production_id, mode, score_task_id, _json(draft), sources)


def validate_composition_sources(store, draft, *, inspect_upload=None):
    """Recheck measured source identities, including after reserving this master."""
    if not isinstance(draft, CompositionDraft):
        raise ValueError("Use a prepared composition draft")
    sources = composition_sources(
        store,
        draft.recipe,
        production_id=draft.production_id,
        mode=draft.mode,
        score_task_id=draft.score_task_id,
        inspect_upload=inspect_upload,
    )
    if sources != draft.sources:
        raise ValueError("Composition sources changed; prepare a fresh draft")
    return draft.recipe


def validate_composition_draft(store, draft, *, inspect_upload=None):
    """Recheck sources and unused master; this read grants no spending authority."""
    recipe = validate_composition_sources(store, draft, inspect_upload=inspect_upload)
    _unused_master(store, recipe, draft.production_id, draft.mode)
    return recipe
