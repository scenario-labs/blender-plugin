# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Workflow MCP commands against the installed SDK, scoped store and workers."""

import json
import tempfile
import threading
import time
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
                    state_dir=Path(root),
                    cache_dir=Path(root) / "cache",
                    registry_file=Path(root) / "jobs.json",
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
            "flow": [{"id": "node-a", "type": "custom-model"}],
        }
        self.lose_response, self.fail_metadata = False, False
        self.project = None
        self.remote_job = {
            "jobId": "workflow-job",
            "jobType": "workflow",
            "status": "in-progress",
            "metadata": {"input": {"workflowId": self.workflow["id"]}},
        }
        self.decisions, self.decision_reply = [], None
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
                    return httpx.Response(200, json={"job": self.remote_job})
                self.assertEqual(request.url.path, "/v1/workflows/fixture-workflow")
                return httpx.Response(200, json={"workflow": self.workflow})
            self.assertEqual(request.method, "PUT")
            if request.url.path.rsplit("/", 1)[-1] in ("user-approval", "user-selection"):
                self.decisions.append(request)
                reply = self.decision_reply(request) if self.decision_reply else None
                if isinstance(reply, httpx.Response):
                    return reply
                return httpx.Response(200, json={"job": {"jobId": "workflow-job"}})
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

    def test_loop_quote_and_run_return_nonblocking_one_pass_warning(self):
        quote = self.quote()
        self.assertEqual(
            (quote["loop_steps"], quote["quote_may_understate"], quote["cost_warning"]),
            (0, False, None),
        )
        self.workflow["flow"] = [
            {"id": "loop", "type": "for-each", "loopBodyNodeIds": ["node-a"]},
            {"id": "node-a", "type": "custom-model"},
        ]
        quote = self.quote()
        self.assertEqual(quote["cu_cost_exact"], "0.1234567890123456789")
        self.assertEqual((quote["loop_steps"], quote["quote_may_understate"]), (1, True))
        self.assertIn("covers one loop pass", quote["cost_warning"])
        result = self.approve(quote)
        self.settle()
        self.assertEqual(len(self.paid), 1)
        self.assertEqual((result["loop_steps"], result["quote_may_understate"]), (1, True))
        self.assertEqual(result["cost_warning"], quote["cost_warning"])
        self.assertIn("approved quote", result["note"])
        self.assertEqual(
            self.store.get(result["local_id"]).intent.quote_cost, quote["cu_cost_exact"]
        )
        status = self.tools.job_status({"job_id": result["local_id"]})
        self.assertEqual(status["cu_cost_exact"], quote["cu_cost_exact"])
        self.assertEqual((status["loop_steps"], status["quote_may_understate"]), (1, True))
        self.assertEqual(status["cost_warning"], quote["cost_warning"])

    def test_unknown_flow_is_flagged_without_blocking_approval(self):
        # Coverage is unknown unless every node is proven not to loop.
        for flow in (
            None,
            [],
            [{"id": "node-a"}],
            [{"id": "node-a", "type": 5}],
            [{"id": "node-a", "type": "ForEach"}],
            [{"id": "node-a", "type": "future-node"}],
            [{"id": "node-a", "type": "workflow"}],
            [{"id": "node-a", "type": "custom-model", "workflowId": "nested"}],
        ):
            with self.subTest(flow=flow):
                if flow is None:
                    self.workflow.pop("flow", None)
                else:
                    self.workflow["flow"] = flow
                quote = self.quote()
                self.assertEqual((quote["loop_steps"], quote["quote_may_understate"]), (None, True))
                self.assertIn("could not be checked", quote["cost_warning"])
                self.tools.discard_workflow_estimate({"quote_id": quote["quote_id"]})
        self.approve(self.quote())
        self.settle()
        self.assertEqual(len(self.paid), 1)

    def test_status_without_a_recorded_loop_count_reports_unknown_coverage(self):
        quote = self.quote()
        owner = self.runtime.state.model_jobs
        submit = owner.submit_workflow

        def without_count(*args, **kwargs):
            view = submit(*args, **kwargs)
            del view.meta["workflow_loop_steps"]
            return view

        with patch.object(owner, "submit_workflow", side_effect=without_count):
            result = self.approve(quote)
        self.settle()
        self.assertEqual((result["loop_steps"], result["quote_may_understate"]), (None, True))
        status = self.tools.job_status({"job_id": result["local_id"]})
        self.assertEqual((status["loop_steps"], status["quote_may_understate"]), (None, True))
        self.assertEqual(len(self.paid), 1)

    def test_status_after_restart_flags_the_unrecorded_loop_count(self):
        result = self.approve(self.quote())
        self.settle()
        status = self.tools.job_status({"job_id": result["local_id"]})
        self.assertEqual(
            (status["loop_steps"], status["quote_may_understate"], status["cost_warning"]),
            (0, False, None),
        )
        # The saved record keeps the approved quote, not the definition's loop count.
        self.runtime.state.reset()
        status = self.tools.job_status({"job_id": result["local_id"]})
        self.assertEqual(status["cu_cost_exact"], "0.1234567890123456789")
        self.assertEqual((status["loop_steps"], status["quote_may_understate"]), (None, True))
        self.assertIn("could not be checked", status["cost_warning"])
        self.assertEqual(len(self.paid), 1)

    # Waiting workflow steps: projection, decisions and their guards.

    def waiting(self, *nodes, status="in-progress"):
        signed = "https://cdn.example.invalid/render.png?X-Signature=private-signature"
        self.remote_job = {
            "jobId": "workflow-job",
            "jobType": "workflow",
            "status": status,
            "progress": 0.5,
            "createdAt": "2026-10-10T10:56:00.366Z",
            "metadata": {
                "input": {"workflowId": self.workflow["id"]},
                "flow": [
                    {
                        "id": "render",
                        "type": "model",
                        "status": "success",
                        "assets": [{"assetId": "asset-render", "url": signed}],
                    },
                    *nodes,
                ],
            },
        }

    @staticmethod
    def approval(status="processing"):
        return {"id": "check", "type": "user-approval", "status": status, "dependsOn": ["render"]}

    @staticmethod
    def selection(status="processing"):
        return {
            "id": "pick",
            "type": "user-selection",
            "status": status,
            "items": ["asset-a", "asset-b", "asset-c"],
            "inputs": [{"name": "choices", "type": "file_array", "min": 1, "max": 2}],
        }

    def paused_workflow(self, *nodes):
        self.waiting(*nodes)
        result = self.approve(self.quote())
        self.settle()
        return result["local_id"]

    def step(self, local_id, node_id):
        owner = self.runtime.state.model_jobs
        return next(item for item in owner.steps(local_id) if item.node_id == node_id)

    def decide(self, local_id, node_id, action, picks=None, *, context=None):
        record = self.store.get(local_id)
        return self.runtime.decide_workflow_step(
            self.runtime.state.job_context_id if context is None else context,
            local_id,
            record.revision,
            node_id,
            self.step(local_id, node_id).review_id,
            action,
            picks,
        )

    def test_waiting_steps_are_projected_after_polling_without_urls(self):
        local_id = self.paused_workflow(self.approval(), self.selection())
        owner = self.runtime.state.model_jobs
        status = self.tools.job_status({"job_id": local_id})
        self.assertTrue(status["awaiting_decision"])
        self.assertEqual(
            [(row["node_id"], row["type"]) for row in status["pending_steps"]],
            [("check", "user-approval"), ("pick", "user-selection")],
        )
        approval, selection = status["pending_steps"]
        self.assertEqual(approval["review_asset_ids"], ["asset-render"])
        self.assertEqual(approval["actions"], ["approve", "reject"])
        self.assertEqual(selection["items"], ["asset-a", "asset-b", "asset-c"])
        self.assertEqual((selection["min"], selection["max"]), (1, 2))
        self.assertEqual(selection["actions"], ["select", "reject"])
        self.assertIsNone(status["decision_error"])
        self.assertEqual(status["actions"][0], "review_step")
        # A waiting step needs a decision, so the session does not advance it.
        self.assertFalse(status["delivery_active"])
        self.assertFalse(status["delivery_paused"])
        text = json.dumps(status)
        self.assertNotIn("https", text)
        self.assertNotIn("Signature", text)
        self.assertGreater(owner._next_poll[local_id], time.monotonic() + 10)
        started = time.monotonic()
        waited = self.finish(self.tools.wait_for_job({"job_id": local_id, "timeout": 30}))
        self.assertLess(time.monotonic() - started, 5)
        self.assertTrue(waited["awaiting_decision"])
        rows = submodule("blender.job_recovery").result_actions(owner.views[local_id])
        self.assertEqual(
            (rows[0].action, rows[0].label, rows[0].operator),
            ("review_step", "Workflow waits for your decision", None),
        )
        self.assertFalse(self.decisions)
        self.assertEqual(len(self.paid), 1)

    def test_approval_is_sent_once_from_any_scene_and_polling_resumes(self):
        local_id = self.paused_workflow(self.approval())

        def proceed(request):
            self.waiting(self.approval("success"))

        self.decision_reply = proceed
        original = bpy.context.scene
        other = bpy.data.scenes.new("Other decision scene")
        try:
            # Like cancellation, a decision needs no current scene or target.
            bpy.context.window.scene = other
            owner, task = self.decide(local_id, "check", "approve")
            self.assertIn(local_id, owner._commands)
            with self.assertRaisesRegex(Exception, "current job command"):
                self.decide(local_id, "check", "approve")
            task.result(5)
            owner.poll()
        finally:
            bpy.context.window.scene = original
            bpy.data.scenes.remove(other)
        self.assertEqual(len(self.decisions), 1)
        self.assertEqual(self.decisions[0].url.path, "/v1/workflows/fixture-workflow/user-approval")
        self.assertIsNone(self.decisions[0].url.params.get("projectId"))
        self.assertEqual(
            json.loads(self.decisions[0].content),
            {"nodeId": "check", "workflowJobId": "workflow-job", "action": "approve"},
        )
        status = self.tools.job_status({"job_id": local_id})
        self.assertFalse(status["awaiting_decision"])
        self.assertEqual(status["pending_steps"], [])
        self.assertIsNone(status["decision_error"])
        self.assertEqual(status["status"], "remote")
        self.assertTrue(status["delivery_active"])
        self.assertNotIn("review_step", status["actions"])
        self.assertLess(owner._next_poll[local_id], time.monotonic() + 3)
        self.assertEqual(len(self.paid), 1)

    def test_a_decision_in_flight_is_not_reported_as_waiting(self):
        local_id = self.paused_workflow(self.approval())
        entered, release = threading.Event(), threading.Event()

        def hold(request):
            entered.set()
            self.assertTrue(release.wait(5))
            self.waiting(self.approval("success"))

        self.decision_reply = hold
        owner, task = self.decide(local_id, "check", "approve")
        try:
            self.assertTrue(entered.wait(5))
            status = self.tools.job_status({"job_id": local_id})
            self.assertFalse(status["awaiting_decision"])
            self.assertTrue(status["delivery_active"])
            self.assertEqual(status["actions"], ())
            # No recovery control replaces the decision command while it is sent.
            revision = self.store.get(local_id).revision
            for action in ("refresh", "resume"):
                with self.assertRaisesRegex(Exception, "available action changed"):
                    owner.control(local_id, revision, action)
            self.assertIs(owner._commands[local_id][1], task)
            # The wait keeps waiting while the decision is being sent.
            waited = self.finish(self.tools.wait_for_job({"job_id": local_id, "timeout": 0.3}))
            self.assertTrue(waited["delivery_active"])
        finally:
            release.set()
        task.result(5)
        owner.poll()
        self.assertFalse(owner.steps(local_id))
        self.assertEqual(len(self.decisions), 1)

    def test_reject_stops_the_workflow_and_persists_its_cancellation(self):
        local_id = self.paused_workflow(self.selection())

        def stop(request):
            self.waiting(self.selection("rejected"), status="canceled")

        self.decision_reply = stop
        owner, task = self.decide(local_id, "pick", "reject")
        task.result(5)
        owner.poll()
        self.assertEqual(len(self.decisions), 1)
        self.assertEqual(
            json.loads(self.decisions[0].content),
            {"action": "reject", "nodeId": "pick", "workflowJobId": "workflow-job"},
        )
        self.assertEqual(self.store.get(local_id).state.value, "canceled")
        status = self.tools.job_status({"job_id": local_id})
        self.assertEqual(status["status"], "canceled")
        self.assertFalse(status["awaiting_decision"])
        self.assertEqual(owner.steps(local_id), ())
        self.assertEqual(owner.views[local_id].status, "canceled")
        self.assertEqual(len(self.paid), 1)

    def test_selection_sends_ordered_picks(self):
        local_id = self.paused_workflow(self.selection())
        owner, task = self.decide(local_id, "pick", "select", [2, 0])
        task.result(5)
        owner.poll()
        self.assertEqual(
            json.loads(self.decisions[0].content),
            {
                "action": "select",
                "nodeId": "pick",
                "workflowJobId": "workflow-job",
                "selectedIndices": [2, 0],
            },
        )
        self.assertEqual(
            self.decisions[0].url.path, "/v1/workflows/fixture-workflow/user-selection"
        )

    def test_blocked_or_invalid_decisions_send_nothing(self):
        loop = {
            "id": "loop",
            "type": "for-each",
            "status": "pending",
            "inputs": [{"name": "items", "ref": {"node": "pick"}}],
        }
        local_id = self.paused_workflow(self.selection(), loop)
        status = self.tools.job_status({"job_id": local_id})
        self.assertEqual(status["pending_steps"][0]["blocked"], "loop")
        self.assertEqual(status["pending_steps"][0]["actions"], ["reject"])
        with self.assertRaisesRegex(Exception, "ForEach loop"):
            self.decide(local_id, "pick", "select", [0])
        record = self.store.get(local_id)
        review = self.step(local_id, "pick").review_id
        context = self.runtime.state.job_context_id
        for args, message in (
            ((local_id, record.revision, "pick", "0" * 64, "reject"), "step changed"),
            ((local_id, record.revision + 1, "pick", review, "reject"), "job changed"),
            ((local_id, record.revision, "pick", review, "approve"), "decision this workflow"),
        ):
            with self.subTest(args=args), self.assertRaisesRegex(Exception, message):
                self.runtime.decide_workflow_step(context, *args)
        with self.assertRaisesRegex(Exception, "job context changed"):
            self.decide(local_id, "pick", "reject", context="stale-context")
        with patch.object(self.runtime.state.model_jobs, "_online", return_value=False):
            with self.assertRaisesRegex(Exception, "Allow Online Access"):
                self.decide(local_id, "pick", "reject")
        self.assertFalse(self.decisions)
        self.assertNotIn(local_id, self.runtime.state.model_jobs._commands)

    def test_refused_decision_is_reported_without_pausing_delivery(self):
        local_id = self.paused_workflow(self.approval())

        def refuse(request):
            self.waiting(self.approval("success"))
            return httpx.Response(400, json={"message": "private detail"})

        self.decision_reply = refuse
        owner, task = self.decide(local_id, "check", "approve")
        with self.assertRaisesRegex(Exception, "refused this decision"):
            task.result(5)
        # The owner drains the same completion and reports it without raising.
        owner.poll()
        status = self.tools.job_status({"job_id": local_id})
        self.assertTrue(status["decision_error"].startswith("Scenario refused this decision"))
        self.assertNotIn("private", status["decision_error"])
        self.assertFalse(status["delivery_paused"])
        self.assertFalse(status["awaiting_decision"])
        self.assertEqual(status["status"], "remote")
        self.assertEqual(len(self.decisions), 1)

    def test_restarted_jobs_show_steps_only_after_explicit_refresh(self):
        local_id = self.paused_workflow(self.approval())
        self.runtime.state.reset()
        count = len(self.calls)
        owner = self.runtime.ensure_model_jobs()
        owner.inspect()
        status = self.tools.job_status({"job_id": local_id})
        self.assertFalse(status["awaiting_decision"])
        self.assertTrue(status["delivery_paused"])
        self.assertEqual(len(self.calls), count)
        record = self.store.get(local_id)
        _, task = self.runtime.control_model_job(
            self.runtime.state.job_context_id, local_id, record.revision, "refresh"
        )
        task.result(5)
        owner.poll()
        self.assertEqual([step.node_id for step in owner.steps(local_id)], ["check"])
        owner, task = self.decide(local_id, "check", "approve")
        self.assertNotIn(local_id, owner._paused)
        task.result(5)
        owner.poll()
        self.assertEqual(len(self.decisions), 1)
        self.assertEqual(len(self.paid), 1)

    def test_project_switch_retires_waiting_steps_and_decisions(self):
        local_id = self.paused_workflow(self.approval())
        context = self.runtime.state.job_context_id
        review = self.step(local_id, "check").review_id
        revision = self.store.get(local_id).revision
        self.prefs.project_id = "another-project"
        self.project = "another-project"
        with self.assertRaisesRegex(Exception, "context changed"):
            self.runtime.decide_workflow_step(
                context, local_id, revision, "check", review, "approve"
            )
        owner = self.runtime.ensure_model_jobs()
        self.assertEqual(owner.steps(), {})
        self.assertFalse(self.decisions)

    # Live job flows list links only on selections; the definition read with
    # SDK workflows.retrieve supplies the rest, and its absence fails closed.

    def live_definition(self, *flow):
        render = {"id": "render", "type": "model", "inputs": [{"name": "p", "type": "string"}]}
        self.workflow["flow"] = [render, *flow]
        self.workflow["updatedAt"] = "2026-10-10T10:23:21.000Z"

    def definition_reads(self):
        """Workflow reads after the first job retrieval; quoting reads it before."""
        first = next(index for index, item in enumerate(self.calls) if "/jobs/" in item.url.path)
        return [
            request
            for request in self.calls[first:]
            if (request.method, request.url.path) == ("GET", "/v1/workflows/fixture-workflow")
        ]

    def live_selection(self):
        selection = self.selection()
        selection["inputs"][0]["ref"] = {"node": "workflow", "name": "prompt"}
        return selection

    def test_a_live_selection_into_a_loop_without_its_definition_offers_only_reject(self):
        loop = {"id": "loop", "type": "for-each", "status": "pending"}
        local_id = self.paused_workflow(self.live_selection(), loop)
        (step,) = self.tools.job_status({"job_id": local_id})["pending_steps"]
        self.assertEqual(step["blocked"], "unverified")
        self.assertEqual(step["actions"], ["reject"])
        self.assertFalse(step["links_complete"])
        # The definition lacks a flow, so it was read and not trusted.
        self.assertEqual(len(self.definition_reads()), 1)
        with self.assertRaisesRegex(Exception, "could not read how this workflow"):
            self.decide(local_id, "pick", "select", [0])
        self.assertFalse(self.decisions)

        def stop(request):
            self.waiting(self.live_selection() | {"status": "rejected"}, status="canceled")

        self.decision_reply = stop
        owner, task = self.decide(local_id, "pick", "reject")
        task.result(5)
        owner.poll()
        self.assertEqual(json.loads(self.decisions[0].content)["action"], "reject")
        self.assertEqual(self.store.get(local_id).state.value, "canceled")
        self.assertEqual(len(self.paid), 1)

    def test_the_definition_proves_a_live_selection_feeds_a_loop(self):
        self.live_definition(
            {
                "id": "pick",
                "type": "user-selection",
                "inputs": [{"name": "choices", "type": "file_array", "ref": {"node": "workflow"}}],
            },
            {
                "id": "loop",
                "type": "for-each",
                "loopBodyNodeIds": [],
                "inputs": [{"name": "items", "ref": {"node": "pick"}}],
            },
        )
        loop = {"id": "loop", "type": "for-each", "status": "pending"}
        local_id = self.paused_workflow(self.live_selection(), loop)
        (step,) = self.tools.job_status({"job_id": local_id})["pending_steps"]
        self.assertEqual((step["blocked"], step["actions"]), ("loop", ["reject"]))
        self.assertTrue(step["links_complete"])
        with self.assertRaisesRegex(Exception, "ForEach loop"):
            self.decide(local_id, "pick", "select", [0])
        self.assertFalse(self.decisions)

    def test_a_live_selection_after_a_loop_is_offered_with_its_definition(self):
        self.live_definition(
            {
                "id": "loop",
                "type": "for-each",
                "loopBodyNodeIds": ["cut"],
                "inputs": [{"name": "items", "ref": {"node": "workflow"}}],
            },
            {"id": "cut", "type": "model", "inputs": [{"name": "i", "ref": {"node": "loop"}}]},
            {
                "id": "pick",
                "type": "user-selection",
                "inputs": [{"name": "choices", "type": "file_array", "ref": {"node": "workflow"}}],
            },
            {"id": "grid", "type": "model", "inputs": [{"name": "i", "ref": {"node": "pick"}}]},
        )
        local_id = self.paused_workflow(
            {"id": "loop", "type": "for-each", "status": "success"},
            {"id": "cut", "type": "model", "status": "skipped"},
            {"id": "cut__iter__0", "type": "model", "status": "success"},
            self.live_selection(),
            {"id": "grid", "type": "model", "status": "pending"},
        )
        (step,) = self.tools.job_status({"job_id": local_id})["pending_steps"]
        self.assertEqual((step["blocked"], step["actions"]), (None, ["select", "reject"]))
        owner, task = self.decide(local_id, "pick", "select", [2, 0])
        task.result(5)
        owner.poll()
        self.assertEqual(json.loads(self.decisions[0].content)["selectedIndices"], [2, 0])
        self.assertEqual(len(self.definition_reads()), 1)

    def test_a_live_approval_lists_its_definition_review_assets(self):
        self.live_definition({"id": "check", "type": "user-approval", "dependsOn": ["render"]})
        local_id = self.paused_workflow(
            {"id": "check", "type": "user-approval", "status": "processing"}
        )
        (step,) = self.tools.job_status({"job_id": local_id})["pending_steps"]
        self.assertEqual(step["depends_on"], ["render"])
        self.assertEqual(step["review_asset_ids"], ["asset-render"])
        self.assertTrue(step["links_complete"])
        self.assertEqual(step["actions"], ["approve", "reject"])
        self.assertNotIn("https", json.dumps(step))
        self.assertEqual(len(self.definition_reads()), 1)

    # Local MCP workflow step tools: the same projection and decision entry.

    def job_reads(self):
        return sum(1 for request in self.calls if "/jobs/" in request.url.path)

    def step_args(self, local_id, **changes):
        return {
            "context_id": self.tools.list_local_jobs({})["context_id"],
            "request_id": local_id,
            **changes,
        }

    def mcp_decide(self, local_id, node_id, action, picks=None, **changes):
        steps = self.finish(self.tools.workflow_job_steps(self.step_args(local_id)))
        step = next(row for row in steps["steps"] if row["node_id"] == node_id)
        args = self.step_args(
            local_id,
            expected_revision=steps["revision"],
            node_id=node_id,
            review_id=step["review_id"],
            action=action,
        )
        if picks is not None:
            args["selected_indices"] = picks
        return self.finish(self.tools.decide_workflow_step({**args, **changes}))

    def test_mcp_steps_are_read_again_without_changing_delivery(self):
        local_id = self.paused_workflow(self.approval(), self.selection())
        owner = self.runtime.state.model_jobs
        reads = self.job_reads()
        pending = self.tools.workflow_job_steps(self.step_args(local_id))
        self.assertIn(local_id, owner._commands)
        result = self.finish(pending)
        self.assertEqual(self.job_reads(), reads + 1)
        record = self.store.get(local_id)
        self.assertEqual(result["request_id"], local_id)
        self.assertEqual(result["workflow_id"], self.workflow["id"])
        self.assertEqual((result["revision"], result["state"]), (record.revision, "remote"))
        self.assertEqual(result["cu_cost_exact"], "0.1234567890123456789")
        self.assertTrue(result["awaiting_decision"])
        self.assertEqual([row["node_id"] for row in result["steps"]], ["check", "pick"])
        approval, selection = result["steps"]
        self.assertEqual(approval["review_asset_ids"], ["asset-render"])
        self.assertEqual(selection["items"], ["asset-a", "asset-b", "asset-c"])
        self.assertEqual(selection["actions"], ["select", "reject"])
        self.assertIsNone(selection["blocked_reason"])
        # The same projection as job_status, plus the blocked explanation only.
        status = self.tools.job_status({"job_id": local_id})
        self.assertEqual(
            [{**row, "blocked_reason": None} for row in status["pending_steps"]], result["steps"]
        )
        text = json.dumps(result)
        self.assertNotIn("https", text)
        self.assertNotIn("Signature", text)
        # Reading keeps an automatically polled job polled.
        self.assertFalse(result["delivery_paused"])
        self.assertNotIn(local_id, owner._paused)
        # An automatic refresh already in flight is awaited, not repeated.
        owner._next_poll[local_id] = 0.0
        owner.poll()
        _, automatic = owner._commands[local_id]
        _, task = self.runtime.read_workflow_steps(self.runtime.state.job_context_id, local_id)
        self.assertIs(task, automatic)
        task.result(5)
        owner.poll()
        self.assertEqual(self.job_reads(), reads + 2)
        self.assertFalse(self.decisions)
        self.assertEqual(len(self.paid), 1)

    def test_mcp_steps_after_restart_keep_the_job_paused_until_a_decision(self):
        local_id = self.paused_workflow(self.approval())
        self.runtime.state.reset()
        owner = self.runtime.ensure_model_jobs()
        result = self.finish(self.tools.workflow_job_steps(self.step_args(local_id)))
        self.assertEqual([row["node_id"] for row in result["steps"]], ["check"])
        self.assertTrue(result["awaiting_decision"])
        # Reading neither resumes polling nor downloads anything.
        self.assertTrue(result["delivery_paused"])
        self.assertIn(local_id, owner._paused)

        def proceed(request):
            self.waiting(self.approval("success"))

        self.decision_reply = proceed
        decided = self.mcp_decide(local_id, "check", "approve")
        self.assertEqual(decided["outcome"], "applied")
        self.assertFalse(decided["delivery_paused"])
        self.assertNotIn(local_id, owner._paused)
        self.assertEqual(len(self.decisions), 1)
        self.assertEqual(len(self.paid), 1)

    def test_mcp_decisions_report_each_outcome(self):
        def accept(request):
            self.waiting(self.approval("success"))

        def refuse(request):
            self.waiting(self.approval("success"))
            return httpx.Response(409, json={"message": "private detail"})

        def unavailable(request):
            return httpx.Response(503, json={"message": "private detail"})

        def lost(request):
            raise httpx.ReadTimeout("private fixture timeout", request=request)

        for reply, outcome, error in (
            (accept, "applied", None),
            (refuse, "refused", "Scenario refused this decision"),
            (unavailable, "uncertain", "Decision outcome unknown"),
            (lost, "uncertain", "Decision outcome unknown"),
        ):
            with self.subTest(outcome=outcome, reply=reply.__name__):
                self.decision_reply = None
                local_id = self.paused_workflow(self.approval())
                sent = len(self.decisions)
                self.decision_reply = reply
                result = self.mcp_decide(local_id, "check", "approve")
                self.assertEqual(result["outcome"], outcome)
                self.assertIn(result["outcome"], submodule("blender.model_jobs").DECISION_OUTCOMES)
                self.assertEqual(len(self.decisions), sent + 1)
                if error is None:
                    self.assertIsNone(result["decision_error"])
                    self.assertEqual(result["steps"], [])
                    self.assertIn("accepted", result["note"])
                else:
                    self.assertTrue(result["decision_error"].startswith(error))
                    self.assertNotIn("private", json.dumps(result))
                if outcome == "uncertain":
                    self.assertIn("Never repeat it", result["note"])
                self.assertFalse(result["delivery_paused"])
                self.assertEqual(result["state"], "remote")

    def test_mcp_decision_for_a_job_finished_meanwhile_is_not_sent(self):
        local_id = self.paused_workflow(self.approval())
        steps = self.finish(self.tools.workflow_job_steps(self.step_args(local_id)))
        self.waiting(self.approval("failure"), status="failure")
        result = self.finish(
            self.tools.decide_workflow_step(
                self.step_args(
                    local_id,
                    expected_revision=steps["revision"],
                    node_id="check",
                    review_id=steps["steps"][0]["review_id"],
                    action="approve",
                )
            )
        )
        self.assertEqual(result["outcome"], "not_sent")
        self.assertEqual(result["state"], "failed")
        self.assertEqual(result["steps"], [])
        self.assertIn("Nothing was sent", result["note"])
        self.assertFalse(self.decisions)

    def test_mcp_selection_keeps_the_given_order_and_reject_stops_the_workflow(self):
        local_id = self.paused_workflow(self.selection())
        result = self.mcp_decide(local_id, "pick", "select", [2, 0])
        self.assertEqual(result["outcome"], "applied")
        self.assertEqual(json.loads(self.decisions[0].content)["selectedIndices"], [2, 0])
        local_id = self.paused_workflow(self.selection())

        def stop(request):
            self.waiting(self.selection("rejected"), status="canceled")

        self.decision_reply = stop
        result = self.mcp_decide(local_id, "pick", "reject")
        self.assertEqual(result["outcome"], "applied")
        self.assertEqual(result["state"], "canceled")
        self.assertFalse(result["awaiting_decision"])
        self.assertEqual(self.store.get(local_id).state.value, "canceled")
        self.assertEqual(
            json.loads(self.decisions[1].content),
            {"action": "reject", "nodeId": "pick", "workflowJobId": "workflow-job"},
        )

    def test_mcp_invalid_or_stale_decisions_are_refused_before_any_request(self):
        loop = {
            "id": "loop",
            "type": "for-each",
            "status": "pending",
            "inputs": [{"name": "items", "ref": {"node": "pick"}}],
        }
        blocked = self.paused_workflow(self.selection(), loop)
        steps = self.finish(self.tools.workflow_job_steps(self.step_args(blocked)))
        self.assertEqual(steps["steps"][0]["blocked"], "loop")
        self.assertEqual(steps["steps"][0]["actions"], ["reject"])
        self.assertIn("ForEach loop", steps["steps"][0]["blocked_reason"])
        with self.assertRaisesRegex(Exception, "ForEach loop"):
            self.tools.decide_workflow_step(
                self.step_args(
                    blocked,
                    expected_revision=steps["revision"],
                    node_id="pick",
                    review_id=steps["steps"][0]["review_id"],
                    action="select",
                    selected_indices=[0],
                )
            )
        local_id = self.paused_workflow(self.selection())
        steps = self.finish(self.tools.workflow_job_steps(self.step_args(local_id)))
        review = steps["steps"][0]["review_id"]
        valid = self.step_args(
            local_id,
            expected_revision=steps["revision"],
            node_id="pick",
            review_id=review,
            action="select",
            selected_indices=[0],
        )
        cases = (
            ({"selected_indices": [0, 1, 2]}, "Select 1 to 2 items"),
            ({"selected_indices": []}, "Select 1 to 2 items"),
            ({"selected_indices": [3]}, "listed candidates"),
            ({"selected_indices": [0, 0]}, "at most once"),
            ({"selected_indices": [True]}, "integer indices"),
            ({"selected_indices": None}, "list of indices"),
            ({"action": "approve"}, "decision this workflow"),
            ({"action": "reject"}, "Only a selection"),
            ({"review_id": "0" * 64}, "step changed"),
            ({"node_id": "missing"}, "step changed"),
            ({"expected_revision": steps["revision"] + 1}, "job changed"),
            ({"expected_revision": True}, "nonnegative integer"),
            ({"action": "cancel"}, "approve, select or reject"),
            ({"context_id": "stale-context"}, "context changed"),
            ({"request_id": ""}, "returned by list_local_jobs"),
            ({"review_id": 7}, "returned by workflow_job_steps"),
        )
        for changes, message in cases:
            with self.subTest(changes=changes), self.assertRaisesRegex(Exception, message):
                self.tools.decide_workflow_step({**valid, **changes})
        with patch.object(self.runtime.state.model_jobs, "_online", return_value=False):
            with self.assertRaisesRegex(Exception, "Allow Online Access"):
                self.tools.decide_workflow_step(valid)
            with self.assertRaisesRegex(Exception, "Allow Online Access"):
                self.tools.workflow_job_steps(self.step_args(local_id))
        self.assertFalse(self.decisions)
        self.assertNotIn(local_id, self.runtime.state.model_jobs._commands)

    def test_mcp_steps_reject_other_jobs_and_read_nothing_for_finished_ones(self):
        local_id = self.paused_workflow(self.approval())
        reads = self.job_reads()
        for args, message in (
            ({"request_id": "unknown-request"}, "Only saved workflow jobs"),
            ({"context_id": "stale-context"}, "context changed"),
            ({"context_id": ""}, "returned by list_local_jobs"),
        ):
            with self.subTest(args=args), self.assertRaisesRegex(Exception, message):
                self.tools.workflow_job_steps(self.step_args(local_id, **args))
        self.assertEqual(self.job_reads(), reads)
        # A failed job settles without a download, so no other read can follow.
        self.waiting(self.approval("failure"), status="failure")
        self.finish(self.tools.workflow_job_steps(self.step_args(local_id)))
        reads = self.job_reads()
        self.assertEqual(self.store.get(local_id).state.value, "failed")
        result = self.tools.workflow_job_steps(self.step_args(local_id))
        self.assertIsInstance(result, dict)
        self.assertEqual((result["state"], result["steps"]), ("failed", []))
        self.assertFalse(result["awaiting_decision"])
        self.assertEqual(self.job_reads(), reads)

    def test_workflow_cancel_explains_rejection_and_sends_nothing(self):
        local_id = self.paused_workflow()
        running = self.store.get(local_id)
        owner = self.runtime.state.model_jobs
        calls = len(self.calls)
        args = self.step_args(local_id, expected_revision=running.revision, action="cancel")
        with self.assertRaisesRegex(Exception, "cannot cancel a running workflow") as caught:
            self.tools.recover_local_job(args)
        self.assertIn("decide_workflow_step with action reject", str(caught.exception))
        self.assertIn("Nothing was sent", str(caught.exception))
        self.assertEqual(len(self.calls), calls)
        # Native callers share the typed explanation, also for a waiting step.
        self.waiting(self.approval())
        owner._next_poll[local_id] = 0.0
        self.settle()
        self.assertTrue(owner.steps(local_id))
        model_jobs = submodule("blender.model_jobs")
        calls = len(self.calls)
        for revision in (running.revision, running.revision + 1):
            with self.subTest(revision=revision):
                with self.assertRaises(model_jobs.WorkflowCancelUnavailable):
                    owner.control(local_id, revision, "cancel")
        self.assertEqual(len(self.calls), calls)
        self.assertNotIn(local_id, owner._commands)
        self.assertEqual(self.store.get(local_id), running)
        self.assertFalse(self.decisions)

    def test_mcp_and_native_decisions_share_one_projection(self):
        local_id = self.paused_workflow(self.approval())

        def refuse(request):
            self.waiting(self.approval("success"))
            return httpx.Response(400, json={"message": "private detail"})

        # A native decision's refusal is what MCP then reports.
        self.decision_reply = refuse
        owner, task = self.decide(local_id, "check", "approve")
        with self.assertRaisesRegex(Exception, "refused this decision"):
            task.result(5)
        owner.poll()
        result = self.finish(self.tools.workflow_job_steps(self.step_args(local_id)))
        self.assertTrue(result["decision_error"].startswith("Scenario refused this decision"))
        self.assertEqual(result["steps"], [])
        # An MCP decision is what the native projection and rows then show.
        self.decision_reply = None
        local_id = self.paused_workflow(self.approval())
        rows = submodule("blender.job_recovery").result_actions(owner.views[local_id])
        self.assertEqual(rows[0].action, "review_step")

        def accept(request):
            self.waiting(self.approval("success"))

        self.decision_reply = accept
        self.assertEqual(self.mcp_decide(local_id, "check", "approve")["outcome"], "applied")
        self.assertEqual(owner.steps(local_id), ())
        rows = submodule("blender.job_recovery").result_actions(owner.views[local_id])
        self.assertNotIn("review_step", [row.action for row in rows])
        self.assertEqual(len(self.decisions), 2)

    def test_context_change_during_an_mcp_decision_reports_its_outcome(self):
        local_id = self.paused_workflow(self.approval())
        steps = self.finish(self.tools.workflow_job_steps(self.step_args(local_id)))
        pending = self.tools.decide_workflow_step(
            self.step_args(
                local_id,
                expected_revision=steps["revision"],
                node_id="check",
                review_id=steps["steps"][0]["review_id"],
                action="reject",
            )
        )
        pending.run()
        self.prefs.project_id = "another-project"
        self.project = "another-project"
        with self.assertRaisesRegex(Exception, r"outcome: applied\); never repeat"):
            pending.finish(None)
        self.assertEqual(len(self.decisions), 1)
