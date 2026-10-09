# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Workflow MCP commands against the installed SDK, scoped store and workers."""

import json
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import bpy
import httpx
from helpers import online_access, reset_scene, submodule, temp_credentials


class WorkflowCommandTests(unittest.TestCase):
    def setUp(self):
        reset_scene()
        self.runtime = submodule("blender.runtime")
        self.tools = submodule("mcp.tools_scenario")
        self.enterContext(patch.object(self.runtime, "state", self.runtime.RuntimeState()))
        self.enterContext(online_access(True))
        self.prefs = self.enterContext(temp_credentials())
        self.addCleanup(setattr, self.prefs, "project_id", self.prefs.project_id)
        self.prefs.project_id = ""
        root = self.enterContext(tempfile.TemporaryDirectory(dir=bpy.utils.resource_path("USER")))
        self.enterContext(
            patch.object(
                self.runtime,
                "paths",
                return_value=SimpleNamespace(
                    state_dir=Path(root), registry_file=Path(root) / "jobs.json"
                ),
            )
        )
        self.calls, self.paid, self.sessions = [], [], []
        self.workflow = {
            "id": "fixture-workflow",
            "name": "Fixture workflow",
            "inputs": [
                {"name": "prompt", "type": "string", "required": True},
                {"name": "count", "type": "number", "default": 1},
            ],
        }
        self.lose_response, self.fail_metadata = False, False
        self.project = None
        api = submodule("core.api.sdk_adapter")
        catalog_type, session_type = self.runtime.SDKCatalog, self.runtime.JobSession

        def respond(request):
            self.assertIsNot(threading.current_thread(), threading.main_thread())
            self.calls.append(request)
            self.assertEqual(request.url.params.get("projectId"), self.project)
            if request.method == "GET":
                if self.fail_metadata:
                    return httpx.Response(403, json={"message": "private fixture error"})
                if request.url.path == "/v1/workflows":
                    if request.url.params.get("paginationToken"):
                        return httpx.Response(200, json={"workflows": [self.workflow]})
                    return httpx.Response(
                        200,
                        json={
                            "workflows": [{"id": "other-workflow", "name": "Other"}, self.workflow],
                            "nextPaginationToken": "next-page",
                        },
                    )
                if "/jobs/" in request.url.path:
                    return httpx.Response(
                        200,
                        json={
                            "job": {
                                "jobId": "workflow-job",
                                "jobType": "workflow",
                                "status": "in-progress",
                                "metadata": {"input": {"workflowId": self.workflow["id"]}},
                            }
                        },
                    )
                self.assertEqual(request.url.path, "/v1/workflows/fixture-workflow")
                return httpx.Response(200, json={"workflow": self.workflow})
            self.assertEqual(request.method, "PUT")
            self.assertEqual(request.url.path, "/v1/workflows/fixture-workflow/run")
            self.assertEqual(json.loads(request.content), {"prompt": "a cup", "count": 1})
            if request.url.params.get("dryRun") == "true":
                return httpx.Response(269, content=b'{"creativeUnitsCost":0.1234567890123456789}')
            self.assertTrue(any(r.state.value == "submitting" for r in self.store.records()))
            self.paid.append(request)
            if self.lose_response:
                raise httpx.ReadTimeout("private fixture timeout", request=request)
            return httpx.Response(200, json={"job": {"jobId": "workflow-job"}})

        def factory(credentials, **options):
            return api.SDKAdapter(credentials, transport=httpx.MockTransport(respond), **options)

        def session(*args, **options):
            item = session_type(*args, **options)
            self.sessions.append(item)
            return item

        self.enterContext(
            patch.object(
                self.runtime,
                "SDKCatalog",
                side_effect=lambda *a, **k: catalog_type(*a, adapter_factory=factory, **k),
            )
        )
        self.enterContext(patch.object(self.runtime, "JobSession", side_effect=session))
        self.addCleanup(self.cleanup)
        self.store = self.runtime.ensure_job_store()
        self.args = {"workflow_id": self.workflow["id"], "parameters": {"prompt": "a cup"}}

    def cleanup(self):
        self.runtime.state.reset()
        for session in self.sessions:
            session.shutdown()

    def finish(self, deferred):
        # Only wait runs on an HTTP worker in production; finish runs on main.
        deferred.run()
        return deferred.finish(None)

    def quote(self):
        return self.finish(self.tools.estimate_workflow(self.args))

    def approve(self, quote, **changes):
        return self.tools.run_workflow(
            {
                **self.args,
                "quote_id": quote["quote_id"],
                "approved_cost": quote["cu_cost_exact"],
                **changes,
            }
        )

    def settle(self):
        owner = self.runtime.state.model_jobs
        for task in tuple(owner.submissions.values()):
            try:
                task.result(5)
            except Exception:
                # Keep draining after errors; polling and later saved-state
                # assertions verify the submission outcome.
                pass
        owner.poll()
        for _, task in tuple(owner._commands.values()):
            task.result(5)
        owner.poll()

    def test_discovery_pages_deduplicate_and_preserve_input_definitions(self):
        result = self.finish(self.tools.list_workflows({"privacy": "public", "limit": 1}))
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["next_offset"], 1)
        result = self.finish(self.tools.list_workflows({"query": "fixture", "offset": 0}))
        self.assertEqual([row["id"] for row in result["workflows"]], [self.workflow["id"]])
        schema = self.finish(self.tools.workflow_schema(self.args))
        self.assertEqual(schema["inputs"], self.workflow["inputs"])
        self.assertFalse(self.store.records())
        self.assertFalse(self.paid)

    def test_exact_approval_submits_once_through_saved_workflow_lifecycle(self):
        quote = self.quote()
        self.assertEqual(quote["cu_cost_exact"], "0.1234567890123456789")
        self.assertEqual(quote["parameters"], self.args["parameters"])
        self.assertEqual(quote["payload"], {"prompt": "a cup", "count": 1})
        self.assertFalse(self.store.records())
        images = tuple(bpy.data.images)
        result = self.approve(quote)
        self.settle()
        record = self.store.get(result["local_id"])
        self.assertEqual(record.intent.operation, "workflow")
        self.assertEqual(record.state.value, "remote")
        self.assertEqual(len(self.paid), 1)
        self.assertNotIn("cancel", self.runtime.state.model_jobs.actions(record))
        self.assertEqual(tuple(bpy.data.images), images)
        with self.assertRaisesRegex(Exception, "fresh, unsubmitted"):
            self.approve(quote)
        self.assertEqual(len(self.paid), 1)

    def test_workflow_jobs_stay_unbound_from_scene_lanes(self):
        result = self.approve(self.quote())
        self.settle()
        owner = self.runtime.state.model_jobs
        for lane in (*submodule("core.api.catalog").GENERATION_LANES, "workflow"):
            self.assertEqual(owner.bound_views(bpy.context.scene, lane), ())
        status = self.tools.job_status({"job_id": result["local_id"]})
        self.assertIsNone(status["lane"])
        # Workflow jobs still project their validated remote status.
        self.assertEqual((status["status"], status["remote_status"]), ("remote", "in-progress"))
        self.assertEqual(len(self.paid), 1)

    def test_changed_price_payload_identity_and_scene_do_not_submit(self):
        quote = self.quote()
        for changes in (
            {"approved_cost": "0.123"},
            {"parameters": {"prompt": "different"}},
            {"workflow_id": "another-workflow"},
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaisesRegex(Exception, "unchanged workflow"),
            ):
                self.approve(quote, **changes)
        original = bpy.context.scene
        other = bpy.data.scenes.new("Other workflow scene")
        try:
            bpy.context.window.scene = other
            with self.assertRaisesRegex(Exception, "unchanged workflow"):
                self.approve(quote)
        finally:
            bpy.context.window.scene = original
            bpy.data.scenes.remove(other)
        self.assertFalse(self.store.records())
        self.assertFalse(self.paid)

    def test_workflow_quote_cannot_authorize_a_model(self):
        quote = self.quote()
        with self.assertRaisesRegex(Exception, "request or approved cost changed"):
            self.runtime.state.model_jobs.submit(
                quote["quote_id"],
                bpy.context.scene,
                self.workflow["id"],
                self.args["parameters"],
                approved_cost=quote["cu_cost_exact"],
            )
        self.assertFalse(self.paid)

    def test_lost_response_is_uncertain_without_retry(self):
        self.lose_response = True
        quote = self.quote()
        result = self.approve(quote)
        self.settle()
        self.assertEqual(self.store.get(result["local_id"]).state.value, "uncertain")
        with self.assertRaisesRegex(Exception, "fresh, unsubmitted"):
            self.approve(quote)
        self.assertEqual(len(self.paid), 1)

    def test_failed_persistence_consumes_approval_without_spending(self):
        quote = self.quote()
        with patch.object(
            self.runtime.state.model_jobs.session,
            "prepare_quote",
            side_effect=OSError("fixture write"),
        ):
            with self.assertRaises(OSError):
                self.approve(quote)
        with self.assertRaisesRegex(Exception, "fresh, unsubmitted"):
            self.approve(quote)
        self.assertFalse(self.paid)

    def test_discard_consumes_only_local_approval(self):
        quote = self.quote()
        self.assertEqual(
            self.tools.discard_workflow_estimate({"quote_id": quote["quote_id"]}),
            {"discarded": True},
        )
        with self.assertRaisesRegex(Exception, "fresh, unsubmitted"):
            self.approve(quote)
        self.assertFalse(self.store.records())
        self.assertFalse(self.paid)

    def test_offline_and_gui_probe_reject_approval(self):
        quote = self.quote()
        with patch.object(self.runtime.state.model_jobs, "_online", return_value=False):
            with self.assertRaisesRegex(Exception, "while online"):
                self.approve(quote)
        with patch.dict("os.environ", {"SCENARIO_GUI_PROBE": "1"}):
            with self.assertRaises(PermissionError):
                self.approve(quote)
        self.assertFalse(self.store.records())
        self.assertFalse(self.paid)

    def test_project_switch_rejects_quote_and_pending_metadata(self):
        quote = self.quote()
        pending = self.tools.list_workflows({})
        pending.run()
        self.prefs.project_id = "another-project"
        self.project = "another-project"
        with self.assertRaisesRegex(Exception, "context changed"):
            pending.finish(None)
        with self.assertRaisesRegex(Exception, "fresh, unsubmitted"):
            self.approve(quote)
        self.assertFalse(self.paid)

    def test_metadata_error_drains_pending_task_without_exposing_response(self):
        self.fail_metadata = True
        with self.assertRaises(Exception) as caught:
            self.finish(self.tools.list_workflows({}))
        self.assertNotIn("private fixture", str(caught.exception))
        self.assertFalse(self.runtime.state.job_session._pending)
        self.assertFalse(self.paid)

    def test_bad_list_arguments_fail_before_creating_session(self):
        for args in ({"privacy": "unknown"}, {"offset": -1}, {"limit": True}, {"query": []}):
            with self.subTest(args=args), self.assertRaises(ValueError):
                self.tools.list_workflows(args)
        self.assertIsNone(self.runtime.state.job_session)
        self.assertFalse(self.calls)

    def test_scene_revision_change_rejects_ready_approval_without_dispatch(self):
        quote = self.quote()
        self.runtime.state.model_jobs.session.invalidate_scene(bpy.context.scene)
        with self.assertRaisesRegex(Exception, "Origin changed"):
            self.approve(quote)
        self.assertFalse(self.store.records())
        self.assertFalse(self.paid)

    def test_scene_revision_change_rejects_metadata_delivery(self):
        pending = self.tools.workflow_schema(self.args)
        pending.run()
        self.runtime.state.job_session.invalidate_scene(bpy.context.scene)
        with self.assertRaisesRegex(Exception, "Origin changed"):
            pending.finish(None)
        self.assertFalse(self.paid)

    def test_failed_quote_releases_approval_capacity(self):
        self.fail_metadata = True
        with self.assertRaisesRegex(submodule("core.api.sdk_adapter").AdapterError, "HTTP 403"):
            self.quote()
        owner = self.runtime.state.model_jobs
        self.assertTrue(all(ticket.used for ticket in owner.quotes.values()))
        self.assertFalse(owner.session._pending)
        self.fail_metadata = False
        self.assertTrue(self.quote()["quote_id"])
        self.assertFalse(self.store.records())

    def test_restart_keeps_workflow_identity_without_polling_or_resubmission(self):
        result = self.approve(self.quote())
        self.settle()
        self.runtime.state.reset()
        count = len(self.calls)
        owner = self.runtime.ensure_model_jobs()
        rows = owner.inspect()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].local_id, result["local_id"])
        self.assertEqual((rows[0].lane, rows[0].kind), ("workflow", "workflow"))
        self.assertEqual(len(self.calls), count)
        self.assertEqual(len(self.paid), 1)

    def test_schema_null_definition_falls_back_but_empty_definition_is_preserved(self):
        self.workflow["inputs_definition"] = None
        result = self.finish(self.tools.workflow_schema(self.args))
        self.assertEqual(result["inputs"], self.workflow["inputs"])
        self.workflow["inputs_definition"] = []
        result = self.finish(self.tools.workflow_schema(self.args))
        self.assertEqual(result["inputs"], [])
        self.assertFalse(self.store.records())
        self.assertFalse(self.paid)
