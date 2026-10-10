# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Real SDK serialization, immutable snapshots and one-attempt upload orchestration."""

import copy
import hashlib
import json
import pickle
import sqlite3
import threading
from contextlib import contextmanager
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest

from scenario.core.api.sdk_adapter import Credentials, SDKAdapter
from scenario.core.jobs.coordinator import JobCoordinator
from scenario.core.jobs.origins import OriginRevisions
from scenario.core.jobs.store import JobScope, JobStore, StoreConflict, StoreError
from scenario.core.jobs.transfers import TransferError
from scenario.core.jobs.upload_sources import UploadSources
from scenario.core.jobs.upload_store import UploadState, UploadStore
from scenario.core.jobs.upload_transfers import (
    PartUploader,
    S3UploadPolicy,
    UploadedPart,
    UploadUncertain,
)
from scenario.core.jobs.uploads import (
    UploadError,
    UploadMutationUncertain,
    UploadPlanUnavailable,
    UploadRecoveryAction,
)
from scenario.core.jobs.workers import JobWorkers

# Observed live contract: only the create response carries the multipart plan.
# Retrieval and the complete action omit these fields entirely.
PLAN_FIELDS = ("originalFileName", "contentType", "fileSize", "partsCount", "parts")
SIGNED = "fixture-signature=secret-fixture"


