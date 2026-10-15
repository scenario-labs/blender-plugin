# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Native and MCP prompt approvals use one scoped SDK session without paid retries."""

import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import bpy
import httpx
from helpers import (
    assert_finished_without_download,
    mcp_call,
    online_access,
    reset_scene,
    submodule,
    temp_credentials,
)


class PromptToolsTests(unittest.TestCase):
    def setUp(self):
        reset_scene()
        self.tools = submodule("blender.prompt_tools")
        self.runtime = submodule("blender.runtime")
        self.mcp = submodule("mcp.tools_scenario")
        self.storage = submodule("core.jobs.store")
        self.api = submodule("core.api.sdk_adapter")
        self.enterContext(patch.object(self.runtime, "state", self.runtime.RuntimeState()))
        self.enterContext(online_access(True))
        self.enterContext(temp_credentials())
        directory = self.enterContext(
            tempfile.TemporaryDirectory(dir=bpy.utils.resource_path("USER"))
        )
        self.enterContext(
            patch.object(
                self.runtime,
                "paths",
                return_value=SimpleNamespace(
                    state_dir=Path(directory),
                    cache_dir=Path(directory) / "cache",
                    registry_file=Path(directory) / "jobs.json",
                ),
            )
        )
        self.sessions, self.calls, self.paid = [], [], []
        self.lose_response = False
        self.cloud_jobs = []
        self.result_text = "A copper teapot\nSoft studio light"
        self.fail_read = False
        self.render_model = None  # served to model description reads
        self.hold_quotes, self.held_quotes = None, threading.Semaphore(0)
        api, catalog, session = self.api, self.runtime.SDKCatalog, self.runtime.JobSession

        def respond(request):
            self.assertIsNot(threading.current_thread(), threading.main_thread())
            self.calls.append(request)
            self.assertNotIn("projectId", request.url.params)
            if request.method == "GET":
                if "/models/" in request.url.path:
                    return httpx.Response(200, json={"model": self.render_model})
                if request.url.path == "/v1/jobs":
                    # Recent prompt jobs for an unconfirmed submission; read-only.
                    return httpx.Response(200, json={"jobs": list(self.cloud_jobs)})
                if self.fail_read:
                    return httpx.Response(503)
                index = int(request.url.path.rsplit("-", 1)[-1]) - 1
                translate = self.paid[index].url.path.endswith("/translate")
                output = (
                    {"translation": self.result_text}
                    if translate
                    else {"prompts": [self.result_text]}
                )
                return httpx.Response(
                    200,
                    json={
                        "job": {
                            "jobId": f"remote-{index + 1}",
                            "status": "success",
                            "jobType": "translate" if translate else "generate-prompt",
                            "metadata": {"output": output},
                        }
                    },
                )
            if request.url.params.get("dryRun") == "true":
                if self.hold_quotes is not None:
                    # Occupy a shared worker so a later approval stays queued.
                    self.held_quotes.release()
                    self.hold_quotes.wait(5)
                return httpx.Response(269, content=b'{"creativeUnitsCost":0.1234567890123456789}')
            records = self.runtime.state.job_store.records()
            self.assertTrue(any(row.state == self.storage.JobState.SUBMITTING for row in records))
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
        self.lane = self.scene.scenario.lane_state("image")
        self.lane.prompt = "a teapot"

    def tearDown(self):
        for session in self.sessions:
            session.shutdown()
        self.runtime.state.reset()

    def jobs(self):
        return self.runtime.ensure_prompt_jobs()

    def advance(self, item):
        for _ in range(10):
            if item.task is not None:
                try:
                    item.task.result(5)
                except Exception:
                    # poll() consumes the recorded error; callers assert the final phase.
                    pass
            item.next_poll = 0
            self.jobs().poll()
            if item.phase in {"READY", "DONE", "ERROR"}:
                return
        self.fail(f"Prompt action did not finish: {item.phase}")

    def quote(self, action="GENERATE"):
        operator = (
            bpy.ops.scenario.prompt_translate
            if action == "TRANSLATE"
            else bpy.ops.scenario.prompt_spark
        )
        args = {"lane": "image"}
        if action != "TRANSLATE":
            args["mode"] = action
        self.assertEqual(operator(**args), {"FINISHED"})
        item = self.jobs().current(self.scene, "image")
        self.advance(item)
        self.assertEqual(item.phase, "READY")
        self.assertEqual(self.paid, [])
        return item

    def approve(self, item):
        return bpy.ops.scenario.prompt_approve(quote_id=item.identifier, approved_cost=item.cost)

    def test_deleted_scene_action_does_not_block_remaining_scene(self):
        removed = bpy.data.scenes.new("Removed prompt scene")
        bpy.context.window.scene = removed
        try:
            item = self.jobs().quote(removed, "image", "GENERATE")
            self.advance(item)
            self.assertEqual(item.phase, "READY")
        finally:
            bpy.context.window.scene = self.scene
            bpy.data.scenes.remove(removed)
        with self.assertRaises(ReferenceError):
            _ = removed.name
        before = len(self.calls)
        for phase in ("READY", "DONE", "ERROR", "SUBMITTING"):
            with self.subTest(phase=phase):
                item.phase = phase
                self.assertIsNone(self.jobs().current(self.scene, "image"))
                self.assertIs(self.jobs().actions[item.identifier], item)
        self.assertEqual(len(self.calls), before)
        fresh = self.quote()
        self.assertEqual(fresh.scene, self.scene)
        self.assertEqual(self.paid, [])

    def test_new_requires_exact_price_then_updates_only_original_scene(self):
        other = bpy.data.scenes.new("Other prompt scene")
        self.addCleanup(lambda: bpy.data.scenes.remove(other))
        other.scenario.image.prompt = "Keep other scene"
        item = self.quote()
        self.assertEqual(item.cost, "0.1234567890123456789")
        self.assertEqual(self.lane.prompt, "a teapot")
        self.assertEqual(self.approve(item), {"FINISHED"})
        self.assertEqual(self.lane.estimate_key, "")
        request = submodule("blender.generation").build_request(
            self.scene, "image", for_estimate=True
        )
        self.assertIn("Wait for prompt preparation to finish", request.errors)
        self.advance(item)
        self.assertEqual(item.phase, "DONE")
        self.assertEqual(self.lane.prompt, self.result_text)
        self.assertEqual(other.scenario.image.prompt, "Keep other scene")
        self.assertEqual(len(self.paid), 1)
        self.assertEqual(self.approve(item), {"CANCELLED"})
        self.assertEqual(len(self.paid), 1)

    def test_rewrite_and_translation_use_public_sdk_endpoints(self):
        for action, endpoint in [("REWRITE", "prompt"), ("TRANSLATE", "translate")]:
            self.paid.clear()
            self.lane.prompt = "une théière"
            item = self.quote(action)
            body = json.loads(self.calls[-1].content)
            self.assertEqual(body["prompt"], "une théière")
            self.assertEqual(self.approve(item), {"FINISHED"})
            self.advance(item)
            self.assertEqual(item.phase, "DONE")
            self.assertTrue(self.paid[0].url.path.endswith("/" + endpoint))
            self.assertEqual(len(self.paid), 1)

    def test_compact_price_display_preserves_exact_approval(self):
        item = self.quote()
        layout = MagicMock()
        self.tools.draw_prompt_status(layout, self.lane, "image")
        layout.label.assert_called_once_with(text="Cost: 0.123 CU")
        approval = layout.row.return_value.operator.return_value
        self.assertEqual(approval.quote_id, item.identifier)
        self.assertEqual(approval.approved_cost, "0.1234567890123456789")
        self.assertEqual(self.paid, [])
        self.assertEqual(
            bpy.ops.scenario.prompt_approve(
                quote_id=approval.quote_id, approved_cost=approval.approved_cost
            ),
            {"FINISHED"},
        )
        self.advance(item)
        self.assertEqual(len(self.paid), 1)
        self.assertEqual(self.lane.prompt, self.result_text)

    def test_empty_rewrite_and_translation_do_not_request_prices(self):
        self.lane.prompt = ""
        self.assertEqual(bpy.ops.scenario.prompt_spark(lane="image", mode="REWRITE"), {"CANCELLED"})
        self.assertEqual(bpy.ops.scenario.prompt_translate(lane="image"), {"CANCELLED"})
        self.assertEqual(self.calls, [])

    def test_changed_prompt_or_wrong_cost_cannot_spend(self):
        item = self.quote()
        self.assertEqual(
            bpy.ops.scenario.prompt_approve(quote_id=item.identifier, approved_cost="0.123"),
            {"CANCELLED"},
        )
        self.lane.prompt = "Changed after quote"
        self.assertEqual(self.approve(item), {"CANCELLED"})
        self.assertEqual(self.paid, [])

    def finished_after_inspection(self, action, operation):
        item = self.quote(action)
        self.assertEqual(self.approve(item), {"FINISHED"})
        self.advance(item)
        self.assertEqual(item.phase, "DONE")
        record = self.runtime.state.job_store.get(item.request_id)
        # Reading the text commits no later state, and nothing downloads it.
        self.assertEqual(
            (record.intent.operation, record.state),
            (operation, self.storage.JobState.SUCCEEDED),
        )
        calls = len(self.calls)
        _, status = assert_finished_without_download(self, item.request_id)
        self.assertEqual(status["actions"], ())
        self.assertEqual(len(self.calls), calls)
        self.assertEqual(len(self.paid), 1)

    def test_finished_prompt_spark_stays_out_of_jobs_after_inspecting_saved_jobs(self):
        self.finished_after_inspection("GENERATE", "prompt")

    def test_finished_translation_stays_out_of_jobs_after_inspecting_saved_jobs(self):
        self.finished_after_inspection("TRANSLATE", "translate")

    def test_late_result_preserves_edited_prompt_and_can_be_read_via_mcp(self):
        item = self.quote()
        self.assertEqual(self.approve(item), {"FINISHED"})
        item.task.result(5)
        self.lane.prompt = "Keep this newer text"
        self.advance(item)
        self.assertEqual(item.phase, "ERROR")
        self.assertEqual(self.lane.prompt, "Keep this newer text")
        record = self.runtime.state.job_store.get(item.request_id)
        self.assertEqual(record.state, self.storage.JobState.SUCCEEDED)
        self.jobs().session.invalidate_scene(self.scene)
        read = self.mcp.read_prompt_result(
            {
                "context_id": self.runtime.state.job_context_id,
                "request_id": item.request_id,
                "expected_revision": record.revision,
            }
        )
        result = read.finish(read.run())
        self.assertEqual(result["prompts"], [self.result_text])
        self.assertEqual(self.lane.prompt, "Keep this newer text")
        self.assertEqual(len(self.paid), 1)

    def test_timeout_is_uncertain_without_retry_or_llm_fallback(self):
        item = self.quote()
        self.lose_response = True
        self.approve(item)
        self.advance(item)
        self.assertEqual(item.phase, "ERROR")
        self.assertEqual(
            self.runtime.state.job_store.get(item.request_id).state, self.storage.JobState.UNCERTAIN
        )
        self.assertEqual(bpy.ops.scenario.prompt_spark(lane="image"), {"CANCELLED"})
        self.assertEqual(len(self.paid), 1)
        self.assertEqual(self.lane.prompt, "a teapot")

    def test_an_unconfirmed_prompt_refuses_an_identical_one_after_restart_until_reviewed(self):
        item = self.quote()
        self.lose_response = True
        self.approve(item)
        self.advance(item)
        self.lose_response = False
        request_id = item.request_id
        state = self.storage.JobState
        self.assertEqual(self.runtime.state.job_store.get(request_id).state, state.UNCERTAIN)
        # A restart forgets the field's own action; the shared guard still refuses.
        self.runtime.state.reset()
        deferred = self.mcp.estimate_prompt({"lane": "image", "action": "GENERATE"})
        with self.assertRaisesRegex(Exception, request_id[:8]):
            deferred.finish(deferred.run())
        jobs = self.runtime.ensure_model_jobs()
        record = self.runtime.state.job_store.get(request_id)
        self.assertEqual(jobs.actions(record), ("find_cloud_job", "mark_reviewed"))
        jobs.control(request_id, record.revision, "mark_reviewed")
        deferred = self.mcp.estimate_prompt({"lane": "image", "action": "GENERATE"})
        self.assertIn("quote_id", deferred.finish(deferred.run()))
        self.assertEqual(len(self.paid), 1)

    def settle_model_jobs(self, owner):
        for _ in range(10):
            owner.poll()
            tasks = [task for _, task in tuple(owner._commands.values())]
            if not tasks:
                return
            for task in tasks:
                try:
                    task.result(5)
                except Exception:
                    pass  # The owner records each outcome when it drains the task.
        self.fail("Saved prompt job commands did not settle")

    def lost_prompt(self):
        """An approved prompt whose response is lost, with one listed cloud job."""
        item = self.quote()
        self.cloud_jobs = [
            {
                # The fake serves retrievals of remote-N from the Nth paid request.
                "jobId": "remote-1",
                "jobType": "generate-prompt",
                "status": "success",
                "createdAt": self.storage.claim_time(time.time() + 1),
                "metadata": {"input": {"prompt": "a teapot"}},
            }
        ]
        self.lose_response = True
        self.approve(item)
        self.advance(item)
        self.lose_response = False
        self.assertEqual(item.phase, "ERROR")
        self.assertIn("find its cloud job in Jobs", item.error)
        return item

    def link(self, owner, request_id, job_id="remote-1"):
        rows = submodule("blender.job_recovery").result_actions(owner.views[request_id])
        link = next(row for row in rows if row.action == "link_cloud_job")
        self.assertEqual(
            bpy.ops.scenario.link_cloud_job("EXEC_DEFAULT", **dict(link.properties), job_id=job_id),
            {"FINISHED"},
        )
        self.settle_model_jobs(owner)

    def test_a_linked_prompt_job_fills_its_unchanged_field_in_the_same_session(self):
        item = self.lost_prompt()
        owner = self.runtime.inspect_model_jobs()
        self.settle_model_jobs(owner)
        listings = [r for r in self.calls if r.url.path == "/v1/jobs"]
        self.assertEqual(listings[0].url.params["types"], "generate-prompt,image-prompt-editing")
        view = owner.views[item.request_id]
        self.assertEqual(view.meta["cloud_lookup"], "1 possible cloud job found")
        self.link(owner, item.request_id)
        record = self.runtime.state.job_store.get(item.request_id)
        self.assertEqual((record.state.value, record.remote_job_id), ("succeeded", "remote-1"))
        # Seen finished while Online Access is off, the action waits instead of stopping.
        with online_access(False):
            self.jobs().poll()
        self.assertEqual(item.phase, "ERROR")
        self.assertIn("allow Online Access", item.error)
        self.assertEqual(self.lane.prompt, "a teapot")
        self.advance(item)
        self.assertEqual(item.phase, "DONE")
        self.assertEqual(self.lane.prompt, self.result_text)
        self.assertEqual(len(self.paid), 1)

    def test_a_linked_prompt_job_after_restart_offers_its_text_to_copy(self):
        item = self.lost_prompt()
        request_id = item.request_id
        self.runtime.state.reset()
        owner = self.runtime.inspect_model_jobs()
        self.settle_model_jobs(owner)
        self.link(owner, request_id)
        record = self.runtime.state.job_store.get(request_id)
        self.assertEqual(record.state.value, "succeeded")
        self.assertEqual(owner.actions(record), ("read_prompt_text",))
        status = self.mcp.job_status({"job_id": request_id})
        # MCP keeps its own read_prompt_result tool for the text.
        self.assertNotIn("read_prompt_text", status["actions"])
        owner.control(request_id, record.revision, "read_prompt_text")
        self.settle_model_jobs(owner)
        rows = submodule("blender.job_recovery").result_actions(owner.views[request_id])
        copy = next(row for row in rows if row.operator == "scenario.copy_text")
        self.assertEqual(dict(copy.properties)["text"], self.result_text)
        self.assertEqual(bpy.ops.scenario.copy_text(**dict(copy.properties)), {"FINISHED"})
        # The field is never written by a restarted job.
        self.assertEqual(self.lane.prompt, "a teapot")
        self.assertEqual(len(self.paid), 1)

    def test_native_cancellation_of_queued_prompt_request_never_dispatches(self):
        state = self.storage.JobState
        item = self.quote("TRANSLATE")
        self.hold_quotes = threading.Event()
        self.addCleanup(self.hold_quotes.set)
        # Two pending price requests occupy both shared workers.
        for lane in ("video", "audio"):
            self.jobs().quote(self.scene, lane, "GENERATE")
            self.assertTrue(self.held_quotes.acquire(timeout=5))
        self.assertEqual(self.approve(item), {"FINISHED"})
        record = self.runtime.state.job_store.get(item.request_id)
        self.assertEqual((record.intent.operation, record.state), ("translate", state.PREPARED))
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
        self.assertEqual(saved.revision, record.revision + 1)
        self.assertEqual(
            (item.phase, item.error),
            ("ERROR", "Prompt request canceled; nothing was sent to Scenario"),
        )
        self.assertEqual((view.status, view.error), ("canceled", None))
        self.assertEqual(self.lane.prompt, "a teapot")
        self.assertEqual(self.paid, [])

    def test_credential_retirement_discards_old_approval(self):
        item = self.quote()
        self.runtime.state.retire_jobs()
        self.assertEqual(self.approve(item), {"CANCELLED"})
        self.assertEqual(self.paid, [])

    def test_mcp_quotes_and_approves_the_same_prompt_service(self):
        deferred = self.mcp.estimate_prompt({"lane": "image", "action": "GENERATE"})
        quote = deferred.finish(deferred.run())
        self.assertEqual(self.paid, [])
        item = self.jobs().current(self.scene, "image")
        self.assertEqual(quote["quote_id"], item.identifier)
        result = self.mcp.approve_prompt(
            {"quote_id": quote["quote_id"], "approved_cost": quote["cu_cost_exact"]}
        )
        self.assertEqual(result["request_id"], item.request_id)
        self.advance(item)
        self.assertEqual(self.lane.prompt, self.result_text)
        self.assertEqual(len(self.paid), 1)

    def test_result_read_failure_never_calls_a_paid_fallback(self):
        item = self.quote()
        self.approve(item)
        item.task.result(5)
        self.fail_read = True
        self.advance(item)
        self.assertEqual(item.phase, "ERROR")
        self.assertEqual(len(self.paid), 1)
        self.assertEqual(self.lane.prompt, "a teapot")

    def test_another_scene_or_offline_state_cannot_approve(self):
        item = self.quote()
        other = bpy.data.scenes.new("Approval other scene")
        try:
            with self.assertRaises(submodule("core.api.errors").ScenarioError):
                self.jobs().approve(item.identifier, other, approved_cost=item.cost)
            with (
                online_access(False),
                self.assertRaises(submodule("core.api.errors").ScenarioError),
            ):
                self.jobs().approve(item.identifier, self.scene, approved_cost=item.cost)
            self.assertEqual(self.paid, [])
        finally:
            bpy.data.scenes.remove(other)

    def test_legacy_unbound_event_never_changes_a_field(self):
        self.tools.on_prompt_event({"lane": "image", "text": "unbound", "mode": "GENERATE"})
        self.assertEqual(self.lane.prompt, "a teapot")

    def test_prompt_controls_respect_offline_permission(self):
        self.assertTrue(bpy.ops.scenario.prompt_spark.poll())
        with online_access(False):
            self.assertFalse(bpy.ops.scenario.prompt_spark.poll())
            self.assertFalse(bpy.ops.scenario.prompt_translate.poll())
            self.assertFalse(bpy.ops.scenario.prompt_approve.poll())

    def test_clear_prompt_is_local(self):
        self.assertEqual(bpy.ops.scenario.prompt_clear(lane="image"), {"FINISHED"})
        self.assertEqual(self.lane.prompt, "")
        self.assertEqual(self.calls, [])

    def render_lane(self, lane_name="render_image"):
        generation = submodule("blender.generation")
        references = submodule("blender.render_references")
        video = lane_name == "render_video"
        model = {
            "id": "fixture-render-model",
            "name": "Render fixture",
            "type": "custom",
            "capabilities": ["video2video" if video else "img2img"],
            "inputs": [
                {"name": "prompt", "type": "string", "required": True, "prompt": True},
                {"name": "referenceImages", "type": "file_array", "kind": "image"},
            ]
            + (
                [
                    {"name": "video", "type": "file", "kind": "video"},
                    {"name": "firstFrameImage", "type": "file", "kind": "image"},
                ]
                if video
                else []
            ),
        }
        self.render_model = model
        record = submodule("core.api.catalog").ModelRecord.from_api(model)
        generation.set_catalog([record], [record])
        lane = self.scene.scenario.lane_state(lane_name)
        lane.model_id, lane.prompt = record.id, ""
        lane.spark_enabled = True
        scene = lane.references.add()
        scene.param_name = "video" if video else "referenceImages"
        scene.source, scene.asset_id = "ASSET", "asset_scene"
        scene[references.ROLE] = references.SCENE
        if video:
            lane.use_first_frame, lane.first_frame_path = True, "first-frame.png"
            first = lane.references.add()
            first.param_name, first.source, first.asset_id = (
                "firstFrameImage",
                "ASSET",
                "asset_first",
            )
            first.filepath = lane.first_frame_path
            first[references.ROLE] = references.FIRST_FRAME
        style = lane.references.add()
        style.param_name, style.source, style.asset_id = "referenceImages", "ASSET", "asset_style"
        return lane

    def test_mcp_render_spark_requires_separate_exact_approval_and_delivers_the_look(self):
        for lane_name in ("render_image", "render_video"):
            with self.subTest(lane=lane_name):
                lane = self.render_lane(lane_name)
                form = self.mcp.render_form({"lane": lane_name})
                self.assertTrue(form["spark_required"])
                deferred = self.mcp.estimate_prompt({"lane": lane_name, "action": "GENERATE"})
                quote = deferred.finish(deferred.run())
                paid = len(self.paid)
                with self.assertRaises(submodule("core.api.errors").ScenarioError):
                    self.mcp.approve_prompt({"quote_id": quote["quote_id"], "approved_cost": "0"})
                self.assertEqual(len(self.paid), paid)
                self.mcp.approve_prompt(
                    {"quote_id": quote["quote_id"], "approved_cost": quote["cu_cost_exact"]}
                )
                self.advance(self.jobs().current(self.scene, lane_name))
                self.assertEqual(lane.prompt, self.result_text)
                self.assertTrue(self.mcp.render_form({"lane": lane_name})["ready_to_estimate"])
                self.assertEqual(len(self.paid), paid + 1)

    def test_mcp_render_look_price_waits_for_the_model_description(self):
        self.render_lane()
        generation = submodule("blender.generation")
        model_id = self.render_model["id"]
        listed = {key: self.render_model[key] for key in ("id", "name", "type", "capabilities")}
        self.runtime.state.records[model_id] = submodule("core.api.catalog").ModelRecord.from_api(
            listed
        )
        generation._schemas.pop(model_id, None)
        self.assertIsNone(self.runtime.ensure_catalog().load_cached(model_id))
        response = mcp_call("estimate_prompt", {"lane": "render_image", "action": "GENERATE"})
        self.assertNotIn("error", response)
        self.assertFalse(response["result"].get("isError"), response)
        quote = json.loads(response["result"]["content"][0]["text"])
        self.assertEqual(quote["cu_cost_exact"], "0.1234567890123456789")
        # The description read the call started, then the look's dry run.
        self.assertEqual(
            [(call.method, call.url.path.rsplit("/", 1)[-1]) for call in self.calls],
            [("GET", model_id), ("POST", "prompt")],
        )
        self.assertEqual(self.paid, [])

    def test_render_automatic_preparation_quotes_once_then_requires_approval(self):
        lane = self.render_lane()
        generation = submodule("blender.generation")
        generation.request_estimate(self.scene, "render_image")
        item = self.jobs().current(self.scene, "render_image")
        self.advance(item)
        self.assertEqual(item.phase, "READY")
        self.assertEqual(lane.estimate_state, "UNAVAILABLE")
        generation.request_estimate(self.scene, "render_image")
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.paid, [])
        payload = json.loads(self.calls[0].content)
        self.assertEqual(payload["images"], ["asset_scene", "asset_style"])
        self.assertIn("style references only", payload["prompt"])
        self.assertEqual(self.approve(item), {"FINISHED"})
        self.advance(item)
        self.assertEqual(item.phase, "DONE")
        self.assertEqual(lane.prompt, self.result_text)
        request = generation.build_request(self.scene, "render_image", for_estimate=True)
        self.assertEqual(request.errors, [])
        self.assertIsNone(request.spark)
        self.assertIn("A copper teapot Soft studio light", request.body["prompt"])
        self.assertEqual(len(self.paid), 1)
        self.assertTrue(all(call.url.path.endswith("/prompt") for call in self.paid))
        self.assertEqual(lane.estimate_key, "")  # A new render quote is still required.

    def test_video_prompt_uses_first_frame_and_styles_never_the_video_asset(self):
        lane = self.render_lane("render_video")
        item = self.jobs().quote(self.scene, "render_video", "GENERATE")
        self.advance(item)
        payload = json.loads(self.calls[0].content)
        self.assertEqual(payload["images"], ["asset_first", "asset_style"])
        self.assertIn("approved first frame", payload["prompt"])
        self.assertNotIn("asset_scene", payload["images"])
        self.assertEqual(self.approve(item), {"FINISHED"})
        self.advance(item)
        self.assertEqual(lane.prompt, self.result_text)
        self.assertEqual(len(self.paid), 1)

    def test_render_reference_change_rejects_price_and_late_text(self):
        lane = self.render_lane()
        item = self.jobs().quote(self.scene, "render_image", "GENERATE")
        self.advance(item)
        lane.references[0].asset_id = "asset_replaced"
        self.assertEqual(self.approve(item), {"CANCELLED"})
        self.assertEqual(self.paid, [])
        item = self.jobs().quote(self.scene, "render_image", "GENERATE")
        self.advance(item)
        self.assertEqual(self.approve(item), {"FINISHED"})
        lane.references[1].asset_id = "asset_other_style"
        self.advance(item)
        self.assertEqual(item.phase, "ERROR")
        self.assertEqual(lane.prompt, "")
        self.assertEqual(len(self.paid), 1)

    def test_render_spark_toggle_invalidates_preparation_approval(self):
        lane = self.render_lane()
        item = self.jobs().quote(self.scene, "render_image", "GENERATE")
        self.advance(item)
        lane.spark_enabled = False
        self.assertEqual(self.approve(item), {"CANCELLED"})
        self.assertEqual(self.paid, [])

    def test_render_pending_file_or_other_scope_cannot_request_prompt_price(self):
        lane = self.render_lane()
        errors = submodule("core.api.errors")
        style = lane.references[1]
        style.source, style.filepath = "FILE", "style.png"
        with self.assertRaises(errors.ScenarioError):
            self.jobs().quote(self.scene, "render_image", "GENERATE")
        style.source = "ASSET"
        form = submodule("blender.reference_form")
        style[form._SCOPE] = "another-scope"
        with self.assertRaises(errors.ScenarioError):
            self.jobs().quote(self.scene, "render_image", "GENERATE")
        self.assertEqual(self.calls, [])

    def test_video_missing_first_frame_gives_actionable_preparation_error(self):
        lane = self.render_lane("render_video")
        lane.use_first_frame = False
        submodule("blender.generation").request_estimate(self.scene, "render_video")
        self.assertIn("first frame", lane.estimate_error)
        self.assertEqual(lane.estimate_state, "UNAVAILABLE")
        self.assertEqual(self.calls, [])

    def test_uncertain_render_preparation_never_automatically_quotes_or_submits_again(self):
        lane = self.render_lane()
        generation = submodule("blender.generation")
        self.lose_response = True
        generation.request_estimate(self.scene, "render_image")
        item = self.jobs().current(self.scene, "render_image")
        self.advance(item)
        self.assertEqual(self.approve(item), {"FINISHED"})
        self.advance(item)
        before = len(self.calls)
        generation.request_estimate(self.scene, "render_image")
        self.assertEqual(len(self.calls), before)
        self.assertEqual(len(self.paid), 1)
        self.assertEqual(lane.prompt, "")
        self.assertEqual(
            self.runtime.state.job_store.get(item.request_id).state, self.storage.JobState.UNCERTAIN
        )
