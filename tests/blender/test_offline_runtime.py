# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise real Blender online-access gates with private storage and synthetic services."""

import json
import socket
import threading
import unittest
from unittest.mock import patch

import bpy
import httpx
from helpers import (
    FIXTURES,
    isolated_manager,
    online_access,
    reset_scene,
    submodule,
    temp_credentials,
)


class OfflineRuntimeTests(unittest.TestCase):
    def setUp(self):
        reset_scene()
        self.runtime = submodule("blender.runtime")
        self.generation = submodule("blender.generation")
        self.pump = submodule("blender.pump")
        self.service = submodule("blender.mcp_service")
        self.service.stop()
        self.enterContext(patch.object(self.runtime, "state", self.runtime.RuntimeState()))
        self.prefs = self.enterContext(temp_credentials())
        self.enterContext(online_access(False))
        self.manager = self.enterContext(isolated_manager())
        self.addCleanup(self.runtime.state.reset)
        tripwire = self.enterContext(
            patch.object(
                httpx.HTTPTransport,
                "handle_request",
                side_effect=AssertionError("Unexpected service transport"),
            )
        )
        self.addCleanup(tripwire.assert_not_called)
        self.addCleanup(self.service.stop)

    def dispatch_workers(self):
        self.manager.join(timeout=5)
        self.assertFalse(self.manager.has_active(), "Synthetic service worker did not finish")
        self.pump._process()

    def test_offline_catalog_is_refused_without_stuck_loading(self):
        self.assertTrue(self.runtime.credentials().valid)
        self.assertFalse(self.runtime.online())
        with patch.object(self.manager, "fetch_catalog") as fetch:
            for _ in range(2):
                self.assertFalse(self.generation.request_catalog())
                self.pump._process()
                self.assertFalse(self.runtime.state.catalog_loading)
            fetch.assert_not_called()
        self.assertIsNone(self.runtime.state.catalog)
        self.assertFalse(self.manager.has_active())

    def test_invalid_project_catalog_error_stops_ticks_and_recovers_after_edit(self):
        _, calls = self.catalog_client()
        self.addCleanup(setattr, self.prefs, "project_id", self.prefs.project_id)
        self.prefs.project_id = "https://example.invalid/project"
        with (
            online_access(True),
            patch.object(
                self.generation, "request_catalog", wraps=self.generation.request_catalog
            ) as request,
        ):
            for _ in range(5):
                self.pump._process()
            self.assertEqual(request.call_count, 1)
            self.assertIn("Project ID must be an opaque ID", self.runtime.state.catalog_error)
            self.assertFalse(self.runtime.state.catalog_loading)
            self.assertIsNone(self.runtime.state.catalog)
            self.assertEqual(calls, [])
            # An explicit refresh remains possible, without enabling automatic retries.
            self.assertFalse(self.generation.request_catalog())
            self.pump._process()
            self.assertEqual(request.call_count, 2)
            # The callback must clear the failure even though no catalog was created.
            self.prefs.project_id = "fixture-project"
            self.assertEqual(self.runtime.state.catalog_error, "")
            self.pump._process()
            self.dispatch_workers()
            self.assertEqual(request.call_count, 3)
            self.assertTrue(self.runtime.state.catalog_loaded)
            self.assertEqual(self.runtime.state.catalog.scope.project_id, "fixture-project")
            self.assertEqual(self.runtime.state.catalog_error, "")

    def test_catalog_local_error_recovers_when_environment_credentials_change(self):
        _, calls = self.catalog_client()
        source = self.prefs.credential_source
        self.addCleanup(setattr, self.prefs, "credential_source", source)
        self.prefs.credential_source = "ENVIRONMENT"
        with (
            patch.dict("os.environ", SCENARIO_API_KEY="bad:key", SCENARIO_API_SECRET="fixture"),
            online_access(True),
        ):
            self.pump._process()
            self.assertIn("not a valid API key", self.runtime.state.catalog_error)
            self.assertIsNone(self.runtime.state.catalog)
            self.assertEqual(calls, [])
            # Environment edits have no RNA preference callback.
            with patch.dict("os.environ", SCENARIO_API_KEY="fixture-key"):
                self.pump._process()
                self.dispatch_workers()
                self.assertTrue(self.runtime.state.catalog_loaded)
                self.assertEqual(self.runtime.state.catalog_error, "")

    def catalog_client(self, fail=False):
        model = json.loads((FIXTURES / "models/model_google-gemini-3-1-flash.json").read_text())[
            "model"
        ]
        calls = []
        self.private_reads = []  # the trained-model list each catalog load reads too (#97)
        adapter = submodule("core.api.sdk_adapter")

        def respond(request):
            path = request.url.path.removeprefix("/v1")
            if path == "/models" and request.url.params.get("privacy") == "private":
                self.assertEqual(request.url.params.get("status"), "trained")
                self.private_reads.append(threading.current_thread())
                if fail:
                    return httpx.Response(503, json={"error": "Synthetic catalog outage"})
                return httpx.Response(200, json={"models": []})
            calls.append((path, threading.current_thread()))
            if fail:
                return httpx.Response(503, json={"error": "Synthetic catalog outage"})
            if path == "/models":
                return httpx.Response(200, json={"models": [model]})
            if path == f"/models/{model['id']}":
                return httpx.Response(200, json={"model": model})
            raise AssertionError(f"Unexpected fixture request: {path}")

        def factory(credentials, **kwargs):
            return adapter.SDKAdapter(credentials, transport=httpx.MockTransport(respond), **kwargs)

        self.enterContext(
            patch.object(submodule("core.api.sdk_catalog"), "SDKAdapter", side_effect=factory)
        )
        self.enterContext(patch.object(self.generation, "DEFAULT_MODELS", {"image": [model["id"]]}))
        return model, calls

    def test_online_catalog_worker_updates_blender_then_offline_refuses_refresh(self):
        model, calls = self.catalog_client()
        with online_access(True):
            self.assertTrue(self.runtime.online())
            self.assertTrue(self.generation.request_catalog())
            self.assertTrue(self.runtime.state.catalog_loading)
            self.dispatch_workers()
            self.assertTrue(self.runtime.state.catalog_loaded)
            self.assertFalse(self.runtime.state.catalog_loading)
            self.assertEqual(self.runtime.state.catalog_error, "")
            self.assertIn(model["id"], self.runtime.state.records)
            self.assertIn(
                model["id"], [item[0] for item in self.runtime.enum_items(("models", "image"))]
            )
        before = len(calls)
        self.assertFalse(self.generation.request_catalog())
        self.assertEqual(len(calls), before)
        self.assertEqual([path for path, _ in calls], ["/models", f"/models/{model['id']}"])
        self.assertTrue(all(thread is not threading.main_thread() for _, thread in calls))
        self.assertEqual(len(self.private_reads), 1)
        self.assertIsNot(self.private_reads[0], threading.main_thread())
        self.assertTrue(self.runtime.state.trained_loaded)

    def test_catalog_service_failure_clears_loading_and_reaches_ui_state(self):
        _, calls = self.catalog_client(fail=True)
        with online_access(True):
            self.assertTrue(self.generation.request_catalog())
            self.dispatch_workers()
        self.assertFalse(self.runtime.state.catalog_loading)
        self.assertFalse(self.runtime.state.catalog_loaded)
        self.assertIn("HTTP 503", self.runtime.state.catalog_error)
        self.assertIn("Could not load models", self.runtime.state.last_message)
        # Each catalog list read fails after the SDK's own read retries.
        attempts = 1 + submodule("core.api.sdk_adapter").READ_RETRIES
        self.assertEqual(len(calls), attempts)
        self.assertEqual(len(self.private_reads), attempts)
        self.assertIn("HTTP 503", self.runtime.state.trained_error)
        self.assertFalse(self.generation.request_catalog())

    def test_headless_mcp_and_ui_deliver_the_same_sdk_catalog_and_schema(self):
        model, calls = self.catalog_client()
        tools = submodule("mcp.tools_scenario")
        with online_access(True):
            with self.assertRaisesRegex(RuntimeError, "still loading"):
                tools.list_models({"lane": "image"})
            context = self.runtime.state.catalog
            self.manager.join(timeout=5)
            self.assertFalse(self.manager.has_active())
            # No GUI pump in background mode. A subsequent MCP read delivers
            # the same queued catalog into the shared UI state.
            listed = tools.list_models({"lane": "image"})
            schema = tools.model_schema({"model_id": model["id"]})
            self.assertIs(context, self.runtime.ensure_catalog())
            self.assertEqual(listed["models"][0]["id"], model["id"])
            self.assertEqual(schema["model_id"], model["id"])
            self.assertIn("resolution", [item["name"] for item in schema["parameters"]])
            self.assertEqual(len(calls), 2)
            self.assertEqual(self.runtime.state.records[model["id"]].name, model["name"])

    def test_changed_credentials_discard_inflight_catalog_and_invalidate_forms(self):
        adapter = submodule("core.api.sdk_adapter")
        catalog_module = submodule("core.api.sdk_catalog")
        started, release = threading.Event(), threading.Event()
        calls, pools = [], []
        model = {
            "id": "fixture",
            "name": "Current",
            "type": "custom",
            "capabilities": ["txt2img"],
            "inputs": [{"name": "prompt", "type": "string"}],
        }

        def factory(credentials, **kwargs):
            first = credentials.api_secret == "fixture-secret"

            def respond(request):
                calls.append((first, request.url.path))
                if first:
                    started.set()
                    self.assertTrue(release.wait(5))
                payload = (
                    {"models": [model]}
                    if request.url.path.endswith("/models")
                    else {"model": model}
                )
                return httpx.Response(200, json=payload)

            result = adapter.SDKAdapter(
                credentials, transport=httpx.MockTransport(respond), **kwargs
            )
            pools.append(result)
            return result

        self.enterContext(patch.object(catalog_module, "SDKAdapter", side_effect=factory))
        self.enterContext(patch.object(self.generation, "DEFAULT_MODELS", {"image": ["fixture"]}))
        with online_access(True):
            self.assertTrue(self.generation.request_catalog())
            old = self.runtime.state.catalog
            try:
                self.assertTrue(started.wait(5))
                lane = bpy.context.scene.scenario.lane_state("image")
                lane.estimate_key, lane.estimate_state = "old-quote", "READY"
                self.generation._pending_dirty_models.add(model["id"])
                self.prefs.api_secret = "other-secret"
                self.assertIsNone(self.runtime.state.catalog)
                self.assertEqual(lane.estimate_key, "")
                self.assertEqual(lane.estimate_state, "IDLE")
                self.assertFalse(self.generation._pending_dirty_models)
                self.assertFalse(old.closed)
                self.assertFalse(pools[0]._closed)
                self.assertTrue(self.generation.request_catalog())
                current = self.runtime.state.catalog
            finally:
                release.set()
            self.dispatch_workers()
            self.assertIs(self.runtime.state.catalog, current)
            self.assertTrue(old.closed)
            self.assertEqual(self.runtime.state.catalog_error, "")
            self.assertTrue(self.runtime.state.catalog_loaded)
            self.assertEqual(self.runtime.state.records["fixture"].name, "Current")
            self.assertTrue(pools[0]._closed)
            self.assertFalse(pools[1]._closed)
            # The retired connection made only its list reads: the public one and, if it
            # started before retirement, the private trained list; no description read.
            retired = [path for first, path in calls if first]
            self.assertIn(len(retired), (1, 2))
            self.assertEqual(set(retired), {"/v1/models"})

    def test_catalog_reset_returns_before_blocked_read_and_worker_closes_its_pool(self):
        catalog_module = submodule("core.api.sdk_catalog")
        adapter = submodule("core.api.sdk_adapter")
        entered, release, reset_returned = (threading.Event(), threading.Event(), threading.Event())
        pools, returned_promptly = [], []

        def respond(request):
            entered.set()
            self.assertTrue(release.wait(5))
            return httpx.Response(200, json={"models": []})

        def factory(credentials, **kwargs):
            result = adapter.SDKAdapter(
                credentials, transport=httpx.MockTransport(respond), **kwargs
            )
            pools.append(result)
            return result

        def release_after_reset():
            returned_promptly.append(reset_returned.wait(2))
            release.set()

        self.enterContext(patch.object(catalog_module, "SDKAdapter", side_effect=factory))
        with online_access(True):
            self.assertTrue(self.generation.request_catalog())
            context = self.runtime.state.catalog
            self.assertTrue(entered.wait(5))
            releaser = threading.Thread(target=release_after_reset)
            releaser.start()
            try:
                self.generation._schemas["fixture"] = object()
                self.generation._pending_models.add("fixture")
                self.generation._pending_dirty_models.add("fixture")
                # Resetting an unrelated state cannot clear the active singleton.
                self.runtime.RuntimeState().reset()
                self.assertIn("fixture", self.generation._pending_dirty_models)
                self.runtime.state.reset()
                self.assertFalse(self.generation._schemas)
                self.assertFalse(self.generation._pending_models)
                self.assertFalse(self.generation._pending_dirty_models)
                self.assertFalse(context.closed)
                self.assertFalse(pools[0]._closed)
            finally:
                reset_returned.set()
                release.set()
                releaser.join(5)
                self.manager.join(5)
        self.assertEqual(returned_promptly, [True])
        self.assertFalse(self.manager.has_active())
        self.assertTrue(context.closed)
        self.assertTrue(pools[0]._closed)
        self.assertIsNone(self.runtime.state.catalog)
        self.assertFalse(self.runtime.state.catalog_loaded)

    def test_online_permission_snapshot_is_updated_on_main_thread(self):
        model, calls = self.catalog_client()
        with online_access(True):
            self.assertTrue(self.generation.request_catalog())
            self.dispatch_workers()
            context = self.runtime.state.catalog
        self.pump._process()
        errors = []

        def read():
            try:
                context.get(model["id"], refresh=True)
            except Exception as error:
                errors.append(error)

        worker = threading.Thread(target=read)
        worker.start()
        worker.join(5)
        self.assertFalse(worker.is_alive())
        self.assertEqual(len(errors), 1)
        self.assertIn("Online access is disabled", str(errors[0]))
        self.assertEqual(len(calls), 2)

    def test_failed_catalog_delivery_preserves_later_model_completion(self):
        model, _ = self.catalog_client()
        handlers = submodule("blender.handlers")
        record = submodule("core.api.catalog").ModelRecord.from_api(model)
        with online_access(True):
            context = self.runtime.ensure_catalog()
            self.runtime.state.catalog_loading = True
            self.generation._pending_models.add(model["id"])
            self.manager.catalog_events.put(
                ("catalog", {"catalog": context, "records": [], "detailed": []})
            )
            self.manager.catalog_events.put(
                ("models", {"catalog": context, "detailed": [record], "failed": {}})
            )
            dispatch = handlers.dispatch

            def deliver(event):
                if event[0] == "catalog":
                    raise ValueError("Synthetic malformed catalog")
                dispatch(event)

            with patch.object(handlers, "dispatch", side_effect=deliver):
                self.assertTrue(self.generation.process_catalog_events())
            self.assertFalse(self.runtime.state.catalog_loading)
            self.assertNotIn(model["id"], self.generation._pending_models)
            self.assertEqual(self.runtime.state.records[model["id"]].name, model["name"])

    def test_offline_mcp_start_is_refused_and_online_local_start_works(self):
        with patch.object(self.service, "McpServer", wraps=self.service.McpServer) as constructor:
            self.assertIsNone(self.service.start())
            constructor.assert_not_called()
        self.assertIn("Online Access", self.service.status()["error"])
        saved_port = self.prefs.mcp_port
        self.addCleanup(setattr, self.prefs, "mcp_port", saved_port)
        with socket.socket() as reservation:
            reservation.bind(("127.0.0.1", 0))
            self.prefs.mcp_port = reservation.getsockname()[1]
        with online_access(True):
            server = self.service.start()
            self.assertIsNotNone(server)
            self.assertTrue(server.running)
            self.assertEqual(self.service.status()["error"], "")
            self.service.stop()
        self.assertIsNone(self.service.start())
        self.assertFalse(self.service.status()["running"])

    def free_mcp_port(self):
        saved_port = self.prefs.mcp_port
        self.addCleanup(setattr, self.prefs, "mcp_port", saved_port)
        with socket.socket() as reservation:
            reservation.bind(("127.0.0.1", 0))
            self.prefs.mcp_port = reservation.getsockname()[1]
        # Ticks below only follow online access; a loaded catalog keeps them from reading one.
        self.runtime.state.catalog_loaded = True

    def gui_ticks(self, count=3):
        for _ in range(count):
            self.pump._process()

    def assert_serving(self, token):
        status = self.service.status()
        self.assertTrue(status["running"])
        self.assertEqual(status["error"], "")
        self.assertEqual(status["token"], token)
        with socket.create_connection(("127.0.0.1", self.runtime.state.mcp.port), timeout=2):
            pass

    def assert_stopped(self, port, error):
        status = self.service.status()
        self.assertFalse(status["running"])
        self.assertEqual(status["error"], error)
        # Refused, or on Windows possibly timed out while it retries a closed port.
        with self.assertRaises(OSError):
            socket.create_connection(("127.0.0.1", port), timeout=5).close()

    def test_switching_online_access_on_starts_the_window_server_without_restart(self):
        self.free_mcp_port()
        self.assertIsNone(self.service.start_with_extension())
        self.assertEqual(self.service.status()["error"], self.service.OFFLINE)
        with online_access(True):
            self.gui_ticks()
            token = self.runtime.state.mcp_token
            self.assertTrue(token)
            self.assert_serving(token)

    def test_switching_online_access_off_stops_the_server_and_on_restarts_it(self):
        self.free_mcp_port()
        with online_access(True):
            server = self.service.start_with_extension()
            token = self.runtime.state.mcp_token
            self.assert_serving(token)
        self.gui_ticks()
        self.assertFalse(server.running)
        self.assert_stopped(server.port, self.service.OFFLINE)
        with online_access(True):
            self.gui_ticks()
            # The per-session token survives, so connected agents keep their setup.
            self.assert_serving(token)

    def test_a_server_stopped_by_hand_stays_stopped_when_online_access_returns(self):
        self.free_mcp_port()
        with online_access(True):
            server = self.service.start_with_extension()
            token = self.runtime.state.mcp_token
            self.assertEqual(bpy.ops.scenario.mcp_stop(), {"FINISHED"})
            self.assert_stopped(server.port, "")
        self.gui_ticks()
        with online_access(True):
            self.gui_ticks()
            self.assert_stopped(server.port, "")
            self.assertEqual(bpy.ops.scenario.mcp_start(), {"FINISHED"})
            self.assert_serving(token)
        # Start MCP server ends the hand stop: the next switch follows online access again.
        self.gui_ticks()
        self.assertFalse(self.service.status()["running"])
        with online_access(True):
            self.gui_ticks()
            self.assert_serving(token)

    def test_nothing_starts_while_online_access_is_off_or_in_background_sessions(self):
        self.free_mcp_port()
        with patch.object(self.service, "McpServer", wraps=self.service.McpServer) as constructor:
            # Background registration never arms following: only the explicit command starts it.
            with online_access(True):
                self.gui_ticks()
            self.gui_ticks()
            with online_access(True):
                self.gui_ticks()
            constructor.assert_not_called()
            self.assertIsNone(self.service.start_with_extension())
            self.gui_ticks(5)
            constructor.assert_not_called()
        self.assertEqual(self.service.status()["error"], self.service.OFFLINE)
        self.assertFalse(self.service.status()["running"])

    def test_a_failed_start_waits_for_the_next_switch_instead_of_retrying_every_tick(self):
        self.free_mcp_port()
        self.service.start_with_extension()
        with (
            patch.object(
                self.service.McpServer, "start", side_effect=OSError("synthetic busy port")
            ) as bind,
            online_access(True),
        ):
            self.gui_ticks(5)
            self.assertEqual(bind.call_count, 1)
            self.assertEqual(self.service.status()["error"], "synthetic busy port")
            self.assertFalse(self.service.status()["running"])

    def test_network_operator_polls_follow_real_preference_with_credentials_present(self):
        operators = (
            bpy.ops.scenario.generate,
            bpy.ops.scenario.prompt_spark,
            bpy.ops.scenario.prompt_translate,
            bpy.ops.scenario.blockout_design,
            bpy.ops.scenario.blockout_refine,
            bpy.ops.scenario.history_refresh,
            bpy.ops.scenario.history_older,
            bpy.ops.scenario.import_result,
        )
        for operator in operators:
            self.assertFalse(operator.poll(), str(operator))
        with online_access(True):
            for operator in operators:
                self.assertTrue(operator.poll(), str(operator))
        for operator in operators:
            self.assertFalse(operator.poll(), str(operator))

    def saved_job(self):
        records = submodule("core.jobs.records")
        job = records.JobRecord.new(lane="image", kind="image", model_id="fixture-model", body={})
        job.job_id, job.status = "fixture-submitted-job", "processing"
        self.manager.registry.add(job)
        self.manager.registry.save()
        return job

    def test_manager_loads_prototype_records_without_requests_in_any_scope(self):
        job = self.saved_job()
        registry_bytes = self.manager.paths.registry_file.read_bytes()
        for allowed in (False, True):
            for project in (None, "fixture-project"):
                with (
                    self.subTest(online=allowed, project=project),
                    online_access(allowed),
                    patch.object(self.runtime, "project_id", return_value=project),
                    patch.object(self.runtime.state, "manager", None),
                ):
                    restored = self.runtime.ensure_manager()
                    try:
                        self.assertEqual(
                            [rec.job_id for rec in restored.registry.active()], [job.job_id]
                        )
                        self.assertEqual(restored.paths.registry_file.read_bytes(), registry_bytes)
                        self.assertFalse(restored.has_active())
                        self.assertEqual(restored.drain(), [])
                    finally:
                        restored.shutdown()
                        restored.join(timeout=5)

    def test_pump_never_resumes_prototype_jobs_after_scope_or_online_changes(self):
        job = self.saved_job()
        registry_bytes = self.manager.paths.registry_file.read_bytes()
        self.runtime.state.catalog_loaded = True
        with (
            patch.object(self.generation, "process_catalog_events", return_value=False),
            patch.object(self.service, "process_pending"),
            patch.object(self.runtime, "project_id") as project,
        ):
            for selected in (None, "fixture-project", None):
                project.return_value = selected
                for allowed in (False, True):
                    with online_access(allowed):
                        for _ in range(5):
                            self.pump._process()
                    self.assertEqual(self.manager.paths.registry_file.read_bytes(), registry_bytes)
                    self.assertEqual(self.manager.registry.active(), [job])
                    self.assertEqual(self.manager.drain(), [])
                    self.assertFalse(self.manager.has_active())
