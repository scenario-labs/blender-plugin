# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Durable claims make interrupted upload mutations visible instead of replayable."""

import hashlib
import json
import os
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from threading import Barrier

import pytest

from scenario.core.jobs.store import JobOrigin, JobScope, JobStore, StoreConflict, StoreError
from scenario.core.jobs.upload_store import UploadIntent, UploadState, UploadStore
from scenario.core.jobs.upload_transfers import UploadedPart


def digest(data):
    return hashlib.sha256(data).hexdigest()


@pytest.fixture
def intent():
    return UploadIntent(
        "reference-one",
        JobScope("https://service.example.invalid/v1", "account-one", "project-one", "team-one"),
        JobOrigin("file-one", "scene-one", "revision-one", "object-one"),
        "image",
        "reference.png",
        "image/png",
        5,
        digest(b"abcde"),
        3,
        (digest(b"abc"), digest(b"de")),
    )


@pytest.fixture
def store(tmp_path, intent):
    return UploadStore(tmp_path / "private" / "uploads.sqlite3", intent.scope)


def advance(store, record, state, **kwargs):
    return store.transition(
        record.intent.request_id, expected_revision=record.revision, state=state, **kwargs
    )


def uploading(store, intent):
    record = advance(store, store.create(intent), UploadState.INITIALIZING)
    return advance(store, record, UploadState.UPLOADING, upload_id="remote-one")


def send_part(store, record):
    claimed = store.claim_part(record.intent.request_id, expected_revision=record.revision)
    number = claimed.active_part
    receipt = UploadedPart(
        number, record.intent.part_bytes(number), record.intent.part_sha256[number - 1]
    )
    return store.record_part(record.intent.request_id, receipt, expected_revision=claimed.revision)


def test_reopen_retains_exact_source_scope_origin_and_receipts(store, intent):
    record = send_part(store, uploading(store, intent))
    reopened = UploadStore(store._path, intent.scope)
    assert reopened.get(intent.request_id) == record
    assert reopened.records() == (record,)
    assert record.active_part is None
    assert record.receipts == (UploadedPart(1, 3, digest(b"abc")),)
    assert record.intent.part_bytes(2) == 2
    if os.name != "nt":
        assert store._path.stat().st_mode & 0o777 == 0o600
        assert store._path.parent.stat().st_mode & 0o777 == 0o700


@pytest.mark.parametrize(
    "field,value",
    [
        ("account_id", "account-two"),
        ("project_id", "project-two"),
        ("team_id", "team-two"),
        ("service", "https://other.example.invalid/v1"),
    ],
)
def test_scopes_cannot_read_or_overwrite_each_other(store, intent, field, value):
    original = store.create(intent)
    other_scope = replace(intent.scope, **{field: value})
    other = UploadStore(store._path, other_scope)
    assert other.get(intent.request_id) is None
    assert other.records() == ()
    with pytest.raises(ValueError):
        other.create(intent)
    other.create(replace(intent, scope=other_scope))
    assert store.get(intent.request_id) == original


@pytest.mark.parametrize(
    "field,value",
    [
        ("kind", []),
        ("kind", "unknown"),
        ("file_name", "../private.png"),
        ("content_type", "image/png\r\nprivate"),
        ("file_size", True),
        ("file_size", 0),
        ("part_size", 0),
        ("part_size", 6),
        ("part_sha256", ("0" * 64,)),
        ("part_sha256", ("x" * 64, "0" * 64)),
        ("file_sha256", "x" * 64),
    ],
)
def test_invalid_source_identity_rejected_before_storage(intent, field, value):
    with pytest.raises(ValueError):
        replace(intent, **{field: value})


