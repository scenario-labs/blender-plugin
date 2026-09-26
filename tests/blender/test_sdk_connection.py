# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Native asynchronous connection operator with synthetic SDK responses."""

import os
import threading
import unittest
from unittest.mock import Mock, patch

import bpy
import httpx
from helpers import isolated_manager, online_access, submodule, temp_credentials


class SDKConnectionTests(unittest.TestCase):
    def setUp(self):
        self.runtime = submodule("blender.runtime")
        self.generation = submodule("blender.generation")
        self.handlers = submodule("blender.handlers")
        self.enterContext(patch.object(self.runtime, "state", self.runtime.RuntimeState()))
        self.prefs = self.enterContext(temp_credentials())
        self.enterContext(online_access(True))
        self.manager = self.enterContext(isolated_manager())
        self.addCleanup(self.runtime.state.reset)
        self.calls = []
        self.status = 200
        self.entered, self.release = threading.Event(), threading.Event()
        self.release.set()
        self.addCleanup(self.release.set)
        adapter = submodule("core.api.sdk_adapter")

        def respond(request):
            self.assertIsNot(threading.current_thread(), threading.main_thread())
            self.calls.append(request)
            self.entered.set()
            self.assertTrue(self.release.wait(5))
            self.assertEqual((request.method, request.url.path), ("GET", "/v1/models"))
            self.assertEqual(dict(request.url.params), {"privacy": "public", "pageSize": "1"})
            return httpx.Response(self.status, json={"models": [], "private": "do-not-expose"})

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
        for event in self.completed():
            self.handlers.dispatch(event)

    def test_operator_returns_while_network_is_pending_and_repeated_clicks_share_check(self):
        self.release.clear()
        self.assertIsNotNone(self.runtime.request_connection_check())
        try:
            self.assertTrue(self.entered.wait(5))
            self.assertIn("Checking", self.runtime.state.account_label)
            key = self.runtime.state.connection_request
            self.assertIsNotNone(key)
            self.assertIsNotNone(self.runtime.request_connection_check())
            self.assertIs(self.runtime.state.connection_request, key)
            self.assertEqual(len(self.calls), 1)
        finally:
            self.release.set()
        self.deliver()
        self.assertEqual(
            self.runtime.state.account_label, "Connected to Scenario (model access verified)"
        )
        self.assertIsNone(self.runtime.state.connection_request)
        self.assertFalse(self.runtime.state.catalog_loaded)

    def test_failed_credentials_are_visible_without_private_response_details(self):
        self.status = 403
        self.runtime.request_connection_check()
        self.deliver()
        self.assertIn("Connection failed", self.runtime.state.account_label)
        self.assertIn("403", self.runtime.state.account_label)
        self.assertNotIn("do-not-expose", self.runtime.state.account_label)
        self.status = 200
        self.runtime.request_connection_check()
        self.deliver()
        self.assertIn("verified", self.runtime.state.account_label)

    def test_queued_old_success_and_failure_do_not_relabel_replacement_credentials(self):
        for status in (200, 403):
            with self.subTest(status=status):
                self.status = status
                self.runtime.request_connection_check()
                queued = self.completed()
                self.prefs.api_secret = f"replacement-{status}"
                self.runtime.state.account_label = "replacement label"
                for event in queued:
                    self.handlers.dispatch(event)
                self.assertEqual(self.runtime.state.account_label, "replacement label")
                self.assertIsNone(self.runtime.state.connection_request)

    def test_environment_change_invalidates_connection_label_during_sync(self):
        saved = self.prefs.credential_source
        try:
            with patch.dict(
                os.environ,
                {"SCENARIO_API_KEY": "launch-key", "SCENARIO_API_SECRET": "launch-secret"},
            ):
                self.prefs.credential_source = "ENVIRONMENT"
                self.runtime.request_connection_check()
                self.deliver()
                self.assertIn("verified", self.runtime.state.account_label)
                os.environ["SCENARIO_API_SECRET"] = "other-secret"
                self.runtime.sync_catalog_context()
                self.assertEqual(self.runtime.state.account_label, "")
        finally:
            self.prefs.credential_source = saved

    def test_runtime_reset_rejects_a_queued_connection_result(self):
        self.runtime.request_connection_check()
        queued = self.completed()
        self.runtime.state.reset()
        for event in queued:
            self.handlers.dispatch(event)
        self.assertEqual(self.runtime.state.account_label, "")

    def test_offline_and_missing_credentials_fail_before_scheduling(self):
        with online_access(False):
            with self.assertRaisesRegex(Exception, "Online Access"):
                self.runtime.request_connection_check()
        self.prefs.api_secret = ""
        with self.assertRaisesRegex(Exception, "selected credential source"):
            self.runtime.request_connection_check()
        self.assertFalse(self.calls)
        self.assertIsNone(self.runtime.state.connection_request)

    def test_thread_start_failure_does_not_leave_a_stuck_check(self):
        with patch.object(
            self.manager, "check_connection", side_effect=RuntimeError("private detail")
        ):
            with self.assertRaisesRegex(Exception, "Could not start"):
                self.runtime.request_connection_check()
        self.assertIsNone(self.runtime.state.connection_request)
        self.assertEqual(self.runtime.state.account_label, "")
        self.assertFalse(self.calls)

    def test_connection_check_preserves_existing_catalog(self):
        catalog = self.runtime.ensure_catalog()
        self.runtime.state.catalog_loaded = True
        self.runtime.state.records["fixture-model"] = object()
        self.runtime.request_connection_check()
        self.manager.join(5)
        self.generation.process_catalog_events()
        self.assertIs(self.runtime.state.catalog, catalog)
        self.assertTrue(self.runtime.state.catalog_loaded)
        self.assertIn("fixture-model", self.runtime.state.records)

    def test_background_operator_delivers_success_and_error_without_a_gui_pump(self):
        self.assertTrue(bpy.app.background)
        for status, expected in ((200, "verified"), (403, "Connection failed")):
            with self.subTest(status=status):
                self.status = status
                self.assertEqual(bpy.ops.scenario.test_connection(), {"FINISHED"})
                self.assertIn(expected, self.runtime.state.account_label)
                self.assertIsNone(self.runtime.state.connection_request)
                self.assertIsNone(self.runtime.state.connection_worker)
                self.assertFalse(self.manager.has_active())

    def test_account_icon_tracks_check_state_even_with_a_loaded_catalog(self):
        self.runtime.state.catalog_loaded = True
        panels = submodule("blender.panels")
        for status, expected in (
            ("pending", "SORTTIME"),
            ("error", "ERROR"),
            ("success", "CHECKMARK"),
        ):
            with self.subTest(status=status):
                self.runtime.state.connection_status = status
                layout = Mock()
                self.assertTrue(panels.draw_account_strip(layout, bpy.context))
                self.assertEqual(layout.row.return_value.label.call_args.kwargs["icon"], expected)
