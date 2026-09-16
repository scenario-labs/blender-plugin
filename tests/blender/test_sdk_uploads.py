# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Installed SDK upload metadata requests; no local-file or network transfer."""

import json
import unittest

from helpers import submodule


class SDKUploadTests(unittest.TestCase):
    def test_installed_upload_commands_keep_scope_and_processing_state(self):
        import httpx

        api = submodule("core.api.sdk_adapter")
        requests = []

        def respond(request):
            requests.append(request)
            return httpx.Response(
                200,
                json={"upload": {"id": "fixture-upload", "status": "validating", "future": True}},
            )

        with api.SDKAdapter(
            api.Credentials("fixture-key", "fixture-secret"),
            online=lambda: True,
            project_id="fixture-project",
            base_url="https://fixture.invalid/v1",
            transport=httpx.MockTransport(respond),
        ) as adapter:
            created = adapter.create_upload(
                kind="image",
                file_name="reference.png",
                content_type="image/png",
                file_size=128,
                parts=1,
            )
            read = adapter.upload(created["id"])
            completed = adapter.complete_upload(created["id"])
            self.assertEqual(created, read)
            self.assertEqual(read, completed)
            self.assertEqual(completed["status"], "validating")
            self.assertEqual([request.method for request in requests], ["POST", "GET", "POST"])
            self.assertTrue(
                all(
                    dict(request.url.params) == {"projectId": "fixture-project"}
                    for request in requests
                )
            )
            self.assertEqual(json.loads(requests[-1].content), {"action": "complete"})
