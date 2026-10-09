# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""SDK-backed result commands never submit, guess identity or replay generation."""

import hashlib
import json
import sqlite3
import threading
from dataclasses import replace

import httpx
import pytest

from scenario.core.api.sdk_adapter import Credentials, SDKAdapter
from scenario.core.jobs.coordinator import JobCoordinator
from scenario.core.jobs.results import ResultError
from scenario.core.jobs.store import (
    JobIntent,
    JobOrigin,
    JobScope,
    JobState,
    JobStore,
    StoreConflict,
    StoreError,
)
from scenario.core.jobs.transfers import (
    DownloadedResult,
    ResultDownloader,
    StoragePolicy,
    TransferError,
)
from scenario.core.jobs.workers import JobWorkers

DATA = b"result bytes"


class OfflineDownloader(ResultDownloader):
    def __init__(self, store):
        super().__init__(
            StoragePolicy(frozenset({"storage.example.invalid"})), online_access=lambda: True
        )
        self.store = store
        self.calls = []
        self.fail_at = None
        self.after_download = None

    def download(self, url, *, root, name, expected_size, expected_sha256):
        self._policy.destination(url)
        active = [record for record in self.store.records() if record.state == JobState.DOWNLOADING]
        assert len(active) == 1 and active[0].results
        self.calls.append((url, root, name, threading.current_thread()))
        if len(self.calls) == self.fail_at:
            raise TransferError("synthetic private url?token=do-not-report")
        assert expected_size == len(DATA)
        path = root / name
        with path.open("xb") as target:
            target.write(DATA)
        if self.after_download:
            self.after_download()
        return DownloadedResult(name, len(DATA), hashlib.sha256(DATA).hexdigest())


@pytest.fixture
def setup(tmp_path):
    scope = JobScope("https://service.example.invalid/v1", "account", "project", "team")
    store = JobStore(tmp_path / "jobs.sqlite3", scope)
    intent = JobIntent(
        "request",
        scope,
        JobOrigin("file", "scene", "revision", "target"),
        "model",
        "model",
        "a" * 64,
        "b" * 64,
        "1.0",
    )
    current = store.create(intent)
    for state in (JobState.SUBMITTING, JobState.REMOTE, JobState.SUCCEEDED):
        current = store.transition(
            "request",
            expected_revision=current.revision,
            state=state,
            remote_job_id="remote" if state == JobState.REMOTE else None,
        )
    job = {
        "jobId": "remote",
        "status": "success",
        "metadata": {"assetIds": ["asset-one", "asset-two"]},
    }
    assets = {
        identifier: {
            "id": identifier,
            "status": "success",
            "mimeType": "image/png",
            "properties": {"size": len(DATA)},
            "url": f"https://storage.example.invalid/{identifier}?signed=initial",
        }
        for identifier in job["metadata"]["assetIds"]
    }
    calls = []

    def respond(request):
        calls.append(request)
        assert request.method == "GET", "Result recovery must never submit generation"
        assert request.url.params["projectId"] == "project"
        if request.url.path == "/v1/jobs/remote":
            return httpx.Response(200, json={"job": job})
        return httpx.Response(200, json={"asset": assets[request.url.path.rsplit("/", 1)[-1]]})

    downloader = OfflineDownloader(store)
    root = tmp_path / "results"
    root.mkdir()
    with SDKAdapter(
        Credentials("fixture-key", "fixture-secret"),
        online=lambda: True,
        base_url=scope.service,
        account_id=scope.account_id,
        team_id=scope.team_id,
        project_id=scope.project_id,
        transport=httpx.MockTransport(respond),
    ) as adapter:
        coordinator = JobCoordinator(adapter, store, result_root=root, result_downloader=downloader)
        yield coordinator, store, current, job, assets, downloader, calls, root


def test_manifest_download_and_reverification_keep_scope_origin_and_no_urls(setup, tmp_path):
    coordinator, store, current, _, _, downloader, calls, root = setup
    result = coordinator.download_results("request", expected_revision=current.revision)
    assert result.state == JobState.READY
    assert result.intent == current.intent
    assert len(result.results) == len(downloader.calls) == 2
    assert len(calls) == 5  # job + metadata pair + fresh URL pair
    verified = coordinator.verify_results("request", expected_revision=result.revision)
    assert verified.record == result
    assert all(path.read_bytes() == DATA and path.is_relative_to(root) for path in verified.paths)
    reopened = JobStore(tmp_path / "jobs.sqlite3", store.scope)
    assert reopened.get("request") == result
    assert b"signed=" not in (tmp_path / "jobs.sqlite3").read_bytes()
    assert "url" not in json.dumps(result.results[0].asset.__dict__)


