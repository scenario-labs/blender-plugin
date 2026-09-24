# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Bundled TLS trust and signed PUT framing, with storage connections mocked."""

import hashlib
import ssl
import unittest
from unittest.mock import Mock, patch

from helpers import submodule


class UploadTransferTests(unittest.TestCase):
    def test_installed_part_transport_retains_identity_and_never_retries(self):
        module = submodule("core.jobs.upload_transfers")
        transfers = submodule("core.jobs.transfers")
        data = b"offline upload part"
        digest = hashlib.sha256(data).hexdigest()
        connection = Mock()
        connection.getresponse.return_value.status = 200
        uploader = module.PartUploader(
            transfers.StoragePolicy(frozenset({"storage.example.invalid"})),
            online_access=lambda: True,
        )
        with patch.object(
            module.http.client, "HTTPSConnection", return_value=connection
        ) as factory:
            result = uploader.upload(
                "https://storage.example.invalid/part?signature=fixture",
                data,
                number=1,
                content_type="image/png",
                expected_sha256=digest,
            )
            self.assertEqual(result, module.UploadedPart(1, len(data), digest))
            self.assertEqual(factory.call_count, 1)
            context = factory.call_args.kwargs["context"]
            self.assertTrue(context.check_hostname)
            self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
            connection.send.assert_called_once_with(data)
            connection.reset_mock()
            connection.getresponse.side_effect = OSError("private-signature")
            with self.assertRaises(module.UploadUncertain) as error:
                uploader.upload(
                    "https://storage.example.invalid/part?signature=fixture",
                    data,
                    number=1,
                    content_type="image/png",
                    expected_sha256=digest,
                )
            self.assertNotIn("private-signature", str(error.exception))
            self.assertEqual(connection.endheaders.call_count, 1)
            self.assertEqual(factory.call_count, 2)
