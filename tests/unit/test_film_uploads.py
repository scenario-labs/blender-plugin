# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Film source associations use durable imported uploads without replaying transfer."""

import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, replace
from threading import Barrier, Event
from types import SimpleNamespace

import httpx
import pytest

from scenario.core.api.sdk_adapter import Credentials, SDKAdapter
from scenario.core.jobs.coordinator import FilmUploadResult, JobCoordinator, QuoteError
from scenario.core.jobs.film_tasks import model_task_request, upload_task_reference
from scenario.core.jobs.origins import OriginRevisions
from scenario.core.jobs.store import (
    FilmTaskBinding,
    FilmUploadReference,
    JobIntent,
    JobScope,
    JobStore,
    StoreConflict,
    StoreError,
)
from scenario.core.jobs.transfers import StoragePolicy
from scenario.core.jobs.upload_sources import UploadSources
from scenario.core.jobs.upload_store import UploadIntent, UploadState, UploadStore
from scenario.core.jobs.upload_transfers import PartUploader
from scenario.core.jobs.workers import JobWorkers
from scenario.core.scene.film_scene_plan import local_plan


@pytest.fixture
def env(tmp_path):
    scope = JobScope("https://fixture.invalid/v1", "fixture")
    store = JobStore(tmp_path / "jobs.sqlite3", scope)
    uploads = UploadStore(tmp_path / "uploads.sqlite3", scope)
    revisions = OriginRevisions()
    (tmp_path / "sources").mkdir(mode=0o700)
    sources = UploadSources(tmp_path / "sources")
    e = SimpleNamespace(
        scope=scope,
        store=store,
        uploads=uploads,
        sources=sources,
        origin=revisions.capture("scene"),
        revisions=revisions,
        calls=[],
    )
    e.recipe = {
        "title": "Fixture",
        "shots": [
            {"id": "shot", "title": "Shot", "duration": 4, "scene": local_plan("studio", "", 4)}
        ],
        "tasks": [
            {"id": "reference", "title": "Source", "kind": "upload"},
            {
                "id": "take",
                "title": "Take",
                "kind": "model",
                "model": "model",
                "parameters": {"prompt": "$reference"},
            },
        ],
    }

    def handler(request):
        e.calls.append(request)
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
        assert request.url.params.get("dryRun") == "true", "No paid submission or upload permitted"
        return httpx.Response(200, json={"creativeUnitsCost": 1})

    adapter = SDKAdapter(
        Credentials("fixture", "fixture-secret"),
        online=lambda: True,
        base_url=scope.service,
        account_id=scope.account_id,
        transport=httpx.MockTransport(handler),
    )
    e.owner = JobCoordinator(
        adapter,
        store,
        origin_guard=revisions.guard,
        upload_store=uploads,
        upload_sources=sources,
        part_uploader=PartUploader(
            StoragePolicy(frozenset({"storage.invalid"})), online_access=lambda: True
        ),
    )
    yield e
    e.owner.close()


def imported(e, *, request_id="upload", kind="image", state=UploadState.IMPORTED, store=None):
    store = store or e.uploads
    intent = UploadIntent(
        request_id,
        store.scope,
        e.origin,
        kind,
        "reference.bin",
        "application/octet-stream",
        4,
        "a" * 64,
        4,
        ("a" * 64,),
    )
    row = store.create(intent)
    if state == UploadState.PREPARED:
        return row
    row = store.transition(
        request_id, expected_revision=row.revision, state=UploadState.INITIALIZING
    )
    if state == UploadState.INITIALIZATION_UNCERTAIN:
        return store.transition(request_id, expected_revision=row.revision, state=state)
    row = store.transition(
        request_id,
        expected_revision=row.revision,
        state=UploadState.UPLOADING,
        upload_id="remote-" + request_id,
    )
    if state == UploadState.UPLOADING:
        return row
    return store.transition(
        request_id,
        expected_revision=row.revision,
        state=state,
        asset_id="opaque-" + request_id if state == UploadState.IMPORTED else None,
    )


def bind(e, row, *, raw=None, **options):
    values = {
        "production_id": "production",
        "task_id": "reference",
        "request_id": row.intent.request_id,
        "expected_revision": row.revision,
        "origin": e.origin,
    } | options
    return e.owner.bind_film_upload(e.recipe if raw is None else raw, **values)