def test_explicit_retry_reuses_verified_receipt_and_refreshes_failed_asset_url(setup):
    coordinator, store, current, _, assets, downloader, calls, _ = setup
    downloader.fail_at = 2
    with pytest.raises(ResultError) as error:
        coordinator.download_results("request", expected_revision=current.revision)
    assert "private" not in str(error.value) and "token" not in str(error.value)
    failed = store.get("request")
    assert failed.state == JobState.DOWNLOAD_FAILED
    assert failed.results[0].receipt and failed.results[1].receipt is None
    assets["asset-two"]["url"] = "https://storage.example.invalid/asset-two?signed=fresh"
    downloader.fail_at = None
    before = len(calls)
    ready = coordinator.download_results("request", expected_revision=failed.revision)
    assert ready.state == JobState.READY
    assert len(downloader.calls) == 3 and len(calls) == before + 1
    assert downloader.calls[-1][0].endswith("signed=fresh")
    assert ready.results[0].receipt == failed.results[0].receipt


def test_corrupt_receipted_file_does_not_trigger_redownload_or_generation(setup):
    coordinator, store, current, _, _, downloader, calls, _ = setup
    downloader.fail_at = 2
    with pytest.raises(ResultError):
        coordinator.download_results("request", expected_revision=current.revision)
    failed = store.get("request")
    _, directory, name, _ = downloader.calls[0]
    (directory / name).write_bytes(b"changed")
    before = len(calls)
    with pytest.raises(ResultError):
        coordinator.download_results("request", expected_revision=failed.revision)
    assert len(calls) == before and len(downloader.calls) == 2
    assert (directory / name).read_bytes() == b"changed"
    assert store.get("request").state == JobState.DOWNLOAD_FAILED


@pytest.mark.parametrize(
    "mutation",
    [
        "job-id",
        "job-state",
        "duplicate",
        "empty",
        "many",
        "bad-id",
        "asset-id",
        "asset-state",
        "size",
        "mime",
    ],
)
def test_inconsistent_remote_metadata_never_persists_a_partial_manifest(setup, mutation):
    coordinator, store, current, job, assets, downloader, _, _ = setup
    if mutation == "job-id":
        job["jobId"] = "another"
    elif mutation == "job-state":
        job["status"] = "in-progress"
    elif mutation == "duplicate":
        job["metadata"]["assetIds"] *= 2
    elif mutation == "empty":
        job["metadata"]["assetIds"] = []
    elif mutation == "many":
        job["metadata"]["assetIds"] = ["asset-one"] * 129
    elif mutation == "bad-id":
        job["metadata"]["assetIds"] = ["https://host/?secret"]
    elif mutation == "asset-id":
        assets["asset-two"]["id"] = "another"
    elif mutation == "asset-state":
        assets["asset-two"]["status"] = "pending"
    elif mutation == "size":
        assets["asset-two"]["properties"]["size"] = 10**300
    elif mutation == "mime":
        assets["asset-two"]["mimeType"] = "image/png; private"
    with pytest.raises(ResultError):
        coordinator.load_results("request", expected_revision=current.revision)
    assert store.get("request") == current
    assert not downloader.calls


def test_manifest_is_immutable_and_changed_provider_metadata_is_rejected(setup):
    coordinator, store, current, _, assets, downloader, calls, _ = setup
    manifest = coordinator.load_results("request", expected_revision=current.revision)
    count = len(calls)
    assert coordinator.load_results("request", expected_revision=manifest.revision) == manifest
    assert len(calls) == count
    assets["asset-one"]["properties"]["size"] += 1
    with pytest.raises(ResultError):
        coordinator.download_results("request", expected_revision=manifest.revision)
    assert store.get("request").results == manifest.results
    assert not downloader.calls


def test_failed_receipt_write_leaves_interrupted_download_for_review(setup, monkeypatch):
    coordinator, store, current, _, _, downloader, calls, _ = setup

    def fail(*args, **kwargs):
        raise StoreError("synthetic write failure")

    monkeypatch.setattr(store, "record_download", fail)
    with pytest.raises(StoreError):
        coordinator.download_results("request", expected_revision=current.revision)
    interrupted = store.get("request")
    assert interrupted.state == JobState.DOWNLOADING
    assert all(item.receipt is None for item in interrupted.results)
    assert len(downloader.calls) == 1
    count = len(calls)
    with pytest.raises(StoreConflict):
        coordinator.download_results("request", expected_revision=interrupted.revision)
    assert len(calls) == count


