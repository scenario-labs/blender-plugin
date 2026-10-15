# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Bounded result download retries, fresh signed URLs, resume and cancellation (#453)."""

import hashlib
import io
import threading
from unittest.mock import Mock

import httpx
import pytest

from scenario.core.api.sdk_adapter import Credentials, SDKAdapter
from scenario.core.jobs import results, transfers
from scenario.core.jobs.coordinator import JobCoordinator
from scenario.core.jobs.results import ResultError
from scenario.core.jobs.store import JobIntent, JobOrigin, JobScope, JobState, JobStore
from scenario.core.jobs.transfers import ResultDownloader, StoragePolicy

DATA = bytes(range(256)) * 64  # 16 KiB
ETAG = '"fixture-etag"'


class Response(io.BytesIO):
    def __init__(self, data=DATA, *, status=200, headers=None, fail_after=None, on_read=None):
        super().__init__(data)
        self.status = status
        self.headers = {"Content-Length": str(len(data))} if headers is None else headers
        self.fail_after = fail_after
        self.on_read = on_read

    def getheader(self, key, default=None):
        return self.headers.get(key, default)

    def read1(self, size=-1):
        if self.on_read is not None:
            self.on_read(self)
        if self.fail_after is not None and self.tell() >= self.fail_after:
            raise ConnectionResetError("private reset")
        limit = 1024 if self.fail_after is None else min(1024, self.fail_after - self.tell())
        return super().read1(min(size, limit))


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(results, "DOWNLOAD_RETRY_DELAYS", (0.0, 0.0))
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
    job = {"jobId": "remote", "status": "success", "metadata": {"assetIds": ["asset-one"]}}
    asset_reads = []

    def respond(request):
        assert request.method == "GET", "Result recovery must never submit generation"
        if request.url.path == "/v1/jobs/remote":
            return httpx.Response(200, json={"job": job})
        asset_reads.append(dict(request.url.params))
        # Each read signs a new storage URL, as the CDN does.
        url = f"https://storage.example.invalid/asset-one?signed=read-{len(asset_reads)}"
        return httpx.Response(
            200,
            json={
                "asset": {
                    "id": "asset-one",
                    "status": "success",
                    "mimeType": "image/png",
                    "properties": {"size": len(DATA)},
                    "url": url,
                }
            },
        )

    served, requests = [], []

    def connect(*args, **kwargs):
        connection = Mock()

        def request(method, target, headers):
            requests.append((target, dict(headers)))
            if not served:
                pytest.fail("Unexpected storage request")
            connection.getresponse.return_value = served.pop(0)

        connection.request.side_effect = request
        return connection

    monkeypatch.setattr(transfers.http.client, "HTTPSConnection", connect)
    downloader = ResultDownloader(
        StoragePolicy(frozenset({"storage.example.invalid"})), online_access=lambda: True
    )
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
        coordinator.load_results("request", expected_revision=current.revision)
        manifest = store.get("request")
        yield coordinator, store, manifest, served, requests, asset_reads, root


def files(root):
    return sorted(path.name for path in root.rglob("*") if path.is_file())


def test_failed_attempts_retry_with_a_fresh_signed_url_each_time(env):
    coordinator, store, manifest, served, requests, asset_reads, root = env
    served += [Response(status=403), Response(status=503), Response()]
    before = len(asset_reads)
    ready = coordinator.download_results("request", expected_revision=manifest.revision)
    assert ready.state == JobState.READY
    assert ready.results[0].receipt.sha256 == hashlib.sha256(DATA).hexdigest()
    # One SDK asset read per attempt; every attempt used its own signed URL.
    assert len(asset_reads) - before == 3
    assert all(params["originalAssets"] == "true" for params in asset_reads[before:])
    assert [target for target, _ in requests] == [
        f"/asset-one?signed=read-{before + n}" for n in (1, 2, 3)
    ]


def test_retries_are_bounded_and_end_in_a_resumable_failure(env):
    coordinator, store, manifest, served, requests, asset_reads, root = env
    served += [Response(status=500) for _ in range(results.DOWNLOAD_ATTEMPTS)]
    with pytest.raises(ResultError) as caught:
        coordinator.download_results("request", expected_revision=manifest.revision)
    assert "signed" not in str(caught.value)
    failed = store.get("request")
    assert failed.state == JobState.DOWNLOAD_FAILED
    assert failed.results[0].receipt is None
    assert len(requests) == results.DOWNLOAD_ATTEMPTS == 3
    assert not files(root)
    # The explicit Resume still works afterwards.
    served.append(Response())
    ready = coordinator.download_results("request", expected_revision=failed.revision)
    assert ready.state == JobState.READY


def test_non_retryable_failure_makes_one_attempt(env):
    coordinator, store, manifest, served, requests, _, root = env
    served += [Response(headers={"Content-Length": str(len(DATA)), "Content-Encoding": "gzip"})]
    with pytest.raises(ResultError):
        coordinator.download_results("request", expected_revision=manifest.revision)
    assert len(requests) == 1
    assert store.get("request").state == JobState.DOWNLOAD_FAILED
    assert not files(root)


