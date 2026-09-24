# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Scoped upload inspection preserves evidence without dispatch or recovery writes."""

import hashlib
import json
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError, asdict, replace
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest

from scenario.core.api.sdk_adapter import Credentials, SDKAdapter
from scenario.core.jobs.coordinator import JobCoordinator
from scenario.core.jobs.store import JobOrigin, JobScope, JobStore, StoreConflict, StoreError
from scenario.core.jobs.transfers import StoragePolicy
from scenario.core.jobs.upload_sources import UploadSources
from scenario.core.jobs.upload_store import UploadIntent, UploadState, UploadStore
from scenario.core.jobs.upload_transfers import PartUploader, UploadedPart
from scenario.core.jobs.uploads import UploadError, UploadRecoveryAction, UploadRecoveryItem

SCOPE = JobScope("https://service.example.invalid/v1", "account", "project", "team")
ORIGIN = JobOrigin("file", "scene", "revision", "target")


@pytest.fixture
def make_env(tmp_path):
    coordinators = []

    def make(scope=SCOPE, *, respond=None, configured=True):
        requests = []

        def handler(request):
            requests.append(request)
            if respond is None:
                pytest.fail("Inspection must not contact the service")
            return respond(request)

        adapter = SDKAdapter(
            Credentials("fixture-key", "fixture-secret"),
            base_url=scope.service,
            account_id=scope.account_id,
            project_id=scope.project_id,
            team_id=scope.team_id,
            online=lambda: respond is not None,
            transport=httpx.MockTransport(handler),
        )
        path = tmp_path / "uploads.sqlite3"
        store = UploadStore(path, scope)
        root = tmp_path / "sources"
        root.mkdir(exist_ok=True)
        sources = UploadSources(root, max_bytes=30, part_bytes=3)
        uploader = PartUploader(
            StoragePolicy(frozenset({"storage.example.invalid"}), max_bytes=3),
            online_access=lambda: False,
        )
        uploader.upload = Mock(side_effect=AssertionError("Inspection cannot send bytes"))
        options = (
            {"upload_store": store, "upload_sources": sources, "part_uploader": uploader}
            if configured
            else {}
        )
        coordinator = JobCoordinator(adapter, JobStore(tmp_path / "jobs.sqlite3", scope), **options)
        coordinators.append(coordinator)
        return SimpleNamespace(
            coordinator=coordinator,
            store=store,
            scope=scope,
            path=path,
            root=root,
            sources=sources,
            uploader=uploader,
            requests=requests,
        )

    yield make
    for coordinator in coordinators:
        coordinator.close()


def intent(scope=SCOPE, request_id="local-upload", origin=ORIGIN):
    return UploadIntent(
        request_id,
        scope,
        origin,
        "image",
        "reference.png",
        "image/png",
        5,
        hashlib.sha256(b"abcde").hexdigest(),
        3,
        tuple(hashlib.sha256(part).hexdigest() for part in (b"abc", b"de")),
    )


def seed(env, state, *, active=False, complete=False):
    record = env.store.create(intent(env.scope))

    def transition(state, **kwargs):
        return env.store.transition(
            record.intent.request_id, expected_revision=record.revision, state=state, **kwargs
        )

    if state == UploadState.PREPARED:
        return record
    if state == UploadState.CANCELED:
        return transition(state)
    record = transition(UploadState.INITIALIZING)
    if state == UploadState.INITIALIZING:
        return record
    if state == UploadState.INITIALIZATION_UNCERTAIN:
        return transition(state)
    record = transition(UploadState.UPLOADING, upload_id="remote-upload")
    if active or state == UploadState.PART_UNCERTAIN:
        record = env.store.claim_part(record.intent.request_id, expected_revision=record.revision)
    if complete or state in {UploadState.FINALIZING, UploadState.FINALIZATION_UNCERTAIN}:
        for number, digest in enumerate(record.intent.part_sha256, 1):
            record = env.store.claim_part(
                record.intent.request_id, expected_revision=record.revision
            )
            record = env.store.record_part(
                record.intent.request_id,
                UploadedPart(number, record.intent.part_bytes(number), digest),
                expected_revision=record.revision,
            )
    if state == UploadState.UPLOADING:
        return record
    if state in {UploadState.FINALIZING, UploadState.FINALIZATION_UNCERTAIN}:
        record = transition(UploadState.FINALIZING)
        if state == UploadState.FINALIZING:
            return record
    return transition(state, asset_id="asset-upload" if state == UploadState.IMPORTED else None)