def test_deactivation_during_transfer_preserves_original_receipt_and_stops_next_asset(setup):
    coordinator, store, current, _, _, downloader, _, _ = setup
    downloader.after_download = coordinator.deactivate
    with pytest.raises(ResultError):
        coordinator.download_results("request", expected_revision=current.revision)
    record = store.get("request")
    assert record.state == JobState.DOWNLOAD_FAILED
    assert record.results[0].receipt and record.results[1].receipt is None
    assert record.intent.origin == current.intent.origin
    assert len(downloader.calls) == 1


def test_stale_or_inactive_commands_do_not_request_metadata(setup):
    coordinator, _, current, _, _, _, calls, _ = setup
    for revision in (-1, True, current.revision + 1):
        with pytest.raises(StoreConflict):
            coordinator.load_results("request", expected_revision=revision)
    coordinator.deactivate()
    with pytest.raises(ResultError):
        coordinator.load_results("request", expected_revision=current.revision)
    assert not calls


def test_shared_workers_deliver_verified_results_without_main_thread_callbacks(setup):
    coordinator, _, current, _, _, downloader, _, _ = setup
    workers = JobWorkers(coordinator, workers=1)
    try:
        task = workers.download_results("request", expected_revision=current.revision)
        ready = task.result(timeout=5)
        verified = workers.verify_results("request", expected_revision=ready.revision).result(
            timeout=5
        )
        assert verified.record == ready
        assert all(item[3] is not threading.current_thread() for item in downloader.calls)
    finally:
        workers.shutdown()
    assert workers.stopped


def test_verification_detects_stale_record_without_claiming_application(setup, monkeypatch):
    coordinator, store, current, _, _, downloader, _, _ = setup
    ready = coordinator.download_results("request", expected_revision=current.revision)
    verify = downloader.verify
    changed = False

    def change(root, receipt):
        nonlocal changed
        path = verify(root, receipt)
        if not changed:
            store.transition("request", expected_revision=ready.revision, state=JobState.APPLYING)
            changed = True
        return path

    monkeypatch.setattr(downloader, "verify", change)
    with pytest.raises(StoreConflict):
        coordinator.verify_results("request", expected_revision=ready.revision)
    assert store.get("request").state == JobState.APPLYING


@pytest.mark.parametrize("error_type", [OSError, ResultError])
def test_local_verification_errors_remain_sanitized_without_side_effects(
    setup, monkeypatch, error_type
):
    coordinator, store, current, _, _, downloader, calls, _ = setup
    ready = coordinator.download_results("request", expected_revision=current.revision)
    before = len(calls), len(downloader.calls)

    def fail(*args, **kwargs):
        raise error_type("private path or transfer detail")

    monkeypatch.setattr(downloader, "verify", fail)
    with pytest.raises(ResultError, match="^Saved result files could not be verified$") as error:
        coordinator.verify_results("request", expected_revision=ready.revision)
    assert error.value.__suppress_context__
    assert store.get("request") == ready
    assert (len(calls), len(downloader.calls)) == before


def test_two_requests_never_reuse_the_same_local_result_names(setup):
    coordinator, store, current, _, _, _, _, _ = setup
    first = coordinator.download_results("request", expected_revision=current.revision)
    first_paths = coordinator.verify_results("request", expected_revision=first.revision).paths
    from dataclasses import replace

    second = store.create(replace(current.intent, request_id="another-request"))
    for state in (JobState.SUBMITTING, JobState.REMOTE, JobState.SUCCEEDED):
        second = store.transition(
            "another-request",
            expected_revision=second.revision,
            state=state,
            remote_job_id="remote" if state == JobState.REMOTE else None,
        )
    # Use the same provider output with a different local request identity.
    second = coordinator.download_results("another-request", expected_revision=second.revision)
    second_paths = coordinator.verify_results(
        "another-request", expected_revision=second.revision
    ).paths
    assert set(first_paths).isdisjoint(second_paths)
    assert all(path.read_bytes() == DATA for path in first_paths + second_paths)


def test_manifest_persistence_failure_stops_before_storage_transfer(setup, monkeypatch):
    coordinator, store, current, _, _, downloader, _, _ = setup

    def fail(*args, **kwargs):
        raise StoreError("synthetic manifest commit failure")

    monkeypatch.setattr(store, "set_results", fail)
    with pytest.raises(StoreError):
        coordinator.download_results("request", expected_revision=current.revision)
    assert store.get("request") == current
    assert not downloader.calls


@pytest.mark.parametrize("kind", ["missing", "file", "symlink"])
def test_unavailable_result_root_reports_command_error_before_download_claim(setup, tmp_path, kind):
    coordinator, store, current, _, _, downloader, _, root = setup
    manifest = coordinator.load_results("request", expected_revision=current.revision)
    root.rmdir()
    if kind == "file":
        root.write_bytes(b"not a directory")
    elif kind == "symlink":
        other = tmp_path / "replacement"
        other.mkdir()
        root.symlink_to(other, target_is_directory=True)
    with pytest.raises(ResultError, match="prepare private result storage"):
        coordinator.download_results("request", expected_revision=manifest.revision)
    assert store.get("request") == manifest
    assert not downloader.calls


