# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Real SDK serialization, immutable snapshots and one-attempt upload orchestration."""

import copy
import hashlib
import json
import sqlite3
import threading
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest

from scenario.core.api.sdk_adapter import Credentials, SDKAdapter
from scenario.core.jobs.coordinator import JobCoordinator
from scenario.core.jobs.origins import OriginRevisions
from scenario.core.jobs.store import JobScope, JobStore, StoreConflict, StoreError
from scenario.core.jobs.transfers import StoragePolicy, TransferError
from scenario.core.jobs.upload_sources import UploadSources
from scenario.core.jobs.upload_store import UploadState, UploadStore
from scenario.core.jobs.upload_transfers import PartUploader, UploadedPart, UploadUncertain
from scenario.core.jobs.uploads import UploadError, UploadMutationUncertain
from scenario.core.jobs.workers import JobWorkers


@pytest.fixture
def env(tmp_path):
    scope = JobScope("https://service.example.invalid/v1", "account-one", "project-one")
    origins = OriginRevisions()
    origin = origins.capture("scene", "object")
    root = tmp_path / "sources"
    root.mkdir()
    source = tmp_path / "reference.png"
    source.write_bytes(b"abcde")
    sources = UploadSources(root, max_bytes=30, part_bytes=3)
    store = UploadStore(tmp_path / "uploads.sqlite3", scope)
    env = SimpleNamespace(
        scope=scope,
        origin=origin,
        root=root,
        source=source,
        sources=sources,
        store=store,
        requests=[],
        fail=None,
        online=True,
        origins=origins,
        origin_held=False,
    )
    env.remote = {
        "id": "remote-one",
        "status": "pending",
        "source": "multipart",
        "kind": "image",
        "fileName": "reference.png",
        "contentType": "image/png",
        "fileSize": 5,
        "partsCount": 2,
        "parts": [
            {
                "number": i,
                "url": f"https://storage.example.invalid/{i}?secret=fixture",
                "expires": "2099-01-01T00:00:00Z",
            }
            for i in (1, 2)
        ],
    }

    def handler(request):
        assert not env.origin_held, "Origin invalidation must not wait for HTTP"
        env.requests.append(request)
        operation = (
            "complete"
            if request.url.path.endswith("/action")
            else "create"
            if request.method == "POST"
            else "get"
        )
        if env.fail == operation:
            raise httpx.ReadTimeout("private-fixture", request=request)
        result = copy.deepcopy(env.remote)
        if operation == "complete":
            result["status"] = "validating"
        return httpx.Response(200, json={"upload": result})

    adapter = SDKAdapter(
        credentials=Credentials("fixture-key", "fixture-secret"),
        base_url=scope.service,
        account_id=scope.account_id,
        project_id=scope.project_id,
        online=lambda: env.online,
        transport=httpx.MockTransport(handler),
    )
    uploader = PartUploader(
        StoragePolicy(frozenset({"storage.example.invalid"}), max_bytes=3),
        online_access=lambda: env.online,
    )

    def put(url, data, *, number, content_type, expected_sha256):
        assert not env.origin_held, "Origin invalidation must not wait for storage PUT"
        record = store.records()[0]
        assert record.active_part == number
        assert record.state == UploadState.UPLOADING
        assert hashlib.sha256(data).hexdigest() == expected_sha256
        return UploadedPart(number, len(data), expected_sha256)

    uploader.upload = Mock(side_effect=put)

    @contextmanager
    def guard(value):
        with origins.guard(value) as current:
            env.origin_held = True
            try:
                yield current
            finally:
                env.origin_held = False

    coordinator = JobCoordinator(
        adapter,
        JobStore(tmp_path / "jobs.sqlite3", scope),
        upload_store=store,
        upload_sources=sources,
        part_uploader=uploader,
        origin_guard=guard,
    )
    env.coordinator, env.uploader = coordinator, uploader
    yield env
    coordinator.close()


def prepare(env):
    return env.coordinator.prepare_upload(
        env.source, origin=env.origin, kind="image", content_type="image/png"
    )


def invoke(env, method, record):
    return getattr(env.coordinator, method)(
        record.intent.request_id, expected_revision=record.revision
    )


def initialized(env):
    return invoke(env, "initialize_upload", prepare(env))


def transferred(env):
    record = initialized(env)
    for _ in range(2):
        record = invoke(env, "transfer_upload_part", record)
    return record


