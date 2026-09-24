# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Crash boundaries, immutable asset identity and verified local result recovery."""

import hashlib
import json
import os
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Barrier
from types import SimpleNamespace

import pytest

from scenario.core.jobs.store import (
    JobIntent,
    JobOrigin,
    JobScope,
    JobState,
    JobStore,
    ResultAsset,
    StoreConflict,
    StoreError,
)
from scenario.core.jobs.transfers import DownloadedResult, TransferError, verify_download

DATA = b"local result fixture"
DIGEST = hashlib.sha256(DATA).hexdigest()
ASSET = ResultAsset("asset-one", "one.png", "image/png", len(DATA), DIGEST)
RECEIPT = DownloadedResult(ASSET.name, len(DATA), DIGEST)


def advance(store, record, state):
    return store.transition(
        record.intent.request_id,
        expected_revision=record.revision,
        state=state,
        remote_job_id="remote" if state == JobState.REMOTE else None,
    )


@pytest.fixture
def setup(tmp_path):
    scope = JobScope("https://service.example.invalid/v1", "account", "project", "team")
    store = JobStore(tmp_path / "jobs.sqlite3", scope)
    record = store.create(
        JobIntent(
            "request",
            scope,
            JobOrigin("file", "scene", "revision"),
            "model",
            "model",
            "a" * 64,
            "b" * 64,
            "0.1",
        )
    )
    for state in (JobState.SUBMITTING, JobState.REMOTE, JobState.SUCCEEDED):
        record = advance(store, record, state)
    return store, record


def attach(store, record, assets=(ASSET,)):
    return store.set_results(record.intent.request_id, assets, expected_revision=record.revision)


def download(store, record, asset=ASSET, receipt=RECEIPT):
    return store.record_download(
        record.intent.request_id, asset.asset_id, receipt, expected_revision=record.revision
    )


def test_manifest_and_partial_receipts_survive_reopen_and_retry(setup, tmp_path):
    store, record = setup
    second = ResultAsset("asset-two", "two.png", "image/png")
    record = attach(store, record, (ASSET, second))
    record = advance(store, record, JobState.DOWNLOADING)
    record = download(store, record)
    record = advance(store, record, JobState.DOWNLOAD_FAILED)
    reopened = JobStore(tmp_path / "jobs.sqlite3", store.scope)
    assert reopened.get("request") == record
    record = advance(reopened, record, JobState.DOWNLOADING)
    with pytest.raises(ValueError, match="Every result"):
        advance(reopened, record, JobState.READY)
    record = download(reopened, record, second, replace(RECEIPT, name=second.name))
    for state in (
        JobState.READY,
        JobState.APPLYING,
        JobState.APPLY_FAILED,
        JobState.APPLYING,
        JobState.APPLIED,
    ):
        record = advance(reopened, record, state)
    assert len(record.results) == 2
    assert reopened.get("request") == record
    assert record.intent.origin == setup[1].intent.origin


def test_receipt_must_follow_durable_manifest_and_download_claim(setup):
    store, record = setup
    with pytest.raises(ValueError, match="manifest"):
        advance(store, record, JobState.DOWNLOADING)
    record = attach(store, record)
    with pytest.raises(ValueError, match="Claim"):
        download(store, record)
    with pytest.raises(ValueError):
        attach(store, record)
    record = advance(store, record, JobState.DOWNLOADING)
    for wrong in (
        replace(RECEIPT, name="other.png"),
        replace(RECEIPT, size=0),
        replace(RECEIPT, sha256="c" * 64),
    ):
        with pytest.raises(ValueError, match="match"):
            download(store, record, receipt=wrong)
        assert store.get("request") == record
    with pytest.raises(ValueError, match="absent"):
        download(store, record, replace(ASSET, asset_id="unknown"))
    record = download(store, record)
    with pytest.raises(ValueError, match="already"):
        download(store, record)


def test_results_are_scope_isolated_and_revision_checked(setup, tmp_path):
    store, before = setup
    record = attach(store, before)
    with pytest.raises(StoreConflict):
        attach(store, before)
    for field in ("account_id", "project_id", "team_id"):
        other = JobStore(tmp_path / "jobs.sqlite3", replace(store.scope, **{field: "other"}))
        assert other.get("request") is None
        with pytest.raises(StoreConflict):
            attach(other, before)
    assert store.get("request") == record


def test_competing_manifest_writers_cannot_replace_identity(setup, tmp_path):
    store, record = setup
    barrier = Barrier(2)

    def bind(_):
        other = JobStore(tmp_path / "jobs.sqlite3", store.scope)
        barrier.wait()
        try:
            return attach(other, record)
        except StoreConflict:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        records = list(pool.map(bind, range(2)))
    assert sum(item is not None for item in records) == 1
    assert store.get("request").results[0].asset == ASSET


@pytest.mark.parametrize("operation", ["manifest", "receipt"])
def test_failed_commit_preserves_previous_manifest_and_receipts(setup, monkeypatch, operation):
    store, record = setup
    if operation == "receipt":
        record = advance(store, attach(store, record), JobState.DOWNLOADING)
    connect = sqlite3.connect

    class FailCommit(sqlite3.Connection):
        def commit(self):
            raise sqlite3.OperationalError("private failure")

    with monkeypatch.context() as patch:
        patch.setattr(sqlite3, "connect", lambda *a, **kw: connect(*a, **kw, factory=FailCommit))
        with pytest.raises(StoreError):
            attach(store, record) if operation == "manifest" else download(store, record)
    assert store.get("request") == record


