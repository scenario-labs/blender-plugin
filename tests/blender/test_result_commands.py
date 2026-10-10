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

    def test_installed_worker_saves_a_declared_exr_original_through_the_storage_policy(self):
        import io
        from unittest.mock import Mock, patch

        import httpx

        api = submodule("core.api.sdk_adapter")
        storage = submodule("core.jobs.store")
        commands = submodule("core.jobs.coordinator")
        results = submodule("core.jobs.results")
        transfers = submodule("core.jobs.transfers")
        workers_module = submodule("core.jobs.workers")
        body = b"offline native EXR original"
        scope = storage.JobScope("https://service.example.invalid/v1", "account", "project")
        originals = {
            "allowed": "https://storage.example.invalid/hdr?signed=fixture",
            "elsewhere": "https://elsewhere.example.invalid/hdr?signed=fixture",
            "unbounded": "https://storage.example.invalid/unbounded?signed=fixture",
        }

        def respond(request):
            self.assertEqual(request.method, "GET")
            name = request.url.path.rsplit("/", 1)[-1]
            if request.url.path.startswith("/v1/jobs/"):
                return httpx.Response(
                    200,
                    json={
                        "job": {
                            "jobId": name,
                            "status": "success",
                            "metadata": {"assetIds": [f"hdri-{name}"]},
                        }
                    },
                )
            return httpx.Response(
                200,
                json={
                    "asset": {
                        "id": name,
                        "status": "success",
                        "kind": "image-hdr",
                        "mimeType": "image/jpeg",
                        "metadata": {"type": "skybox-hdri"},
                        "properties": {"size": 3},
                        "url": "https://storage.example.invalid/preview?signed=fixture",
                        "originalMimeType": "image/aces",
                        "originalFileUrl": originals[name.removeprefix("hdri-")],
                    }
                },
            )

        requested = []
        connection = Mock()
        connection.request.side_effect = lambda _method, target, **_kwargs: requested.append(target)

        def response():
            # An original has no size metadata: only a declared length bounds its body.
            length = None if requested[-1].startswith("/unbounded") else str(len(body))
            stream = io.BytesIO(body)
            stream.status = 200
            stream.getheader = lambda key, default=None: (
                length if key == "Content-Length" and length is not None else default
            )
            return stream

        connection.getresponse.side_effect = response
        with tempfile.TemporaryDirectory(dir=bpy.utils.resource_path("USER")) as directory:
            root = Path(directory).resolve()
            store = storage.JobStore(root / "jobs.sqlite3", scope)
            records = {}
            for name in originals:
                record = store.create(
                    storage.JobIntent(
                        name,
                        scope,
                        storage.JobOrigin("file", "scene", "revision"),
                        "model",
                        "model_hdri-fixture",
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
                        name,
                        expected_revision=record.revision,
                        state=state,
                        remote_job_id=name if state == storage.JobState.REMOTE else None,
                    )
                records[name] = record
            with (
                api.SDKAdapter(
                    api.Credentials("fixture-key", "fixture-secret"),
                    online=lambda: True,
                    account_id=scope.account_id,
                    project_id=scope.project_id,
                    base_url=scope.service,
                    transport=httpx.MockTransport(respond),
                ) as adapter,
                patch.object(
                    transfers.http.client, "HTTPSConnection", return_value=connection
                ) as https,
            ):
                coordinator = commands.JobCoordinator(
                    adapter,
                    store,
                    result_downloader=transfers.ResultDownloader(
                        transfers.StoragePolicy(frozenset({"storage.example.invalid"})),
                        online_access=lambda: True,
                    ),
                    result_root=root,
                )
                workers = workers_module.JobWorkers(coordinator, workers=1)
                try:
                    ready = workers.download_results(
                        "allowed", expected_revision=records["allowed"].revision
                    ).result(timeout=10)
                    for name in ("elsewhere", "unbounded"):
                        with self.assertRaises(results.ResultError):
                            workers.download_results(
                                name, expected_revision=records[name].revision
                            ).result(timeout=10)
                finally:
                    workers.shutdown()
            asset = ready.results[0].asset
            self.assertEqual(ready.state, storage.JobState.READY)
            self.assertEqual(
                (asset.media_type, asset.source, asset.projection, asset.expected_size),
                ("image/aces", "original", "equirectangular", None),
            )
            self.assertTrue(asset.name.endswith(".exr"))
            self.assertEqual(ready.results[0].receipt.sha256, hashlib.sha256(body).hexdigest())
            self.assertEqual(requested, ["/hdr?signed=fixture", "/unbounded?signed=fixture"])
            self.assertEqual(
                [call.args[0] for call in https.call_args_list], ["storage.example.invalid"] * 2
            )
            for name in ("elsewhere", "unbounded"):
                rejected = store.get(name)
                self.assertEqual(rejected.state, storage.JobState.DOWNLOAD_FAILED)
                self.assertIsNone(rejected.results[0].receipt)
            self.assertEqual(len(list(root.rglob("*.exr"))), 1)
            self.assertEqual(storage.JobStore(root / "jobs.sqlite3", scope).get("allowed"), ready)
            self.assertNotIn(b"signed=", (root / "jobs.sqlite3").read_bytes())
