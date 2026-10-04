# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Bind Film model tasks to the shared scoped store, without another job engine."""

import hashlib
import re

from ..scene.film_plan import (
    TaskAssets,
    require_plan_scope,
    resolve_references,
    validate_film_plan,
)
from .store import FilmTaskBinding, JobState, StoreConflict, _json


def _digest(value):
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _references(value):
    if isinstance(value, dict):
        for item in value.values():
            yield from _references(item)
    elif isinstance(value, list):
        for item in value:
            yield from _references(item)
    elif isinstance(value, str) and value.startswith("$"):
        match = re.fullmatch(r"\$([a-zA-Z0-9][a-zA-Z0-9_-]{0,95})(?::(0|[1-9][0-9]{0,2}))?", value)
        if match is None:
            raise ValueError("Use a task reference with an optional nonnegative output index")
        yield match[1]


def model_task_request(store, recipe, *, production_id, task_id):
    """Resolve a validated recipe task only from matching completed saved tasks.

    The returned binding must accompany the owned quote into JobStore.create's
    atomic uniqueness check. This read alone does not reserve a task or authorize
    submission. Persist only the digests, never recipe text or remote URLs.
    """
    plan = validate_film_plan(recipe)
    require_plan_scope(plan, store.scope)
    tasks, digests, dependencies = {}, {}, {}
    for task in plan["tasks"]:
        refs = set(_references(task.get("parameters", {})))
        if not refs <= tasks.keys():
            raise ValueError("Film references must name earlier recipe tasks")
        dependencies[task["id"]] = refs
        digests[task["id"]] = _digest(
            {"task": task, "dependencies": {key: digests[key] for key in sorted(refs)}}
        )
        tasks[task["id"]] = task
    if not isinstance(task_id, str) or task_id not in tasks or tasks[task_id]["kind"] != "model":
        raise ValueError("Choose a model task from the Film recipe")
    binding = FilmTaskBinding(production_id, task_id, _digest(plan), digests[task_id])
    if store.film_job(production_id, task_id) is not None:
        raise StoreConflict("Film task already has a saved job; inspect it or name a new take")
    observations = {}
    for reference in dependencies[task_id]:
        source = tasks[reference]
        if source["kind"] != "model":
            raise ValueError("Film upload-task binding is not available yet")
        saved = store.film_job(production_id, reference)
        if (
            saved is None
            or saved.intent.film_task.task_sha256 != digests[reference]
            or saved.intent.target_id != source["model"]
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
            or not saved.results
        ):
            raise ValueError("Film reference needs matching completed saved outputs")
        observations[reference] = TaskAssets(
            store.scope, tuple(item.asset.asset_id for item in saved.results)
        )
    task = tasks[task_id]
    parameters = resolve_references(task["parameters"], observations, scope=store.scope)
    return binding, task["model"], parameters