@pytest.mark.parametrize(
    "assets",
    [(), (ASSET, ASSET), (ASSET, replace(ASSET, asset_id="other", name="ONE.png")), (ASSET,) * 129],
)
def test_empty_duplicate_or_unbounded_manifest_is_rejected(setup, assets):
    store, record = setup
    with pytest.raises(ValueError):
        attach(store, record, assets)
    assert store.get("request") == record


@pytest.mark.parametrize(
    "changes",
    [
        {"asset_id": "https://host/asset?secret=yes"},
        {"name": "../escape.png"},
        {"name": "NUL.png"},
        {"media_type": "image/png; signed=secret"},
        {"expected_size": True},
        {"expected_size": -1},
        {"expected_size": 2**63},
        {"expected_sha256": "invalid"},
    ],
)
def test_metadata_rejects_paths_urls_and_invalid_shapes(changes):
    with pytest.raises(ValueError):
        replace(ASSET, **changes)


@pytest.mark.parametrize(
    "change",
    [
        "missing-results",
        "missing-asset-field",
        "missing-receipt-field",
        "ready-without-receipt",
        "unexpected-field",
    ],
)
def test_corrupt_result_data_is_preserved_and_rejected(setup, tmp_path, change):
    store, record = setup
    record = advance(store, attach(store, record), JobState.DOWNLOADING)
    if change == "missing-receipt-field":
        download(store, record)
    with sqlite3.connect(tmp_path / "jobs.sqlite3") as connection:
        raw = json.loads(connection.execute("SELECT record FROM jobs").fetchone()[0])
        if change == "missing-results":
            del raw["results"]
        elif change == "missing-asset-field":
            del raw["results"][0]["asset"]["expected_size"]
        elif change == "missing-receipt-field":
            del raw["results"][0]["receipt"]["size"]
        elif change == "ready-without-receipt":
            raw["state"] = "ready"
        else:
            raw["results"][0]["url"] = "https://private.invalid/?secret"
        connection.execute("UPDATE jobs SET record=?", (json.dumps(raw),))
    with pytest.raises(StoreError):
        store.get("request")


def test_previous_schema_is_preserved_without_silent_reset(setup, tmp_path):
    store, _ = setup
    with sqlite3.connect(tmp_path / "jobs.sqlite3") as connection:
        connection.execute("PRAGMA user_version=1")
    with pytest.raises(StoreError, match="Unsupported"):
        JobStore(tmp_path / "jobs.sqlite3", store.scope)
    with sqlite3.connect(tmp_path / "jobs.sqlite3") as connection:
        assert connection.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 1


def test_verified_file_is_rehashed_and_changes_fail_without_repair(tmp_path):
    path = tmp_path / ASSET.name
    path.write_bytes(DATA)
    assert verify_download(tmp_path, RECEIPT) == path
    path.write_bytes(b"x" * len(DATA))
    with pytest.raises(TransferError, match="receipt"):
        verify_download(tmp_path, RECEIPT)
    assert path.read_bytes() == b"x" * len(DATA)
    path.unlink()
    with pytest.raises(TransferError):
        verify_download(tmp_path, RECEIPT)


@pytest.mark.parametrize(
    "change",
    [None, "descriptor-ctime", "path-inode", "path-birthtime", "path-mtime", "path-mode"],
)
def test_windows_verification_compares_consistent_times_without_hiding_changes(
    tmp_path, monkeypatch, change
):
    from scenario.core.jobs import transfers

    path = tmp_path / ASSET.name
    path.write_bytes(DATA)
    original = path.stat()
    attributes = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns", "st_mode")

    def snapshot(**overrides):
        values = {name: getattr(original, name) for name in attributes}
        values.update(st_ctime_ns=200, st_birthtime_ns=100)
        values.update(overrides)
        return SimpleNamespace(**values)

    before, after, current = snapshot(), snapshot(), snapshot(st_ctime_ns=100)
    if change == "descriptor-ctime":
        after.st_ctime_ns += 1
    elif change is not None:
        attribute = {
            "path-inode": "st_ino",
            "path-birthtime": "st_birthtime_ns",
            "path-mtime": "st_mtime_ns",
            "path-mode": "st_mode",
        }[change]
        setattr(current, attribute, getattr(current, attribute) + 1)
    windows_os = SimpleNamespace(**vars(os))
    windows_os.name = "nt"
    snapshots = iter((before, after))
    windows_os.fstat = lambda descriptor: next(snapshots)
    monkeypatch.setattr(transfers, "os", windows_os)
    lstat = type(path).lstat
    monkeypatch.setattr(type(path), "lstat", lambda self: current if self == path else lstat(self))
    if change is None:
        assert verify_download(tmp_path, RECEIPT) == path
    else:
        with pytest.raises(TransferError, match="receipt"):
            verify_download(tmp_path, RECEIPT)


def test_symlinks_directories_and_over_limit_files_are_not_verified(tmp_path):
    destination = tmp_path / ASSET.name
    target = tmp_path / "target"
    target.write_bytes(DATA)
    destination.symlink_to(target)
    with pytest.raises(TransferError):
        verify_download(tmp_path, RECEIPT)
    destination.unlink()
    destination.mkdir()
    with pytest.raises(TransferError):
        verify_download(tmp_path, RECEIPT)
    with pytest.raises(TransferError):
        verify_download(tmp_path, RECEIPT, max_bytes=1)


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="POSIX FIFO")
def test_fifo_is_rejected_without_waiting_for_writer(tmp_path):
    os.mkfifo(tmp_path / ASSET.name)
    with pytest.raises(TransferError):
        verify_download(tmp_path, RECEIPT)
