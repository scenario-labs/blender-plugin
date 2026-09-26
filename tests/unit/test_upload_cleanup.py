# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Explicit upload snapshot cleanup preserves history and unfamiliar files."""

import os
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from scenario.core.api.sdk_adapter import Credentials, SDKAdapter
from scenario.core.jobs.coordinator import JobCoordinator
from scenario.core.jobs.store import JobOrigin, JobScope, JobStore, StoreConflict, StoreError
from scenario.core.jobs.transfers import StoragePolicy, TransferError
from scenario.core.jobs.upload_sources import UploadSources
from scenario.core.jobs.upload_store import UploadState, UploadStore
from scenario.core.jobs.upload_transfers import PartUploader
from scenario.core.jobs.uploads import UploadError
from scenario.core.jobs.workers import JobWorkers


@pytest.fixture
def env(tmp_path):
    root = tmp_path / "staged"
    root.mkdir()
    source = tmp_path / "reference.png"
    source.write_bytes(b"abcde")
    scope = JobScope("https://service.example.invalid/v1", "account", "project", "team")
    sources = UploadSources(root, max_bytes=30, part_bytes=3)
    intent = sources.stage(
        source,
        request_id="request",
        scope=scope,
        origin=JobOrigin("file", "scene", "revision", "target"),
        kind="image",
        content_type="image/png",
    )
    store = UploadStore(tmp_path / "uploads.sqlite3", scope)
    record = store.create(intent)
    calls = []

    def deny(request):
        calls.append(request)
        pytest.fail("Source cleanup cannot contact Scenario")

    adapter = SDKAdapter(
        Credentials("fixture-key", "fixture-secret"),
        base_url=scope.service,
        account_id=scope.account_id,
        project_id=scope.project_id,
        team_id=scope.team_id,
        online=lambda: False,
        transport=httpx.MockTransport(deny),
    )
    coordinator = JobCoordinator(
        adapter,
        JobStore(tmp_path / "jobs.sqlite3", scope),
        upload_store=store,
        upload_sources=sources,
        part_uploader=PartUploader(
            StoragePolicy(frozenset({"storage.example.invalid"}), max_bytes=3),
            online_access=lambda: False,
        ),
    )
    directory = sources._directory(scope, intent.request_id)
    yield SimpleNamespace(
        root=root,
        source=source,
        sources=sources,
        intent=intent,
        store=store,
        record=record,
        coordinator=coordinator,
        scope=scope,
        directory=directory,
        staged=directory / "source.bin",
        calls=calls,
    )
    coordinator.close()
    assert calls == []
    assert source.read_bytes() == b"abcde"


def finish(env, state=UploadState.CANCELED):
    current = env.record
    if state != UploadState.CANCELED:
        current = env.store.transition(
            "request", expected_revision=current.revision, state=UploadState.INITIALIZING
        )
        current = env.store.transition(
            "request",
            expected_revision=current.revision,
            state=UploadState.UPLOADING,
            upload_id="remote",
        )
    return env.store.transition(
        "request",
        expected_revision=current.revision,
        state=state,
        asset_id="asset" if state == UploadState.IMPORTED else None,
    )


def discard(env, record):
    return env.coordinator.discard_upload_source("request", expected_revision=record.revision)


@pytest.mark.parametrize("state", [UploadState.CANCELED, UploadState.FAILED, UploadState.IMPORTED])
def test_terminal_cleanup_is_offline_idempotent_and_keeps_durable_evidence(env, state):
    record = finish(env, state)
    assert discard(env, record) == record
    assert not env.directory.exists()
    assert env.store.get("request") == record
    assert discard(env, record) == record
    assert env.coordinator.upload_recovery_plan()[0].record == record


@pytest.mark.parametrize(
    "kind",
    [
        "extra-file",
        "extra-directory",
        "file-symlink",
        "dangling-symlink",
        "hardlink",
        "directory-symlink",
        "root-symlink",
        "corrupt",
        "truncated",
    ],
)
def test_cleanup_preserves_unfamiliar_or_changed_storage(env, tmp_path, kind):
    record = finish(env)
    outside = tmp_path / "outside"
    outside.mkdir()
    protected = outside / "protected"
    protected.write_bytes(b"abcde")
    if kind.startswith("extra"):
        extra = env.directory / "keep"
        extra.mkdir() if kind.endswith("directory") else extra.write_bytes(b"keep")
    elif kind in {"file-symlink", "dangling-symlink", "hardlink"}:
        env.staged.unlink()
        if kind == "hardlink":
            os.link(protected, env.staged)
        else:
            env.staged.symlink_to(protected if kind == "file-symlink" else outside / "missing")
    elif kind == "directory-symlink":
        env.directory.rename(outside / "saved")
        env.directory.symlink_to(outside / "saved", target_is_directory=True)
    elif kind == "root-symlink":
        env.root.rename(outside / "saved")
        env.root.symlink_to(outside / "saved", target_is_directory=True)
    else:
        env.staged.write_bytes(b"wrong" if kind == "corrupt" else b"a")
    with pytest.raises(UploadError):
        discard(env, record)
    assert env.directory.exists()
    assert env.staged.exists() or env.staged.is_symlink()
    assert protected.read_bytes() == b"abcde"
    assert env.store.get("request") == record


