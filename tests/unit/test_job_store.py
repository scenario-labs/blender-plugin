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
    JobMeshSource,
    JobOrigin,
    JobScope,
    JobState,
    JobStore,
    LocalApplicationState,
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
    "missing",
    ["state", "revision", "remote_job_id", "project_id", "target_id", "application_origin"],
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


def make_ready(store, intent, *, texture_role=None):
    record = store.create(intent)
    for state in (JobState.SUBMITTING, JobState.REMOTE, JobState.SUCCEEDED):
        record = advance(
            store,
            record,
            state,
            **({"remote_job_id": "remote"} if state == JobState.REMOTE else {}),
        )
    record = store.set_results(
        intent.request_id,
        (ResultAsset("asset", "result.png", "image/png", texture_role=texture_role),),
        expected_revision=record.revision,
    )
    record = advance(store, record, JobState.DOWNLOADING)
    record = store.record_download(
        intent.request_id,
        "asset",
        DownloadedResult("result.png", 1, "a" * 64),
        expected_revision=record.revision,
    )
    return advance(store, record, JobState.READY)


def legacy_store(path, version):
    """Write the exact previous shared-store record shape, not prototype history."""
    with sqlite3.connect(path) as connection:
        for scope, request_id, raw in connection.execute(
            "SELECT scope, request_id, record FROM jobs"
        ).fetchall():
            value = json.loads(raw)
            if version < 8 and "film_task" in value["intent"]:
                del value["intent"]["film_task"]
            if version < 6:
                del value["intent"]["mesh_sources"]
            if version < 5:
                del value["local_applications"]
            if version == 2:
                del value["application_origin"]
            if version in {2, 3}:
                for item in value["results"]:
                    del item["asset"]["texture_role"]
            connection.execute(
                "UPDATE jobs SET record=? WHERE scope=? AND request_id=?",
                (json.dumps(value), scope, request_id),
            )
        connection.execute("DROP TABLE film_uploads")
        connection.execute(f"PRAGMA user_version={version}")


@pytest.mark.parametrize("version", [2, 3, 4, 5, 6, 7, 8])
def test_shared_store_upgrade_preserves_all_scopes_states_and_receipts(tmp_path, intent, version):
    path = tmp_path / "jobs.sqlite3"
    expected = {}
    for scope in (intent.scope, replace(intent.scope, account_id="other-account")):
        scoped = JobStore(path, scope)
        records = []
        for state in (
            JobState.SUBMITTING,
            JobState.UNCERTAIN,
            JobState.READY,
            JobState.APPLYING,
            JobState.APPLY_FAILED,
            JobState.APPLIED,
        ):
            item = replace(intent, scope=scope, request_id=state.value)
            if state in {JobState.SUBMITTING, JobState.UNCERTAIN}:
                record = advance(scoped, scoped.create(item), JobState.SUBMITTING)
                if state == JobState.UNCERTAIN:
                    record = advance(scoped, record, state)
            else:
                record = make_ready(scoped, item, texture_role="normal" if version >= 4 else None)
                if state != JobState.READY:
                    record = advance(scoped, record, JobState.APPLYING)
                if state in {JobState.APPLY_FAILED, JobState.APPLIED}:
                    record = advance(scoped, record, state)
            records.append(record)
        expected[scope] = tuple(sorted(records, key=lambda record: record.intent.request_id))
    legacy_store(path, version)
    for scope, records in expected.items():
        assert JobStore(path, scope).records() == records
    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 9


