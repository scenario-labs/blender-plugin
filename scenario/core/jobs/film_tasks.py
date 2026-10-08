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
from .store import FilmTaskBinding, FilmUploadReference, JobState, StoreConflict, _json
from .upload_store import StoredUpload, UploadState


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


def _recipe_context(store, recipe):
    """Validate scope and compute the recipe's transitive task identities once."""
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
    return plan, tasks, digests, dependencies


def _task_context(store, recipe, *, production_id, task_id, kind):
    """Validate the recipe and compute exact task/dependency identities."""
    plan, tasks, digests, dependencies = _recipe_context(store, recipe)
    if not isinstance(task_id, str) or task_id not in tasks or tasks[task_id]["kind"] != kind:
        raise ValueError(f"Choose a {kind} task from the Film recipe")
    binding = FilmTaskBinding(production_id, task_id, _digest(plan), digests[task_id])
    return binding, tasks, digests, dependencies


def _upload_evidence(inspect_upload, binding, scope, request_id, expected_revision):
    if inspect_upload is None:
        raise ValueError("Film upload references require the selected upload store")
    saved = inspect_upload(request_id)
    if (
        not isinstance(saved, StoredUpload)
        or saved.intent.scope != scope
        or saved.intent.request_id != request_id
        or type(expected_revision) is not int
        or saved.revision != expected_revision
        or saved.state != UploadState.IMPORTED
    ):
        raise ValueError("Choose an unchanged imported upload in the selected scope")
    return FilmUploadReference(
        scope,
        binding,
        request_id,
        saved.revision,
        saved.asset_id,
        saved.intent.file_sha256,
        saved.intent.kind,
    )


def upload_task_reference(
    store, recipe, *, production_id, task_id, inspect_upload, request_id, expected_revision
):
    """Validate a local association; no upload, staging, cleanup or remote reads."""
    binding, _, _, _ = _task_context(
        store, recipe, production_id=production_id, task_id=task_id, kind="upload"
    )
    return _upload_evidence(inspect_upload, binding, store.scope, request_id, expected_revision)


def model_task_request(store, recipe, *, production_id, task_id, inspect_upload=None):
    """Resolve matching completed saved tasks; this read does not reserve a take."""
    binding, tasks, digests, dependencies = _task_context(
        store, recipe, production_id=production_id, task_id=task_id, kind="model"
    )
    if (
        store.film_job(production_id, task_id) is not None
        or store.film_upload(production_id, task_id) is not None
    ):
        raise StoreConflict("Film task already has saved work; inspect it or name a new take")
    observations = {}
    for reference in dependencies[task_id]:
        source = tasks[reference]
        if source["kind"] == "upload":
            attached = store.film_upload(production_id, reference)
            if attached is None or attached.film_task.task_sha256 != digests[reference]:
                raise ValueError("Film reference needs a matching saved upload association")
            current = _upload_evidence(
                inspect_upload,
                attached.film_task,
                store.scope,
                attached.upload_request_id,
                attached.upload_revision,
            )
            if current != attached:
                raise ValueError("Film upload changed; inspect the saved association")
            observations[reference] = TaskAssets(store.scope, (attached.asset_id,))
            continue
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