def expires(hours=48):
    moment = datetime.now(UTC) + timedelta(hours=hours)
    return moment.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def part_url(number, host="fixture-bucket.s3-accelerate.amazonaws.com"):
    return (
        f"https://{host}/uploads/synthetic/reference.png"
        f"?x-id=UploadPart&partNumber={number}&uploadId=fixture&{SIGNED}"
    )


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
        responses=[],
        fail=None,
        online=True,
        origins=origins,
        origin_held=False,
        retrieval={},
        retrieval_plan=False,
    )
    env.remote = {
        "id": "remote-one",
        "status": "pending",
        "source": "multipart",
        "kind": "image",
        "fileName": "uploads/synthetic-storage/reference.png",
        "jobId": "upload-job",
        "authorId": "fixture-author",
        "ownerId": "fixture-owner",
        "assetOptions": {"collectionIds": [], "hide": False},
        "config": {},
        "originalFileName": "reference.png",
        "contentType": "image/png",
        "fileSize": 5,
        "partsCount": 2,
        "parts": [{"number": i, "url": part_url(i), "expires": expires()} for i in (1, 2)],
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
        if operation != "create":
            if not env.retrieval_plan:
                result = {key: value for key, value in result.items() if key not in PLAN_FIELDS}
            result.update(copy.deepcopy(env.retrieval))
        if operation == "complete":
            result["status"] = "validating"
        env.responses.append((operation, result))
        return httpx.Response(200, json={"upload": result})

    adapter = SDKAdapter(
        credentials=Credentials("fixture-key", "fixture-secret"),
        base_url=scope.service,
        account_id=scope.account_id,
        project_id=scope.project_id,
        online=lambda: env.online,
        transport=httpx.MockTransport(handler),
    )
    uploader = PartUploader(S3UploadPolicy(max_bytes=3), online_access=lambda: env.online)

    def put(url, data, *, number, content_type, expected_sha256):
        assert not env.origin_held, "Origin invalidation must not wait for storage PUT"
        record = next(row for row in store.records() if row.state == UploadState.UPLOADING)
        assert record.active_part == number
        assert url == part_url(number) or url.startswith("https://second-bucket.")
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
        # The PUTs used the create plan; both part retrievals were live-shaped.
        assert [call.args[0] for call in env.uploader.upload.call_args_list] == [
            part_url(1),
            part_url(2),
        ]
        for marker in (b"secret-fixture", b"s3-accelerate", b"fixture-signature"):
            assert marker not in env.store._path.read_bytes()
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


def test_live_retrieval_without_plan_fields_still_sends_from_the_create_plan(env):
    record = initialized(env)
    record = invoke(env, "transfer_upload_part", record)
    assert [operation for operation, _ in env.responses] == ["create", "get"]
    assert all(field in env.responses[0][1] for field in PLAN_FIELDS)
    assert not any(field in env.responses[1][1] for field in PLAN_FIELDS)
    assert record.receipts[0].number == 1
    assert env.uploader.upload.call_args.args[0] == part_url(1)
    assert env.coordinator.upload_recovery_plan()[0].action == UploadRecoveryAction.REVIEW_TRANSFER


@pytest.mark.parametrize(
    "field,value",
    [
        ("originalFileName", "other.png"),
        ("fileSize", 6),
        ("partsCount", 3),
        ("kind", "model"),
        ("source", "url"),
        ("contentType", "image/jpeg"),
        ("status", "complete"),
        ("status", "validating"),
        # A retrieval that does carry a plan must pass every create-plan check.
        ("parts", []),
        ("parts", [{"number": 1}, {"number": 1}]),
    ],
)
def test_changed_retrieval_cannot_claim_or_send(env, field, value):
    record = initialized(env)
    env.retrieval[field] = value
    with pytest.raises(UploadError):
        invoke(env, "transfer_upload_part", record)
    assert env.store.get(record.intent.request_id) == record
    env.uploader.upload.assert_not_called()


@pytest.mark.parametrize(
    "field,value",
    [
        ("originalFileName", "other.png"),
        ("originalFileName", None),
        ("contentType", "image/jpeg"),
        ("contentType", None),
        ("fileSize", 6),
        ("fileSize", None),
        ("partsCount", 3),
        ("partsCount", None),
        ("parts", None),
        ("parts", []),
        ("parts", [{"number": 1}, {"number": 1}]),
        ("parts", [{"number": 2}, {"number": 1}]),
        ("expires", "2001-01-01T00:00:00Z"),
        ("expires", "2099-01-01T00:00:00"),
        ("expires", "invalid"),
        ("expires", None),
        ("url", "https://other.example.invalid/part"),
        ("url", "https://s3-accelerate.amazonaws.com/fixture-bucket/part"),
        ("url", "http://fixture-bucket.s3-accelerate.amazonaws.com/part"),
    ],
)
def test_unusable_create_plan_is_never_cached_and_needs_restart(env, field, value):
    if field in {"expires", "url"}:
        env.remote["parts"][0][field] = value
    else:
        env.remote[field] = value
    prepared = prepare(env)
    with pytest.raises(UploadPlanUnavailable) as error:
        invoke(env, "initialize_upload", prepared)
    assert "secret" not in str(error.value)
    record = env.store.get(prepared.intent.request_id)
    # The known remote identity is durable even though no part can be sent.
    assert record.state == UploadState.UPLOADING
    assert record.upload_id == "remote-one"
    assert env.coordinator._uploads._plans == {}
    assert env.coordinator.upload_recovery_plan()[0].action == UploadRecoveryAction.RESTART_UPLOAD
    with pytest.raises(UploadPlanUnavailable):
        invoke(env, "transfer_upload_part", record)
    assert env.store.get(record.intent.request_id) == record
    env.uploader.upload.assert_not_called()
    assert sum(request.method == "POST" for request in env.requests) == 1


def test_new_owner_cannot_resume_a_transfer_and_sends_nothing(env, tmp_path):
    record = invoke(env, "transfer_upload_part", initialized(env))
    assert len(record.receipts) == 1
    restarted = JobCoordinator(
        env.coordinator._adapter,
        JobStore(tmp_path / "jobs.sqlite3", env.scope),
        upload_store=UploadStore(env.store._path, env.scope),
        upload_sources=env.sources,
        part_uploader=env.uploader,
        origin_guard=env.origins.guard,
    )
    requests = len(env.requests)
    assert restarted.upload_recovery_plan()[0].action == UploadRecoveryAction.RESTART_UPLOAD
    with pytest.raises(UploadPlanUnavailable, match="restart the upload"):
        restarted.transfer_upload_part(record.intent.request_id, expected_revision=record.revision)
    # Only a liveness read was sent: no claim, PUT, completion or new initialization.
    assert [request.method for request in env.requests[requests:]] == ["GET"]
    assert env.store.get(record.intent.request_id) == record
    assert env.uploader.upload.call_count == 1
    # The original owner still holds its in-memory plan and can continue.
    finished = invoke(env, "transfer_upload_part", record)
    assert len(finished.receipts) == 2
    assert env.coordinator._uploads._plans == {}


def test_retrieval_that_carries_a_valid_plan_is_used_once_without_caching(env, tmp_path):
    record = initialized(env)
    env.coordinator._uploads.retire()
    restarted = JobCoordinator(
        env.coordinator._adapter,
        JobStore(tmp_path / "jobs.sqlite3", env.scope),
        upload_store=UploadStore(env.store._path, env.scope),
        upload_sources=env.sources,
        part_uploader=env.uploader,
    )
    env.retrieval_plan = True
    record = restarted.transfer_upload_part(
        record.intent.request_id, expected_revision=record.revision
    )
    assert len(record.receipts) == 1
    assert restarted._uploads._plans == {}
    env.retrieval_plan = False
    with pytest.raises(UploadPlanUnavailable):
        restarted.transfer_upload_part(record.intent.request_id, expected_revision=record.revision)
    assert env.uploader.upload.call_count == 1


def test_expired_plan_fails_before_claim_and_needs_restart(env):
    record = initialized(env)
    env.coordinator._uploads._clock = lambda: datetime.now(UTC).timestamp() + 49 * 3600
    with pytest.raises(UploadPlanUnavailable, match="expired"):
        invoke(env, "transfer_upload_part", record)
    assert env.store.get(record.intent.request_id) == record
    env.uploader.upload.assert_not_called()
    assert env.coordinator._uploads._plans == {}
    assert env.coordinator.upload_recovery_plan()[0].action == UploadRecoveryAction.RESTART_UPLOAD


@pytest.mark.parametrize("failure", ["get", "source", "origin", "uncertain"])
def test_interrupted_transfer_ends_the_plan_and_suggests_restart(env, failure):
    record = initialized(env)
    if failure == "get":
        env.fail = "get"
    elif failure == "source":
        path = env.sources._directory(env.scope, record.intent.request_id) / "source.bin"
        path.write_bytes(b"wrong")
    elif failure == "origin":
        env.origins.invalidate(env.origin.scene_id)
    else:
        env.uploader.upload.side_effect = UploadUncertain("private")
    with pytest.raises(UploadError):
        invoke(env, "transfer_upload_part", record)
    assert env.coordinator._uploads._plans == {}
    assert env.coordinator.upload_recovery_plan()[0].action == UploadRecoveryAction.RESTART_UPLOAD


def test_lost_claim_race_keeps_the_plan_for_the_winning_command(env, monkeypatch):
    record = initialized(env)
    claim = env.store.claim_part
    calls = []

    def race(*args, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            raise StoreConflict("synthetic competing claim")
        return claim(*args, **kwargs)

    monkeypatch.setattr(env.store, "claim_part", race)
    with pytest.raises(StoreConflict):
        invoke(env, "transfer_upload_part", record)
    assert set(env.coordinator._uploads._plans) == {record.intent.request_id}
    assert len(invoke(env, "transfer_upload_part", record).receipts) == 1


def test_deactivation_forgets_plans_and_a_late_create_is_not_cached(env, monkeypatch):
    record = initialized(env)
    assert set(env.coordinator._uploads._plans) == {record.intent.request_id}
    env.coordinator.deactivate()
    assert env.coordinator._uploads._plans == {}
    env.coordinator._uploads._keep_plan("late", object())
    assert env.coordinator._uploads._plans == {}


def test_signed_part_destinations_are_never_persisted_logged_or_serialized(env, caplog):
    record = initialized(env)
    plan = env.coordinator._uploads._plans[record.intent.request_id]
    assert repr(plan) == "<upload part plan>"
    with pytest.raises(TypeError):
        pickle.dumps(plan)
    record = invoke(env, "transfer_upload_part", record)
    item = env.coordinator.upload_recovery_plan()[0]
    staged = env.sources._directory(env.scope, record.intent.request_id)
    texts = [
        repr(record),
        repr(item),
        json.dumps(asdict(item)),
        caplog.text,
        env.store._path.read_bytes().decode("latin-1"),
        *(path.read_bytes().decode("latin-1") for path in staged.iterdir()),
    ]
    for text in texts:
        for marker in ("secret-fixture", "s3-accelerate", "fixture-signature", "uploadId"):
            assert marker not in text


def test_restart_abandons_partial_upload_and_sends_saved_copy_as_new_request(env, tmp_path):
    partial = invoke(env, "transfer_upload_part", initialized(env))
    env.source.write_bytes(b"user changed original source")
    restarted = JobCoordinator(
        env.coordinator._adapter,
        JobStore(tmp_path / "jobs.sqlite3", env.scope),
        upload_store=UploadStore(env.store._path, env.scope),
        upload_sources=env.sources,
        part_uploader=env.uploader,
        origin_guard=env.origins.guard,
    )
    origin = env.origins.capture("scene", "object")
    replacement = restarted.restart_upload(
        partial.intent.request_id, expected_revision=partial.revision, origin=origin
    )
    abandoned = env.store.get(partial.intent.request_id)
    assert abandoned.state == UploadState.ABANDONED
    assert abandoned.upload_id == "remote-one"
    assert abandoned.receipts == partial.receipts
    assert abandoned.revision == partial.revision + 1
    assert replacement.state == UploadState.PREPARED
    assert replacement.intent.request_id != partial.intent.request_id
    for key in ("kind", "file_name", "content_type", "file_size", "file_sha256", "part_sha256"):
        assert getattr(replacement.intent, key) == getattr(partial.intent, key)
    assert restarted.upload_recovery_plan()[0].action in {
        UploadRecoveryAction.FINISHED,
        UploadRecoveryAction.REVIEW_SOURCE,
    }
    # The abandoned upload is never resumed, completed or polled again.
    for method in ("transfer_upload_part", "finalize_upload", "refresh_upload"):
        with pytest.raises(StoreConflict):
            getattr(restarted, method)(
                abandoned.intent.request_id, expected_revision=abandoned.revision
            )
    env.remote["id"] = "remote-two"
    record = restarted.initialize_upload(
        replacement.intent.request_id, expected_revision=replacement.revision
    )
    for method in ("transfer_upload_part", "transfer_upload_part", "finalize_upload"):
        record = getattr(restarted, method)(
            record.intent.request_id, expected_revision=record.revision
        )
    assert record.state == UploadState.PROCESSING
    assert record.upload_id == "remote-two"
    sent = [(call.args[1], call.kwargs["number"]) for call in env.uploader.upload.call_args_list]
    assert sent == [(b"abc", 1), (b"abc", 1), (b"de", 2)]
    completions = [r for r in env.requests if r.url.path.endswith("/action")]
    assert [r.url.path.split("/")[-2] for r in completions] == ["remote-two"]
    cleaned = restarted.discard_upload_source(
        abandoned.intent.request_id, expected_revision=abandoned.revision
    )
    assert cleaned == abandoned
    restarted.close()


@pytest.mark.parametrize("stage", ["prepared", "finalizing", "processing", "imported", "stale"])
def test_restart_refuses_unstarted_completed_or_stale_uploads(env, stage):
    if stage == "prepared":
        record = prepare(env)
    elif stage == "imported":
        record = initialized(env)
        env.remote.update(status="imported", entityId="asset-one")
        record = invoke(env, "refresh_upload", record)
    else:
        record = initialized(env)
        if stage != "stale":
            for _ in range(2):
                record = invoke(env, "transfer_upload_part", record)
            record = (
                env.store.transition(
                    record.intent.request_id,
                    expected_revision=record.revision,
                    state=UploadState.FINALIZING,
                )
                if stage == "finalizing"
                else invoke(env, "finalize_upload", record)
            )
    revision = record.revision + (1 if stage == "stale" else 0)
    roots = set(env.root.iterdir())
    with pytest.raises(StoreConflict):
        env.coordinator.restart_upload(
            record.intent.request_id, expected_revision=revision, origin=env.origin
        )
    assert env.store.get(record.intent.request_id) == record
    assert set(env.root.iterdir()) == roots


def test_restart_refuses_a_part_that_is_still_being_sent(env):
    record = initialized(env)
    entered, release = threading.Event(), threading.Event()
    original = env.uploader.upload.side_effect

    def paused(*args, **kwargs):
        entered.set()
        assert release.wait(5)
        return original(*args, **kwargs)

    env.uploader.upload.side_effect = paused
    workers = JobWorkers(env.coordinator, workers=1)
    try:
        task = workers.transfer_upload_part(
            record.intent.request_id, expected_revision=record.revision
        )
        assert entered.wait(5)
        claimed = env.store.get(record.intent.request_id)
        assert claimed.active_part == 1
        assert env.coordinator.upload_recovery_plan()[0].action == UploadRecoveryAction.POLL_REMOTE
        with pytest.raises(StoreConflict, match="still being sent"):
            env.coordinator.restart_upload(
                record.intent.request_id, expected_revision=claimed.revision, origin=env.origin
            )
        release.set()
        assert len(task.result(5).receipts) == 1
    finally:
        release.set()
        workers.shutdown()
    assert len(env.store.records()) == 1


def test_restart_refuses_an_upload_its_owner_can_still_continue(env):
    record = initialized(env)
    assert env.coordinator.upload_recovery_plan()[0].action == UploadRecoveryAction.REVIEW_TRANSFER
    with pytest.raises(StoreConflict, match="can still continue"):
        env.coordinator.restart_upload(
            record.intent.request_id, expected_revision=record.revision, origin=env.origin
        )
    for _ in range(2):
        record = invoke(env, "transfer_upload_part", record)
    # Every receipt is saved: completion needs only the known ID, so no restart.
    with pytest.raises(StoreConflict, match="can still continue"):
        env.coordinator.restart_upload(
            record.intent.request_id, expected_revision=record.revision, origin=env.origin
        )
    assert env.store.records() == (record,)
    assert invoke(env, "finalize_upload", record).state == UploadState.PROCESSING


def test_restart_with_missing_saved_copy_abandons_nothing(env):
    record = initialized(env)
    env.fail = "get"
    with pytest.raises(UploadError):
        invoke(env, "transfer_upload_part", record)
    env.fail = None
    path = env.sources._directory(env.scope, record.intent.request_id) / "source.bin"
    path.write_bytes(b"wrong")
    with pytest.raises(UploadError, match="upload the original file again"):
        env.coordinator.restart_upload(
            record.intent.request_id, expected_revision=record.revision, origin=env.origin
        )
    assert env.store.records() == (record,)


def test_restart_under_a_new_origin_drops_mesh_provenance_only_when_origin_changes(env):
    record = invoke(env, "transfer_upload_part", initialized(env))
    env.origins.invalidate(env.origin.scene_id)
    with pytest.raises(UploadError, match="origin changed"):
        env.coordinator.restart_upload(
            record.intent.request_id, expected_revision=record.revision, origin=env.origin
        )
    origin = env.origins.capture("scene")
    replacement = env.coordinator.restart_upload(
        record.intent.request_id, expected_revision=record.revision, origin=origin
    )
    assert replacement.intent.origin == origin
    assert replacement.intent.mesh_source is None


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


def test_cancel_prepared_upload_is_offline_and_preserves_both_sources(env, monkeypatch):
    record = prepare(env)
    staged = env.sources._directory(env.scope, record.intent.request_id) / "source.bin"
    env.online = False
    env.origins.reset()
    monkeypatch.setattr(env.sources, "verify", lambda *a: pytest.fail("Read source to cancel"))
    canceled = invoke(env, "cancel_prepared_upload", record)
    assert canceled.state == UploadState.CANCELED
    assert canceled.intent == record.intent
    assert canceled.revision == record.revision + 1
    assert canceled.upload_id is None
    assert env.source.read_bytes() == staged.read_bytes() == b"abcde"
    assert env.coordinator.upload_recovery_plan()[0].action.value == "finished"
    assert env.requests == []
    env.uploader.upload.assert_not_called()
    with pytest.raises(StoreConflict):
        invoke(env, "initialize_upload", canceled)


@pytest.mark.parametrize("revision", [True, -1, 1, None])
def test_cancel_prepared_upload_rejects_stale_or_invalid_revisions(env, revision):
    record = prepare(env)
    with pytest.raises(StoreConflict):
        env.coordinator.cancel_prepared_upload(record.intent.request_id, expected_revision=revision)
    assert env.store.get(record.intent.request_id) == record
    assert env.requests == []


def test_cancel_prepared_upload_rejects_inactive_and_missing_requests(env):
    record = prepare(env)
    with pytest.raises(StoreConflict):
        env.coordinator.cancel_prepared_upload("missing", expected_revision=0)
    env.coordinator.deactivate()
    with pytest.raises(UploadError, match="inactive"):
        invoke(env, "cancel_prepared_upload", record)
    assert env.store.get(record.intent.request_id) == record
    assert env.requests == []


@pytest.mark.parametrize("after_commit", [False, True])
def test_cancel_upload_write_failure_requires_inspection_without_dispatch(
    env, monkeypatch, after_commit
):
    record = prepare(env)
    transition = env.store.transition

    def fail(*args, **kwargs):
        if after_commit:
            transition(*args, **kwargs)
        raise StoreError("synthetic cancellation write failure")

    monkeypatch.setattr(env.store, "transition", fail)
    with pytest.raises(StoreError):
        invoke(env, "cancel_prepared_upload", record)
    saved = env.store.get(record.intent.request_id)
    assert saved.state == (UploadState.CANCELED if after_commit else UploadState.PREPARED)
    assert saved.intent == record.intent
    assert env.requests == []


def test_cancel_upload_wins_during_initialization_preflight(env, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor

    record = prepare(env)
    entered, release = threading.Event(), threading.Event()
    verify = env.sources.verify

    def paused(intent):
        entered.set()
        assert release.wait(5)
        return verify(intent)

    monkeypatch.setattr(env.sources, "verify", paused)
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(invoke, env, "initialize_upload", record)
        try:
            assert entered.wait(5)
            canceled = invoke(env, "cancel_prepared_upload", record)
        finally:
            release.set()
        with pytest.raises(StoreConflict):
            pending.result(5)
    assert env.store.get(record.intent.request_id) == canceled
    assert env.requests == []


def test_initialization_claim_wins_before_upload_cancellation(env, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor

    record = prepare(env)
    entered, release = threading.Event(), threading.Event()
    create = env.coordinator._adapter.create_upload

    def paused(**kwargs):
        entered.set()
        assert release.wait(5)
        return create(**kwargs)

    monkeypatch.setattr(env.coordinator._adapter, "create_upload", paused)
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(invoke, env, "initialize_upload", record)
        try:
            assert entered.wait(5)
            claimed = env.store.get(record.intent.request_id)
            assert claimed.state == UploadState.INITIALIZING
            with pytest.raises(StoreConflict):
                invoke(env, "cancel_prepared_upload", claimed)
        finally:
            release.set()
        uploaded = pending.result(5)
    assert uploaded.state == UploadState.UPLOADING
    assert len(env.requests) == 1


def test_full_worker_queue_does_not_delay_prepared_upload_cancellation(env, monkeypatch):
    from scenario.core.jobs.workers import WorkerError

    first, second = prepare(env), prepare(env)
    entered, release = threading.Event(), threading.Event()
    create = env.coordinator._adapter.create_upload

    def paused(**kwargs):
        entered.set()
        assert release.wait(5)
        return create(**kwargs)

    monkeypatch.setattr(env.coordinator._adapter, "create_upload", paused)
    workers = JobWorkers(env.coordinator, workers=1, pending_limit=1)
    try:
        running = workers.initialize_upload(
            first.intent.request_id, expected_revision=first.revision
        )
        assert entered.wait(5)
        queued = workers.initialize_upload(
            second.intent.request_id, expected_revision=second.revision
        )
        with pytest.raises(WorkerError, match="full"):
            workers.initialize_upload(second.intent.request_id, expected_revision=second.revision)
        canceled = workers.cancel_prepared_upload(
            second.intent.request_id, expected_revision=second.revision
        )
        assert canceled.state == UploadState.CANCELED
        release.set()
        running.result(5)
        with pytest.raises(StoreConflict):
            queued.result(5)
        assert len(env.requests) == 1
        workers.deactivate()
        with pytest.raises(WorkerError, match="inactive"):
            workers.cancel_prepared_upload(
                second.intent.request_id, expected_revision=canceled.revision
            )
    finally:
        release.set()
        workers.shutdown()


@pytest.mark.parametrize(
    "stage",
    [
        "initializing",
        "uncertain",
        "uploading",
        "part_uncertain",
        "processing",
        "imported",
        "canceled",
    ],
)
def test_cancel_prepared_upload_never_aborts_claimed_or_finished_work(env, stage):
    if stage in {"initializing", "uncertain", "canceled"}:
        record = prepare(env)
        record = env.store.transition(
            record.intent.request_id,
            expected_revision=record.revision,
            state=UploadState.CANCELED if stage == "canceled" else UploadState.INITIALIZING,
        )
        if stage == "uncertain":
            record = env.store.transition(
                record.intent.request_id,
                expected_revision=record.revision,
                state=UploadState.INITIALIZATION_UNCERTAIN,
            )
    elif stage == "processing":
        record = invoke(env, "finalize_upload", transferred(env))
    else:
        record = initialized(env)
        if stage == "part_uncertain":
            env.uploader.upload.side_effect = UploadUncertain("fixture uncertain transfer")
            with pytest.raises(UploadMutationUncertain):
                invoke(env, "transfer_upload_part", record)
            record = env.store.get(record.intent.request_id)
        elif stage == "imported":
            env.remote.update(status="imported", entityId="asset-one")
            record = invoke(env, "refresh_upload", record)
    calls = len(env.requests)
    transfers = env.uploader.upload.call_count
    with pytest.raises(StoreConflict):
        invoke(env, "cancel_prepared_upload", record)
    assert env.store.get(record.intent.request_id) == record
    assert len(env.requests) == calls
    assert env.uploader.upload.call_count == transfers


@pytest.mark.parametrize("component", ["service", "account_id", "project_id", "team_id"])
def test_upload_cancellation_stays_in_the_selected_scope(env, component):
    from dataclasses import replace

    record = prepare(env)
    changed = "https://other.example.invalid/v1" if component == "service" else "other"
    scope = replace(env.scope, **{component: changed})
    foreign = UploadStore(env.store._path, scope)
    same_id = foreign.create(replace(record.intent, scope=scope))
    foreign_only = foreign.create(replace(record.intent, scope=scope, request_id="foreign-only"))
    with pytest.raises(StoreConflict):
        env.coordinator.cancel_prepared_upload("foreign-only", expected_revision=0)
    invoke(env, "cancel_prepared_upload", record)
    assert foreign.get(same_id.intent.request_id) == same_id
    assert foreign.get("foreign-only") == foreign_only
    assert env.requests == []


def test_independent_upload_owners_cannot_both_cancel_and_initialize(env, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from contextlib import nullcontext

    from scenario.core.jobs.uploads import UploadCommands

    record = prepare(env)
    other_store = UploadStore(env.store._path, env.scope)
    other = UploadCommands(
        env.coordinator._adapter,
        other_store,
        env.sources,
        env.uploader,
        lambda origin=None: nullcontext(),
    )
    barrier = threading.Barrier(2)
    for store in (env.store, other_store):
        transition = store.transition

        def synchronized(*args, _transition=transition, **kwargs):
            if kwargs.get("state") in {UploadState.INITIALIZING, UploadState.CANCELED}:
                barrier.wait(5)
            return _transition(*args, **kwargs)

        monkeypatch.setattr(store, "transition", synchronized)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(invoke, env, "cancel_prepared_upload", record),
            pool.submit(
                other.initialize, record.intent.request_id, expected_revision=record.revision
            ),
        ]
        results = []
        for future in futures:
            try:
                results.append(future.result(5))
            except StoreConflict:
                results.append(None)
    assert sum(result is not None for result in results) == 1
    saved = env.store.get(record.intent.request_id)
    assert saved.state in {UploadState.CANCELED, UploadState.UPLOADING}
    assert len(env.requests) == (0 if saved.state == UploadState.CANCELED else 1)