@pytest.mark.parametrize("damage", ["commit", "scope", "revision", "record", "foreign", "v1"])
@pytest.mark.parametrize("version", [2, 3, 4, 5, 6, 7, 8])
def test_shared_store_upgrade_failure_preserves_every_row_and_version(
    tmp_path, intent, monkeypatch, damage, version
):
    path = tmp_path / "jobs.sqlite3"
    scoped = JobStore(path, intent.scope)
    scoped.create(intent)
    scoped.create(replace(intent, request_id="z-later"))
    legacy_store(path, version)
    with sqlite3.connect(path) as connection:
        if damage == "scope":
            connection.execute("UPDATE jobs SET scope='invalid' WHERE request_id='z-later'")
        elif damage == "revision":
            connection.execute("UPDATE jobs SET revision=42 WHERE request_id='z-later'")
        elif damage == "record":
            connection.execute("UPDATE jobs SET record='{}' WHERE request_id='z-later'")
        elif damage == "foreign":
            connection.execute("PRAGMA application_id=1")
        elif damage == "v1":
            connection.execute("PRAGMA user_version=1")
    before = path.read_bytes()
    original = sqlite3.connect

    class FailCommit(sqlite3.Connection):
        def commit(self):
            raise sqlite3.OperationalError("synthetic migration commit failure")

    with monkeypatch.context() as patch:
        if damage == "commit":
            patch.setattr(
                sqlite3, "connect", lambda *a, **kw: original(*a, **kw, factory=FailCommit)
            )
        with pytest.raises(StoreError):
            JobStore(path, intent.scope)
    assert path.read_bytes() == before


def test_application_destination_is_claimed_atomically_and_cannot_change_at_receipt(
    store, intent, tmp_path
):
    ready = make_ready(store, intent)
    destination = JobOrigin("new-file", "new-scene", "new-revision")
    claim = advance(store, ready, JobState.APPLYING, application_origin=destination)
    assert claim.intent.origin == intent.origin
    assert (
        JobStore(tmp_path / "jobs.sqlite3", intent.scope).get(intent.request_id).application_origin
        == destination
    )
    with pytest.raises(ValueError):
        advance(store, claim, JobState.APPLIED, application_origin=intent.origin)
    applied = advance(store, claim, JobState.APPLIED)
    assert applied.application_origin == destination
    assert applied.intent == intent


@pytest.mark.parametrize("destination", ["not-an-origin", None])
def test_corrupt_application_destination_is_rejected(store, intent, tmp_path, destination):
    record = advance(store, make_ready(store, intent), JobState.APPLYING)
    value = asdict(record)
    value["application_origin"] = destination
    with sqlite3.connect(tmp_path / "jobs.sqlite3") as connection:
        connection.execute("UPDATE jobs SET record=?", (json.dumps(value),))
    with pytest.raises(StoreError):
        store.get(intent.request_id)


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
        locks = list(tmp_path.glob(".scenario-result-locks/*.lock"))
        assert len(locks) == 1
        assert locks[0].read_bytes() == b"\0"
        assert len(str(locks[0].relative_to(tmp_path))) < 100


def test_result_transfer_locks_are_scoped_and_shared_by_reopened_stores(store, tmp_path):
    reopened = JobStore(tmp_path / "jobs.sqlite3", store.scope)
    other_scope = replace(store.scope, project_id="other-project")
    other = JobStore(tmp_path / "jobs.sqlite3", other_scope)
    other_database = JobStore(tmp_path / "other.sqlite3", store.scope)
    with store.result_transfer_lock("request-one"):
        with pytest.raises(StoreConflict):
            with reopened.result_transfer_lock("request-one"):
                pytest.fail("Two owners acquired the same lock")
        with (
            reopened.result_transfer_lock("request-two"),
            other.result_transfer_lock("request-one"),
            other_database.result_transfer_lock("request-one"),
        ):
            pass
    with reopened.result_transfer_lock("request-one"):
        pass


@pytest.mark.parametrize("kind", ["symlink", "hardlink", "directory", "oversized"])
def test_result_transfer_lock_rejects_nonprivate_paths(store, tmp_path, kind):
    with store.result_transfer_lock("request-one"):
        pass
    path = next(tmp_path.glob(".scenario-result-locks/*.lock"))
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


def test_parent_alias_shares_database_and_lock_and_cannot_retarget_open_store(
    store, tmp_path, intent
):
    alias = tmp_path / "alias"
    alias.symlink_to(tmp_path, target_is_directory=True)
    opened = JobStore(alias / "jobs.sqlite3", store.scope)
    record = opened.create(intent)
    assert store.get(intent.request_id) == record
    with store.result_transfer_lock(intent.request_id):
        with pytest.raises(StoreConflict):
            with opened.result_transfer_lock(intent.request_id):
                pytest.fail("Alias bypassed the original database's lock")
    replacement = tmp_path / "replacement"
    replacement.mkdir()
    replacement_store = JobStore(replacement / "jobs.sqlite3", store.scope)
    alias.unlink()
    alias.symlink_to(replacement, target_is_directory=True)
    assert opened.get(intent.request_id) == record
    assert replacement_store.get(intent.request_id) is None
    with store.result_transfer_lock(intent.request_id):
        with pytest.raises(StoreConflict):
            with opened.result_transfer_lock(intent.request_id):
                pytest.fail("Retargeted alias changed an existing owner's lock")