def test_existing_request_cannot_be_recreated_or_rebound(store, intent):
    original = store.create(intent)
    with pytest.raises(StoreConflict):
        store.create(replace(intent, file_sha256=digest(b"other")))
    assert store.get(intent.request_id) == original
    record = advance(store, original, UploadState.INITIALIZING)
    with pytest.raises(ValueError):
        advance(store, record, UploadState.UPLOADING)
    record = advance(store, record, UploadState.UPLOADING, upload_id="remote-one")
    with pytest.raises(ValueError):
        advance(store, record, UploadState.PROCESSING, upload_id="remote-two")
    assert store.get(intent.request_id) == record


def test_two_connections_can_claim_only_one_part(store, intent):
    record = uploading(store, intent)
    barrier = Barrier(2)

    def claim():
        peer = UploadStore(store._path, intent.scope)
        barrier.wait(timeout=5)
        try:
            return peer.claim_part(intent.request_id, expected_revision=record.revision)
        except StoreConflict:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(claim) for _ in range(2)]
        results = [future.result(timeout=10) for future in futures]
    assert sum(result is not None for result in results) == 1
    assert store.get(intent.request_id).active_part == 1


@pytest.mark.parametrize("phase", ["initialize", "part", "finalize"])
def test_restart_keeps_inflight_claim_without_automatic_replay(store, intent, phase):
    if phase == "initialize":
        record = advance(store, store.create(intent), UploadState.INITIALIZING)
        uncertain = UploadState.INITIALIZATION_UNCERTAIN
    else:
        record = uploading(store, intent)
        if phase == "part":
            record = store.claim_part(intent.request_id, expected_revision=record.revision)
            uncertain = UploadState.PART_UNCERTAIN
        else:
            record = send_part(store, send_part(store, record))
            record = advance(store, record, UploadState.FINALIZING)
            uncertain = UploadState.FINALIZATION_UNCERTAIN
    reopened = UploadStore(store._path, intent.scope)
    assert reopened.get(intent.request_id) == record
    with pytest.raises(StoreConflict):
        reopened.claim_part(intent.request_id, expected_revision=record.revision)
    record = advance(reopened, record, uncertain)
    for state in (
        UploadState.PREPARED,
        UploadState.INITIALIZING,
        UploadState.UPLOADING,
        UploadState.FINALIZING,
    ):
        with pytest.raises(ValueError):
            advance(reopened, record, state)
    assert reopened.get(intent.request_id) == record


@pytest.mark.parametrize(
    "receipt",
    [
        UploadedPart(2, 2, digest(b"de")),
        UploadedPart(1, 4, digest(b"abc")),
        UploadedPart(1, 3, digest(b"bad")),
        UploadedPart(True, 3, digest(b"abc")),
    ],
)
def test_wrong_receipt_never_clears_claim(store, intent, receipt):
    record = uploading(store, intent)
    record = store.claim_part(intent.request_id, expected_revision=record.revision)
    with pytest.raises((ValueError, StoreConflict)):
        store.record_part(intent.request_id, receipt, expected_revision=record.revision)
    assert store.get(intent.request_id) == record


def test_finalization_requires_all_receipts_and_import_requires_asset(store, intent):
    record = uploading(store, intent)
    with pytest.raises(ValueError):
        advance(store, record, UploadState.FINALIZING)
    record = send_part(store, record)
    with pytest.raises(ValueError):
        advance(store, record, UploadState.FINALIZING)
    record = send_part(store, record)
    with pytest.raises(ValueError):
        store.claim_part(intent.request_id, expected_revision=record.revision)
    record = advance(store, record, UploadState.FINALIZING)
    record = advance(store, record, UploadState.PROCESSING)
    with pytest.raises(ValueError):
        advance(store, record, UploadState.IMPORTED)
    record = advance(store, record, UploadState.IMPORTED, asset_id="asset-one")
    assert record.asset_id == "asset-one"
    with pytest.raises(ValueError):
        advance(store, record, UploadState.FINALIZING)


