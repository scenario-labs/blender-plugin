# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Installed SQLite upload claims survive reopen without releasing interrupted work."""

import hashlib
import tempfile
import unittest
from pathlib import Path

from helpers import submodule


class UploadStoreTests(unittest.TestCase):
    def test_installed_store_preserves_interrupted_part(self):
        module = submodule("core.jobs.upload_store")
        jobs = submodule("core.jobs.store")
        transfers = submodule("core.jobs.upload_transfers")
        scope = jobs.JobScope("https://service.example.invalid/v1", "account", None, None)
        origin = jobs.JobOrigin("file", "scene", "revision", "target")
        digest = hashlib.sha256(b"data").hexdigest()
        intent = module.UploadIntent(
            "upload-one",
            scope,
            origin,
            "image",
            "fixture.png",
            "image/png",
            4,
            digest,
            4,
            (digest,),
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "uploads.sqlite3"
            store = module.UploadStore(path, scope)
            record = store.create(intent)
            record = store.transition(
                intent.request_id,
                expected_revision=record.revision,
                state=module.UploadState.INITIALIZING,
            )
            record = store.transition(
                intent.request_id,
                expected_revision=record.revision,
                state=module.UploadState.UPLOADING,
                upload_id="remote-one",
            )
            record = store.claim_part(intent.request_id, expected_revision=record.revision)
            reopened = module.UploadStore(path, scope)
            self.assertEqual(reopened.get(intent.request_id), record)
            with self.assertRaises(jobs.StoreConflict):
                reopened.claim_part(intent.request_id, expected_revision=record.revision)
            record = reopened.record_part(
                intent.request_id,
                transfers.UploadedPart(1, 4, digest),
                expected_revision=record.revision,
            )
            record = reopened.transition(
                intent.request_id,
                expected_revision=record.revision,
                state=module.UploadState.FINALIZING,
            )
            self.assertEqual(module.UploadStore(path, scope).get(intent.request_id), record)
