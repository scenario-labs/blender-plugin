# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""SDK-backed result commands never submit, guess identity or replay generation."""

import hashlib
import json
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