@pytest.mark.parametrize("exists", [True, False])
def test_resolving_parent_never_accepts_a_symlinked_database(tmp_path, intent, exists):
    actual = tmp_path / "actual"
    actual.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(actual, target_is_directory=True)
    target = actual / "target.sqlite3"
    if exists:
        JobStore(target, intent.scope).create(intent)
    (actual / "jobs.sqlite3").symlink_to(target)
    before = target.read_bytes() if exists else None
    with pytest.raises(StoreError, match="regular local file"):
        JobStore(alias / "jobs.sqlite3", intent.scope)
    assert (target.read_bytes() if target.exists() else None) == before


def test_v3_upgrade_preserves_a_recovered_application_destination(tmp_path, intent):
    path = tmp_path / "jobs.sqlite3"
    store = JobStore(path, intent.scope)
    ready = make_ready(store, intent)
    destination = JobOrigin("recovered-file", "recovered-scene", "recovered-revision")
    claim = advance(store, ready, JobState.APPLYING, application_origin=destination)
    legacy_store(path, 3)
    reopened = JobStore(path, intent.scope).get(intent.request_id)
    assert reopened == claim
    assert reopened.application_origin == destination
    assert reopened.results[0].asset.texture_role is None


def completed_result(store, intent):
    ready = make_ready(store, intent)
    return advance(store, advance(store, ready, JobState.APPLYING), JobState.APPLIED)


def reuse(store, record, **changes):
    arguments = {
        "expected_revision": record.revision,
        "application_id": "local-one",
        "destination": JobOrigin("new-file", "new-scene", "new-revision", "new-target"),
        "purpose": "world",
        "asset_ids": ("asset",),
        **changes,
    }
    return store.claim_local_application(record.intent.request_id, **arguments)


@pytest.mark.parametrize("outcome", [LocalApplicationState.APPLIED, LocalApplicationState.FAILED])
@pytest.mark.parametrize("purpose", ["world", "model", "mesh_edit"])
def test_local_reuse_keeps_generation_completed_and_history_survives_restart(
    store, intent, tmp_path, outcome, purpose
):
    original = completed_result(store, intent)
    claimed = reuse(store, original, purpose=purpose)
    assert replace(claimed, revision=original.revision, local_applications=()) == original
    assert claimed.local_applications[0].source_revision == original.revision
    reopened = JobStore(tmp_path / "jobs.sqlite3", store.scope)
    assert reopened.get(intent.request_id) == claimed
    assert reopened.get(intent.request_id).local_applications[0].purpose == purpose
    with pytest.raises(StoreConflict, match="unfinished"):
        reuse(reopened, claimed, application_id="local-two")
    finished = reopened.finish_local_application(
        intent.request_id,
        expected_revision=claimed.revision,
        application_id="local-one",
        state=outcome,
    )
    assert finished.state == JobState.APPLIED
    assert finished.local_applications == (replace(claimed.local_applications[0], state=outcome),)
    with pytest.raises(StoreConflict):
        reuse(store, original, application_id="stale-review")
    with pytest.raises(StoreConflict, match="already used"):
        reuse(store, finished)
    second = reuse(store, finished, application_id="local-two", purpose="images")
    assert second.local_applications[:-1] == finished.local_applications
    assert second.local_applications[-1].source_revision == finished.revision
    assert JobStore(tmp_path / "jobs.sqlite3", store.scope).get(intent.request_id) == second
    for state in (JobState.PREPARED, JobState.SUBMITTING, JobState.READY, JobState.APPLYING):
        with pytest.raises(ValueError):
            advance(store, second, state)