@pytest.mark.parametrize("identity_kind", ["job", "asset"])
def test_sdk_rejected_result_identity_is_sanitized_without_store_changes(setup, identity_kind):
    coordinator, store, current, job, _, downloader, calls, _ = setup
    if identity_kind == "job":
        current = store.create(replace(current.intent, request_id="invalid-remote"))
        for state in (JobState.SUBMITTING, JobState.REMOTE, JobState.SUCCEEDED):
            current = store.transition(
                current.intent.request_id,
                expected_revision=current.revision,
                state=state,
                remote_job_id="remote%private" if state == JobState.REMOTE else None,
            )
    else:
        job["metadata"]["assetIds"] = ["asset%private"]
    with pytest.raises(ResultError, match="metadata could not be retrieved") as error:
        coordinator.load_results(current.intent.request_id, expected_revision=current.revision)
    assert "private" not in str(error.value)
    assert error.value.__suppress_context__
    assert store.get(current.intent.request_id) == current
    assert len(calls) == (0 if identity_kind == "job" else 1)
    assert not downloader.calls


def interrupt_download(setup, monkeypatch, stage):
    coordinator, store, current, _, _, downloader, _, _ = setup
    download = downloader.download
    transition = store.transition

    def stop_transfer(*args, **kwargs):
        if stage == "empty" or (stage == "partial" and len(downloader.calls) == 1):
            raise SystemExit("synthetic process interruption")
        return download(*args, **kwargs)

    def stop_completion(*args, **kwargs):
        if stage == "complete" and kwargs.get("state") == JobState.READY:
            raise StoreError("synthetic final commit failure")
        return transition(*args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(downloader, "download", stop_transfer)
        patch.setattr(store, "transition", stop_completion)
        with pytest.raises((SystemExit, StoreError)):
            coordinator.download_results("request", expected_revision=current.revision)
    interrupted = store.get("request")
    assert interrupted.state == JobState.DOWNLOADING
    return interrupted


@pytest.mark.parametrize("stage", ["empty", "partial", "complete"])
def test_reopened_owner_recovers_offline_and_only_explicitly_retries_missing_downloads(
    setup, monkeypatch, tmp_path, stage
):
    coordinator, store, _, _, _, downloader, calls, root = setup
    interrupted = interrupt_download(setup, monkeypatch, stage)
    reopened = JobStore(tmp_path / "jobs.sqlite3", store.scope)
    recovered_owner = JobCoordinator(
        coordinator._adapter, reopened, result_root=root, result_downloader=downloader
    )
    before = len(calls), len(downloader.calls)
    recovered = recovered_owner.recover_downloads("request", expected_revision=interrupted.revision)
    assert (len(calls), len(downloader.calls)) == before
    assert recovered.intent == interrupted.intent
    assert recovered.results == interrupted.results
    assert recovered.remote_job_id == interrupted.remote_job_id
    assert recovered.revision == interrupted.revision + 1
    expected = JobState.READY if stage == "complete" else JobState.DOWNLOAD_FAILED
    assert recovered.state == expected
    if stage != "complete":
        ready = recovered_owner.download_results("request", expected_revision=recovered.revision)
        assert ready.state == JobState.READY
        missing = sum(item.receipt is None for item in interrupted.results)
        assert len(calls) == before[0] + missing
        assert len(downloader.calls) == before[1] + missing
    assert all(request.method == "GET" for request in calls)


@pytest.mark.parametrize("damage", ["missing", "changed", "symlink", "orphan", "orphan-symlink"])
def test_recovery_preserves_untrusted_files_and_record_without_network(setup, monkeypatch, damage):
    coordinator, store, _, _, _, downloader, calls, _ = setup
    interrupted = interrupt_download(setup, monkeypatch, "partial")
    directory = downloader.calls[0][1]
    item = interrupted.results[1 if damage.startswith("orphan") else 0]
    path = directory / item.asset.name
    if damage in {"missing", "symlink"}:
        path.unlink()
    if damage in {"changed", "orphan"}:
        path.write_bytes(b"untrusted bytes")
    if damage in {"symlink", "orphan-symlink"}:
        path.symlink_to(directory / "missing-target")
    before = len(calls), len(downloader.calls)
    with pytest.raises(ResultError, match="need review"):
        coordinator.recover_downloads("request", expected_revision=interrupted.revision)
    assert store.get("request") == interrupted
    assert (len(calls), len(downloader.calls)) == before
    if damage != "missing":
        assert path.is_symlink() or path.read_bytes() == b"untrusted bytes"


def test_live_transfer_excludes_recovery_and_another_download(setup):
    coordinator, store, current, _, _, downloader, _, root = setup
    competing = JobCoordinator(
        coordinator._adapter, store, result_root=root, result_downloader=downloader
    )
    checks = []

    def during_transfer():
        active = store.get("request")
        for command in (competing.recover_downloads, competing.download_results):
            with pytest.raises(StoreConflict, match="busy"):
                command("request", expected_revision=active.revision)
        checks.append(active.revision)

    downloader.after_download = during_transfer
    assert (
        coordinator.download_results("request", expected_revision=current.revision).state
        == JobState.READY
    )
    assert len(checks) == 2


def test_recovery_rejects_stale_foreign_and_inactive_contexts(setup, monkeypatch, tmp_path):
    coordinator, store, _, _, _, downloader, calls, root = setup
    interrupted = interrupt_download(setup, monkeypatch, "partial")
    count = len(calls)
    for request, revision in (
        ("request", -1),
        ("request", True),
        ("missing", interrupted.revision),
    ):
        with pytest.raises(StoreConflict):
            coordinator.recover_downloads(request, expected_revision=revision)
    foreign_store = JobStore(tmp_path / "jobs.sqlite3", replace(store.scope, account_id="other"))
    with SDKAdapter(
        Credentials("fixture-key", "fixture-secret"),
        online=lambda: False,
        base_url=store.scope.service,
        account_id="other",
        project_id="project",
        team_id="team",
    ) as adapter:
        foreign = JobCoordinator(
            adapter, foreign_store, result_root=root, result_downloader=downloader
        )
        with pytest.raises(StoreConflict):
            foreign.recover_downloads("request", expected_revision=interrupted.revision)
    coordinator.deactivate()
    with pytest.raises(ResultError):
        coordinator.recover_downloads("request", expected_revision=interrupted.revision)
    assert store.get("request") == interrupted and len(calls) == count


def test_recovery_commit_failure_preserves_interruption_and_can_be_explicitly_retried(
    setup, monkeypatch
):
    coordinator, store, _, _, _, _, calls, _ = setup
    interrupted = interrupt_download(setup, monkeypatch, "complete")
    count = len(calls)
    with monkeypatch.context() as patch:
        patch.setattr(
            store, "transition", lambda *args, **kwargs: (_ for _ in ()).throw(StoreError("disk"))
        )
        with pytest.raises(StoreError):
            coordinator.recover_downloads("request", expected_revision=interrupted.revision)
    assert store.get("request") == interrupted
    assert (
        coordinator.recover_downloads("request", expected_revision=interrupted.revision).state
        == JobState.READY
    )
    assert len(calls) == count


def test_recovery_worker_returns_saved_record_without_network_or_application(setup, monkeypatch):
    coordinator, store, _, _, _, _, calls, _ = setup
    interrupted = interrupt_download(setup, monkeypatch, "partial")
    count = len(calls)
    workers = JobWorkers(coordinator, workers=1)
    try:
        record = workers.recover_downloads(
            "request", expected_revision=interrupted.revision
        ).result(5)
        assert record.state == JobState.DOWNLOAD_FAILED
        assert record == store.get("request")
        assert len(calls) == count
    finally:
        workers.shutdown()


def test_recovery_deactivated_during_verification_never_commits_a_state_change(setup, monkeypatch):
    coordinator, store, _, _, _, downloader, calls, _ = setup
    interrupted = interrupt_download(setup, monkeypatch, "partial")
    verify = downloader.verify

    def retire(root, receipt):
        result = verify(root, receipt)
        coordinator.deactivate()
        return result

    monkeypatch.setattr(downloader, "verify", retire)
    count = len(calls)
    with pytest.raises(ResultError):
        coordinator.recover_downloads("request", expected_revision=interrupted.revision)
    assert store.get("request") == interrupted
    assert len(calls) == count


def test_recovery_sanitizes_verifier_errors_without_altering_files(setup, monkeypatch):
    coordinator, store, _, _, _, downloader, calls, _ = setup
    interrupted = interrupt_download(setup, monkeypatch, "partial")

    def fail(*args):
        raise ResultError("private-file-path")

    monkeypatch.setattr(downloader, "verify", fail)
    count = len(calls)
    with pytest.raises(ResultError, match="need review") as error:
        coordinator.recover_downloads("request", expected_revision=interrupted.revision)
    assert "private-file-path" not in str(error.value)
    assert error.value.__suppress_context__
    assert store.get("request") == interrupted
    assert len(calls) == count


@pytest.mark.parametrize("recover", [False, True])
def test_result_commands_accept_a_database_parent_alias(setup, monkeypatch, tmp_path, recover):
    coordinator, store, current, _, _, downloader, calls, root = setup
    if recover:
        current = interrupt_download(setup, monkeypatch, "complete")
    alias = tmp_path / "database-alias"
    alias.symlink_to(tmp_path, target_is_directory=True)
    aliased_store = JobStore(alias / "jobs.sqlite3", store.scope)
    owner = JobCoordinator(
        coordinator._adapter, aliased_store, result_root=root, result_downloader=downloader
    )
    before = len(calls)
    command = owner.recover_downloads if recover else owner.download_results
    ready = command("request", expected_revision=current.revision)
    assert ready.state == JobState.READY
    assert store.get("request") == ready
    if recover:
        assert len(calls) == before


def test_texture_roles_survive_sdk_download_and_reopen_without_raw_metadata(setup, tmp_path):
    coordinator, store, current, _, assets, _, calls, _ = setup
    assets["asset-one"]["metadata"] = {"type": "texture-albedo", "prompt": "private fixture prompt"}
    assets["asset-two"]["metadata"] = {"type": "texture-normal", "other": "private fixture data"}
    result = coordinator.download_results("request", expected_revision=current.revision)
    assert [item.asset.texture_role for item in result.results] == ["albedo", "normal"]
    assert all(item.asset.media_type == "image/png" for item in result.results)
    assert JobStore(tmp_path / "jobs.sqlite3", store.scope).get("request") == result
    assert all(request.method == "GET" for request in calls)
    assert b"private fixture" not in (tmp_path / "jobs.sqlite3").read_bytes()


def test_known_texture_role_change_blocks_download_before_storage_transfer(setup):
    coordinator, store, current, _, assets, downloader, _, _ = setup
    assets["asset-one"]["metadata"] = {"type": "texture-normal"}
    manifest = coordinator.load_results("request", expected_revision=current.revision)
    assets["asset-one"]["metadata"] = {"type": "texture-albedo"}
    with pytest.raises(ResultError):
        coordinator.download_results("request", expected_revision=manifest.revision)
    assert store.get("request").state == JobState.DOWNLOAD_FAILED
    assert store.get("request").results[0].asset.texture_role == "normal"
    assert downloader.calls == []


def test_unclassified_saved_results_download_without_acquiring_new_semantics(setup):
    coordinator, _, current, _, assets, _, _, _ = setup
    manifest = coordinator.load_results("request", expected_revision=current.revision)
    assets["asset-one"]["metadata"] = {"type": "texture-normal"}
    result = coordinator.download_results("request", expected_revision=manifest.revision)
    assert result.state == JobState.READY
    assert all(item.asset.texture_role is None for item in result.results)


@pytest.mark.parametrize("mime", ["model/mtl", "model/obj"])
def test_legacy_mesh_resume_corrects_only_local_size_and_keeps_prior_receipt(
    setup, monkeypatch, mime
):
    import io
    from unittest.mock import Mock

    from scenario.core.jobs import transfers

    coordinator, store, current, _, assets, _, calls, root = setup
    assets["asset-two"]["mimeType"] = mime
    assets["asset-two"]["properties"]["size"] = 1
    complete = False

    class Response(io.BytesIO):
        status = 200

        def getheader(self, key, default=None):
            if key == "Content-Length" and (complete or self.first):
                return str(len(DATA))
            return default

    count = 0

    def response():
        nonlocal count
        count += 1
        result = Response(DATA)
        result.first = count == 1
        return result

    connection = Mock()
    connection.getresponse.side_effect = response
    monkeypatch.setattr(transfers.http.client, "HTTPSConnection", Mock(return_value=connection))
    coordinator._results._downloader = ResultDownloader(
        StoragePolicy(frozenset({"storage.example.invalid"})), online_access=lambda: True
    )
    with pytest.raises(ResultError):
        coordinator.download_results("request", expected_revision=current.revision)
    failed = store.get("request")
    assert failed.state == JobState.DOWNLOAD_FAILED
    assert failed.results[0].receipt is not None and failed.results[1].receipt is None
    assert failed.results[1].asset.expected_size == 1
    complete = True
    # Even a separately corrected server size must not strand an older manifest.
    assets["asset-two"]["properties"]["size"] = 2
    ready = coordinator.download_results("request", expected_revision=failed.revision)
    assert ready.state == JobState.READY
    assert ready.results[0] == failed.results[0]
    assert ready.results[1].asset.expected_size == len(DATA)
    assert ready.results[1].receipt.size == len(DATA)
    assert ready.intent == failed.intent and count == 3
    assert all(call.method == "GET" for call in calls)
    assert assets["asset-two"]["properties"]["size"] == 2
    verified = coordinator.verify_results("request", expected_revision=ready.revision)
    assert all(path.read_bytes() == DATA for path in verified.paths)


class OriginalDownloader(ResultDownloader):
    """Record each destination and byte cap without contacting storage."""

    def __init__(self):
        super().__init__(
            StoragePolicy(frozenset({"storage.example.invalid"})), online_access=lambda: True
        )
        self.calls = []

    def download(self, url, *, root, name, expected_size, expected_sha256, max_bytes=None):
        self._policy.destination(url)
        self.calls.append((url, name, expected_size, max_bytes))
        with (root / name).open("xb") as target:
            target.write(DATA)
        return DownloadedResult(name, len(DATA), hashlib.sha256(DATA).hexdigest())


def hdri(assets, identifier="asset-one", *, original="image/aces"):
    """An HDRi skybox: JPEG preview as `url`, its EXR as the declared original."""
    assets[identifier].update(
        mimeType="image/jpeg",
        kind="image-hdr",
        metadata={"type": "skybox-hdri", "prompt": "private fixture prompt"},
        originalMimeType=original,
        originalFileUrl=f"https://storage.example.invalid/{identifier}-original?signed=private",
    )


@pytest.mark.parametrize("original", ["image/aces", "image/x-exr"])
def test_declared_exr_original_is_saved_instead_of_its_preview(setup, tmp_path, original):
    from scenario.core.jobs.results import MAX_ORIGINAL_BYTES

    coordinator, store, current, _, assets, _, calls, _ = setup
    hdri(assets, original=original)
    assets["asset-two"]["metadata"] = {"type": "skybox-base-360"}
    downloader = OriginalDownloader()
    coordinator._results._downloader = downloader
    result = coordinator.download_results("request", expected_revision=current.revision)
    assert result.state == JobState.READY
    first, second = (item.asset for item in result.results)
    assert (first.media_type, first.source, first.projection, first.expected_size) == (
        original,
        "original",
        "equirectangular",
        None,
    )
    assert first.name.endswith(".exr") and first.texture_role is None
    assert (second.media_type, second.source, second.projection) == (
        "image/png",
        "asset",
        "equirectangular",
    )
    assert downloader.calls[0][0] == assets["asset-one"]["originalFileUrl"]
    assert downloader.calls[0][2:] == (None, MAX_ORIGINAL_BYTES)
    assert downloader.calls[1][0] == assets["asset-two"]["url"]
    assert downloader.calls[1][2:] == (len(DATA), None)
    assert all(request.method == "GET" for request in calls)
    assert JobStore(tmp_path / "jobs.sqlite3", store.scope).get("request") == result
    saved = (tmp_path / "jobs.sqlite3").read_bytes()
    assert b"signed=" not in saved and b"private fixture" not in saved


@pytest.mark.parametrize(
    "mime,original",
    [
        ("image/jpeg", "image/vnd.radiance"),
        ("model/spz", "model/ply"),
        ("video/mp4", "video/quicktime"),
        ("model/gltf-binary", "image/x-exr"),
    ],
)
def test_other_originals_keep_the_asset_file_and_its_size(setup, mime, original):
    coordinator, _, current, _, assets, _, _, _ = setup
    assets["asset-one"].update(
        mimeType=mime,
        originalMimeType=original,
        originalFileUrl="https://storage.example.invalid/original",
    )
    downloader = OriginalDownloader()
    coordinator._results._downloader = downloader
    result = coordinator.download_results("request", expected_revision=current.revision)
    asset = result.results[0].asset
    assert (asset.media_type, asset.source, asset.expected_size) == (mime, "asset", len(DATA))
    assert downloader.calls[0][0] == assets["asset-one"]["url"]
    assert downloader.calls[0][3] is None


@pytest.mark.parametrize("url", ["missing", None, "", 7])
def test_declared_original_without_destination_never_saves_its_preview(setup, url):
    coordinator, store, current, _, assets, downloader, _, _ = setup
    hdri(assets)
    if url == "missing":
        del assets["asset-one"]["originalFileUrl"]
    else:
        assets["asset-one"]["originalFileUrl"] = url
    with pytest.raises(ResultError, match="destination"):
        coordinator.download_results("request", expected_revision=current.revision)
    assert store.get("request") == current
    assert downloader.calls == []


@pytest.mark.parametrize("change", ["withdrawn", "no-url", "radiance", "projection"])
def test_saved_original_fails_closed_when_scenario_changes_it(setup, change):
    coordinator, store, current, _, assets, _, _, _ = setup
    hdri(assets)
    downloader = OriginalDownloader()
    coordinator._results._downloader = downloader
    manifest = coordinator.load_results("request", expected_revision=current.revision)
    if change == "withdrawn":
        del assets["asset-one"]["originalMimeType"]
    elif change == "no-url":
        del assets["asset-one"]["originalFileUrl"]
    elif change == "radiance":
        assets["asset-one"]["originalMimeType"] = "image/vnd.radiance"
    else:
        assets["asset-one"]["metadata"] = {"type": "texture"}
    with pytest.raises(ResultError):
        coordinator.download_results("request", expected_revision=manifest.revision)
    failed = store.get("request")
    assert failed.state == JobState.DOWNLOAD_FAILED
    assert failed.results == manifest.results
    assert downloader.calls == []


def test_schema_nine_manifest_keeps_downloading_its_saved_preview(setup, tmp_path):
    coordinator, store, current, _, assets, _, _, _ = setup
    assets["asset-one"]["mimeType"] = "image/jpeg"
    manifest = coordinator.load_results("request", expected_revision=current.revision)
    path = tmp_path / "jobs.sqlite3"
    with sqlite3.connect(path) as connection:
        value = json.loads(connection.execute("SELECT record FROM jobs").fetchone()[0])
        for item in value["results"]:
            del item["asset"]["source"], item["asset"]["projection"]
        connection.execute("UPDATE jobs SET record=?", (json.dumps(value),))
        connection.execute("DROP TABLE trained_defaults")
        connection.execute("PRAGMA user_version=9")
    assert JobStore(path, store.scope).get("request") == manifest
    # Scenario now declares an HDR original and a 360 type for the saved preview.
    hdri(assets)
    downloader = OriginalDownloader()
    coordinator._results._downloader = downloader
    result = coordinator.download_results("request", expected_revision=manifest.revision)
    assert result.state == JobState.READY
    asset = result.results[0].asset
    assert (asset.media_type, asset.source, asset.projection) == ("image/jpeg", "asset", None)
    assert downloader.calls[0][0] == assets["asset-one"]["url"]
    assert downloader.calls[0][3] is None


def _mock_storage(monkeypatch, length=None):
    import io
    from unittest.mock import Mock

    from scenario.core.jobs import transfers

    class Response(io.BytesIO):
        status = 200

        def getheader(self, key, default=None):
            return str(length) if key == "Content-Length" and length is not None else default

    requested = []
    connection = Mock()
    connection.request.side_effect = lambda method, target, headers: requested.append(target)
    connection.getresponse.side_effect = lambda: Response(DATA)
    https = Mock(return_value=connection)
    monkeypatch.setattr(transfers.http.client, "HTTPSConnection", https)
    return https, requested


def test_original_transfer_uses_the_storage_policy_downloader(setup, monkeypatch):
    coordinator, store, current, _, assets, _, _, _ = setup
    hdri(assets)
    https, requested = _mock_storage(monkeypatch)
    coordinator._results._downloader = ResultDownloader(
        StoragePolicy(frozenset({"storage.example.invalid"})), online_access=lambda: True
    )
    result = coordinator.download_results("request", expected_revision=current.revision)
    assert result.state == JobState.READY
    assert requested == ["/asset-one-original?signed=private", "/asset-two?signed=initial"]
    assert {call.args[0] for call in https.call_args_list} == {"storage.example.invalid"}
    assert result.results[0].receipt.size == len(DATA)
    verified = coordinator.verify_results("request", expected_revision=result.revision)
    assert verified.paths[0].read_bytes() == DATA


@pytest.mark.parametrize("damage", ["host", "cap"])
def test_original_outside_policy_or_world_byte_cap_is_rejected(setup, monkeypatch, damage):
    from scenario.core.jobs.results import MAX_ORIGINAL_BYTES

    coordinator, store, current, _, assets, _, _, _ = setup
    hdri(assets)
    if damage == "host":
        assets["asset-one"]["originalFileUrl"] = "https://elsewhere.example.invalid/original"
    # Within the general 256 MiB storage policy, beyond the 128 MiB original cap.
    https, requested = _mock_storage(
        monkeypatch, MAX_ORIGINAL_BYTES + 1 if damage == "cap" else None
    )
    coordinator._results._downloader = ResultDownloader(
        StoragePolicy(frozenset({"storage.example.invalid"})), online_access=lambda: True
    )
    with pytest.raises(ResultError):
        coordinator.download_results("request", expected_revision=current.revision)
    failed = store.get("request")
    assert failed.state == JobState.DOWNLOAD_FAILED
    assert all(item.receipt is None for item in failed.results)
    assert https.called is (damage == "cap")
    assert requested == (["/asset-one-original?signed=private"] if damage == "cap" else [])