def test_shared_workers_drive_staged_upload_to_authoritative_asset(env):
    workers = JobWorkers(env.coordinator, workers=1)
    try:
        record = workers.prepare_upload(
            env.source, origin=env.origin, kind="image", content_type="image/png"
        ).result(5)
        env.source.write_bytes(b"user changed original source")
        for method in (
            "initialize_upload",
            "transfer_upload_part",
            "transfer_upload_part",
            "finalize_upload",
        ):
            record = getattr(workers, method)(
                record.intent.request_id, expected_revision=record.revision
            ).result(5)
        assert record.state == UploadState.PROCESSING
        assert record.asset_id is None
        env.remote.update(status="imported", entityId="asset-one")
        record = workers.refresh_upload(
            record.intent.request_id, expected_revision=record.revision
        ).result(5)
        assert record.state == UploadState.IMPORTED
        assert record.asset_id == "asset-one"
        assert [call.args[1] for call in env.uploader.upload.call_args_list] == [b"abc", b"de"]
        assert [r.method for r in env.requests] == ["POST", "GET", "GET", "POST", "GET"]
        assert all(r.url.params["projectId"] == "project-one" for r in env.requests)
        assert json.loads(env.requests[0].content) == {
            "kind": "image",
            "fileName": "reference.png",
            "contentType": "image/png",
            "fileSize": 5,
            "parts": 2,
        }
        assert json.loads(env.requests[3].content) == {"action": "complete"}
        assert b"secret=fixture" not in env.store._path.read_bytes()
        assert bytes(str(env.source), "utf8") not in env.store._path.read_bytes()
    finally:
        workers.shutdown()
    assert workers.stopped


@pytest.mark.parametrize(
    "phase,state",
    [
        ("create", UploadState.INITIALIZATION_UNCERTAIN),
        ("part", UploadState.PART_UNCERTAIN),
        ("complete", UploadState.FINALIZATION_UNCERTAIN),
    ],
)
def test_lost_mutation_response_is_durable_and_never_retried(env, phase, state):
    record = (
        prepare(env)
        if phase == "create"
        else initialized(env)
        if phase == "part"
        else transferred(env)
    )
    method = {
        "create": "initialize_upload",
        "part": "transfer_upload_part",
        "complete": "finalize_upload",
    }[phase]
    if phase == "part":
        env.uploader.upload.side_effect = UploadUncertain("private-signed-url")
    else:
        env.fail = phase
    with pytest.raises(UploadMutationUncertain) as error:
        invoke(env, method, record)
    assert "private" not in str(error.value)
    recovered = UploadStore(env.store._path, env.scope).get(record.intent.request_id)
    assert recovered.state == state
    calls = len(env.requests), env.uploader.upload.call_count
    with pytest.raises(StoreConflict):
        invoke(env, method, recovered)
    assert (len(env.requests), env.uploader.upload.call_count) == calls
    if phase != "create":
        env.fail = None
        env.remote.update(status="imported", entityId="asset-one")
        recovered = invoke(env, "refresh_upload", recovered)
        assert recovered.asset_id == "asset-one"
        assert env.requests[-1].method == "GET"


@pytest.mark.parametrize(
    "field,value",
    [
        ("fileName", "other.png"),
        ("fileSize", 6),
        ("partsCount", 3),
        ("kind", "model"),
        ("source", "url"),
        ("contentType", "image/jpeg"),
        ("status", "complete"),
        ("parts", []),
        ("parts", [{"number": 1}, {"number": 1}]),
    ],
)
def test_changed_remote_plan_cannot_claim_or_send(env, field, value):
    record = initialized(env)
    env.remote[field] = value
    with pytest.raises(UploadError):
        invoke(env, "transfer_upload_part", record)
    assert env.store.get(record.intent.request_id) == record
    env.uploader.upload.assert_not_called()


@pytest.mark.parametrize(
    "field,value",
    [
        ("expires", "2001-01-01T00:00:00Z"),
        ("expires", "2099-01-01T00:00:00"),
        ("expires", "invalid"),
        ("url", "https://other.example.invalid/part"),
    ],
)
def test_untrusted_or_expired_destination_fails_before_claim(env, field, value):
    record = initialized(env)
    env.remote["parts"][0][field] = value
    with pytest.raises(UploadError):
        invoke(env, "transfer_upload_part", record)
    assert env.store.get(record.intent.request_id) == record
    env.uploader.upload.assert_not_called()


@pytest.mark.parametrize("action", ["initialize_upload", "transfer_upload_part"])
def test_staged_corruption_prevents_mutation(env, action):
    record = prepare(env) if action == "initialize_upload" else initialized(env)
    path = env.sources._directory(env.scope, record.intent.request_id) / "source.bin"
    path.write_bytes(b"wrong")
    mutations = sum(r.method == "POST" for r in env.requests)
    with pytest.raises(UploadError):
        invoke(env, action, record)
    assert env.store.get(record.intent.request_id) == record
    env.uploader.upload.assert_not_called()
    assert sum(r.method == "POST" for r in env.requests) == mutations


