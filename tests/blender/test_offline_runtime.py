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
        client_class = submodule("core.api.client").ScenarioClient
        for method in ("get", "post"):
            tripwire = self.enterContext(
                patch.object(
                    client_class, method, side_effect=AssertionError("Unexpected service transport")
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

    def catalog_client(self, fail=False):
        model = json.loads((FIXTURES / "models/model_google-gemini-3-1-flash.json").read_text())[
            "model"
        ]
        calls = []
        adapter = submodule("core.api.sdk_adapter")

        def respond(request):
            path = request.url.path.removeprefix("/v1")
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

    def test_catalog_service_failure_clears_loading_and_reaches_ui_state(self):
        _, calls = self.catalog_client(fail=True)
        with online_access(True):
            self.assertTrue(self.generation.request_catalog())
            self.dispatch_workers()
        self.assertFalse(self.runtime.state.catalog_loading)
        self.assertFalse(self.runtime.state.catalog_loaded)
        self.assertIn("HTTP 503", self.runtime.state.catalog_error)
        self.assertIn("Could not load models", self.runtime.state.last_message)
        self.assertEqual(len(calls), 1)
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
                self.prefs.api_secret = "other-secret"
                self.assertIsNone(self.runtime.state.catalog)
                self.assertEqual(lane.estimate_key, "")
                self.assertEqual(lane.estimate_state, "IDLE")
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
            self.assertTrue(all(pool._closed for pool in pools))
            self.assertEqual(sum(first for first, _ in calls), 1)

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

    def test_offline_manager_loads_saved_job_without_resuming_it(self):
        job = self.saved_job()
        registry_bytes = self.manager.paths.registry_file.read_bytes()
        with patch.object(self.runtime.state, "manager", None):
            manager_class = submodule("core.jobs.manager").JobManager
            with patch.object(manager_class, "resume", autospec=True) as resume:
                restored = self.runtime.ensure_manager()
                try:
                    resume.assert_not_called()
                    self.assertEqual(
                        [rec.job_id for rec in restored.registry.active()], [job.job_id]
                    )
                    self.assertEqual(restored.paths.registry_file.read_bytes(), registry_bytes)
                    self.assertFalse(restored.has_active())
                finally:
                    restored.shutdown()
                    restored.join(timeout=5)
        # Control branch: the same saved job does reach resume when online.
        with online_access(True), patch.object(self.runtime.state, "manager", None):
            with patch.object(manager_class, "resume", autospec=True) as resume:
                restored = self.runtime.ensure_manager()
                resume.assert_called_once_with(restored)
                restored.shutdown()

    def test_pump_does_not_retry_suspended_jobs_until_online(self):
        job = self.saved_job()
        self.manager.resume_pending = [job]
        self.runtime.state.catalog_loaded = True
        with patch.object(self.manager, "retry_resume") as retry:
            self.pump._process()
            retry.assert_not_called()
            self.assertEqual(self.manager.resume_pending, [job])
            with online_access(True):
                self.pump._process()
                retry.assert_called_once_with()