def test_local_reuse_is_scoped_and_only_one_racing_claim_wins(store, intent, tmp_path):
    original = completed_result(store, intent)
    other = JobStore(tmp_path / "jobs.sqlite3", replace(store.scope, project_id="other-project"))
    with pytest.raises(StoreConflict):
        reuse(other, original)
    owners = [JobStore(tmp_path / "jobs.sqlite3", store.scope) for _ in range(2)]
    barrier = Barrier(2)

    def claim(index):
        barrier.wait(timeout=5)
        try:
            return reuse(owners[index], original, application_id=f"racer-{index}")
        except StoreConflict:
            return None

    with ThreadPoolExecutor(max_workers=2) as workers:
        results = tuple(workers.map(claim, range(2)))
    assert sum(item is not None for item in results) == 1
    current = store.get(intent.request_id)
    assert current.revision == original.revision + 1
    assert len(current.local_applications) == 1
    assert other.get(intent.request_id) is None


@pytest.mark.parametrize(
    "change",
    [
        {"expected_revision": True},
        {"application_id": "https://private.invalid/"},
        {"purpose": "generate"},
        {"asset_ids": ()},
        {"asset_ids": ["asset"]},
        {"asset_ids": ("asset", "asset")},
        {"asset_ids": ("missing",)},
        {"destination": None},
        {"asset_ids": tuple(str(i) for i in range(129))},
    ],
)
def test_invalid_local_reuse_preserves_completed_job(store, intent, change):
    original = completed_result(store, intent)
    with pytest.raises((ValueError, StoreConflict)):
        reuse(store, original, **change)
    assert store.get(intent.request_id) == original


@pytest.mark.parametrize("state", [JobState.READY, JobState.APPLYING, JobState.APPLY_FAILED])
def test_unfinished_original_application_cannot_be_bypassed_by_local_reuse(store, intent, state):
    record = make_ready(store, intent)
    if state != JobState.READY:
        record = advance(store, record, JobState.APPLYING)
    if state == JobState.APPLY_FAILED:
        record = advance(store, record, state)
    with pytest.raises(ValueError, match="completed"):
        reuse(store, record)
    assert store.get(intent.request_id) == record


@pytest.mark.parametrize("committed", [False, True])
@pytest.mark.parametrize("operation", ["claim", "finish"])
def test_local_application_write_failure_never_authorizes_replay(
    store, intent, monkeypatch, committed, operation
):
    original = completed_result(store, intent)
    before = reuse(store, original) if operation == "finish" else original
    connect = sqlite3.connect

    class FailCommit(sqlite3.Connection):
        def commit(self):
            if committed:
                super().commit()
            raise sqlite3.OperationalError("private-path write response lost")

    with monkeypatch.context() as patch:
        patch.setattr(sqlite3, "connect", lambda *a, **kw: connect(*a, **kw, factory=FailCommit))
        with pytest.raises(StoreError) as caught:
            if operation == "claim":
                reuse(store, before)
            else:
                store.finish_local_application(
                    intent.request_id,
                    expected_revision=before.revision,
                    application_id="local-one",
                    state=LocalApplicationState.APPLIED,
                )
        assert "private-path" not in str(caught.value)
    saved = store.get(intent.request_id)
    assert saved.state == JobState.APPLIED and saved.intent == original.intent
    if not committed:
        assert saved == before
    elif operation == "claim":
        assert saved.local_applications[-1].state == LocalApplicationState.APPLYING
        with pytest.raises(StoreConflict):
            reuse(store, saved, application_id="retry")
    else:
        assert saved.local_applications[-1].state == LocalApplicationState.APPLIED
        with pytest.raises(StoreConflict):
            store.finish_local_application(
                intent.request_id,
                expected_revision=before.revision,
                application_id="local-one",
                state=LocalApplicationState.FAILED,
            )


def test_local_application_outcome_requires_current_unfinished_identity(store, intent):
    claimed = reuse(store, completed_result(store, intent))
    for identifier, revision, state in [
        ("missing", claimed.revision, LocalApplicationState.APPLIED),
        ("local-one", claimed.revision - 1, LocalApplicationState.APPLIED),
        ("local-one", claimed.revision, LocalApplicationState.APPLYING),
        ("local-one", claimed.revision, "applied"),
    ]:
        with pytest.raises((ValueError, StoreConflict)):
            store.finish_local_application(
                intent.request_id,
                expected_revision=revision,
                application_id=identifier,
                state=state,
            )
        assert store.get(intent.request_id) == claimed
    finished = store.finish_local_application(
        intent.request_id,
        expected_revision=claimed.revision,
        application_id="local-one",
        state=LocalApplicationState.APPLIED,
    )
    with pytest.raises(StoreConflict):
        store.finish_local_application(
            intent.request_id,
            expected_revision=finished.revision,
            application_id="local-one",
            state=LocalApplicationState.FAILED,
        )


