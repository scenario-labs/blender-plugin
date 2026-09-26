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
from helpers import isolated_manager, online_access, reset_scene, submodule, temp_credentials


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
            if request.method == "GET":
                return httpx.Response(200, json={"model": self.model})
            self.assertEqual(dict(request.url.params), {"dryRun": "true"})
            self.assertEqual(request.url.path, "/v1/generate/custom/fixture-price")
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
        self.enterContext(
            patch.object(
                self.runtime, "make_client", side_effect=AssertionError("Legacy client used")
            )
        )

    def deliver(self):
        self.manager.join(5)
        self.assertFalse(self.manager.has_active())
        for event in self.manager.drain():
            self.handlers.dispatch(event)

    def mcp_estimate(self):
        registry = submodule("blender.mcp_service").build_registry()
        server = submodule("mcp.server").McpServer(
            "127.0.0.1", 0, "fixture-token", registry, {}, timeout=5
        )
        message = {
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "estimate_cost",
                "arguments": {"model_id": self.model["id"], "parameters": {"prompt": "a teapot"}},
            },
        }
        with ThreadPoolExecutor(max_workers=1) as worker:
            result = worker.submit(server.handle, message)
            deadline = time.monotonic() + 5
            while not result.done() and time.monotonic() < deadline:
                server.process_pending()
                time.sleep(0.001)
            response = result.result(1)
        self.assertNotIn("error", response)
        self.assertFalse(response["result"].get("isError"), response)
        return json.loads(response["result"]["content"][0]["text"])

    def test_ui_and_mcp_share_sdk_schema_payload_and_exact_cost(self):
        self.generation.request_estimate(bpy.context.scene, "image")
        self.deliver()
        self.assertEqual(self.lane.estimate_state, "READY", self.lane.estimate_error)
        quote = self.runtime.state.estimates[self.lane.estimate_key]
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
        self.assertEqual(len(self.calls), 3)  # One shared schema read, two dry runs.

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
        with self.assertRaisesRegex(Exception, "connection changed"):
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
        self.assertEqual(second_lane.estimate_state, "READY")
        self.assertEqual(len(self.runtime.state.estimates), 2)

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
