# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Installed SDK, result persistence and worker delivery with offline fixtures."""

import hashlib
import tempfile
import threading
import unittest
from pathlib import Path

import bpy
from helpers import submodule


class ResultCommandTests(unittest.TestCase):
    def test_installed_worker_downloads_and_verifies_the_original_scoped_result(self):
        import httpx

        api = submodule("core.api.sdk_adapter")
        storage = submodule("core.jobs.store")
        commands = submodule("core.jobs.coordinator")
        transfers = submodule("core.jobs.transfers")
        workers_module = submodule("core.jobs.workers")
        body = b"offline native result"
        scope = storage.JobScope("https://service.example.invalid/v1", "account", "project")
        calls = []
        threads = []

        def respond(request):
            calls.append(request)
            self.assertEqual(request.method, "GET")
            self.assertEqual(request.url.params["projectId"], "project")
            if request.url.path == "/v1/jobs/remote":
                return httpx.Response(
                    200,
                    json={
                        "job": {
                            "jobId": "remote",
                            "status": "success",
                            "metadata": {"assetIds": ["asset"]},
                        }
                    },
                )
            return httpx.Response(
                200,
                json={
                    "asset": {
                        "id": "asset",
                        "status": "success",
                        "mimeType": "image/png",
                        "properties": {"size": len(body)},
                        "url": "https://storage.example.invalid/file?signed=fixture",
                    }
                },
            )

        class OfflineDownloader(transfers.ResultDownloader):
            def download(self, url, *, root, name, **kwargs):
                threads.append(threading.current_thread())
                with (root / name).open("xb") as target:
                    target.write(body)
                return transfers.DownloadedResult(name, len(body), hashlib.sha256(body).hexdigest())

        with tempfile.TemporaryDirectory(dir=bpy.utils.resource_path("USER")) as directory:
            root = Path(directory).resolve()
            store = storage.JobStore(root / "jobs.sqlite3", scope)
            record = store.create(
                storage.JobIntent(
                    "request",
                    scope,
                    storage.JobOrigin("file", "scene", "revision", "target"),
                    "model",
                    "model",
                    "a" * 64,
                    "b" * 64,
                    "1.0",
                )
            )
            for state in (
                storage.JobState.SUBMITTING,
                storage.JobState.REMOTE,
                storage.JobState.SUCCEEDED,
            ):
                record = store.transition(
                    "request",
                    expected_revision=record.revision,
                    state=state,
                    remote_job_id="remote" if state == storage.JobState.REMOTE else None,
                )
            with api.SDKAdapter(
                api.Credentials("fixture-key", "fixture-secret"),
                online=lambda: True,
                account_id=scope.account_id,
                project_id=scope.project_id,
                base_url=scope.service,
                transport=httpx.MockTransport(respond),
            ) as adapter:
                downloader = OfflineDownloader(
                    transfers.StoragePolicy(frozenset({"storage.example.invalid"})),
                    online_access=lambda: True,
                )
                coordinator = commands.JobCoordinator(
                    adapter, store, result_downloader=downloader, result_root=root
                )
                workers = workers_module.JobWorkers(coordinator, workers=1)
                try:
                    ready = workers.download_results(
                        "request", expected_revision=record.revision
                    ).result(timeout=10)
                    verified = workers.verify_results(
                        "request", expected_revision=ready.revision
                    ).result(timeout=10)
                    self.assertEqual(ready.state, storage.JobState.READY)
                    self.assertEqual(verified.record.intent, record.intent)
                    self.assertEqual(verified.paths[0].read_bytes(), body)
                    self.assertEqual(len(calls), 3)
                    self.assertIsNot(threads[0], threading.current_thread())
                finally:
                    workers.shutdown()
