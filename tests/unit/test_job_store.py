# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Durability, scope isolation and stale-callback contracts without dispatch."""

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError, asdict, replace
from decimal import Decimal
from threading import Barrier

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
from scenario.core.jobs.transfers import DownloadedResult


@pytest.fixture
def intent():
    return JobIntent(
        request_id="request-one",
        scope=JobScope(
            "https://service.example.invalid/v1", "account-one", "project-one", "team-one"
        ),
        origin=JobOrigin("file-one", "scene-one", "revision-one", "object-one"),
        operation="model",
        target_id="model-one",
        payload_sha256=hashlib.sha256(b'{"prompt":"fixture"}').hexdigest(),
        quote_sha256=hashlib.sha256(b'{"creativeUnitsCost":0.10000000000000001}').hexdigest(),
        quote_cost="0.10000000000000001",
    )


@pytest.fixture
def store(tmp_path, intent):
    return JobStore(tmp_path / "jobs.sqlite3", intent.scope)


def advance(store, record, state, **kwargs):
    return store.transition(
        record.intent.request_id, expected_revision=record.revision, state=state, **kwargs
    )


def test_intent_reopens_exactly_and_cannot_be_mutated(store, tmp_path, intent):
    first = store.create(intent)
    reopened = JobStore(tmp_path / "jobs.sqlite3", intent.scope).get(intent.request_id)
    assert reopened == first
    assert Decimal(reopened.intent.quote_cost) == Decimal("0.10000000000000001")
    assert reopened.intent.origin == intent.origin
    with pytest.raises(FrozenInstanceError):
        reopened.intent.target_id = "other"
    with pytest.raises(FrozenInstanceError):
        store.scope.account_id = "other"
    assert store.records() == (first,)
    if os.name != "nt":
        assert (tmp_path / "jobs.sqlite3").stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize(
    "change",
    [
        {"account_id": "account-two"},
        {"project_id": None},
        {"project_id": "project-two"},
        {"team_id": None},
        {"team_id": "team-two"},
        {"service": "https://other.example.invalid/v1"},
    ],
)
def test_scope_isolation_for_reads_creates_and_transitions(store, tmp_path, intent, change):
    first = store.create(intent)
    scope = replace(intent.scope, **change)
    other = JobStore(tmp_path / "jobs.sqlite3", scope)
    assert other.get(intent.request_id) is None
    assert other.records() == ()
    with pytest.raises(StoreConflict):
        advance(other, first, JobState.SUBMITTING)
    with pytest.raises(ValueError):
        other.create(intent)
    other.create(replace(intent, scope=scope))
    assert store.get(intent.request_id) == first
    assert other.get(intent.request_id).intent.scope == scope


def test_duplicate_identity_never_overwrites_prior_intent(store, intent):
    first = store.create(intent)
    with pytest.raises(StoreConflict):
        store.create(replace(intent, target_id="different-model"))
    assert store.get(intent.request_id) == first


def test_lost_submission_never_returns_to_dispatchable_state(store, tmp_path, intent):
    submitting = advance(store, store.create(intent), JobState.SUBMITTING)
    # A restart preserves in-flight uncertainty for explicit coordinator recovery.
    assert JobStore(tmp_path / "jobs.sqlite3", intent.scope).get(intent.request_id) == submitting
    uncertain = advance(store, submitting, JobState.UNCERTAIN)
    for state in (JobState.PREPARED, JobState.SUBMITTING, JobState.FAILED, JobState.CANCELED):
        with pytest.raises(ValueError):
            advance(store, uncertain, state)
    with pytest.raises(ValueError, match="authoritative"):
        advance(store, uncertain, JobState.REMOTE)
    remote = advance(store, uncertain, JobState.REMOTE, remote_job_id="remote-one")
    assert remote.intent == intent
    with pytest.raises(ValueError, match="cannot change"):
        advance(store, remote, JobState.SUCCEEDED, remote_job_id="remote-two")
    assert store.get(intent.request_id) == remote