def test_authoritative_observation_can_resolve_uncertain_part_without_replay(store, intent):
    record = uploading(store, intent)
    record = store.claim_part(intent.request_id, expected_revision=record.revision)
    record = advance(store, record, UploadState.PART_UNCERTAIN)
    record = advance(store, record, UploadState.PROCESSING)
    record = advance(store, record, UploadState.IMPORTED, asset_id="asset-one")
    assert record.receipts == ()
    assert record.active_part is None
    assert record.upload_id == "remote-one"


def test_failed_write_preserves_claim_and_sanitizes_error(store, intent):
    record = uploading(store, intent)
    record = store.claim_part(intent.request_id, expected_revision=record.revision)
    with sqlite3.connect(store._path) as connection:
        connection.execute(
            "CREATE TRIGGER reject_write BEFORE UPDATE ON uploads "
            "BEGIN SELECT RAISE(ABORT, 'private-data'); END"
        )
    with pytest.raises(StoreError) as error:
        store.record_part(
            intent.request_id, UploadedPart(1, 3, digest(b"abc")), expected_revision=record.revision
        )
    assert "private-data" not in str(error.value)
    assert store.get(intent.request_id) == record


@pytest.mark.parametrize("damage", ["missing_receipts", "revision", "scope", "state", "digest"])
def test_corrupt_record_is_preserved_for_recovery(store, intent, damage):
    store.create(intent)
    with sqlite3.connect(store._path) as connection:
        value = json.loads(connection.execute("SELECT record FROM uploads").fetchone()[0])
        if damage == "missing_receipts":
            del value["receipts"]
        elif damage == "revision":
            value["revision"] = 9
        elif damage == "scope":
            value["intent"]["scope"]["account_id"] = "other"
        elif damage == "state":
            value["state"] = "imported"
        else:
            value["intent"]["part_sha256"] = ["bad"]
        raw = json.dumps(value)
        connection.execute("UPDATE uploads SET record=?", (raw,))
    with pytest.raises(StoreError):
        store.get(intent.request_id)
    with sqlite3.connect(store._path) as connection:
        assert connection.execute("SELECT record FROM uploads").fetchone()[0] == raw


def test_foreign_database_and_future_schema_are_not_reset(tmp_path, intent):
    path = tmp_path / "foreign.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE unrelated (value TEXT)")
        connection.execute("INSERT INTO unrelated VALUES ('preserve')")
    with pytest.raises(StoreError):
        UploadStore(path, intent.scope)
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT value FROM unrelated").fetchone()[0] == "preserve"
    path = tmp_path / "future.sqlite3"
    store = UploadStore(path, intent.scope)
    store.create(intent)
    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA user_version=99")
    with pytest.raises(StoreError):
        store.get(intent.request_id)
    with pytest.raises(StoreError):
        UploadStore(path, intent.scope)


@pytest.mark.parametrize("store_type", [UploadStore, JobStore])
def test_symlink_created_during_exclusive_open_does_not_reach_sqlite(
    tmp_path, intent, monkeypatch, store_type
):
    path = tmp_path / "database.sqlite3"
    target = tmp_path / "preserve.sqlite3"
    target.write_bytes(b"unrelated original bytes")
    original_open = os.open

    def swapped_open(name, flags, mode=0o777, **kwargs):
        if Path(name) == path:
            path.symlink_to(target)
        return original_open(name, flags, mode, **kwargs)

    monkeypatch.setattr(os, "open", swapped_open)
    with pytest.raises(StoreError, match="regular local file"):
        store_type(path, intent.scope)
    assert target.read_bytes() == b"unrelated original bytes"


@pytest.mark.parametrize("store_type", [UploadStore, JobStore])
def test_database_replaced_by_symlink_after_initialization_is_rejected(
    tmp_path, intent, store_type
):
    path = tmp_path / "database.sqlite3"
    database = store_type(path, intent.scope)
    saved = tmp_path / "saved.sqlite3"
    path.rename(saved)
    previous = saved.read_bytes()
    path.symlink_to(saved)
    with pytest.raises(StoreError, match="regular local file"):
        database.records()
    assert saved.read_bytes() == previous