def quote(e):
    return e.owner.quote_film_task(
        e.recipe, production_id="production", task_id="take", origin=e.origin
    )


@pytest.mark.parametrize("kind", ["image", "audio", "video", "3d", "asset", "avatar", "text"])
def test_imported_asset_binding_reopens_without_transfer_or_service_io(env, tmp_path, kind):
    upload = imported(env, kind=kind)
    result = bind(env, upload)
    assert result.origin == env.origin and result.scope == env.scope
    saved = JobStore(tmp_path / "jobs.sqlite3", env.scope).film_upload("production", "reference")
    assert saved == result.reference
    assert saved.asset_id == upload.asset_id
    assert saved.file_sha256 == upload.intent.file_sha256
    assert saved.kind == kind
    assert env.calls == []
    assert env.store.records() == ()
    assert bind(env, upload).reference == saved
    q = quote(env)
    assert q.estimate.payload == {"prompt": upload.asset_id}
    assert len(env.calls) == 2


@pytest.mark.parametrize(
    "state",
    [
        UploadState.PREPARED,
        UploadState.INITIALIZATION_UNCERTAIN,
        UploadState.UPLOADING,
        UploadState.PROCESSING,
        UploadState.FAILED,
    ],
)
def test_pending_or_uncertain_upload_never_becomes_a_film_reference(env, state):
    upload = imported(env, state=state)
    with pytest.raises(ValueError, match="imported"):
        bind(env, upload)
    assert env.store.film_upload("production", "reference") is None
    assert env.calls == []


def test_stale_revision_wrong_task_and_model_import_are_rejected(env):
    upload = imported(env)
    for changes in (
        {"expected_revision": upload.revision - 1},
        {"expected_revision": True},
        {"request_id": "missing"},
        {"task_id": "take"},
    ):
        with pytest.raises(ValueError):
            bind(env, upload, **changes)
    model = imported(env, request_id="model-import", kind="model")
    with pytest.raises(ValueError):
        bind(env, model)
    assert env.calls == [] and env.store.film_upload("production", "reference") is None


@pytest.mark.parametrize(
    "change",
    [
        {"service": "https://other.invalid"},
        {"account_id": "other"},
        {"project_id": "other"},
        {"team_id": "other"},
    ],
)
def test_foreign_scope_cannot_supply_or_read_film_association(env, tmp_path, change):
    scope = replace(env.scope, **change)
    foreign = UploadStore(tmp_path / "uploads.sqlite3", scope)
    uploaded = imported(env, store=foreign)
    with pytest.raises(ValueError):
        bind(env, uploaded)
    own = imported(env)
    saved = bind(env, own).reference
    other = JobStore(tmp_path / "jobs.sqlite3", scope)
    assert other.film_upload("production", "reference") is None
    with pytest.raises(ValueError):
        other.bind_film_upload(saved)
    assert env.calls == []


def test_rebinding_requires_new_task_but_appended_recipe_keeps_original_association(env):
    first = imported(env)
    saved = bind(env, first).reference
    second = imported(env, request_id="replacement")
    with pytest.raises(StoreConflict):
        bind(env, second)
    env.recipe["tasks"].append({"id": "next", "title": "Next", "kind": "upload"})
    assert bind(env, first).reference == saved
    assert bind(env, second, task_id="next").reference.asset_id == second.asset_id
    assert env.store.film_upload("production", "reference") == saved
    assert env.calls == []


def test_changed_task_or_ancestor_requires_new_binding(env):
    upload = imported(env)
    bind(env, upload)
    env.recipe["tasks"][0]["title"] = "Changed source declaration"
    with pytest.raises(StoreConflict):
        bind(env, upload)
    with pytest.raises(ValueError, match="matching"):
        quote(env)
    assert env.calls == []


@pytest.mark.parametrize(
    "damage", ["missing", "asset", "revision", "digest", "kind", "scope", "request", "state"]
)
def test_saved_upload_evidence_is_rechecked_before_quote(env, monkeypatch, damage):
    upload = imported(env)
    bind(env, upload)
    if damage == "missing":
        current = None
    elif damage == "asset":
        current = replace(upload, asset_id="changed")
    elif damage == "revision":
        current = replace(upload, revision=upload.revision + 1)
    elif damage == "state":
        current = replace(upload, state=UploadState.FAILED, asset_id=None)
    else:
        changes = {
            "digest": {"file_sha256": "b" * 64},
            "kind": {"kind": "audio"},
            "scope": {"scope": replace(env.scope, account_id="other")},
            "request": {"request_id": "wrong"},
        }[damage]
        current = replace(upload, intent=replace(upload.intent, **changes))
    monkeypatch.setattr(env.owner._uploads, "inspect", lambda _: current)
    with pytest.raises(ValueError):
        quote(env)
    assert env.calls == []


