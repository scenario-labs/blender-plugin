# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Select explicit downloaded hero outputs from matching scoped Film tasks."""

from dataclasses import dataclass

from ..scene.film_plan import require_plan_scope, validate_film_plan
from .film_tasks import _task_context
from .store import JobState, LocalApplicationState, StoredJob, StoredResult, _identity


@dataclass(frozen=True)
class FilmHeroResult:
    hero_id: str
    record: StoredJob
    result: StoredResult


def shot_records(store, recipe, *, production_id, shot_id):
    """Read eligible saved models; metadata is not file verification or approval."""
    _identity(production_id)
    plan = validate_film_plan(recipe)
    require_plan_scope(plan, store.scope)
    shot = next((item for item in plan["shots"] if item["id"] == shot_id), None)
    if shot is None:
        raise ValueError("Choose a shot from the current Film recipe")
    records = []
    for hero in sorted({actor["hero"] for actor in shot["actors"]}):
        task_id = plan["heroes"][hero]["mesh"]
        binding, tasks, _, _ = _task_context(
            store, recipe, production_id=production_id, task_id=task_id, kind="model"
        )
        saved = store.film_job(production_id, task_id)
        if (
            not isinstance(saved, StoredJob)
            or saved.intent.scope != store.scope
            or saved.intent.operation != "model"
            or saved.intent.film_task is None
            or saved.intent.film_task.production_id != production_id
            or saved.intent.film_task.task_id != task_id
            or saved.intent.film_task.task_sha256 != binding.task_sha256
            or saved.intent.target_id != tasks[task_id]["model"]
            or saved.state not in {JobState.READY, JobState.APPLY_FAILED, JobState.APPLIED}
            or any(
                item.state == LocalApplicationState.APPLYING for item in saved.local_applications
            )
        ):
            raise ValueError("Each hero needs a matching downloaded Film model task")
        if not any(
            item.asset.media_type == "model/gltf-binary" and item.receipt for item in saved.results
        ):
            raise ValueError("The hero task has no downloaded GLB result")
        records.append((hero, saved))
    return tuple(records)


def select_shot_sources(store, recipe, *, production_id, shot_id, selections):
    """Bind every hero to an observed job revision and explicitly selected GLB."""
    records = shot_records(store, recipe, production_id=production_id, shot_id=shot_id)
    if not isinstance(selections, dict) or set(selections) != {hero for hero, _ in records}:
        raise ValueError("Select exactly one saved GLB for each shot hero")
    selected = []
    for hero, record in records:
        choice = selections[hero]
        if (
            not isinstance(choice, dict)
            or set(choice) != {"request_id", "revision", "asset_id"}
            or choice["request_id"] != record.intent.request_id
            or type(choice["revision"]) is not int
            or choice["revision"] != record.revision
        ):
            raise ValueError("The hero job changed; inspect its current revision")
        matches = [item for item in record.results if item.asset.asset_id == choice["asset_id"]]
        if (
            len(matches) != 1
            or matches[0].asset.media_type != "model/gltf-binary"
            or matches[0].receipt is None
        ):
            raise ValueError("Select a downloaded GLB output from the hero task")
        selected.append(FilmHeroResult(hero, record, matches[0]))
    return tuple(selected)