@pytest.mark.parametrize(
    "damage",
    [
        "missing-history",
        "missing-destination",
        "bad-state",
        "bad-assets",
        "duplicate",
        "future-revision",
        "outcome-revision",
        "out-of-order",
        "unfinished-earlier",
        "wrong-job-state",
    ],
)
def test_corrupt_local_application_history_fails_closed(store, intent, tmp_path, damage):
    first = reuse(store, completed_result(store, intent))
    finished = store.finish_local_application(
        intent.request_id,
        expected_revision=first.revision,
        application_id="local-one",
        state=LocalApplicationState.APPLIED,
    )
    reuse(store, finished, application_id="local-two")
    with sqlite3.connect(tmp_path / "jobs.sqlite3") as connection:
        raw = json.loads(connection.execute("SELECT record FROM jobs").fetchone()[0])
        history = raw["local_applications"]
        if damage == "missing-history":
            del raw["local_applications"]
        elif damage == "missing-destination":
            del history[0]["destination"]["target_id"]
        elif damage == "bad-state":
            history[0]["state"] = "prepared"
        elif damage == "bad-assets":
            history[0]["asset_ids"] = ["different"]
        elif damage == "duplicate":
            history[1]["application_id"] = history[0]["application_id"]
        elif damage == "future-revision":
            history[1]["source_revision"] = raw["revision"]
        elif damage == "outcome-revision":
            history[1]["state"] = "applied"
        elif damage == "out-of-order":
            history[1]["source_revision"] = history[0]["source_revision"]
        elif damage == "unfinished-earlier":
            history[0]["state"] = "applying"
        else:
            raw["state"] = "ready"
            raw["application_origin"] = None
        connection.execute("UPDATE jobs SET record=?", (json.dumps(raw),))
    before = (tmp_path / "jobs.sqlite3").read_bytes()
    with pytest.raises(StoreError):
        store.get(intent.request_id)
    assert (tmp_path / "jobs.sqlite3").read_bytes() == before


def test_local_history_capacity_preserves_all_prior_records(store, intent):
    record = completed_result(store, intent)
    for index in range(128):
        record = reuse(store, record, application_id=f"local-{index}")
        record = store.finish_local_application(
            intent.request_id,
            expected_revision=record.revision,
            application_id=f"local-{index}",
            state=LocalApplicationState.APPLIED,
        )
    with pytest.raises(ValueError, match="bounded"):
        reuse(store, record, application_id="beyond-capacity")
    assert store.get(intent.request_id) == record


@pytest.fixture
def mesh_binding(intent):
    from scenario.core.jobs.mesh_source import MeshSource, MeshSourceObject

    return JobMeshSource(
        "mesh",
        None,
        "mesh-asset",
        "upload-one",
        8,
        intent.origin,
        MeshSource(
            "a" * 64,
            (
                MeshSourceObject(
                    intent.origin.target_id,
                    "b" * 64,
                    ((1, 0, 0, 3), (0, 1, 0, 4), (0, 0, 1, 5), (0, 0, 0, 1)),
                ),
            ),
        ),
    )


@pytest.mark.parametrize(
    "damage", ["missing", "null", "extra", "matrix", "target", "duplicate", "index"]
)
def test_corrupt_mesh_binding_cannot_be_read_as_unbound_job(store, intent, mesh_binding, damage):
    saved = store.create(replace(intent, mesh_sources=(mesh_binding,)))
    with sqlite3.connect(store._path) as connection:
        value = json.loads(connection.execute("SELECT record FROM jobs").fetchone()[0])
        bindings = value["intent"]["mesh_sources"]
        if damage == "missing":
            del value["intent"]["mesh_sources"]
        elif damage == "null":
            value["intent"]["mesh_sources"] = None
        elif damage == "extra":
            bindings[0]["unknown"] = True
        elif damage == "matrix":
            bindings[0]["mesh_source"]["objects"][0]["matrix_world"] = [[1]]
        elif damage == "target":
            bindings[0]["origin"]["target_id"] = "another-object"
        elif damage == "duplicate":
            bindings.append(bindings[0])
        elif damage == "index":
            bindings[0]["index"] = True
        connection.execute("UPDATE jobs SET record=?", (json.dumps(value),))
    with pytest.raises(StoreError):
        store.get(saved.intent.request_id)


