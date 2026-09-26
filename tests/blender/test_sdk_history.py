# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Installed SDK history integration with synthetic network responses."""

import threading
import unittest
from unittest.mock import patch

import httpx
from helpers import isolated_manager, online_access, reset_scene, submodule, temp_credentials


def job(identifier="job-fixture", prompt="asset_prompt"):
    return {
        "jobId": identifier,
        "jobType": "custom",
        "status": "success",
        "metadata": {"input": {"modelId": "fixture-model", "prompt": prompt}},
    }


class SDKHistoryTests(unittest.TestCase):
    def setUp(self):
        reset_scene()
        self.runtime = submodule("blender.runtime")
        self.history = submodule("blender.history")
        self.generation = submodule("blender.generation")
        self.handlers = submodule("blender.handlers")
        self.tools = submodule("mcp.tools_scenario")
        self.enterContext(patch.object(self.runtime, "state", self.runtime.RuntimeState()))
        self.prefs = self.enterContext(temp_credentials())
        self.enterContext(online_access(True))
        self.manager = self.enterContext(isolated_manager())
        self.addCleanup(self.runtime.state.reset)
        self.calls = []
        self.page = {"jobs": [job()], "nextPaginationToken": "page-two"}
        self.status = 200
        self.preview = "resolved prompt"
        adapter = submodule("core.api.sdk_adapter")

        def respond(request):
            self.assertIsNot(threading.current_thread(), threading.main_thread())
            self.calls.append(request)
            if request.url.path == "/v1/jobs":
                self.assertEqual(request.url.params["hideResults"], "false")
                return httpx.Response(self.status, json=self.page)
            self.assertEqual(request.url.path, "/v1/assets/asset_prompt")
            return httpx.Response(200, json={"asset": {"metadata": {"preview": self.preview}}})

        def factory(credentials, **kwargs):
            return adapter.SDKAdapter(credentials, transport=httpx.MockTransport(respond), **kwargs)

        self.enterContext(
            patch.object(submodule("core.api.sdk_catalog"), "SDKAdapter", side_effect=factory)
        )
        self.enterContext(
            patch.object(
                self.runtime, "make_client", side_effect=AssertionError("Legacy client used")
            )
        )

    def completed(self):
        self.manager.join(5)
        self.assertFalse(self.manager.has_active())
        return self.manager.drain_catalog()

    def deliver(self):
        self.manager.join(5)
        self.assertFalse(self.manager.has_active())
        self.generation.process_catalog_events()

    def test_ui_refresh_and_headless_mcp_share_resolved_history(self):
        self.history.refresh()
        self.manager.join(5)
        result = self.tools.list_generations({})  # Delivers without a GUI tick.
        self.assertEqual(result["generations"][0]["prompt"], self.preview)
        self.assertEqual(result["generations"][0]["job_id"], "job-fixture")
        self.assertEqual(len(self.calls), 2)
        self.assertTrue(self.runtime.state.history_loaded)
        self.assertFalse(self.runtime.state.history_loading)
        self.assertEqual(self.runtime.state.history_token, "page-two")

    def test_empty_page_is_loaded_once_and_mcp_does_not_start_repeated_reads(self):
        self.page = {"jobs": []}
        first = self.tools.list_generations({})
        self.assertIn("note", first)
        self.manager.join(5)
        self.assertEqual(self.tools.list_generations({}), {"generations": []})
        self.assertEqual(self.tools.list_generations({}), {"generations": []})
        self.assertEqual(len(self.calls), 1)

    def test_older_page_keeps_cursor_deduplicates_and_has_one_pending_request(self):
        self.history.refresh()
        self.deliver()
        self.page = {"jobs": [job(), job("job-older", "older prompt")]}
        self.assertTrue(self.history.older())
        self.assertFalse(self.history.older())
        self.deliver()
        self.assertEqual(
            [e.job_id for e in self.runtime.state.history], ["job-fixture", "job-older"]
        )
        self.assertIsNone(self.runtime.state.history_token)
        self.assertEqual(self.calls[2].url.params["paginationToken"], "page-two")

    def test_ui_and_mcp_refresh_share_a_pending_read(self):
        with patch.object(self.manager, "fetch_history") as fetch:
            self.history.refresh()
            key = self.runtime.state.history_request
            for _ in range(3):
                self.history.refresh()
                self.tools.list_generations({"refresh": True})
            self.assertEqual(fetch.call_count, 1)
            self.assertEqual(self.runtime.state.history_request, key)
        self.handlers.dispatch(
            (
                "history",
                {
                    "catalog": self.runtime.state.catalog,
                    "key": key,
                    "jobs": [],
                    "error": None,
                },
            )
        )
        self.history.refresh()
        self.deliver()
        self.assertEqual(len(self.calls), 2)

    def test_mcp_rejects_non_boolean_refresh_without_reading(self):
        for value in ("false", "true", 0, 1, None, [], {}):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "refresh must be a boolean"):
                    self.tools.list_generations({"refresh": value})
        self.assertFalse(self.calls)
        self.assertFalse(self.runtime.state.history_loading)
        self.runtime.state.history_loaded = True
        self.assertEqual(self.tools.list_generations({"refresh": False}), {"generations": []})

    def test_credentials_clear_visible_history_and_reject_queued_old_results(self):
        self.history.refresh()
        self.deliver()
        self.history.refresh()
        queued = self.completed()
        self.prefs.api_secret = "replacement-secret"
        self.runtime.ensure_catalog()
        for event in queued:
            self.handlers.dispatch(event)
        self.assertFalse(self.runtime.state.history)
        self.assertFalse(self.runtime.state.history_loaded)
        self.assertIsNone(self.runtime.state.history_token)
        self.preview = "new account prompt"
        self.history.refresh()
        self.deliver()
        self.assertEqual(self.runtime.state.history[0].prompt, self.preview)

    def test_old_failure_does_not_replace_new_context_or_message(self):
        self.status = 403
        self.page = {"message": "private response"}
        self.history.refresh()
        queued = self.completed()
        self.prefs.api_secret = "replacement-secret"
        self.runtime.ensure_catalog()
        self.runtime.set_message("current message")
        for event in queued:
            self.handlers.dispatch(event)
        self.assertEqual(self.runtime.state.last_message, "current message")
        self.assertFalse(self.runtime.state.history_error)

    def test_failed_refresh_keeps_last_page_and_cursor(self):
        self.history.refresh()
        self.deliver()
        with patch.object(self.manager, "fetch_history"):
            self.history.refresh()
            pending = self.tools.list_generations({})
            self.assertIn("pending", pending["note"])
            self.assertEqual(pending["generations"][0]["job_id"], "job-fixture")
        self.handlers.dispatch(
            (
                "history",
                {
                    "catalog": self.runtime.state.catalog,
                    "key": self.runtime.state.history_request,
                    "error": "fixture read failed",
                },
            )
        )
        self.status = 503
        self.page = {"private": "response details"}
        self.history.refresh()
        self.deliver()
        self.assertEqual([e.job_id for e in self.runtime.state.history], ["job-fixture"])
        self.assertEqual(self.runtime.state.history_token, "page-two")
        self.assertTrue(self.runtime.state.history_error)
        self.assertNotIn("response details", self.runtime.state.history_error)
        self.assertFalse(self.runtime.state.history_loading)
        with self.assertRaisesRegex(RuntimeError, "refresh=true"):
            self.tools.list_generations({})

    def test_mcp_failed_initial_read_can_be_retried_explicitly(self):
        self.status = 503
        self.tools.list_generations({})
        self.deliver()
        with self.assertRaisesRegex(RuntimeError, "refresh=true"):
            self.tools.list_generations({})
        self.status = 200
        self.tools.list_generations({"refresh": True})
        self.deliver()
        self.assertEqual(self.tools.list_generations({})["generations"][0]["job_id"], "job-fixture")

    def test_cross_page_cursor_cycle_preserves_last_valid_page(self):
        self.history.refresh()
        self.deliver()
        self.page = {"jobs": [job("job-two", "two")], "nextPaginationToken": "page-three"}
        self.history.older()
        self.deliver()
        self.page = {"jobs": [job("job-three", "three")], "nextPaginationToken": "page-two"}
        self.history.older()
        self.deliver()
        self.assertEqual([e.job_id for e in self.runtime.state.history], ["job-fixture", "job-two"])
        self.assertEqual(self.runtime.state.history_token, "page-three")
        self.assertIn("repeated", self.runtime.state.history_error)

    def test_malformed_metadata_and_billing_fail_without_partial_delivery(self):
        for malformed in ({"metadata": [1]}, {"billing": {"cuCost": "invalid"}}):
            with self.subTest(malformed=malformed):
                self.page = {"jobs": [{**job(prompt="text"), **malformed}]}
                self.history.refresh()
                self.deliver()
                self.assertFalse(self.runtime.state.history)
                self.assertFalse(self.runtime.state.history_loading)
                self.assertTrue(self.runtime.state.history_error)