def test_reference_index_and_missing_upload_configuration_fail_without_spend(env):
    upload = imported(env)
    bind(env, upload)
    env.recipe["tasks"][1]["parameters"]["prompt"] = "$reference:1"
    with pytest.raises(ValueError):
        quote(env)
    env.recipe["tasks"][1]["parameters"]["prompt"] = "$reference"
    with pytest.raises(ValueError, match="upload store"):
        model_task_request(env.store, env.recipe, production_id="production", task_id="take")
    assert env.calls == []


def test_saved_asset_remains_usable_after_verified_staging_cleanup(env, tmp_path):
    source = tmp_path / "source.png"
    source.write_bytes(b"source fixture")
    upload = env.owner.prepare_upload(
        source, origin=env.origin, kind="image", content_type="image/png"
    )
    for state, fields in [
        (UploadState.INITIALIZING, {}),
        (UploadState.UPLOADING, {"upload_id": "remote"}),
        (UploadState.IMPORTED, {"asset_id": "source-asset"}),
    ]:
        upload = env.uploads.transition(
            upload.intent.request_id, expected_revision=upload.revision, state=state, **fields
        )
    saved = bind(env, upload).reference
    env.owner.discard_upload_source(upload.intent.request_id, expected_revision=upload.revision)
    assert source.read_bytes() == b"source fixture"
    assert quote(env).estimate.payload == {"prompt": "source-asset"}
    assert env.store.film_upload("production", "reference") == saved


def test_model_and_upload_task_reservations_share_one_atomic_namespace(env, tmp_path):
    upload = imported(env)
    binding = FilmTaskBinding("production", "reference", "a" * 64, "b" * 64)
    reference = FilmUploadReference(
        env.scope,
        binding,
        upload.intent.request_id,
        upload.revision,
        upload.asset_id,
        upload.intent.file_sha256,
        upload.intent.kind,
    )
    intent = JobIntent(
        "competing-job",
        env.scope,
        env.origin,
        "model",
        "model",
        "c" * 64,
        "d" * 64,
        "1",
        film_task=binding,
    )
    barrier = Barrier(2)

    def claim(kind):
        owner = JobStore(tmp_path / "jobs.sqlite3", env.scope)
        barrier.wait(5)
        try:
            return owner.bind_film_upload(reference) if kind == "upload" else owner.create(intent)
        except StoreConflict:
            return None

    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(claim, ["upload", "model"]))
    assert sum(item is not None for item in results) == 1
    assert bool(env.store.film_upload("production", "reference")) != bool(
        env.store.film_job("production", "reference")
    )
    assert env.calls == []


def test_competing_upload_associations_cannot_replace_selected_source(env, tmp_path):
    first = imported(env)
    second = imported(env, request_id="second")
    base = FilmTaskBinding("production", "reference", "a" * 64, "b" * 64)
    barrier = Barrier(2)

    def claim(row):
        owner = JobStore(tmp_path / "jobs.sqlite3", env.scope)
        reference = FilmUploadReference(
            env.scope,
            base,
            row.intent.request_id,
            row.revision,
            row.asset_id,
            row.intent.file_sha256,
            row.intent.kind,
        )
        barrier.wait(5)
        try:
            return owner.bind_film_upload(reference)
        except StoreConflict:
            return None

    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(claim, [first, second]))
    assert sum(item is not None for item in results) == 1
    assert env.store.film_upload("production", "reference") in results


def test_binding_commit_failure_preserves_original_upload_and_no_association(env, monkeypatch):
    upload = imported(env)
    original = sqlite3.connect

    class FailCommit(sqlite3.Connection):
        def commit(self):
            if (
                self.execute("SELECT name FROM sqlite_master WHERE name='film_uploads'").fetchone()
                and self.execute("SELECT COUNT(*) FROM film_uploads").fetchone()[0]
            ):
                raise sqlite3.OperationalError("fixture")
            return super().commit()

    with monkeypatch.context() as patch:
        patch.setattr(sqlite3, "connect", lambda *a, **k: original(*a, **k, factory=FailCommit))
        with pytest.raises(StoreError):
            bind(env, upload)
    assert env.store.film_upload("production", "reference") is None
    assert env.uploads.get(upload.intent.request_id) == upload
    assert env.calls == []


