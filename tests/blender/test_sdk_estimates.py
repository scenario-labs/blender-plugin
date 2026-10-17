# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Active UI/MCP estimates use the installed SDK without touching the service."""

import json
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from unittest.mock import patch

import bpy
import httpx
from helpers import (
    isolated_manager,
    mcp_call,
    online_access,
    reset_scene,
    submodule,
    temp_credentials,
)


class SDKEstimateTests(unittest.TestCase):
    def setUp(self):
        reset_scene()
        self.runtime = submodule("blender.runtime")
        self.generation = submodule("blender.generation")
        self.handlers = submodule("blender.handlers")
        self.enterContext(patch.object(self.runtime, "state", self.runtime.RuntimeState()))
        self.prefs = self.enterContext(temp_credentials())
        self.enterContext(online_access(True))
        self.manager = self.enterContext(isolated_manager())
        self.addCleanup(self.runtime.state.reset)
        self.calls = []
        self.trained = {}
        self.expected_project = None
        self.hold = None  # An Event that keeps dry runs in flight until it is set.
        self.read_entered = threading.Event()  # A description read of the model started.
        self.read_hold = None  # An Event that keeps description reads in flight until it is set.
        self.read_failures = 0  # Description reads that Scenario answers with HTTP 503.
        self.response = b'{"creativeUnitsCost":1.1234567890123456789,"costDetails":{"base":1.25,"nested":{"parts":[0.5,2]}}}'
        self.model = {
            "id": "fixture-price",
            "name": "Fixture",
            "type": "custom",
            "capabilities": ["txt2img"],
            "inputs": [{"name": "prompt", "type": "string", "required": True, "prompt": True}],
        }
        adapter = submodule("core.api.sdk_adapter")

        def respond(request):
            self.assertIsNot(threading.current_thread(), threading.main_thread())
            self.calls.append(request)
            self.assertEqual(request.url.params.get("projectId"), self.expected_project)
            if request.method == "GET":
                model_id = request.url.path.rsplit("/", 1)[1]
                if model_id in self.trained:
                    return httpx.Response(200, json={"model": self.trained[model_id]})
                if model_id != self.model["id"]:
                    return httpx.Response(404, json={"reason": "not found"})
                self.read_entered.set()
                if self.read_hold is not None:
                    self.assertTrue(self.read_hold.wait(5))
                if self.read_failures:
                    self.read_failures -= 1
                    # retry-after-ms keeps the SDK's own read retries quick here.
                    return httpx.Response(
                        503,
                        json={"reason": "private outage detail"},
                        headers={"retry-after-ms": "1"},
                    )
                return httpx.Response(200, json={"model": self.model})
            expected = {"dryRun": "true"}
            if self.expected_project is not None:
                expected["projectId"] = self.expected_project
            self.assertEqual(dict(request.url.params), expected)
            self.assertEqual(request.url.path, "/v1/generate/custom/fixture-price")
            if self.hold is not None:
                self.assertTrue(self.hold.wait(5))
            return httpx.Response(269, content=self.response)

        def factory(credentials, **kwargs):
            return adapter.SDKAdapter(credentials, transport=httpx.MockTransport(respond), **kwargs)

        self.enterContext(
            patch.object(submodule("core.api.sdk_catalog"), "SDKAdapter", side_effect=factory)
        )
        self.catalog = self.runtime.ensure_catalog()
        record = submodule("core.api.catalog").ModelRecord.from_api(self.model)
        self.generation.set_catalog([record], [record])
        self.lane = bpy.context.scene.scenario.lane_state("image")
        self.lane.prompt = "a teapot"
        self.assertFalse(
            self.generation.build_request(bpy.context.scene, "image", for_estimate=True).errors
        )

    def wait_quotes(self):
        for ticket in tuple(self.runtime.state.model_previews.values()):
            try:
                ticket.task.result(5)
            except Exception:
                pass  # The main-thread delivery reports failed estimates.

    def deliver(self):
        self.wait_quotes()
        self.runtime.sync_catalog_context()
        self.manager.join(5)
        self.assertFalse(self.manager.has_active())
        for event in self.manager.drain():
            self.handlers.dispatch(event)

    def mcp_call(self, name, arguments, *, during=None):
        response = mcp_call(name, arguments, during=during)
        self.assertNotIn("error", response)
        return response["result"]

    def mcp_estimate(self):
        result = self.mcp_call(
            "estimate_cost",
            {"model_id": self.model["id"], "parameters": {"prompt": "a teapot"}},
        )
        self.assertFalse(result.get("isError"), result)
        return json.loads(result["content"][0]["text"])

    def forget_description(self):
        """Keep only the list entry, as before an agent's first call for this model."""
        model_id = self.model["id"]
        listed = {key: self.model[key] for key in ("id", "name", "type", "capabilities")}
        self.runtime.state.records[model_id] = submodule("core.api.catalog").ModelRecord.from_api(
            listed
        )
        self.generation._schemas.pop(model_id, None)
        self.assertIsNone(self.generation.schema_for(model_id))
        self.assertIsNone(self.catalog.load_cached(model_id))

    def first_call(self, name, arguments):
        """Call a tool for an undescribed model; its read is held while the call waits."""
        self.forget_description()
        self.read_hold = threading.Event()
        self.addCleanup(self.read_hold.set)
        observed = []

        def during(server, result):
            if self.read_entered.is_set() and not self.read_hold.is_set():
                # The call's description read is in flight. A call that did not wait
                # would have answered by now; this one waits on the request thread
                # while Blender's main thread has nothing queued and stays free.
                time.sleep(0.05)
                observed.append((server.process_pending(), result.done()))
                self.read_hold.set()

        result = self.mcp_call(name, arguments, during=during)
        self.assertEqual(observed, [(0, False)])
        return result

    def test_first_mcp_schema_waits_for_the_description_it_starts(self):
        result = self.first_call("model_schema", {"model_id": self.model["id"]})
        self.assertFalse(result.get("isError"), result)
        schema = json.loads(result["content"][0]["text"])
        self.assertEqual(schema["model_id"], self.model["id"])
        self.assertEqual([item["name"] for item in schema["parameters"]], ["prompt"])
        self.assertEqual([call.method for call in self.calls], ["GET"])
        self.assertIsNotNone(self.generation.schema_for(self.model["id"]))

    def test_first_mcp_quote_waits_for_the_description_it_starts(self):
        result = self.first_call(
            "estimate_cost", {"model_id": self.model["id"], "parameters": {"prompt": "a teapot"}}
        )
        self.assertFalse(result.get("isError"), result)
        quote = json.loads(result["content"][0]["text"])
        self.assertEqual(quote["cu_cost_exact"], "1.1234567890123456789")
        self.assertIn(quote["quote_id"], self.runtime.state.model_jobs.quotes)
        # The description read, then the quote's own fresh metadata read and dry run.
        self.assertEqual([call.method for call in self.calls], ["GET", "GET", "POST"])
        self.assertEqual(json.loads(self.calls[2].content), {"prompt": "a teapot"})

    def test_a_description_still_loading_after_the_wait_is_retryable(self):
        tools = submodule("mcp.tools_scenario")
        self.forget_description()
        self.read_hold = threading.Event()
        self.addCleanup(self.read_hold.set)
        arguments = {"model_id": self.model["id"], "parameters": {"prompt": "a teapot"}}
        with patch.object(tools, "DESCRIPTION_WAIT", 0.05):
            result = self.mcp_call("estimate_cost", arguments)
        self.assertTrue(result.get("isError"), result)
        self.assertEqual(
            result["content"][0]["text"],
            "ScenarioError: The model description is still loading; call again in a few "
            "seconds. Nothing was quoted, submitted or changed",
        )
        self.assertTrue(self.read_entered.is_set())
        jobs = self.runtime.state.model_jobs
        self.assertFalse(jobs.quotes if jobs is not None else ())
        self.assertFalse([call for call in self.calls if call.method == "POST"])
        # The read continues. Once it is delivered, the next call answers without
        # reading the description again.
        self.read_hold.set()
        self.manager.join(5)
        self.assertFalse(self.manager.has_active())
        result = self.mcp_call("model_schema", {"model_id": self.model["id"]})
        self.assertFalse(result.get("isError"), result)
        self.assertEqual([call.method for call in self.calls], ["GET"])

    def test_a_failed_description_read_is_reported_and_read_again_on_the_next_call(self):
        self.forget_description()
        # The read fails after the SDK's own read retries.
        attempts = 1 + submodule("core.api.sdk_adapter").READ_RETRIES
        self.read_failures = attempts
        arguments = {"model_id": self.model["id"]}
        result = self.mcp_call("model_schema", arguments)
        self.assertTrue(result.get("isError"), result)
        self.assertEqual(
            result["content"][0]["text"],
            "ScenarioError: Could not load this model: Scenario request failed (HTTP 503); "
            "call again to retry",
        )
        result = self.mcp_call("model_schema", arguments)
        self.assertFalse(result.get("isError"), result)
        self.assertEqual(json.loads(result["content"][0]["text"])["model_id"], self.model["id"])
        self.assertEqual([call.method for call in self.calls], ["GET"] * (attempts + 1))

    def test_tools_that_need_a_description_wait_for_it(self):
        tools = submodule("mcp.tools_scenario")
        registry = submodule("blender.mcp_service").build_registry()
        for name in (
            "model_schema",
            "estimate_cost",
            "render_form",
            "generate",
            "estimate_prompt",
        ):
            with self.subTest(name):
                handler = registry.get(name).handler
                self.assertIs(getattr(handler, "__wrapped__", None), getattr(tools, name))

    def test_offline_edits_keep_their_estimate_until_online_access_returns(self):
        pump = submodule("blender.pump")
        panels = submodule("blender.panels")
        self.lane.estimate_dirty_at = 1.0
        self.assertEqual(self.lane.estimate_state, "PENDING")
        with patch.object(submodule("blender.props"), "clock", return_value=10.0):
            with online_access(False):
                pump._process()
                pump._process()
                self.assertEqual(self.lane.estimate_dirty_at, 1.0)
                self.assertEqual(panels.generate_button_text(self.lane), "Offline")
                self.assertFalse(panels.generate_enabled(self.lane, "image"))
                self.assertFalse(self.calls)
            pump._process()
        self.deliver()
        self.assertEqual(self.lane.estimate_state, "READY", self.lane.estimate_error)
        self.assertTrue(panels.generate_enabled(self.lane, "image"))
        pump._process()
        self.assertEqual(len([call for call in self.calls if call.method == "POST"]), 1)
        self.lane.prompt = "another teapot"
        self.assertFalse(panels.generate_enabled(self.lane, "image"))

    def test_unloaded_catalog_is_not_always_loading(self):
        panels = submodule("blender.panels")
        self.runtime.state.records.clear()
        self.runtime.state.catalog_loaded = False
        self.runtime.state.catalog_loading = False
        self.assertEqual(panels.model_button_text(self.lane), "Pick a model")
        with online_access(False):
            self.assertEqual(panels.model_button_text(self.lane), "Online access disabled")
        self.runtime.state.catalog_loading = True
        self.assertEqual(panels.model_button_text(self.lane), "Loading models...")
        self.runtime.state.catalog_error = "Could not load models"
        self.assertEqual(panels.model_button_text(self.lane), "Could not load models")

    def test_ui_and_mcp_share_sdk_schema_payload_and_exact_cost(self):
        self.generation.request_estimate(bpy.context.scene, "image")
        self.deliver()
        self.assertEqual(self.lane.estimate_state, "READY", self.lane.estimate_error)
        quote = self.runtime.state.estimates[self.lane.estimate_key].quote.estimate
        self.assertEqual(quote.cost, Decimal("1.1234567890123456789"))
        self.assertEqual(quote.response_json, self.response)
        result = self.mcp_estimate()
        self.assertEqual(result["cu_cost_exact"], str(quote.cost))
        self.assertEqual(result["details"], {"base": 1.25, "nested": {"parts": [0.5, 2]}})
        self.assertIsInstance(result["details"]["base"], float)
        self.assertEqual(quote.details["costDetails"]["base"], Decimal("1.25"))
        self.assertIs(self.runtime.state.catalog, self.catalog)
        posts = [call for call in self.calls if call.method == "POST"]
        self.assertEqual(len(posts), 2)
        self.assertEqual(posts[0].content, posts[1].content)
        self.assertEqual(json.loads(posts[0].content), {"prompt": "a teapot"})
        self.assertEqual(len(self.calls), 4)  # Each origin-bound quote fetches current schema.

    def test_selected_project_reaches_both_ui_and_mcp_exact_quotes(self):
        self.addCleanup(setattr, self.prefs, "project_id", self.prefs.project_id)
        self.expected_project = "project-a"
        self.prefs.project_id = "project-a"
        self.catalog = self.runtime.ensure_catalog()
        record = submodule("core.api.catalog").ModelRecord.from_api(self.model)
        self.generation.set_catalog([record], [record])
        self.test_ui_and_mcp_share_sdk_schema_payload_and_exact_cost()
        self.assertEqual(self.runtime.state.job_session.scope.project_id, "project-a")
        self.assertTrue(all(call.url.params["projectId"] == "project-a" for call in self.calls))

    def test_project_switch_discards_completed_quote_before_mcp_delivery(self):
        self.addCleanup(setattr, self.prefs, "project_id", self.prefs.project_id)
        deferred = submodule("mcp.tools_scenario").estimate_cost(
            {"model_id": self.model["id"], "parameters": {"prompt": "a teapot"}}
        )
        with ThreadPoolExecutor(max_workers=1) as worker:
            quote = worker.submit(deferred.run).result(5)
        self.prefs.project_id = "project-b"
        with self.assertRaisesRegex(Exception, "context changed"):
            deferred.finish(quote)
        self.assertFalse(self.runtime.state.estimates)
        self.assertFalse(self.runtime.state.model_previews)
        # The rejected finish may open the new selected session, never reuse the old approval.
        self.assertEqual(self.runtime.state.job_session.scope.project_id, "project-b")

    def test_missing_price_is_an_error_and_zero_is_a_valid_price(self):
        self.response = b"{}"
        self.generation.request_estimate(bpy.context.scene, "image")
        self.deliver()
        self.assertEqual(self.lane.estimate_state, "ERROR")
        self.assertFalse(self.runtime.state.estimates)
        self.response = b'{"creativeUnitsCost":0}'
        self.generation.request_estimate(bpy.context.scene, "image")
        self.deliver()
        self.assertEqual(self.lane.estimate_state, "READY", self.lane.estimate_error)
        self.assertEqual(self.lane.estimate_cu, 0)

    def test_queued_quote_from_previous_credentials_cannot_update_ui(self):
        self.generation.request_estimate(bpy.context.scene, "image")
        key = self.lane.estimate_key
        self.manager.join(5)
        self.prefs.api_secret = "replacement-secret"
        self.runtime.ensure_catalog()
        self.lane.estimate_key = key  # Context guard applies even if a stale key survives.
        self.lane.estimate_state = "PENDING"
        self.deliver()
        self.assertEqual(self.lane.estimate_state, "PENDING")
        self.assertFalse(self.runtime.state.estimates)

    def test_mcp_rechecks_credentials_after_worker_completion(self):
        deferred = submodule("mcp.tools_scenario").estimate_cost(
            {"model_id": self.model["id"], "parameters": {"prompt": "a teapot"}}
        )
        with ThreadPoolExecutor(max_workers=1) as worker:
            quote = worker.submit(deferred.run).result(5)
        self.prefs.api_secret = "replacement-secret"
        with self.assertRaisesRegex(Exception, "context changed"):
            deferred.finish(quote)

    def test_identical_model_estimates_for_two_scenes_have_distinct_delivery_keys(self):
        first_scene = bpy.context.scene
        second_scene = first_scene.copy()
        self.addCleanup(bpy.data.scenes.remove, second_scene)
        with patch.object(self.generation.time, "time", return_value=1):
            self.generation.request_estimate(first_scene, "image")
            self.generation.request_estimate(second_scene, "image")
        second_lane = second_scene.scenario.lane_state("image")
        self.assertNotEqual(self.lane.estimate_key, second_lane.estimate_key)
        self.deliver()
        self.assertEqual(self.lane.estimate_state, "READY", self.lane.estimate_error)
        self.assertEqual(second_lane.estimate_state, "ERROR")
        self.assertEqual(len(self.runtime.state.estimates), 1)

    def test_pump_defers_unselected_scene_until_it_becomes_current(self):
        pump = submodule("blender.pump")
        panels = submodule("blender.panels")
        first, window = bpy.context.scene, bpy.context.window
        second = first.copy()
        self.addCleanup(bpy.data.scenes.remove, second)
        self.addCleanup(setattr, window, "scene", first)
        second_lane = second.scenario.lane_state("image")
        self.lane.estimate_dirty_at = second_lane.estimate_dirty_at = 1.0
        self.assertEqual(second_lane.estimate_state, "PENDING")
        clock = patch.object(submodule("blender.props"), "clock", return_value=10.0)
        with clock:
            pump._process()
        self.deliver()
        self.assertEqual(self.lane.estimate_state, "READY", self.lane.estimate_error)
        # Only the selected scene can receive a quote. The other form keeps its
        # pending request without an error or a quote that would be refused.
        self.assertEqual(second_lane.estimate_state, "PENDING")
        self.assertEqual(second_lane.estimate_error, "")
        self.assertEqual(second_lane.estimate_dirty_at, 1.0)
        self.assertEqual(len([call for call in self.calls if call.method == "POST"]), 1)
        window.scene = second
        self.assertIs(bpy.context.scene, second)
        with clock:
            pump._process()
        self.deliver()
        self.assertEqual(second_lane.estimate_state, "READY", second_lane.estimate_error)
        self.assertTrue(panels.generate_enabled(second_lane, "image"))
        self.assertEqual(len([call for call in self.calls if call.method == "POST"]), 2)
        window.scene = first
        with clock:
            pump._process()
        self.deliver()
        # Switching back does not reprice the first scene. This does not show
        # that its displayed quote can still be submitted: the round trip can
        # leave its origin stale, and submission rechecks the origin first.
        self.assertEqual(self.lane.estimate_state, "READY", self.lane.estimate_error)
        self.assertEqual(len([call for call in self.calls if call.method == "POST"]), 2)

    def test_unselected_scene_edit_is_priced_after_switching_to_it(self):
        pump = submodule("blender.pump")
        first, window = bpy.context.scene, bpy.context.window
        second = first.copy()
        self.addCleanup(bpy.data.scenes.remove, second)
        self.addCleanup(setattr, window, "scene", first)
        second_lane = second.scenario.lane_state("image")
        self.lane.estimate_dirty_at = 1.0
        props = submodule("blender.props")
        with patch.object(props, "clock", return_value=10.0):
            pump._process()
        self.deliver()
        self.assertEqual(self.lane.estimate_state, "READY", self.lane.estimate_error)
        with patch.object(props, "clock", return_value=20.0):
            second_lane.prompt = "a kettle"  # A script or driver edits the hidden form.
        self.assertEqual(second_lane.estimate_state, "PENDING")
        with patch.object(props, "clock", return_value=21.0):
            pump._process()
        self.deliver()
        self.assertEqual(second_lane.estimate_state, "PENDING")
        self.assertEqual(second_lane.estimate_error, "")
        self.assertFalse(second_lane.estimate_key)
        window.scene = second
        with patch.object(props, "clock", return_value=21.1):
            pump._process()
        self.deliver()
        self.assertEqual(second_lane.estimate_state, "READY", second_lane.estimate_error)
        posts = [json.loads(call.content) for call in self.calls if call.method == "POST"]
        self.assertEqual(posts, [{"prompt": "a teapot"}, {"prompt": "a kettle"}])

    def switch_away_during_price_request(self):
        """Request the first scene's price, then select another scene before it arrives."""
        first, window = bpy.context.scene, bpy.context.window
        second = first.copy()
        self.addCleanup(bpy.data.scenes.remove, second)
        self.addCleanup(setattr, window, "scene", first)
        second.scenario.lane_state("image").estimate_dirty_at = 0.0  # Nothing to price there.
        self.hold = threading.Event()
        self.addCleanup(self.hold.set)
        self.lane.estimate_dirty_at = 1.0
        props = submodule("blender.props")
        with patch.object(props, "clock", return_value=10.0):
            submodule("blender.pump")._process()
        self.assertEqual(self.lane.estimate_state, "PENDING")
        self.assertTrue(self.lane.estimate_key)
        window.scene = second
        bpy.context.view_layer.update()
        self.hold.set()
        with patch.object(props, "clock", return_value=11.0):
            self.deliver()
        with patch.object(props, "clock", return_value=12.0):
            submodule("blender.pump")._process()  # The other scene is selected.
        self.deliver()
        self.assertEqual(len([call for call in self.calls if call.method == "POST"]), 1)
        return first, window

    def test_price_arriving_after_switching_scenes_is_requested_again_on_return(self):
        pump = submodule("blender.pump")
        props = submodule("blender.props")
        first, window = self.switch_away_during_price_request()
        # The quote cannot be used while another scene is selected. The form
        # waits for its scene instead of keeping an error it cannot clear.
        self.assertEqual(self.lane.estimate_state, "PENDING")
        self.assertEqual(self.lane.estimate_error, "")
        self.assertFalse(self.lane.estimate_key)
        self.assertFalse(self.runtime.state.estimates)
        window.scene = first
        bpy.context.view_layer.update()
        with patch.object(props, "clock", return_value=12.0):
            pump._process()
        self.deliver()
        self.assertEqual(self.lane.estimate_state, "READY", self.lane.estimate_error)
        self.assertTrue(submodule("blender.panels").generate_enabled(self.lane, "image"))
        with patch.object(props, "clock", return_value=13.0):
            pump._process()
        self.deliver()
        posts = [json.loads(call.content) for call in self.calls if call.method == "POST"]
        self.assertEqual(posts, [{"prompt": "a teapot"}, {"prompt": "a teapot"}])

    def test_failed_price_arriving_after_switching_scenes_keeps_its_error(self):
        pump = submodule("blender.pump")
        props = submodule("blender.props")
        self.response = b"{}"  # The service answers without a valid price.
        first, window = self.switch_away_during_price_request()
        self.assertEqual(self.lane.estimate_state, "ERROR")
        self.assertEqual(self.lane.estimate_error, "Could not confirm this price; estimate again")
        window.scene = first
        bpy.context.view_layer.update()
        with patch.object(props, "clock", return_value=13.0):
            pump._process()
        self.deliver()
        self.assertEqual(self.lane.estimate_state, "ERROR")
        self.assertEqual(len([call for call in self.calls if call.method == "POST"]), 1)

    def test_changed_prompt_discards_queued_price(self):
        self.generation.request_estimate(bpy.context.scene, "image")
        self.manager.join(5)
        self.lane.prompt = "changed prompt"
        self.deliver()
        self.assertEqual(self.lane.estimate_state, "PENDING")
        self.assertFalse(self.runtime.state.estimates)

    def test_copying_a_scene_during_pricing_does_not_copy_the_delivery_target(self):
        self.generation.request_estimate(bpy.context.scene, "image")
        other = bpy.context.scene.copy()
        self.addCleanup(bpy.data.scenes.remove, other)
        copied_lane = other.scenario.lane_state("image")
        self.assertEqual(copied_lane.estimate_key, self.lane.estimate_key)
        self.deliver()
        self.assertEqual(self.lane.estimate_state, "READY", self.lane.estimate_error)
        self.assertEqual(copied_lane.estimate_state, "PENDING")
        self.assertFalse(self.runtime.state.estimate_origins)

    def test_deleted_origin_does_not_receive_a_queued_estimate(self):
        origin = bpy.context.scene.copy()
        self.generation.request_estimate(origin, "image")
        bpy.data.scenes.remove(origin)
        self.deliver()
        self.assertFalse(self.runtime.state.estimates)
        self.assertFalse(self.runtime.state.estimate_origins)

    def use_lora_base(self):
        """A base whose REST schema declares LoRA inputs, shaped like the captured FLUX.1 Dev."""
        self.model = {
            **self.model,
            "inputs": [
                *self.model["inputs"],
                {
                    "name": "modelId",
                    "label": "LoRA or Composition Model",
                    "type": "model",
                    "modelTypes": ["flux.1-lora", "flux.1-composition"],
                    "default": "",
                },
                {
                    "name": "loras",
                    "label": "Flux LoRA",
                    "type": "model_array",
                    "modelTypes": ["flux.1-lora"],
                    "maxLength": 6,
                    "default": [],
                },
                {
                    "name": "lorasScale",
                    "label": "LoRA Scale",
                    "type": "number_array",
                    "min": 0,
                    "max": 2,
                },
            ],
            "uiConfig": {
                "lorasComponent": {
                    "label": "Model",
                    "modelInput": "loras",
                    "scaleInput": "lorasScale",
                    "modelIdInput": "modelId",
                }
            },
        }
        record = submodule("core.api.catalog").ModelRecord.from_api(self.model)
        self.generation.set_catalog([record], [record])
        self.trained["fixture-lora"] = {
            "id": "fixture-lora",
            "type": "flux.1-lora",
            "status": "trained",
        }

    def choose_trained(self, model_id, kind, scale=None):
        """A listed trained model chosen in the form, as the picker's Trained chip leaves it."""
        catalog = submodule("core.api.catalog")
        trained = submodule("blender.trained_models")
        listed = {"id": model_id, "type": f"flux.1-{kind}", "status": "trained"}
        state = self.runtime.state
        state.trained_pairs = [(kind, catalog.ModelRecord.from_api(listed))]
        state.trained_records = {model_id: state.trained_pairs[0][1]}
        state.trained_loaded = True
        slot = self.lane.trained.add()
        slot.model_id, slot.kind, slot.lane = model_id, kind, "image"
        if scale is not None:
            slot.fmin, slot.fmax, slot.has_scale = 0.0, 2.0, True
            slot.scale = scale
        slot[trained.SCOPE] = trained.current_scope()
        self.assertLess(self.lane.params.find("modelId"), 0)  # no text field for LoRA inputs

    def test_a_refused_lora_shows_its_reason_without_pricing_in_ui_and_mcp(self):
        self.use_lora_base()
        # The listed LoRA is still training when the quote reads it fresh.
        self.trained["fixture-lora"] = {**self.trained["fixture-lora"], "status": "training"}
        self.choose_trained("fixture-lora", "lora", 0.8)
        self.generation.request_estimate(bpy.context.scene, "image")
        self.deliver()
        self.assertEqual(self.lane.estimate_state, "ERROR")
        self.assertEqual(
            self.lane.estimate_error, "Flux LoRA [1] is not ready to use (status: training)."
        )
        self.assertFalse(self.runtime.state.estimates)
        registry = submodule("blender.mcp_service").build_registry()
        server = submodule("mcp.server").McpServer("127.0.0.1", 0, registry, {}, timeout=5)

        def mcp_refusal(parameters):
            message = {
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "estimate_cost",
                    "arguments": {"model_id": self.model["id"], "parameters": parameters},
                },
            }
            with ThreadPoolExecutor(max_workers=1) as worker:
                result = worker.submit(server.handle, message)
                deadline = time.monotonic() + 5
                while not result.done() and time.monotonic() < deadline:
                    server.process_pending()
                    time.sleep(0.001)
                response = result.result(1)
            self.assertTrue(response["result"]["isError"], response)
            return response["result"]["content"][0]["text"]

        # The same listed LoRA passes MCP's local checks, so its quote reads it fresh too.
        stack = {"prompt": "a teapot", "loras": ["fixture-lora"], "lorasScale": [0.8]}
        self.assertIn(
            "RouteQuoteError: Flux LoRA [1] is not ready to use (status: training).",
            mcp_refusal(stack),
        )
        self.trained["fixture-lora"]["status"] = "trained"
        reason = "LoRA or Composition Model is a LoRA. Add it to Flux LoRA with a strength instead."
        # MCP checks a listed LoRA's kind like the form does, so it refuses before any request.
        self.assertIn(
            f"RouteError: {reason}",
            mcp_refusal({"prompt": "a teapot", "modelId": "fixture-lora"}),
        )
        self.assertFalse([call for call in self.calls if call.method == "POST"])
        # The form's and MCP's quotes each read the base and the LoRA, then stopped;
        # the LoRA in the composition input made no request.
        self.assertEqual(
            [call.url.path.rsplit("/", 1)[1] for call in self.calls],
            ["fixture-price", "fixture-lora"] * 2,
        )

    def test_a_missing_model_is_explained_and_other_failures_stay_generic(self):
        self.use_lora_base()
        self.choose_trained("fixture-missing", "composition")
        self.response = b"{}"
        self.generation.request_estimate(bpy.context.scene, "image")
        self.deliver()
        self.assertEqual(self.lane.estimate_state, "ERROR")
        self.assertEqual(
            self.lane.estimate_error,
            "LoRA or Composition Model is not available to the selected credentials or project "
            "(HTTP 404). Remove it or choose another model.",
        )
        del self.trained["fixture-lora"]
        self.lane.trained.clear()
        self.generation.request_estimate(bpy.context.scene, "image")
        self.deliver()
        self.assertEqual(self.lane.estimate_state, "ERROR")
        self.assertEqual(self.lane.estimate_error, "Could not confirm this price; estimate again")