@pytest.mark.parametrize(
    "state,active,complete,action",
    [
        (UploadState.PREPARED, False, False, UploadRecoveryAction.REVIEW_SOURCE),
        (UploadState.INITIALIZING, False, False, UploadRecoveryAction.RECONCILE_UNKNOWN),
        (
            UploadState.INITIALIZATION_UNCERTAIN,
            False,
            False,
            UploadRecoveryAction.RECONCILE_UNKNOWN,
        ),
        (UploadState.UPLOADING, False, False, UploadRecoveryAction.REVIEW_TRANSFER),
        (UploadState.UPLOADING, False, True, UploadRecoveryAction.REVIEW_TRANSFER),
        (UploadState.UPLOADING, True, False, UploadRecoveryAction.POLL_REMOTE),
        (UploadState.PART_UNCERTAIN, False, False, UploadRecoveryAction.POLL_REMOTE),
        (UploadState.FINALIZING, False, False, UploadRecoveryAction.POLL_REMOTE),
        (UploadState.FINALIZATION_UNCERTAIN, False, False, UploadRecoveryAction.POLL_REMOTE),
        (UploadState.PROCESSING, False, False, UploadRecoveryAction.POLL_REMOTE),
        (UploadState.IMPORTED, False, False, UploadRecoveryAction.FINISHED),
        (UploadState.FAILED, False, False, UploadRecoveryAction.FINISHED),
        (UploadState.CANCELED, False, False, UploadRecoveryAction.FINISHED),
    ],
)
def test_inspection_preserves_each_durable_state_without_source_or_remote_access(
    make_env, monkeypatch, state, active, complete, action
):
    env = make_env()
    record = seed(env, state, active=active, complete=complete)
    saved = env.path.read_bytes()
    for name in ("stage", "verify", "part"):
        monkeypatch.setattr(
            env.sources, name, Mock(side_effect=AssertionError("Inspection cannot read sources"))
        )
    assert env.coordinator.inspect_upload(record.intent.request_id) == record
    assert env.coordinator.upload_recovery_plan() == (UploadRecoveryItem(record, action),)
    assert env.path.read_bytes() == saved
    assert list(env.root.iterdir()) == []
    assert env.requests == []
    env.uploader.upload.assert_not_called()


@pytest.mark.parametrize(
    "change",
    [
        {"account_id": "other-account"},
        {"team_id": "other-team"},
        {"project_id": "other-project"},
        {"project_id": None},
        {"service": "https://other.example.invalid/v1"},
    ],
)
def test_lookup_and_list_isolate_every_scope_dimension_with_colliding_request_ids(make_env, change):
    selected = make_env()
    foreign = make_env(replace(SCOPE, **change))
    own_record = seed(selected, UploadState.PREPARED)
    foreign_record = seed(foreign, UploadState.INITIALIZATION_UNCERTAIN)
    foreign.store.create(intent(foreign.scope, "foreign-only"))
    assert selected.coordinator.inspect_upload("local-upload") == own_record
    assert foreign.coordinator.inspect_upload("local-upload") == foreign_record
    assert selected.coordinator.inspect_upload("foreign-only") is None
    assert selected.coordinator.upload_recovery_plan() == (
        UploadRecoveryItem(own_record, UploadRecoveryAction.REVIEW_SOURCE),
    )
    assert len(foreign.coordinator.upload_recovery_plan()) == 2
    assert selected.requests == foreign.requests == []


def test_restart_inspection_retains_immutable_origin_claims_and_safe_metadata(make_env):
    original = make_env()
    record = seed(original, UploadState.PART_UNCERTAIN)
    original.coordinator.close()
    reopened = make_env()
    plan = reopened.coordinator.upload_recovery_plan()
    assert plan == (UploadRecoveryItem(record, UploadRecoveryAction.POLL_REMOTE),)
    assert reopened.coordinator.inspect_upload(record.intent.request_id) == record
    assert plan[0].record.intent.origin == ORIGIN
    with pytest.raises(FrozenInstanceError):
        plan[0].action = UploadRecoveryAction.REVIEW_TRANSFER
    with pytest.raises(FrozenInstanceError):
        plan[0].record.active_part = None
    with pytest.raises(FrozenInstanceError):
        plan[0].record.intent.origin = JobOrigin("new-file", "new-scene", "new-revision")
    encoded = json.dumps(asdict(plan[0]))
    for forbidden in (
        "fixture-key",
        "fixture-secret",
        "storage.example.invalid",
        str(original.root),
    ):
        assert forbidden not in encoded
    assert reopened.requests == []