def test_committed_but_unacknowledged_binding_can_be_inspected_and_repeated_locally(
    env, monkeypatch
):
    upload = imported(env)
    create = env.store.bind_film_upload

    def committed(reference):
        create(reference)
        raise StoreError("lost acknowledgement")

    with monkeypatch.context() as patch:
        patch.setattr(env.store, "bind_film_upload", committed)
        with pytest.raises(StoreError):
            bind(env, upload)
    saved = env.store.film_upload("production", "reference")
    assert bind(env, upload).reference == saved
    assert env.calls == []


@pytest.mark.parametrize("damage", ["truncated", "scope", "identity", "revision", "digest", "kind"])
def test_malformed_association_fails_closed(env, damage):
    bind(env, imported(env))
    with sqlite3.connect(env.store._path) as connection:
        raw = json.loads(connection.execute("SELECT record FROM film_uploads").fetchone()[0])
        if damage == "truncated":
            del raw["asset_id"]
        elif damage == "scope":
            raw["scope"]["account_id"] = "other"
        elif damage == "identity":
            raw["film_task"]["task_id"] = "other"
        elif damage == "revision":
            raw["upload_revision"] = True
        elif damage == "digest":
            raw["file_sha256"] = "bad"
        else:
            raw["kind"] = "model"
        connection.execute("UPDATE film_uploads SET record=?", (json.dumps(raw),))
    with pytest.raises(StoreError):
        quote(env)
    assert env.calls == []


def test_conflicting_upload_and_model_rows_are_never_silently_selected(env):
    saved = bind(env, imported(env)).reference
    intent = JobIntent(
        "bad-job",
        env.scope,
        env.origin,
        "model",
        "model",
        "c" * 64,
        "d" * 64,
        "1",
        film_task=replace(saved.film_task, task_id="temporary"),
    )
    row = env.store.create(intent)
    raw = asdict(replace(row, intent=replace(intent, film_task=saved.film_task)))
    with sqlite3.connect(env.store._path) as connection:
        connection.execute("UPDATE jobs SET record=?", (json.dumps(raw),))
    for read in (env.store.film_job, env.store.film_upload):
        with pytest.raises(StoreError, match="conflicting"):
            read("production", "reference")


def test_current_origin_guards_association_and_repeated_delivery(env):
    upload = imported(env)
    first = bind(env, upload)
    env.revisions.invalidate("scene")
    with pytest.raises(QuoteError):
        bind(env, upload)
    env.origin = env.revisions.capture("other-scene")
    second = bind(env, upload)
    assert first.reference == second.reference and first.origin != second.origin
    with pytest.raises(ValueError):
        FilmUploadResult(replace(env.scope, account_id="other"), env.origin, first.reference)


def test_worker_uses_copied_recipe_and_existing_queue(env):
    upload = imported(env)
    expected = upload_task_reference(
        env.store,
        env.recipe,
        production_id="production",
        task_id="reference",
        inspect_upload=env.uploads.get,
        request_id=upload.intent.request_id,
        expected_revision=upload.revision,
    )
    workers = JobWorkers(env.owner, workers=1)
    entered, release = Event(), Event()

    def block():
        entered.set()
        assert release.wait(5)

    try:
        workers._enqueue(block)
        assert entered.wait(5)
        task = workers.bind_film_upload(
            env.recipe,
            production_id="production",
            task_id="reference",
            request_id=upload.intent.request_id,
            expected_revision=upload.revision,
            origin=env.origin,
        )
        env.recipe["tasks"][0]["title"] = "edited after admission"
        release.set()
        result = task.result(5)
        assert result.reference == expected
        assert env.calls == []
    finally:
        release.set()
        workers.shutdown()


@pytest.mark.parametrize("origin", [None, {}, "scene"])
def test_binding_requires_captured_origin_before_any_write(env, origin):
    upload = imported(env)
    with pytest.raises(QuoteError, match="origin"):
        bind(env, upload, origin=origin)
    assert env.store.film_upload("production", "reference") is None
    assert env.calls == []