def test_generation_download_and_application_have_separate_states(store, intent):
    record = store.create(intent)
    for state in (
        JobState.SUBMITTING,
        JobState.REMOTE,
        JobState.SUCCEEDED,
        JobState.DOWNLOADING,
        JobState.DOWNLOAD_FAILED,
        JobState.DOWNLOADING,
        JobState.READY,
        JobState.APPLYING,
        JobState.APPLY_FAILED,
        JobState.APPLYING,
        JobState.APPLIED,
    ):
        kwargs = {"remote_job_id": "remote-one"} if state == JobState.REMOTE else {}
        if state == JobState.DOWNLOADING and not record.results:
            record = store.set_results(
                record.intent.request_id,
                (ResultAsset("asset", "result.png", "image/png"),),
                expected_revision=record.revision,
            )
        if state == JobState.READY:
            record = store.record_download(
                record.intent.request_id,
                "asset",
                DownloadedResult("result.png", 1, "a" * 64),
                expected_revision=record.revision,
            )
        record = advance(store, record, state, **kwargs)
        assert store.get(intent.request_id) == record
        assert record.intent == intent
    with pytest.raises(ValueError):
        advance(store, record, JobState.SUBMITTING)
    assert record.remote_job_id == "remote-one"


def test_cancel_before_submission_cannot_be_replayed(store, intent):
    canceled = advance(store, store.create(intent), JobState.CANCELED)
    assert canceled.remote_job_id is None
    with pytest.raises(ValueError):
        advance(store, canceled, JobState.SUBMITTING)


@pytest.mark.parametrize("terminal", [JobState.FAILED, JobState.CANCELED, JobState.SUCCEEDED])
def test_remote_terminal_result_requires_acknowledged_job(store, intent, terminal):
    prepared = store.create(intent)
    with pytest.raises(ValueError):
        advance(store, prepared, JobState.REMOTE, remote_job_id="remote")
    submitting = advance(store, prepared, JobState.SUBMITTING)
    remote = advance(store, submitting, JobState.REMOTE, remote_job_id="remote")
    result = advance(store, remote, terminal)
    assert result.remote_job_id == "remote"


def test_stale_revision_cannot_replace_another_callback(store, intent):
    prepared = store.create(intent)
    current = advance(store, prepared, JobState.SUBMITTING)
    with pytest.raises(StoreConflict):
        advance(store, prepared, JobState.CANCELED)
    assert store.get(intent.request_id) == current


def test_two_connections_cannot_both_claim_submission(store, tmp_path, intent):
    prepared = store.create(intent)
    barrier = Barrier(2)

    def claim():
        connection = JobStore(tmp_path / "jobs.sqlite3", intent.scope)
        barrier.wait(timeout=5)
        try:
            return advance(connection, prepared, JobState.SUBMITTING)
        except StoreConflict:
            return None

    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(lambda _: claim(), range(2)))
    assert sum(result is not None for result in results) == 1
    assert store.get(intent.request_id).revision == 1


@pytest.mark.parametrize("operation", ["create", "transition"])
def test_commit_failure_rolls_back_and_is_not_reported_as_success(
    store, intent, monkeypatch, operation
):
    before = store.create(intent) if operation == "transition" else None
    original = sqlite3.connect

    class FailCommit(sqlite3.Connection):
        def commit(self):
            raise sqlite3.OperationalError("private-path simulated disk failure")

    with monkeypatch.context() as patch:
        patch.setattr(
            sqlite3,
            "connect",
            lambda *args, **kwargs: original(*args, **kwargs, factory=FailCommit),
        )
        with pytest.raises(StoreError) as error:
            if before:
                advance(store, before, JobState.SUBMITTING)
            else:
                store.create(intent)
        assert "private-path" not in str(error.value)
    assert store.get(intent.request_id) == before


