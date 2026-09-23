# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Installed transfer policy and atomic output behavior without network calls."""

import hashlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import bpy
from helpers import submodule


class ResultTransferTests(unittest.TestCase):
    def test_installed_transfer_publishes_verified_bytes_without_credentials(self):
        module = submodule("core.jobs.transfers")
        data = b"installed offline transfer fixture"
        response = io.BytesIO(data)
        response.status = 200
        response.getheader = lambda key, default=None: (
            str(len(data)) if key == "Content-Length" else default
        )
        connection = Mock()
        connection.getresponse.return_value = response
        policy = module.StoragePolicy(frozenset({"storage.example.invalid"}))
        client = module.ResultDownloader(policy, online_access=lambda: True)
        with tempfile.TemporaryDirectory(dir=bpy.utils.resource_path("USER")) as directory:
            root = Path(directory).resolve()
            with patch.object(module.http.client, "HTTPSConnection", return_value=connection):
                result = client.download(
                    "https://storage.example.invalid/file?signature=offline-fixture",
                    root=root,
                    name="result.bin",
                    expected_sha256=hashlib.sha256(data).hexdigest(),
                )
                self.assertEqual((root / result.name).read_bytes(), data)
                self.assertEqual(result.size, len(data))
                self.assertNotIn("signature", repr(result))
                with self.assertRaises(module.TransferError):
                    client.download(
                        "https://storage.example.invalid/file", root=root, name=result.name
                    )
                self.assertEqual(connection.request.call_count, 1)
                self.assertEqual(list(root.iterdir()), [root / result.name])