def test_acknowledged_part_with_failed_persistence_keeps_active_claim(env):
    record = initialized(env)
    original = env.uploader.upload.side_effect

    def fail_receipt(*args, **kwargs):
        result = original(*args, **kwargs)
        with sqlite3.connect(env.store._path) as connection:
            connection.execute(
                "CREATE TRIGGER fail BEFORE UPDATE ON uploads BEGIN SELECT RAISE(ABORT, 'private'); END"
            )
        return result

    env.uploader.upload.side_effect = fail_receipt
    with pytest.raises(StoreError):
        invoke(env, "transfer_upload_part", record)
    recovered = env.store.get(record.intent.request_id)
    assert recovered.active_part == 1
    assert recovered.receipts == ()
    with pytest.raises(StoreConflict):
        invoke(env, "transfer_upload_part", recovered)
    assert env.uploader.upload.call_count == 1


def test_finalize_rejects_missing_receipts_without_dispatch(env):
    record = initialized(env)
    before = len(env.requests)
    with pytest.raises(ValueError):
        invoke(env, "finalize_upload", record)
    assert len(env.requests) == before
    assert env.store.get(record.intent.request_id) == record


def test_inactive_owner_blocks_new_commands_but_retains_inflight_receipt(env):
    record = initialized(env)
    original = env.uploader.upload.side_effect

    def finish(*args, **kwargs):
        env.coordinator.deactivate()
        return original(*args, **kwargs)

    env.uploader.upload.side_effect = finish
    record = invoke(env, "transfer_upload_part", record)
    assert len(record.receipts) == 1
    with pytest.raises(UploadError, match="inactive"):
        invoke(env, "transfer_upload_part", record)
    assert env.uploader.upload.call_count == 1


def test_deactivation_during_part_preflight_prevents_claim(env):
    record = initialized(env)
    original = env.sources.part

    def read(*args):
        env.coordinator.deactivate()
        return original(*args)

    env.sources.part = read
    with pytest.raises(UploadError, match="inactive"):
        invoke(env, "transfer_upload_part", record)
    assert env.store.get(record.intent.request_id) == record
    env.uploader.upload.assert_not_called()


def test_offline_initialization_preserves_uncertainty_without_sdk_dispatch(env):
    record = prepare(env)
    env.online = False
    with pytest.raises(UploadMutationUncertain):
        invoke(env, "initialize_upload", record)
    assert env.requests == []
    assert env.store.get(record.intent.request_id).state == UploadState.INITIALIZATION_UNCERTAIN


def test_model_import_cannot_be_mislabeled_as_asset_reference(env):
    with pytest.raises(UploadError):
        env.coordinator.prepare_upload(
            env.source, origin=env.origin, kind="model", content_type="application/octet-stream"
        )
    assert env.store.records() == ()
    assert list(env.root.iterdir()) == []


@pytest.mark.parametrize("mutation", ["symlink", "truncate", "grow"])
def test_snapshot_reads_reject_replaced_or_resized_content(env, mutation):
    record = prepare(env)
    path = env.sources._directory(env.scope, record.intent.request_id) / "source.bin"
    if mutation == "symlink":
        path.unlink()
        path.symlink_to(env.source)
    else:
        path.write_bytes(b"x" if mutation == "truncate" else b"too much data")
    with pytest.raises(TransferError):
        env.sources.verify(record.intent)
    with pytest.raises(TransferError):
        env.sources.part(record.intent, 1)


def test_staging_limits_and_symlinks_do_not_publish_partial_snapshots(env):
    env.source.write_bytes(b"x" * 31)
    with pytest.raises(UploadError):
        prepare(env)
    assert list(env.root.iterdir()) == []
    other = env.source.parent / "alias.png"
    other.symlink_to(env.source)
    env.source = other
    with pytest.raises(UploadError):
        prepare(env)
    assert list(env.root.iterdir()) == []


def test_failed_part_claim_prevents_storage_write(env):
    record = initialized(env)
    with sqlite3.connect(env.store._path) as connection:
        connection.execute(
            "CREATE TRIGGER fail BEFORE UPDATE ON uploads BEGIN SELECT RAISE(ABORT, 'private'); END"
        )
    with pytest.raises(StoreError):
        invoke(env, "transfer_upload_part", record)
    env.uploader.upload.assert_not_called()
    assert env.store.get(record.intent.request_id) == record