@pytest.mark.parametrize("lifecycle", ["deactivate", "close"])
def test_inactive_owner_rejects_inspection_without_changing_records(make_env, lifecycle):
    env = make_env()
    record = seed(env, UploadState.PREPARED)
    getattr(env.coordinator, lifecycle)()
    for operation in (
        lambda: env.coordinator.inspect_upload(record.intent.request_id),
        env.coordinator.upload_recovery_plan,
    ):
        with pytest.raises(UploadError, match="inactive"):
            operation()
    assert env.store.get(record.intent.request_id) == record
    assert env.requests == []


def test_missing_invalid_and_unconfigured_upload_inspection_is_explicit(make_env):
    env = make_env()
    assert env.coordinator.inspect_upload("missing") is None
    assert env.coordinator.upload_recovery_plan() == ()
    with pytest.raises(ValueError):
        env.coordinator.inspect_upload("../invalid")
    unconfigured = make_env(configured=False)
    with pytest.raises(UploadError, match="not configured"):
        unconfigured.coordinator.inspect_upload("missing")
    with pytest.raises(UploadError, match="not configured"):
        unconfigured.coordinator.upload_recovery_plan()
    assert env.requests == unconfigured.requests == []


def test_corrupt_record_inspection_fails_without_resetting_or_hiding_evidence(make_env):
    env = make_env()
    record = seed(env, UploadState.PREPARED)
    with sqlite3.connect(env.path) as connection:
        connection.execute("UPDATE uploads SET record = ?", ('{"private-invalid":true}',))
    saved = env.path.read_bytes()
    for operation in (
        lambda: env.coordinator.inspect_upload(record.intent.request_id),
        env.coordinator.upload_recovery_plan,
    ):
        with pytest.raises(StoreError) as error:
            operation()
        assert "private-invalid" not in str(error.value)
        assert env.path.read_bytes() == saved
    assert env.requests == []


def test_late_initialization_receipt_stays_in_old_scope_and_does_not_update_snapshot(
    make_env, tmp_path
):
    entered, release = threading.Event(), threading.Event()

    def respond(request):
        entered.set()
        assert release.wait(5)
        return httpx.Response(
            200,
            json={
                "upload": {
                    "id": "remote-upload",
                    "kind": "image",
                    "source": "multipart",
                    "status": "pending",
                    "parts": [{"url": "https://storage.example.invalid/part?secret=fixture"}],
                }
            },
        )

    old = make_env(respond=respond)
    source = tmp_path / "input.png"
    source.write_bytes(b"abcde")
    prepared = old.coordinator.prepare_upload(
        source, origin=ORIGIN, kind="image", content_type="image/png"
    )
    with ThreadPoolExecutor(max_workers=1) as worker:
        task = worker.submit(
            old.coordinator.initialize_upload,
            prepared.intent.request_id,
            expected_revision=prepared.revision,
        )
        try:
            assert entered.wait(5)
            before = old.coordinator.upload_recovery_plan()[0]
            assert before.action == UploadRecoveryAction.RECONCILE_UNKNOWN
            assert before.record.state == UploadState.INITIALIZING
            assert before.record.upload_id is None
            old.coordinator.deactivate()
            current = make_env(replace(SCOPE, project_id="new-project"))
            assert current.coordinator.inspect_upload(prepared.intent.request_id) is None
            assert current.coordinator.upload_recovery_plan() == ()
        finally:
            release.set()
        completed = task.result(5)
    assert completed.state == UploadState.UPLOADING
    assert completed.intent.origin == ORIGIN
    assert completed.intent.scope == SCOPE
    assert before.record.state == UploadState.INITIALIZING
    reopened = make_env()
    assert reopened.coordinator.inspect_upload(prepared.intent.request_id) == completed
    assert (
        reopened.coordinator.upload_recovery_plan()[0].action
        == UploadRecoveryAction.REVIEW_TRANSFER
    )
    with pytest.raises(StoreConflict):
        reopened.coordinator.initialize_upload(
            prepared.intent.request_id, expected_revision=prepared.revision
        )
    assert len(old.requests) == 1
    assert reopened.requests == current.requests == []
    assert "secret=fixture" not in repr(completed)