def test_process_exit_before_commit_keeps_last_durable_state(store, tmp_path, intent):
    before = store.create(intent)
    script = """
import os, sqlite3, sys
connection = sqlite3.connect(sys.argv[1], isolation_level=None)
connection.execute('BEGIN IMMEDIATE')
connection.execute('DELETE FROM jobs')
os._exit(0)
"""
    subprocess.run(
        [sys.executable, "-c", script, str(tmp_path / "jobs.sqlite3")], check=True, timeout=10
    )
    assert store.get(intent.request_id) == before


@pytest.mark.parametrize(
    "mode",
    [
        "future-version",
        "foreign-application",
        "corrupt-json",
        "wrong-scope",
        "wrong-revision",
        "wrong-id",
    ],
)
def test_corrupt_or_incompatible_database_is_preserved_and_rejected(store, tmp_path, intent, mode):
    record = store.create(intent)
    path = tmp_path / "jobs.sqlite3"
    with sqlite3.connect(path) as connection:
        if mode == "future-version":
            connection.execute("PRAGMA user_version=99")
        elif mode == "foreign-application":
            connection.execute("PRAGMA application_id=1")
        else:
            value = asdict(record)
            if mode == "wrong-scope":
                value["intent"]["scope"]["account_id"] = "other"
            elif mode == "wrong-revision":
                value["revision"] = 42
            elif mode == "wrong-id":
                value["intent"]["request_id"] = "other"
            raw = "invalid" if mode == "corrupt-json" else json.dumps(value)
            connection.execute("UPDATE jobs SET record=?", (raw,))
    corrupted = path.read_bytes()
    with pytest.raises(StoreError):
        store.get(intent.request_id)
    with pytest.raises(StoreError):
        store.create(replace(intent, request_id="new")) if mode in {
            "future-version",
            "foreign-application",
        } else store.create(intent)
    assert path.read_bytes() == corrupted


def test_foreign_database_is_not_adopted(tmp_path, intent):
    path = tmp_path / "jobs.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE unrelated (value TEXT)")
    before = path.read_bytes()
    with pytest.raises(StoreError, match="Unsupported"):
        JobStore(path, intent.scope)
    assert path.read_bytes() == before


def test_deleted_database_is_not_silently_recreated(store, tmp_path, intent):
    (tmp_path / "jobs.sqlite3").unlink()
    with pytest.raises(StoreError):
        store.get(intent.request_id)
    assert not (tmp_path / "jobs.sqlite3").exists()


@pytest.mark.parametrize(
    "changes",
    [
        {"request_id": ""},
        {"target_id": "https://private.invalid?secret"},
        {"operation": "unknown"},
        {"payload_sha256": "not-a-hash"},
        {"quote_sha256": "F" * 64},
        {"quote_cost": "NaN"},
        {"quote_cost": "Infinity"},
        {"quote_cost": "-0.1"},
        {"quote_cost": 0.1},
        {"origin": None},
        {"scope": None},
    ],
)
def test_invalid_intent_is_rejected(intent, changes):
    with pytest.raises(ValueError):
        replace(intent, **changes)


@pytest.mark.parametrize(
    "missing", ["state", "revision", "remote_job_id", "project_id", "target_id"]
)
def test_missing_fields_cannot_reset_inflight_state_to_prepared(store, tmp_path, intent, missing):
    record = advance(store, store.create(intent), JobState.SUBMITTING)
    value = asdict(record)
    if missing == "project_id":
        del value["intent"]["scope"][missing]
    elif missing == "target_id":
        del value["intent"]["origin"][missing]
    else:
        del value[missing]
    with sqlite3.connect(tmp_path / "jobs.sqlite3") as connection:
        connection.execute("UPDATE jobs SET record=?", (json.dumps(value),))
    with pytest.raises(StoreError):
        store.get(intent.request_id)
    with pytest.raises(StoreError):
        store.transition(intent.request_id, expected_revision=1, state=JobState.SUBMITTING)