@pytest.mark.parametrize("kind", ["bytes", "replacement", "directory", "extra"])
def test_cleanup_rechecks_identity_and_contents_after_hashing(env, monkeypatch, kind):
    record = finish(env)
    verify = env.sources.verify

    def changed(intent):
        verify(intent)
        if kind == "bytes":
            env.staged.write_bytes(b"wrong")
        elif kind == "replacement":
            env.staged.rename(env.root / "saved-source")
            env.staged.write_bytes(b"abcde")
        elif kind == "directory":
            env.directory.rename(env.root / "saved-directory")
            env.directory.mkdir()
            env.staged.write_bytes(b"abcde")
        else:
            (env.directory / "keep").write_bytes(b"keep")

    monkeypatch.setattr(env.sources, "verify", changed)
    with pytest.raises(UploadError):
        discard(env, record)
    assert env.staged.exists()
    assert env.store.get("request") == record


@pytest.mark.parametrize("operation", ["unlink", "rmdir"])
def test_partial_cleanup_failure_can_be_explicitly_retried(env, monkeypatch, operation):
    record = finish(env)
    original = getattr(Path, operation)

    def fail(path, *args, **kwargs):
        if path == (env.staged if operation == "unlink" else env.directory):
            raise OSError("private storage detail")
        return original(path, *args, **kwargs)

    with monkeypatch.context() as patcher:
        patcher.setattr(Path, operation, fail)
        with pytest.raises(UploadError) as caught:
            discard(env, record)
    assert "private storage detail" not in str(caught.value)
    assert caught.value.__suppress_context__
    assert env.directory.exists()
    assert env.staged.exists() == (operation == "unlink")
    assert discard(env, record) == record
    assert not env.directory.exists()


def test_caller_guard_runs_after_verification_and_can_prevent_removal(env, monkeypatch):
    calls = []
    verify = env.sources.verify

    def checked(intent):
        verify(intent)
        calls.append("verified")

    @contextmanager
    def reject():
        assert calls == ["verified"]
        raise StoreConflict("fixture changed owner")
        yield  # pragma: no cover

    monkeypatch.setattr(env.sources, "verify", checked)
    with pytest.raises(StoreConflict):
        env.sources.discard(env.intent, guard=reject)
    assert env.staged.read_bytes() == b"abcde"


def test_deactivation_during_verification_is_not_blocked_and_preserves_source(env, monkeypatch):
    record = finish(env)
    entered, release = threading.Event(), threading.Event()
    verify = env.sources.verify

    def pause(intent):
        entered.set()
        assert release.wait(5)
        return verify(intent)

    monkeypatch.setattr(env.sources, "verify", pause)
    with ThreadPoolExecutor(max_workers=1) as worker:
        task = worker.submit(discard, env, record)
        try:
            assert entered.wait(5)
            env.coordinator.deactivate()
        finally:
            release.set()
        with pytest.raises(UploadError, match="inactive"):
            task.result(5)
    assert env.staged.read_bytes() == b"abcde"


def test_changed_or_unreadable_record_before_removal_preserves_source(env, monkeypatch):
    record = finish(env)
    verify = env.sources.verify

    def changed(intent):
        verify(intent)
        monkeypatch.setattr(
            env.store, "get", lambda request: replace(record, revision=record.revision + 1)
        )

    monkeypatch.setattr(env.sources, "verify", changed)
    with pytest.raises(StoreConflict):
        discard(env, record)
    assert env.staged.exists()


@pytest.mark.parametrize("revision", [True, -1, 0, None])
def test_invalid_cleanup_revision_does_not_read_or_delete_source(env, monkeypatch, revision):
    finish(env)
    monkeypatch.setattr(
        env.sources, "discard", lambda *a, **kw: pytest.fail("Invalid cleanup reached files")
    )
    with pytest.raises(StoreConflict):
        env.coordinator.discard_upload_source("request", expected_revision=revision)


def test_prepared_upload_cannot_be_discarded_or_rebound_to_another_scope(env, monkeypatch):
    with pytest.raises(StoreConflict):
        discard(env, env.record)
    foreign = replace(env.scope, account_id="other-account")
    foreign_store = UploadStore(env.store._path, foreign)
    foreign_store.create(replace(env.intent, scope=foreign, request_id="foreign-request"))
    with pytest.raises(StoreConflict):
        env.coordinator.discard_upload_source("foreign-request", expected_revision=0)
    assert env.staged.exists()