def test_schema_five_upgrade_preserves_unfinished_local_application(tmp_path, intent):
    path = tmp_path / "jobs.sqlite3"
    store = JobStore(path, intent.scope)
    unfinished = reuse(store, completed_result(store, intent))
    legacy_store(path, 5)
    reopened = JobStore(path, intent.scope)
    assert reopened.get(intent.request_id) == unfinished
    assert unfinished.local_applications[-1].state == LocalApplicationState.APPLYING
    with pytest.raises(StoreConflict, match="unfinished"):
        reuse(reopened, unfinished, application_id="repeat")


def test_schema_six_upgrade_preserves_mesh_sources_and_unfinished_reuse(
    tmp_path, intent, mesh_binding
):
    path = tmp_path / "jobs.sqlite3"
    store = JobStore(path, intent.scope)
    bound = replace(intent, mesh_sources=(mesh_binding,))
    unfinished = reuse(store, completed_result(store, bound))
    legacy_store(path, 6)
    reopened = JobStore(path, intent.scope)
    assert reopened.get(intent.request_id) == unfinished
    assert unfinished.intent.mesh_sources == (mesh_binding,)
    assert unfinished.local_applications[-1].state == LocalApplicationState.APPLYING
    with pytest.raises(StoreConflict, match="unfinished"):
        reuse(reopened, unfinished, application_id="repeat")


def test_schema_seven_cloud_results_survive_upgrade(tmp_path, intent):
    from scenario.core.jobs.store import CloudJobIntent

    path = tmp_path / "jobs.sqlite3"
    store = JobStore(path, intent.scope)
    local = store.create(intent)
    cloud = store.adopt_cloud_job(
        CloudJobIntent("cloud", intent.scope, replace(intent.origin, target_id=None), "model"),
        "cloud-remote",
    )
    legacy_store(path, 7)
    upgraded = JobStore(path, intent.scope)
    assert upgraded.get(intent.request_id) == local
    assert upgraded.get("cloud") == cloud
    assert cloud.intent.film_task is None


def test_schema_eight_preserves_uncertain_film_identity_and_adds_empty_uploads(tmp_path, intent):
    from scenario.core.jobs.store import FilmTaskBinding

    path = tmp_path / "jobs.sqlite3"
    store = JobStore(path, intent.scope)
    bound = replace(intent, film_task=FilmTaskBinding("production", "take", "a" * 64, "b" * 64))
    row = advance(store, store.create(bound), JobState.SUBMITTING)
    row = advance(store, row, JobState.UNCERTAIN)
    legacy_store(path, 8)
    reopened = JobStore(path, intent.scope)
    assert reopened.film_job("production", "take") == row
    assert reopened.film_upload("production", "take") is None
    with pytest.raises(StoreConflict):
        reopened.create(replace(bound, request_id="duplicate"))


def test_schema_eight_ambiguous_film_jobs_roll_back_upgrade(tmp_path, intent):
    from scenario.core.jobs.store import FilmTaskBinding

    path = tmp_path / "jobs.sqlite3"
    store = JobStore(path, intent.scope)
    bound = replace(intent, film_task=FilmTaskBinding("production", "take", "a" * 64, "b" * 64))
    row = store.create(bound)
    duplicate = replace(row, intent=replace(bound, request_id="duplicate"))
    with sqlite3.connect(path) as connection:
        connection.execute(
            "INSERT INTO jobs VALUES (?, ?, ?, ?)",
            (store._key, "duplicate", 0, json.dumps(asdict(duplicate))),
        )
    legacy_store(path, 8)
    before = path.read_bytes()
    with pytest.raises(StoreError, match="multiple"):
        JobStore(path, intent.scope)
    assert path.read_bytes() == before
