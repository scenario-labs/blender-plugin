# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Credential-bound local recovery never requires a service call or stores keys."""

import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import pytest

from scenario.core.api.sdk_adapter import Credentials
from scenario.core.jobs import credential_storage
from scenario.core.jobs.credential_storage import open_credential_store
from scenario.core.jobs.store import JobIntent, JobOrigin, JobState, StoreError

CREDS = Credentials("synthetic-local-key", "synthetic-local-secret")


def uncertain(store):
    intent = JobIntent(
        "request",
        store.scope,
        JobOrigin("file", "scene", "revision"),
        "model",
        "model",
        "a" * 64,
        "b" * 64,
        "0.10000000000000001",
    )
    record = store.create(intent)
    return store.transition(
        record.intent.request_id, expected_revision=record.revision, state=JobState.SUBMITTING
    )


def test_restart_recovers_exact_scope_and_does_not_replay_uncertain_work(tmp_path):
    store = open_credential_store(tmp_path, CREDS)
    record = uncertain(store)
    reopened = open_credential_store(tmp_path, CREDS)
    assert reopened.scope == store.scope
    assert reopened.scope.project_id is None
    assert reopened.scope.team_id is None
    assert reopened.get("request") == record
    assert reopened.get("request").state == JobState.SUBMITTING
    raw = b"".join(p.read_bytes() for p in tmp_path.iterdir() if p.is_file())
    assert CREDS.api_key.encode() not in raw
    assert CREDS.api_secret.encode() not in raw
    assert CREDS.authorization().encode() not in raw


@pytest.mark.parametrize("change", ["key", "secret", "service", "team", "project"])
def test_changed_credentials_or_context_isolate_history_and_switch_back(tmp_path, change):
    original = open_credential_store(tmp_path, CREDS)
    record = uncertain(original)
    creds, options = CREDS, {}
    if change == "key":
        creds = replace(CREDS, api_key="different-key")
    elif change == "secret":
        creds = replace(CREDS, api_secret="different-secret")
    else:
        key = {"service": "service", "team": "team_id", "project": "project_id"}[change]
        options[key] = "https://other.example.invalid/v1" if change == "service" else "other"
    other = open_credential_store(tmp_path, creds, **options)
    assert other.scope != original.scope
    assert other.records() == ()
    assert open_credential_store(tmp_path, CREDS).get("request") == record


def test_same_pair_in_another_installation_has_a_different_local_identity(tmp_path):
    first = open_credential_store(tmp_path / "first", CREDS)
    second = open_credential_store(tmp_path / "second", CREDS)
    assert first.scope.account_id != second.scope.account_id


def test_competing_initialization_uses_one_complete_key(tmp_path):
    with ThreadPoolExecutor(max_workers=8) as pool:
        scopes = list(pool.map(lambda _: open_credential_store(tmp_path, CREDS).scope, range(16)))
    assert len(set(scopes)) == 1
    assert not list(tmp_path.glob(".scope-*"))
    if os.name == "posix":
        assert (tmp_path / "scope.key").stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize("content", [b"", b"invalid", b"SCENARIO-LOCAL-SCOPE-v1\n" + b"x" * 33])
def test_malformed_scope_key_is_preserved(tmp_path, content):
    path = tmp_path / "scope.key"
    path.write_bytes(content)
    with pytest.raises(StoreError, match="invalid"):
        open_credential_store(tmp_path, CREDS)
    assert path.read_bytes() == content
    assert not (tmp_path / "jobs.sqlite3").exists()


def test_missing_scope_key_never_replaces_existing_history(tmp_path):
    original = open_credential_store(tmp_path, CREDS)
    record = uncertain(original)
    key = tmp_path / "scope.key"
    saved = key.read_bytes()
    key.unlink()
    with pytest.raises(StoreError, match="missing"):
        open_credential_store(tmp_path, CREDS)
    assert not key.exists()
    assert original.get("request") == record
    key.write_bytes(saved)
    assert open_credential_store(tmp_path, CREDS).get("request") == record


def test_failed_key_publication_leaves_no_partial_key_or_database(tmp_path, monkeypatch):
    def fail(*args):
        raise OSError("private filesystem detail")

    with monkeypatch.context() as patcher:
        patcher.setattr(credential_storage.os, "link", fail)
        with pytest.raises(StoreError) as caught:
            open_credential_store(tmp_path, CREDS)
    assert "private filesystem detail" not in str(caught.value)
    assert caught.value.__suppress_context__
    assert list(tmp_path.iterdir()) == []
    assert open_credential_store(tmp_path, CREDS).scope.project_id is None


@pytest.mark.parametrize(
    "credentials",
    [
        Credentials(),
        Credentials("key"),
        Credentials(bearer_token="token"),
        Credentials("a:b", "secret"),
    ],
)
def test_invalid_or_bearer_credentials_do_not_create_storage(tmp_path, credentials):
    with pytest.raises(ValueError):
        open_credential_store(tmp_path, credentials)
    assert list(tmp_path.iterdir()) == []


def test_symlinked_scope_key_is_rejected(tmp_path):
    original = open_credential_store(tmp_path / "first", CREDS)
    second = tmp_path / "second"
    second.mkdir()
    try:
        (second / "scope.key").symlink_to(tmp_path / "first/scope.key")
    except OSError:
        pytest.skip("Symlink creation is unavailable")
    with pytest.raises(StoreError, match="regular"):
        open_credential_store(second, CREDS)
    assert open_credential_store(tmp_path / "first", CREDS).scope == original.scope


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="POSIX FIFO")
def test_scope_key_fifo_is_rejected_without_blocking(tmp_path):
    os.mkfifo(tmp_path / "scope.key")
    with pytest.raises(StoreError, match="regular"):
        open_credential_store(tmp_path, CREDS)