def test_cleanup_uses_existing_worker_and_retains_same_record(env):
    record = finish(env)
    workers = JobWorkers(env.coordinator, workers=1)
    try:
        result = workers.discard_upload_source("request", expected_revision=record.revision).result(
            5
        )
        assert result == record
        assert not env.directory.exists()
    finally:
        workers.shutdown()


@pytest.mark.parametrize(
    "state",
    [
        value
        for value in UploadState
        if value not in {UploadState.CANCELED, UploadState.FAILED, UploadState.IMPORTED}
    ],
)
def test_every_nonterminal_upload_preserves_its_staged_source(env, state):
    from scenario.core.jobs.upload_transfers import UploadedPart

    current = env.record

    def transition(target, **kwargs):
        return env.store.transition(
            "request", expected_revision=current.revision, state=target, **kwargs
        )

    if state != UploadState.PREPARED:
        current = transition(UploadState.INITIALIZING)
        if state == UploadState.INITIALIZATION_UNCERTAIN:
            current = transition(state)
        elif state != UploadState.INITIALIZING:
            current = transition(UploadState.UPLOADING, upload_id="remote")
            if state == UploadState.PART_UNCERTAIN:
                current = env.store.claim_part("request", expected_revision=current.revision)
                current = transition(state)
            elif state in {UploadState.FINALIZING, UploadState.FINALIZATION_UNCERTAIN}:
                for number, digest in enumerate(current.intent.part_sha256, 1):
                    current = env.store.claim_part("request", expected_revision=current.revision)
                    current = env.store.record_part(
                        "request",
                        UploadedPart(number, current.intent.part_bytes(number), digest),
                        expected_revision=current.revision,
                    )
                current = transition(UploadState.FINALIZING)
                if state == UploadState.FINALIZATION_UNCERTAIN:
                    current = transition(state)
            elif state == UploadState.PROCESSING:
                current = transition(state)
    with pytest.raises(StoreConflict):
        discard(env, current)
    assert env.staged.read_bytes() == b"abcde"
    assert env.store.get("request") == current


def test_unreadable_store_during_final_guard_preserves_verified_source(env, monkeypatch):
    record = finish(env)
    verify = env.sources.verify

    def unreadable(request):
        raise StoreError("synthetic unavailable store")

    def checked(intent):
        verify(intent)
        monkeypatch.setattr(env.store, "get", unreadable)

    monkeypatch.setattr(env.sources, "verify", checked)
    with pytest.raises(StoreError):
        discard(env, record)
    assert env.staged.read_bytes() == b"abcde"


def test_cleanup_respects_current_verification_limits(env):
    bounded = UploadSources(env.root, max_bytes=4, part_bytes=3)
    with pytest.raises(TransferError):
        bounded.discard(env.intent)
    assert env.staged.read_bytes() == b"abcde"


@pytest.mark.skipif(os.name == "nt", reason="POSIX FIFO fixture")
def test_cleanup_rejects_fifo_without_opening_or_blocking(env):
    record = finish(env)
    env.staged.unlink()
    os.mkfifo(env.staged)
    with pytest.raises(UploadError):
        discard(env, record)
    assert env.staged.exists()


@pytest.mark.parametrize("component", ["service", "account_id", "project_id", "team_id"])
def test_cleanup_does_not_remove_another_scopes_same_request(env, component):
    record = finish(env)
    value = "https://other.example.invalid/v1" if component == "service" else "other"
    scope = replace(env.scope, **{component: value})
    foreign = env.sources.stage(
        env.source,
        request_id="request",
        scope=scope,
        origin=env.intent.origin,
        kind="image",
        content_type="image/png",
    )
    other_path = env.sources._directory(scope, "request") / "source.bin"
    assert discard(env, record) == record
    assert other_path.read_bytes() == b"abcde"
    env.sources.verify(foreign)


@pytest.mark.parametrize("after_unlink", [False, True])
def test_control_interruption_preserves_history_and_allows_explicit_cleanup_retry(
    env, monkeypatch, after_unlink
):
    record = finish(env)
    original = Path.unlink

    def interrupted(path, *args, **kwargs):
        if path == env.staged:
            if after_unlink:
                original(path, *args, **kwargs)
            raise KeyboardInterrupt("synthetic cleanup interruption")
        return original(path, *args, **kwargs)

    with monkeypatch.context() as patcher:
        patcher.setattr(Path, "unlink", interrupted)
        with pytest.raises(KeyboardInterrupt):
            discard(env, record)
    assert env.store.get("request") == record
    assert env.staged.exists() != after_unlink
    assert discard(env, record) == record
    assert not env.directory.exists()
