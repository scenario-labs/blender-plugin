# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Bundled SDK, SQLite, staging and shared workers in an offline upload lifecycle."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from helpers import submodule


class UploadCommandTests(unittest.TestCase):
    def test_installed_workers_keep_uploads_scoped_and_completion_explicit(self):
        sdk = submodule("core.api.sdk_adapter")
        jobs = submodule("core.jobs.store")
        uploads = submodule("core.jobs.upload_store")
        sources = submodule("core.jobs.upload_sources")
        transfer = submodule("core.jobs.upload_transfers")
        policy = submodule("core.jobs.transfers")
        coordinator = submodule("core.jobs.coordinator")
        workers = submodule("core.jobs.workers")
        import httpx

        scope = jobs.JobScope("https://service.example.invalid/v1", "account", "project")
        origin = jobs.JobOrigin("file", "scene", "revision", "object")
        requests = []
        remote = {
            "id": "upload-one",
            "status": "pending",
            "source": "multipart",
            "kind": "image",
            "fileName": "reference.png",
            "contentType": "image/png",
            "fileSize": 4,
            "partsCount": 1,
            "parts": [
                {
                    "number": 1,
                    "expires": "2099-01-01T00:00:00Z",
                    "url": "https://storage.example.invalid/part?signature=fixture",
                }
            ],
        }

        def handler(request):
            requests.append(request)
            result = dict(remote)
            if request.url.path.endswith("/action"):
                result.update(status="imported", entityId="asset-one")
            return httpx.Response(200, json={"upload": result})

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            source = root / "reference.png"
            source.write_bytes(b"data")
            staging = root / "sources"
            staging.mkdir()
            adapter = sdk.SDKAdapter(
                credentials=sdk.Credentials("fixture", "fixture-secret"),
                base_url=scope.service,
                account_id=scope.account_id,
                project_id=scope.project_id,
                online=lambda: True,
                transport=httpx.MockTransport(handler),
            )
            store = uploads.UploadStore(root / "uploads.sqlite3", scope)
            uploader = transfer.PartUploader(
                policy.StoragePolicy(frozenset({"storage.example.invalid"})),
                online_access=lambda: True,
            )

            def put(url, data, *, number, content_type, expected_sha256):
                self.assertEqual(store.records()[0].active_part, 1)
                self.assertEqual(data, b"data")
                return transfer.UploadedPart(number, len(data), expected_sha256)

            uploader.upload = Mock(side_effect=put)
            owner = workers.JobWorkers(
                coordinator.JobCoordinator(
                    adapter,
                    jobs.JobStore(root / "jobs.sqlite3", scope),
                    upload_store=store,
                    upload_sources=sources.UploadSources(staging),
                    part_uploader=uploader,
                ),
                workers=1,
            )
            try:
                record = owner.prepare_upload(
                    source, origin=origin, kind="image", content_type="image/png"
                ).result(5)
                source.write_bytes(b"changed original")
                for method in ("initialize_upload", "transfer_upload_part", "finalize_upload"):
                    record = getattr(owner, method)(
                        record.intent.request_id, expected_revision=record.revision
                    ).result(5)
                self.assertEqual(record.state, uploads.UploadState.IMPORTED)
                self.assertEqual(record.asset_id, "asset-one")
                self.assertEqual([r.method for r in requests], ["POST", "GET", "POST"])
                self.assertTrue(all(r.url.params["projectId"] == "project" for r in requests))
            finally:
                owner.shutdown()
            self.assertTrue(owner.stopped)
