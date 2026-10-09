# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Blockout plans share exact SDK quotes, durable submission and guarded delivery."""

import json
import tempfile
import threading
import unittest
from concurrent.futures import Future
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
        self.hold_quotes, self.held_quotes = None, threading.Semaphore(0)
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
            if self.hold_quotes is not None and request.url.params.get("dryRun") == "true":
                # A held price request of any kind occupies a shared worker.
                self.held_quotes.release()
                self.hold_quotes.wait(5)
                return httpx.Response(269, content=b'{"creativeUnitsCost":0.1234567890123456789}')
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

    def test_wrapped_complete_plan_delivers_without_resubmission_or_geometry(self):
        plan = self.result_text
        for wrapper in ("```json\n{}\n```", "Here is the plan:\n{}\nDone."):
            with self.subTest(wrapper=wrapper):
                self.result_text = wrapper.format(plan)
                objects, paid = tuple(bpy.data.objects), len(self.paid)
                item = self.quote()
                self.assertEqual(self.approve(item), {"FINISHED"})
                self.advance(item)
                self.assertEqual(item.phase, "DONE", item.error)
                self.assertEqual(
                    json.loads(self.scene.scenario_blockout.plan_json), json.loads(plan)
                )
                self.assertEqual(tuple(bpy.data.objects), objects)
                self.assertEqual(len(self.paid), paid + 1)
                self.assertEqual(self.approve(item), {"CANCELLED"})
                self.assertEqual(len(self.paid), paid + 1)

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

    def test_native_cancellation_of_queued_request_reports_cancellation(self):
        state = self.storage.JobState
        item = self.quote()
        self.hold_quotes = threading.Event()
        self.addCleanup(self.hold_quotes.set)
        # Two pending prompt price requests in the same scene occupy both shared
        # workers; switching scenes would retire the Blockout quote.
        for lane in ("video", "audio"):
            self.runtime.ensure_prompt_jobs().quote(self.scene, lane, "GENERATE")
            self.assertTrue(self.held_quotes.acquire(timeout=5))
        plan = self.scene.scenario_blockout.plan_json
        self.assertEqual(self.approve(item), {"FINISHED"})
        record = self.runtime.state.job_store.get(item.request_id)
        self.assertEqual(record.state, state.PREPARED)
        view = self.runtime.inspect_model_jobs().views[item.request_id]
        self.assertIn(view, self.runtime.state.jobs_view)
        self.assertEqual(view.meta["recovery_actions"], ("cancel_prepared",))
        result = bpy.ops.scenario.recover_job(
            context_id=self.runtime.state.job_context_id,
            request_id=item.request_id,
            expected_revision=record.revision,
            action="cancel_prepared",
        )
        self.assertEqual(result, {"FINISHED"})
        self.hold_quotes.set()
        self.advance(item)
        saved = self.runtime.state.job_store.get(item.request_id)
        self.assertEqual((saved.state, saved.remote_job_id), (state.CANCELED, None))
        self.assertEqual(
            (item.phase, item.error),
            ("ERROR", "Blockout request canceled; nothing was sent to Scenario"),
        )
        self.assertEqual(self.scene.scenario_blockout.plan_json, plan)
        self.assertEqual(self.paid, [])

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

    def test_mcp_refinement_requires_a_complete_plan_before_requesting_a_quote(self):
        self.scene.scenario_blockout.refine = "Add a doorway"
        for plan in ("", "not JSON", "[]", "{}", '[{"name":"Partial"},', "[{}, 2]"):
            with self.subTest(plan=plan):
                self.scene.scenario_blockout.plan_json = plan
                with self.assertRaisesRegex(self.facade.ScenarioError, "complete Blockout plan"):
                    self.mcp.estimate_blockout({"action": "REFINE"})
                self.assertEqual(self.scene.scenario_blockout.plan_json, plan)
        self.assertEqual(self.calls, [])
        self.assertEqual(self.paid, [])
        self.assertEqual(self.jobs().actions, {})
        self.assertEqual(self.runtime.state.job_store.records(), ())

    def quote_in_new_scene(self):
        scene = bpy.data.scenes.new("Another Blockout scene")
        bpy.context.window.scene = scene
        scene.scenario_blockout.prompt = "A stone tower"
        item = self.jobs().quote(scene, "DESIGN")
        self.advance(item)
        self.assertEqual(item.phase, "READY", item.error)
        return scene, item

    def test_finished_actions_free_capacity_without_retiring_uncertainty(self):
        self.lose_response = True
        uncertain = self.quote()
        self.approve(uncertain)
        self.advance(uncertain)
        self.assertEqual(uncertain.phase, "ERROR")
        self.lose_response = False
        jobs = self.jobs()
        plans = []
        for _ in range(31):
            scene, item = self.quote_in_new_scene()
            jobs.approve(item.identifier, scene, approved_cost=item.cost)
            self.advance(item)
            self.assertEqual(item.phase, "DONE", item.error)
            plans.append((scene, scene.scenario_blockout.plan_json))
        records = jobs.store.records()
        self.assertEqual(len(jobs.actions), 32)
        _, fresh = self.quote_in_new_scene()
        self.assertEqual(len(jobs.actions), 32)
        self.assertIn(fresh.identifier, jobs.actions)
        self.assertIs(jobs.actions[uncertain.identifier], uncertain)
        self.assertEqual(jobs.store.records(), records)
        for scene, plan in plans:
            self.assertEqual(scene.scenario_blockout.plan_json, plan)
        bpy.context.window.scene = self.scene
        with self.assertRaisesRegex(self.facade.ScenarioError, "uncertain saved Blockout job"):
            jobs.quote(self.scene, "DESIGN")
        self.assertEqual(len(self.paid), 32)

    def test_failed_quotes_free_capacity_without_spending(self):
        jobs = self.jobs()
        for _ in range(32):
            scene = bpy.data.scenes.new("Changed Blockout input")
            bpy.context.window.scene = scene
            scene.scenario_blockout.prompt = "A stone tower"
            item = jobs.quote(scene, "DESIGN")
            scene.scenario_blockout.prompt = "Changed before quote delivery"
            self.advance(item)
            self.assertEqual(item.phase, "ERROR")
            self.assertFalse(item.request_id)
        self.assertEqual(len(jobs.actions), 32)
        _, fresh = self.quote_in_new_scene()
        self.assertIn(fresh.identifier, jobs.actions)
        self.assertEqual(len(jobs.actions), 32)
        self.assertEqual(self.paid, [])

    def test_capacity_preserves_ready_quotes_and_pending_commands(self):
        jobs = self.jobs()
        for _ in range(31):
            self.quote_in_new_scene()
        bpy.context.window.scene = self.scene
        pending = jobs.quote(self.scene, "DESIGN")
        pending.task.result(5)
        self.assertEqual(pending.phase, "QUOTING")
        handles = tuple(jobs.actions)
        scene = bpy.data.scenes.new("No free Blockout slot")
        bpy.context.window.scene = scene
        scene.scenario_blockout.prompt = "A stone tower"
        calls = len(self.calls)
        with self.assertRaisesRegex(self.facade.ScenarioError, "Finish an existing"):
            jobs.quote(scene, "DESIGN")
        self.assertEqual(tuple(jobs.actions), handles)
        self.assertIsNotNone(pending.task)
        self.assertEqual(len(self.calls), calls)
        self.assertEqual(self.paid, [])

    def test_truncated_or_non_array_plan_preserves_previous_plan(self):
        for text in [
            '[{"name":"Partial"},',
            '```json\n[{"name":"Partial"}, {"size":[1,2,3]}\n```',
            'Here is the plan:\n[{"name":"Partial"}, {"size":[1,2,3]}',
            "{}",
            "[{}, 2]",
        ]:
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

    def saved_plan(self, *, manifest=True):
        item = self.quote()
        self.approve(item)
        if manifest:
            self.advance(item)
            self.assertEqual(item.phase, "DONE")
        else:
            item.task.result(5)
            record = self.runtime.state.job_store.get(item.request_id)
            self.jobs().session.refresh_remote(
                item.request_id, expected_revision=record.revision
            ).result(5)
        self.runtime.state.reset()
        self.scene.scenario_blockout.plan_json = ""
        self.runtime.local_job_recovery()
        record = self.runtime.state.job_store.get(item.request_id)
        return record

    def ready_review(self, record):
        recovery = self.jobs().recovery
        review = recovery.prepare(record.intent.request_id, record.revision, bpy.context.scene)
        for _ in range(3):
            if review.task is not None:
                try:
                    review.task.result(5)
                except Exception:
                    # Recovery polling below consumes and reports this failed task.
                    pass
            recovery.poll()
        return recovery, review

    def test_recovered_plan_native_approval_preserves_geometry_and_is_single_use(self):
        record = self.saved_plan()
        self.scene.scenario_blockout.plan_json = '[{"name":"Existing plan"}]'
        before = tuple(self.scene.objects)
        self.assertEqual(
            bpy.ops.scenario.read_saved_blockout(
                context_id=self.runtime.state.job_context_id,
                request_id=record.intent.request_id,
                expected_revision=record.revision,
            ),
            {"FINISHED"},
        )
        recovery = self.jobs().recovery
        review = recovery.current(record.intent.request_id, self.scene)
        review.task.result(5)
        recovery.poll()
        summary = recovery.status(review.identifier)
        self.assertEqual(summary["state"], "ready")
        self.assertTrue(summary["replaces_plan"])
        self.assertEqual(summary["elements"], 1)
        self.assertIn("Existing plan", self.scene.scenario_blockout.plan_json)
        calls = len(self.calls)
        arguments = dict(context_id=self.runtime.state.job_context_id, review_id=review.identifier)
        self.assertEqual(bpy.ops.scenario.use_saved_blockout(**arguments), {"FINISHED"})
        self.assertIn("Test tower", self.scene.scenario_blockout.plan_json)
        self.assertEqual(tuple(self.scene.objects), before)
        # Blender surfaces this operator's reported ERROR as RuntimeError.
        with self.assertRaises(RuntimeError):
            bpy.ops.scenario.use_saved_blockout(**arguments)
        self.assertEqual(len(self.calls), calls)
        self.assertEqual(len(self.paid), 1)
        self.assertEqual(self.runtime.state.job_store.get(record.intent.request_id), record)

    def test_recovered_plan_loads_missing_manifest_without_regeneration(self):
        record = self.saved_plan(manifest=False)
        self.assertFalse(record.results)
        recovery, review = self.ready_review(record)
        self.assertEqual(review.phase, "READY", review.error)
        self.assertGreater(review.revision, record.revision)
        recovery.apply(review.identifier)
        self.assertIn("Test tower", self.scene.scenario_blockout.plan_json)
        self.assertEqual(len(self.paid), 1)

    def test_mcp_recovered_plan_uses_explicit_new_scene_and_can_discard(self):
        record = self.saved_plan()
        other = bpy.data.scenes.new("Recovered plan destination")
        bpy.context.window.scene = other
        arguments = {
            "context_id": self.runtime.state.job_context_id,
            "request_id": record.intent.request_id,
            "expected_revision": record.revision,
        }
        started = self.mcp.prepare_blockout_plan(arguments)
        recovery = self.jobs().recovery
        review = recovery.reviews[started["review_id"]]
        review.task.result(5)
        keys = {"context_id": arguments["context_id"], "review_id": review.identifier}
        summary = self.mcp.blockout_plan_status(keys)
        self.assertEqual(summary["state"], "ready")
        self.assertEqual(summary["scene"], other.name)
        self.assertEqual(
            self.mcp.blockout_plan_status({**keys, "discard": True})["state"], "discarded"
        )
        with self.assertRaises((RuntimeError, self.facade.ScenarioError)):
            self.mcp.apply_blockout_plan(keys)
        recovery, review = self.ready_review(record)
        result = self.mcp.apply_blockout_plan({**keys, "review_id": review.identifier})
        self.assertFalse(result["geometry_changed"])
        self.assertEqual(self.scene.scenario_blockout.plan_json, "")
        self.assertIn("Test tower", other.scenario_blockout.plan_json)
        self.assertEqual(len(self.paid), 1)

    def test_recovered_plan_rejects_changed_destination_and_same_name_replacement(self):
        record = self.saved_plan()
        for field in ("prompt", "refine", "plan_json", "scale", "scene_type"):
            with self.subTest(field=field):
                recovery, review = self.ready_review(record)
                self.assertEqual(review.phase, "READY")
                props = self.scene.scenario_blockout
                original = getattr(props, field)
                replacement = {"scale": "room", "scene_type": "interior"}.get(field, "changed")
                setattr(props, field, replacement)
                with self.assertRaises((RuntimeError, self.facade.ScenarioError)):
                    recovery.apply(review.identifier)
                setattr(props, field, original)
        recovery, review = self.ready_review(record)
        other = bpy.data.scenes.new("Other")
        bpy.context.window.scene = other
        old_name = self.scene.name
        bpy.data.scenes.remove(self.scene)
        replacement = bpy.data.scenes.new(old_name)
        bpy.context.window.scene = replacement
        self.assertIsNone(recovery.current(record.intent.request_id, replacement))
        summary = self.mcp.blockout_plan_status(
            {"context_id": self.runtime.state.job_context_id, "review_id": review.identifier}
        )
        self.assertEqual(summary["state"], "error")
        self.assertEqual(summary["scene"], "Unavailable")
        self.assertIn("removed", summary["error"])
        with self.assertRaises((RuntimeError, self.facade.ScenarioError)):
            recovery.apply(review.identifier)
        self.assertEqual(replacement.scenario_blockout.plan_json, "")
        self.assertEqual(len(self.paid), 1)

    def test_recovered_plan_rejects_late_read_and_retired_context(self):
        record = self.saved_plan()
        recovery = self.jobs().recovery
        review = recovery.prepare(record.intent.request_id, record.revision, self.scene)
        self.scene.scenario_blockout.plan_json = "newer work"
        review.task.result(5)
        recovery.poll()
        self.assertEqual(review.phase, "ERROR")
        self.assertEqual(self.scene.scenario_blockout.plan_json, "newer work")
        self.scene.scenario_blockout.plan_json = ""
        recovery, review = self.ready_review(record)
        old_context = self.runtime.state.job_context_id
        self.runtime.state.reset()
        with self.assertRaises((RuntimeError, self.facade.ScenarioError)):
            recovery.apply(review.identifier)
        with self.assertRaises((RuntimeError, self.facade.ScenarioError)):
            self.mcp.apply_blockout_plan(
                {"context_id": old_context, "review_id": review.identifier}
            )
        self.assertEqual(self.scene.scenario_blockout.plan_json, "")

    def test_deleted_destinations_do_not_exhaust_saved_plan_review_capacity(self):
        record = self.saved_plan()
        scenes = []
        for _ in range(16):
            scene = bpy.data.scenes.new("Temporary plan destination")
            bpy.context.window.scene = scene
            recovery, review = self.ready_review(record)
            self.assertEqual(review.phase, "READY")
            scenes.append(scene)
        self.assertEqual(len(recovery.reviews), 16)
        bpy.context.window.scene = self.scene
        for scene in scenes:
            bpy.data.scenes.remove(scene)
        recovery, review = self.ready_review(record)
        self.assertEqual(review.phase, "READY", review.error)
        self.assertEqual(tuple(recovery.reviews), (review.identifier,))
        self.assertEqual(self.scene.scenario_blockout.plan_json, "")
        self.assertEqual(len(self.paid), 1)
        self.assertEqual(self.runtime.state.job_store.get(record.intent.request_id), record)

    def test_deleted_review_keeps_its_pending_read_until_drained(self):
        record = self.saved_plan()
        recovery = self.jobs().recovery
        scene = bpy.data.scenes.new("Pending removed destination")
        bpy.context.window.scene = scene
        task = Future()
        with (
            patch.object(recovery.session, "read_model_text", return_value=task),
            patch.object(recovery.session, "drain", return_value=[]) as drain,
        ):
            review = recovery.prepare(record.intent.request_id, record.revision, scene)
            bpy.context.window.scene = self.scene
            bpy.data.scenes.remove(scene)
            recovery.poll()
            self.assertIs(recovery.reviews[review.identifier].task, task)
            drain.assert_not_called()
            task.set_result(None)
            recovery.poll()
            drain.assert_called_once_with(task=task)
            self.assertIsNone(review.task)
        recovery, fresh = self.ready_review(record)
        self.assertEqual(fresh.phase, "READY")
        self.assertNotIn(review.identifier, recovery.reviews)
        self.assertEqual(len(self.paid), 1)

    def test_recovered_plan_failure_can_retry_read_but_never_generation(self):
        record = self.saved_plan()
        for text in ('[{"name":"partial"},', "not a plan", "[]"):
            with self.subTest(text=text):
                self.result_text = text
                recovery, review = self.ready_review(record)
                self.assertEqual(review.phase, "ERROR")
                with self.assertRaises((RuntimeError, self.facade.ScenarioError)):
                    recovery.apply(review.identifier)
        self.result_text = '[{"name":"Recovered tower"}]'
        recovery, review = self.ready_review(record)
        self.assertEqual(review.phase, "READY", review.error)
        recovery.apply(review.identifier)
        self.assertIn("Recovered tower", self.scene.scenario_blockout.plan_json)
        self.assertEqual(len(self.paid), 1)

    def test_recovered_plan_rejects_stale_revision_and_offline_reads(self):
        record = self.saved_plan()
        recovery = self.jobs().recovery
        with self.assertRaises((RuntimeError, self.facade.ScenarioError)):
            recovery.prepare(record.intent.request_id, record.revision - 1, self.scene)
        calls = len(self.calls)
        with online_access(False):
            self.runtime.sync_catalog_context()
            try:
                _, review = self.ready_review(record)
            except Exception:
                pass  # Admission may reject before a task exists.
            else:
                self.assertEqual(review.phase, "ERROR")
        self.assertEqual(len(self.calls), calls)
        self.assertEqual(self.scene.scenario_blockout.plan_json, "")

    def test_saved_plan_controls_draw_without_reading_or_changing_state(self):
        from unittest.mock import MagicMock

        record = self.saved_plan()
        jobs = self.runtime.inspect_model_jobs()
        view = jobs.views[record.intent.request_id]
        self.assertIn("recover_blockout", view.meta["recovery_actions"])
        recovery_ui = submodule("blender.job_recovery")
        before, calls = self.facade.binding(self.scene), len(self.calls)
        layout = MagicMock()
        recovery_ui.draw_controls(layout, view)
        self.assertEqual(layout.operator.call_args.args[0], "scenario.read_saved_blockout")
        self.assertEqual(self.facade.binding(self.scene), before)
        self.assertEqual(len(self.calls), calls)
        recovery, review = self.ready_review(record)
        layout.reset_mock()
        recovery_ui.draw_controls(layout, view)
        self.assertEqual(layout.operator.call_args.args[0], "scenario.use_saved_blockout")
        self.assertEqual(layout.operator.return_value.review_id, review.identifier)