def test_thread_control_exception_retains_inflight_claim(env):
    record = initialized(env)
    env.uploader.upload.side_effect = KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):
        invoke(env, "transfer_upload_part", record)
    current = env.store.get(record.intent.request_id)
    assert current.state == UploadState.UPLOADING
    assert current.active_part == 1
    with pytest.raises(StoreConflict):
        invoke(env, "transfer_upload_part", current)
    assert env.uploader.upload.call_count == 1


def test_unknown_create_status_keeps_known_id_for_explicit_retrieval(env):
    record = prepare(env)
    env.remote["status"] = "future-status"
    with pytest.raises(UploadError):
        invoke(env, "initialize_upload", record)
    current = env.store.get(record.intent.request_id)
    assert current.upload_id == "remote-one"
    assert current.state == UploadState.UPLOADING
    with pytest.raises(StoreConflict):
        invoke(env, "initialize_upload", current)
    assert len(env.requests) == 1


def test_completion_failure_after_response_preserves_uncertainty(env, monkeypatch):
    record = transferred(env)
    monkeypatch.setattr(
        env.coordinator._adapter,
        "complete_upload",
        lambda identifier: {**env.remote, "status": "imported", "entityId": None},
    )
    with pytest.raises(UploadMutationUncertain):
        invoke(env, "finalize_upload", record)
    assert env.store.get(record.intent.request_id).state == UploadState.FINALIZATION_UNCERTAIN


def test_pending_remote_status_does_not_release_an_uncertain_part(env):
    record = initialized(env)
    env.uploader.upload.side_effect = UploadUncertain()
    with pytest.raises(UploadMutationUncertain):
        invoke(env, "transfer_upload_part", record)
    current = env.store.get(record.intent.request_id)
    assert invoke(env, "refresh_upload", current) == current
    assert current.state == UploadState.PART_UNCERTAIN
    assert current.active_part == 1


def test_failed_snapshot_flush_leaves_no_intent_or_partial_file(env, monkeypatch):
    from scenario.core.jobs import upload_sources

    def fail(_):
        raise OSError("private source path")

    monkeypatch.setattr(upload_sources.os, "fsync", fail)
    with pytest.raises(UploadError) as error:
        prepare(env)
    assert "private" not in str(error.value)
    assert env.store.records() == ()
    assert list(env.root.iterdir()) == []
    assert env.source.read_bytes() == b"abcde"


@pytest.mark.parametrize("origin", [None, "scene", object()])
def test_prepare_requires_captured_origin_before_reading_source(env, origin, monkeypatch):
    stage = Mock(side_effect=AssertionError("Invalid origin must not stage a source"))
    monkeypatch.setattr(env.sources, "stage", stage)
    with pytest.raises(UploadError, match="Capture the upload origin"):
        env.coordinator.prepare_upload(
            env.source, origin=origin, kind="image", content_type="image/png"
        )
    stage.assert_not_called()
    assert env.store.records() == ()
    assert env.requests == []


@pytest.mark.parametrize("change", ["scene", "file", "other-scene"])
def test_stale_origin_is_rejected_before_staging_but_other_scene_is_independent(env, change):
    if change == "file":
        env.origins.reset()
    else:
        env.origins.invalidate(change)
    if change == "other-scene":
        assert prepare(env).intent.origin == env.origin
        assert len(env.store.records()) == 1
    else:
        with pytest.raises(UploadError, match="origin changed"):
            prepare(env)
        assert env.store.records() == ()
        assert list(env.root.iterdir()) == []
    assert env.source.read_bytes() == b"abcde"
    assert env.requests == []


def test_invalidation_during_staging_retains_only_owned_orphan_and_original_source(
    env, monkeypatch
):
    original = env.sources.stage

    def stage(*args, **kwargs):
        assert not env.origin_held
        staged = original(*args, **kwargs)
        env.origins.invalidate(env.origin.scene_id)
        return staged

    monkeypatch.setattr(env.sources, "stage", stage)
    with pytest.raises(UploadError, match="origin changed"):
        prepare(env)
    assert env.store.records() == ()
    assert env.requests == []
    assert env.source.read_bytes() == b"abcde"
    snapshots = tuple(env.root.glob("*/source.bin"))
    assert len(snapshots) == 1
    assert snapshots[0].read_bytes() == b"abcde"


