# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Blockout plans share exact SDK quotes, durable submission and guarded delivery."""

import json
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import bpy
import httpx
from helpers import FIXTURES, online_access, reset_scene, submodule, temp_credentials


class BlockoutJobsTests(unittest.TestCase):
    def setUp(self):
        reset_scene()
        self.runtime = submodule("blender.runtime")
        self.blockout = submodule("blender.blockout")
        self.facade = submodule("blender.blockout_jobs")
        self.mcp = submodule("mcp.tools_scenario")
        self.storage = submodule("core.jobs.store")
        self.enterContext(patch.object(self.runtime, "state", self.runtime.RuntimeState()))
        self.enterContext(online_access(True))
        self.enterContext(temp_credentials())
        directory = Path(
            self.enterContext(tempfile.TemporaryDirectory(dir=bpy.utils.resource_path("USER")))
        )
        self.enterContext(
            patch.object(
                self.runtime,
                "paths",
                return_value=SimpleNamespace(
                    state_dir=directory, registry_file=directory / "jobs.json"
                ),
            )
        )
        self.model = json.loads((FIXTURES / "models/model_scenario-llm.json").read_text())["model"]
        self.calls, self.paid, self.sessions = [], [], []
        self.lose_response, self.fail_read = False, False
        self.result_text = json.dumps(
            [
                {
                    "name": "Test tower",
                    "category": "structure",
                    "primitive": "box",
                    "position": [1, 2, 3],
                    "size": [2, 2, 6],
                    "rotation": 0,
                    "group": "Buildings",
                }
            ]
        )
        api = submodule("core.api.sdk_adapter")
        catalog, session = self.runtime.SDKCatalog, self.runtime.JobSession

        def respond(request):
            self.assertIsNot(threading.current_thread(), threading.main_thread())
            self.calls.append(request)
            self.assertNotIn("projectId", request.url.params)
            if request.method == "GET":
                if "/jobs/" in request.url.path:
                    return httpx.Response(
                        200,
                        json={
                            "job": {
                                "jobId": request.url.path.rsplit("/", 1)[-1],
                                "status": "success",
                                "jobType": "custom",
                                "metadata": {"assetIds": ["asset_plan"]},
                            }
                        },
                    )
                if "/assets/" in request.url.path:
                    if self.fail_read:
                        return httpx.Response(503)
                    return httpx.Response(
                        200,
                        json={
                            "asset": {
                                "id": "asset_plan",
                                "status": "success",
                                "kind": "text",
                                "mimeType": "text/plain",
                                "properties": {
                                    "size": len(self.result_text.encode()),
                                    "preview": self.result_text,
                                    "hasFullPreview": True,
                                },
                            }
                        },
                    )
                return httpx.Response(200, json={"model": self.model})
            self.assertEqual(request.url.path, "/v1/generate/custom/model_scenario-llm")
            if request.url.params.get("dryRun") == "true":
                return httpx.Response(269, content=b'{"creativeUnitsCost":0.1234567890123456789}')
            self.assertTrue(
                any(
                    row.state == self.storage.JobState.SUBMITTING
                    for row in self.runtime.state.job_store.records()
                )
            )
            self.paid.append(request)
            if self.lose_response:
                raise httpx.ReadTimeout("private response detail", request=request)
            return httpx.Response(200, json={"job": {"jobId": f"remote-{len(self.paid)}"}})

        def adapter(credentials, **options):
            return api.SDKAdapter(credentials, transport=httpx.MockTransport(respond), **options)

        def create_session(*args, **options):
            value = session(*args, **options)
            self.sessions.append(value)
            return value

        self.enterContext(
            patch.object(
                self.runtime,
                "SDKCatalog",
                side_effect=lambda *a, **k: catalog(*a, adapter_factory=adapter, **k),
            )
        )
        self.enterContext(patch.object(self.runtime, "JobSession", side_effect=create_session))
        self.scene = bpy.context.scene
        self.scene.scenario_blockout.prompt = "A stone tower"

    def tearDown(self):
        for session in self.sessions:
            session.shutdown()
        self.runtime.state.reset()

    def jobs(self):
        return self.runtime.ensure_blockout_jobs()

    def advance(self, item):
        for _ in range(12):
            if item.task is not None:
                try:
                    item.task.result(5)
                except Exception:
                    # The facade must consume and report the failed task below.
                    pass
            item.next_poll = 0
            self.jobs().poll()
            if item.phase in {"READY", "DONE", "ERROR"}:
                return
        self.fail(f"Blockout did not finish: {item.phase}")

    def quote(self):
        self.assertEqual(bpy.ops.scenario.blockout_design(), {"FINISHED"})
        item = self.jobs().current(self.scene)
        self.advance(item)
        self.assertEqual(item.phase, "READY", item.error)
        return item

    def approve(self, item):
        return bpy.ops.scenario.blockout_approve(quote_id=item.identifier, approved_cost=item.cost)

    def test_native_approval_saves_one_plan_without_automatic_geometry(self):
        item = self.quote()
        self.assertEqual(self.paid, [])
        self.assertEqual(item.cost, "0.1234567890123456789")
        objects = tuple(bpy.data.objects)
        self.assertEqual(self.approve(item), {"FINISHED"})
        self.advance(item)
        self.assertEqual(item.phase, "DONE", item.error)
        self.assertEqual(len(self.paid), 1)
        self.assertEqual(tuple(bpy.data.objects), objects)
        self.assertEqual(
            json.loads(self.scene.scenario_blockout.plan_json), json.loads(self.result_text)
        )
        self.assertEqual(self.approve(item), {"CANCELLED"})
        self.assertEqual(len(self.paid), 1)
        self.assertEqual(bpy.ops.scenario.blockout_build(), {"FINISHED"})
        self.assertIn("Test tower", bpy.data.objects)

    def test_mcp_uses_same_quote_and_native_delivery(self):
        deferred = self.mcp.estimate_blockout({"action": "DESIGN"})
        value = deferred.finish(deferred.run())
        self.assertEqual(value["cu_cost_exact"], "0.1234567890123456789")
        self.mcp.approve_blockout(
            {"quote_id": value["quote_id"], "approved_cost": value["cu_cost_exact"]}
        )
        item = self.jobs().actions[value["quote_id"]]
        self.advance(item)
        self.assertEqual(item.phase, "DONE")
        self.assertEqual(len(self.paid), 1)

    def test_changed_inputs_and_rounded_cost_cannot_spend(self):
        for name, value in [
            ("prompt", "new"),
            ("refine", "new"),
            ("scene_type", "interior"),
            ("scale", "room"),
            ("plan_json", "[]"),
        ]:
            with self.subTest(name=name):
                item = self.quote()
                setattr(self.scene.scenario_blockout, name, value)
                self.assertEqual(self.approve(item), {"CANCELLED"})
                setattr(
                    self.scene.scenario_blockout,
                    name,
                    item.binding[
                        ("prompt", "refine", "scene_type", "scale", "plan_json").index(name)
                    ],
                )
        item = self.quote()
        self.assertEqual(
            bpy.ops.scenario.blockout_approve(quote_id=item.identifier, approved_cost="0.123"),
            {"CANCELLED"},
        )
        self.assertEqual(self.paid, [])

    def test_late_result_does_not_overwrite_edited_plan(self):
        item = self.quote()
        self.approve(item)
        self.scene.scenario_blockout.plan_json = '[{"name":"User plan"}]'
        self.advance(item)
        self.assertEqual(item.phase, "ERROR")
        self.assertEqual(self.scene.scenario_blockout.plan_json, '[{"name":"User plan"}]')
        self.assertEqual(len(self.paid), 1)

    def test_uncertain_submission_is_saved_and_never_retried(self):
        self.lose_response = True
        item = self.quote()
        self.approve(item)
        self.advance(item)
        self.assertEqual(item.phase, "ERROR")
        self.assertEqual(
            self.runtime.state.job_store.get(item.request_id).state, self.storage.JobState.UNCERTAIN
        )
        self.assertEqual(self.approve(item), {"CANCELLED"})
        self.assertEqual(bpy.ops.scenario.blockout_design(), {"CANCELLED"})
        self.assertEqual(len(self.paid), 1)

    def test_refinement_quotes_the_complete_current_plan(self):
        previous = [
            {"name": "Long named element " + str(i), "group": "Building group " + str(i)}
            for i in range(100)
        ]
        self.scene.scenario_blockout.plan_json = json.dumps(previous)
        self.scene.scenario_blockout.refine = "Add a doorway"
        self.assertEqual(bpy.ops.scenario.blockout_refine(), {"FINISHED"})
        item = self.jobs().current(self.scene)
        self.advance(item)
        self.assertEqual(item.phase, "READY")
        quoted = next(call for call in self.calls if call.method == "POST")
        instruction = json.loads(quoted.content)["instruction"]
        self.assertIn("Long named element 99", instruction)
        self.assertIn("Add a doorway", instruction)
        self.assertNotIn("Scene to block out:", instruction)
        self.assertIn("UPDATED full plan applying this change: Add a doorway", instruction)
        self.assertEqual(len(json.loads(instruction.split("\nCurrent plan:\n")[1])), 100)
        self.assertEqual(self.paid, [])

    def test_truncated_or_non_array_plan_preserves_previous_plan(self):
        for text in ['[{"name":"Partial"},', "{}", "[{}, 2]"]:
            with self.subTest(text=text):
                self.result_text = text
                item = self.quote()
                self.approve(item)
                self.advance(item)
                self.assertEqual(item.phase, "ERROR")
                self.assertEqual(self.scene.scenario_blockout.plan_json, "")

    def test_restart_can_read_saved_text_without_spending_or_scene_mutation(self):
        item = self.quote()
        self.approve(item)
        self.advance(item)
        request = item.request_id
        self.runtime.state.reset()
        self.scene.scenario_blockout.plan_json = ""
        context, records = self.runtime.local_job_recovery()
        record = next(row.record for row in records if row.record.intent.request_id == request)
        deferred = self.mcp.read_model_text(
            {
                "context_id": context,
                "request_id": request,
                "expected_revision": record.revision,
                "asset_id": "asset_plan",
            }
        )
        result = deferred.finish(deferred.run())
        self.assertEqual(result["text"], self.result_text)
        self.assertEqual(self.scene.scenario_blockout.plan_json, "")
        self.assertEqual(len(self.paid), 1)

    def test_retired_context_cannot_approve(self):
        item = self.quote()
        self.runtime.state.reset()
        self.assertEqual(self.approve(item), {"CANCELLED"})
        self.assertEqual(self.paid, [])

    def test_offline_approval_is_rejected_without_spending(self):
        item = self.quote()
        with online_access(False):
            with self.assertRaises(RuntimeError):
                self.approve(item)
        self.assertEqual(self.paid, [])

    def test_scene_switch_cannot_approve_or_receive_late_plan(self):
        item = self.quote()
        other = bpy.data.scenes.new("Other plan scene")
        bpy.context.window.scene = other
        self.assertEqual(self.approve(item), {"CANCELLED"})
        bpy.context.window.scene = self.scene
        item = self.quote()
        self.approve(item)
        item.task.result(5)
        bpy.context.window.scene = other
        self.advance(item)
        self.assertEqual(item.phase, "ERROR")
        self.assertEqual(other.scenario_blockout.plan_json, "")
        self.assertEqual(self.scene.scenario_blockout.plan_json, "")
        self.assertEqual(len(self.paid), 1)

    def test_failed_text_read_keeps_one_saved_job_for_read_only_recovery(self):
        item = self.quote()
        self.approve(item)
        self.fail_read = True
        self.advance(item)
        self.assertEqual(item.phase, "ERROR")
        record = self.runtime.state.job_store.get(item.request_id)
        self.assertEqual(record.state, self.storage.JobState.SUCCEEDED)
        self.fail_read = False
        deferred = self.mcp.read_model_text(
            {
                "context_id": self.runtime.state.job_context_id,
                "request_id": item.request_id,
                "expected_revision": record.revision,
                "asset_id": "asset_plan",
            }
        )
        self.assertEqual(deferred.finish(deferred.run())["text"], self.result_text)
        self.assertEqual(len(self.paid), 1)
        self.assertEqual(self.scene.scenario_blockout.plan_json, "")

    def test_drawing_ready_approval_does_not_submit_or_change_inputs(self):
        from unittest.mock import MagicMock

        item = self.quote()
        before = self.facade.binding(self.scene)
        calls = len(self.calls)
        layout = MagicMock()
        self.blockout.draw_status(layout, self.scene)
        self.assertEqual(self.facade.binding(self.scene), before)
        self.assertEqual(len(self.calls), calls)
        op = layout.row.return_value.operator.return_value
        self.assertEqual(op.quote_id, item.identifier)
        self.assertEqual(op.approved_cost, item.cost)