@pytest.mark.parametrize(
    "service",
    [
        "http://invalid",
        "https://user:secret@host/v1",
        "https://host/v1?token=secret",
        "https://host/v1/",
        "https://host/\npath",
        None,
    ],
)
def test_invalid_service_scope_is_rejected(service):
    with pytest.raises(ValueError):
        JobScope(service, "account")


@pytest.mark.parametrize("terminal", [JobState.SUCCEEDED, JobState.FAILED, JobState.CANCELED])
def test_cancel_claim_never_returns_to_dispatchable_remote(store, tmp_path, intent, terminal):
    remote = advance(
        store,
        advance(store, store.create(intent), JobState.SUBMITTING),
        JobState.REMOTE,
        remote_job_id="remote-one",
    )
    claimed = advance(store, remote, JobState.CANCEL_REQUESTED)
    assert JobStore(tmp_path / "jobs.sqlite3", intent.scope).get(intent.request_id) == claimed
    for forbidden in (
        JobState.CANCEL_REQUESTED,
        JobState.REMOTE,
        JobState.PREPARED,
        JobState.SUBMITTING,
    ):
        with pytest.raises(ValueError):
            advance(store, claimed, forbidden)
    assert advance(store, claimed, terminal).remote_job_id == "remote-one"


def test_result_transfer_lock_excludes_another_process_and_releases_after_death(store, tmp_path):
    script = """
import json, os, sys
from scenario.core.jobs.store import JobScope, JobStore, StoreConflict
store = JobStore(sys.argv[1], JobScope(**json.loads(sys.argv[2])))
try:
    with store.result_transfer_lock("request-one"):
        os._exit(23)
except StoreConflict:
    sys.exit(22)
"""
    args = [
        sys.executable,
        "-c",
        script,
        str(tmp_path / "jobs.sqlite3"),
        json.dumps(asdict(store.scope)),
    ]
    with store.result_transfer_lock("request-one"):
        result = subprocess.run(args, timeout=15, capture_output=True, text=True)
        assert result.returncode == 22, result.stderr
    result = subprocess.run(args, timeout=15, capture_output=True, text=True)
    assert result.returncode == 23, result.stderr
    # Abrupt process exit releases the OS lock; its file must remain in place.
    with store.result_transfer_lock("request-one"):
        locks = list(tmp_path.glob(".scenario-result-locks-*/*.lock"))
        assert len(locks) == 1
        assert locks[0].read_bytes() == b"\0"


def test_result_transfer_locks_are_scoped_and_shared_by_reopened_stores(store, tmp_path):
    reopened = JobStore(tmp_path / "jobs.sqlite3", store.scope)
    other_scope = replace(store.scope, project_id="other-project")
    other = JobStore(tmp_path / "jobs.sqlite3", other_scope)
    with store.result_transfer_lock("request-one"):
        with pytest.raises(StoreConflict):
            with reopened.result_transfer_lock("request-one"):
                pytest.fail("Two owners acquired the same lock")
        with (
            reopened.result_transfer_lock("request-two"),
            other.result_transfer_lock("request-one"),
        ):
            pass
    with reopened.result_transfer_lock("request-one"):
        pass


@pytest.mark.parametrize("kind", ["symlink", "hardlink", "directory", "oversized"])
def test_result_transfer_lock_rejects_nonprivate_paths(store, tmp_path, kind):
    with store.result_transfer_lock("request-one"):
        pass
    path = next(tmp_path.glob(".scenario-result-locks-*/*.lock"))
    path.unlink()
    outside = tmp_path / "untouched"
    outside.write_bytes(b"x")
    if kind == "symlink":
        path.symlink_to(outside)
    elif kind == "hardlink":
        os.link(outside, path)
    elif kind == "directory":
        path.mkdir()
    else:
        path.write_bytes(b"not a lock")
    with pytest.raises(StoreError):
        with store.result_transfer_lock("request-one"):
            pytest.fail("Accepted unsafe lock")
    assert outside.read_bytes() == b"x"