def test_retry_resumes_with_range_when_the_etag_is_strong(env):
    coordinator, store, manifest, served, requests, _, root = env
    served += [
        Response(fail_after=6000, headers={"Content-Length": str(len(DATA)), "ETag": ETAG}),
        Response(
            DATA[6000:],
            status=206,
            headers={
                "Content-Length": str(len(DATA) - 6000),
                "Content-Range": f"bytes 6000-{len(DATA) - 1}/{len(DATA)}",
                "ETag": ETAG,
            },
        ),
    ]
    ready = coordinator.download_results("request", expected_revision=manifest.revision)
    assert ready.state == JobState.READY
    assert "Range" not in requests[0][1]
    assert requests[1][1]["Range"] == "bytes=6000-" and requests[1][1]["If-Range"] == ETAG
    verified = coordinator.verify_results("request", expected_revision=ready.revision)
    assert verified.paths[0].read_bytes() == DATA
    assert files(root) == [ready.results[0].asset.name]


def test_retry_without_a_strong_etag_starts_again_from_zero(env):
    coordinator, store, manifest, served, requests, _, root = env
    served += [
        Response(fail_after=6000, headers={"Content-Length": str(len(DATA)), "ETag": 'W/"weak"'}),
        Response(),
    ]
    ready = coordinator.download_results("request", expected_revision=manifest.revision)
    assert ready.state == JobState.READY
    assert "Range" not in requests[1][1] and "If-Range" not in requests[1][1]
    assert files(root) == [ready.results[0].asset.name]


def test_cancellation_mid_download_stops_without_a_receipt_or_partial_file(env):
    coordinator, store, manifest, served, requests, _, root = env
    cancel = threading.Event()

    def cancel_midway(response):
        if response.tell() >= 4096:
            cancel.set()

    served += [
        Response(headers={"Content-Length": str(len(DATA)), "ETag": ETAG}, on_read=cancel_midway)
    ]
    with pytest.raises(ResultError, match="canceled"):
        coordinator.download_results("request", expected_revision=manifest.revision, cancel=cancel)
    failed = store.get("request")
    assert failed.state == JobState.DOWNLOAD_FAILED
    assert failed.results[0].receipt is None
    # A canceled transfer is never retried and leaves no private staging behind.
    assert len(requests) == 1
    assert not files(root)
    assert not [path for path in root.rglob(".scenario-download-*")]


def test_cancellation_during_the_retry_wait_stops_before_another_request(env, monkeypatch):
    coordinator, store, manifest, served, requests, asset_reads, root = env
    monkeypatch.setattr(results, "DOWNLOAD_RETRY_DELAYS", (5.0, 5.0))
    cancel = threading.Event()

    class Unavailable(Response):
        """A 503 reply observed just as the user cancels."""

        @property
        def status(self):
            cancel.set()
            return 503

        @status.setter
        def status(self, value):
            pass

    served += [Unavailable(), Response()]
    reads = len(asset_reads)
    with pytest.raises(ResultError, match="canceled"):
        coordinator.download_results("request", expected_revision=manifest.revision, cancel=cancel)
    assert len(requests) == 1 and len(asset_reads) == reads + 1
    assert store.get("request").state == JobState.DOWNLOAD_FAILED
    assert not files(root)


def test_a_failed_url_refresh_uses_one_attempt_and_keeps_the_staged_bytes(env, monkeypatch):
    coordinator, store, manifest, served, requests, asset_reads, root = env
    adapter = coordinator._adapter
    real = adapter.asset
    calls = []

    def flaky(identifier, **options):
        calls.append(identifier)
        if len(calls) == 2:
            raise results.AdapterError("private transient refresh failure")
        return real(identifier, **options)

    monkeypatch.setattr(adapter, "asset", flaky)
    served += [
        Response(fail_after=6000, headers={"Content-Length": str(len(DATA)), "ETag": ETAG}),
        Response(
            DATA[6000:],
            status=206,
            headers={
                "Content-Length": str(len(DATA) - 6000),
                "Content-Range": f"bytes 6000-{len(DATA) - 1}/{len(DATA)}",
                "ETag": ETAG,
            },
        ),
    ]
    ready = coordinator.download_results("request", expected_revision=manifest.revision)
    assert ready.state == JobState.READY
    # Attempt 1 failed in storage, attempt 2 in the SDK read, attempt 3 resumed.
    assert len(calls) == 3 and len(requests) == 2
    assert requests[1][1]["Range"] == "bytes=6000-"


def test_url_refresh_failures_are_bounded_too(env, monkeypatch):
    coordinator, store, manifest, served, requests, _, root = env

    def failing(identifier, **options):
        raise results.AdapterError("private refresh failure")

    monkeypatch.setattr(coordinator._adapter, "asset", failing)
    with pytest.raises(ResultError, match="did not complete"):
        coordinator.download_results("request", expected_revision=manifest.revision)
    assert requests == [] and store.get("request").state == JobState.DOWNLOAD_FAILED


def test_a_real_failure_seen_while_canceling_is_not_reported_as_cancellation(env):
    coordinator, store, manifest, served, requests, _, root = env
    cancel = threading.Event()

    class Encoded(Response):
        """A refused encoding, observed just as the user stops the download."""

        def getheader(self, key, default=None):
            if key == "Content-Encoding":
                cancel.set()
                return "gzip"
            return super().getheader(key, default)

    served += [Encoded()]
    with pytest.raises(ResultError, match="did not complete"):
        coordinator.download_results("request", expected_revision=manifest.revision, cancel=cancel)
    assert len(requests) == 1
    assert store.get("request").state == JobState.DOWNLOAD_FAILED