@pytest.mark.parametrize(
    "command", ["prepare_upload", "initialize_upload", "transfer_upload_part", "finalize_upload"]
)
def test_queued_upload_rechecks_origin_before_staging_or_mutation(env, command, monkeypatch):
    record = (
        initialized(env)
        if command == "transfer_upload_part"
        else transferred(env)
        if command == "finalize_upload"
        else prepare(env)
    )
    previous_calls = len(env.requests), env.uploader.upload.call_count
    entered, release = threading.Event(), threading.Event()
    stage = env.sources.stage

    def blocked(*args, **kwargs):
        entered.set()
        assert release.wait(5)
        return stage(*args, **kwargs)

    monkeypatch.setattr(env.sources, "stage", blocked)
    workers = JobWorkers(env.coordinator, workers=1)
    try:
        running = workers.prepare_upload(
            env.source,
            origin=env.origins.capture("other-scene"),
            kind="image",
            content_type="image/png",
        )
        assert entered.wait(5)
        queued = (
            workers.prepare_upload(
                env.source, origin=env.origin, kind="image", content_type="image/png"
            )
            if command == "prepare_upload"
            else getattr(workers, command)(
                record.intent.request_id, expected_revision=record.revision
            )
        )
        env.origins.invalidate(env.origin.scene_id)
        release.set()
        assert running.result(5).intent.origin.scene_id == "other-scene"
        with pytest.raises(UploadError, match="origin changed"):
            queued.result(5)
        assert env.store.get(record.intent.request_id) == record
        assert len(env.store.records()) == 2
        assert (len(env.requests), env.uploader.upload.call_count) == previous_calls
    finally:
        release.set()
        workers.shutdown()


@pytest.mark.parametrize(
    "command,preflight", [("initialize_upload", "verify"), ("transfer_upload_part", "part")]
)
def test_origin_change_during_preflight_prevents_the_durable_claim(
    env, command, preflight, monkeypatch
):
    record = prepare(env) if command == "initialize_upload" else initialized(env)
    original = getattr(env.sources, preflight)
    mutation_count = sum(request.method == "POST" for request in env.requests)

    def changed(*args):
        assert not env.origin_held
        result = original(*args)
        env.origins.invalidate(env.origin.scene_id)
        return result

    monkeypatch.setattr(env.sources, preflight, changed)
    with pytest.raises(UploadError, match="origin changed"):
        invoke(env, command, record)
    assert env.store.get(record.intent.request_id) == record
    assert sum(request.method == "POST" for request in env.requests) == mutation_count
    env.uploader.upload.assert_not_called()


def test_upload_origin_guard_covers_intent_and_mutation_claims_but_not_receipts(env, monkeypatch):
    writes = []
    for method in ("create", "transition", "claim_part", "record_part"):
        original = getattr(env.store, method)

        def record_write(*args, _method=method, _original=original, **kwargs):
            writes.append((kwargs.get("state", _method), env.origin_held))
            return _original(*args, **kwargs)

        monkeypatch.setattr(env.store, method, record_write)
    result = invoke(env, "finalize_upload", transferred(env))
    assert result.state == UploadState.PROCESSING
    assert writes == [
        ("create", True),
        (UploadState.INITIALIZING, True),
        (UploadState.UPLOADING, False),
        ("claim_part", True),
        ("record_part", False),
        ("claim_part", True),
        ("record_part", False),
        (UploadState.FINALIZING, True),
        (UploadState.PROCESSING, False),
    ]


@pytest.mark.parametrize(
    "command", ["initialize_upload", "transfer_upload_part", "finalize_upload"]
)
def test_claimed_upload_finishes_after_origin_change_and_explicit_refresh_stays_available(
    env, command, monkeypatch
):
    record = (
        prepare(env)
        if command == "initialize_upload"
        else initialized(env)
        if command == "transfer_upload_part"
        else transferred(env)
    )
    if command == "transfer_upload_part":
        original = env.uploader.upload.side_effect
    else:
        method = "create_upload" if command == "initialize_upload" else "complete_upload"
        original = getattr(env.coordinator._adapter, method)

    def changed(*args, **kwargs):
        assert not env.origin_held
        result = original(*args, **kwargs)
        env.origins.invalidate(env.origin.scene_id)
        return result

    if command == "transfer_upload_part":
        env.uploader.upload.side_effect = changed
    else:
        monkeypatch.setattr(env.coordinator._adapter, method, changed)
    current = invoke(env, command, record)
    assert current.intent.scope == env.scope
    assert current.intent.origin == env.origin
    assert not env.origins.current(env.origin)
    assert env.coordinator.inspect_upload(record.intent.request_id) == current
    assert env.coordinator.upload_recovery_plan()[0].record == current
    env.remote.update(status="imported", entityId="asset-one")
    calls = len(env.requests)
    imported = invoke(env, "refresh_upload", current)
    assert imported.state == UploadState.IMPORTED
    assert imported.intent.origin == env.origin
    assert [request.method for request in env.requests[calls:]] == ["GET"]
