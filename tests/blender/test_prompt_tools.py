# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Native and MCP prompt approvals use one scoped SDK session without paid retries."""

import json
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import bpy
import httpx
from helpers import online_access, reset_scene, submodule, temp_credentials


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
                    state_dir=Path(directory), registry_file=Path(directory) / "jobs.json"
                ),
            )
        )
        self.sessions, self.calls, self.paid = [], [], []
        self.lose_response = False
        self.result_text = "A copper teapot\nSoft studio light"
        self.fail_read = False
        api, catalog, session = self.api, self.runtime.SDKCatalog, self.runtime.JobSession

        def respond(request):
            self.assertIsNot(threading.current_thread(), threading.main_thread())
            self.calls.append(request)
            self.assertNotIn("projectId", request.url.params)
            if request.method == "GET":
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
