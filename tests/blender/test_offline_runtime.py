# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise real Blender online-access gates with private storage and synthetic services."""

import json
import socket
import threading
import unittest
from unittest.mock import patch

import bpy
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
        errors = submodule("core.api.errors")

        class Client:
            def get(self, path, query=None):
                calls.append((path, threading.current_thread()))
                if fail:
                    raise errors.ScenarioError(503, "Synthetic catalog outage")
                if path == "/models":
                    return {"models": [model]}
                if path == f"/models/{model['id']}":
                    return {"model": model}
                raise AssertionError(f"Unexpected fixture request: {path}")

        self.enterContext(patch.object(self.runtime, "make_client", return_value=Client()))
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
        self.assertIn("Synthetic catalog outage", self.runtime.state.catalog_error)
        self.assertIn("Could not load models", self.runtime.state.last_message)
        self.assertEqual(len(calls), 1)
        self.assertFalse(self.generation.request_catalog())

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
