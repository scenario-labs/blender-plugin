# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Active Image UI/MCP spend boundary against the bundled SDK and real storage."""

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


class ModelGenerationTests(unittest.TestCase):
    def setUp(self):
        reset_scene()
        self.runtime = submodule("blender.runtime")
        self.generation = submodule("blender.generation")
        self.tools = submodule("mcp.tools_scenario")
        self.storemod = submodule("core.jobs.store")
        self.request_error = submodule("core.api.errors").ScenarioError
        self.origin_error = submodule("blender.job_session").OriginUnavailable
        self.enterContext(patch.object(self.runtime, "state", self.runtime.RuntimeState()))
        self.enterContext(online_access(True))
        self.prefs = self.enterContext(temp_credentials())
        root = self.enterContext(tempfile.TemporaryDirectory(dir=bpy.utils.resource_path("USER")))
        self.enterContext(
            patch.object(self.runtime, "paths", return_value=SimpleNamespace(state_dir=Path(root)))
        )
        self.calls, self.paid, self.sessions = [], [], []
        self.lose_response = False
        self.entered, self.release = threading.Event(), threading.Event()
        self.release.set()
        self.model = {
            "id": "fixture-shared-image",
            "name": "Shared image",
            "type": "custom",
            "capabilities": ["txt2img"],
            "inputs": [{"name": "prompt", "type": "string", "required": True, "prompt": True}],
        }
        api = submodule("core.api.sdk_adapter")
        catalog_type, session_type = self.runtime.SDKCatalog, self.runtime.JobSession

        def respond(request):
            self.assertIsNot(threading.current_thread(), threading.main_thread())
            self.calls.append(request)
            if request.method == "GET":
                return httpx.Response(200, json={"model": self.model})
            if request.url.params.get("dryRun") == "true":
                return httpx.Response(269, content=b'{"creativeUnitsCost":0.1234567890123456789}')
            records = self.store.records()
            self.assertTrue(any(r.state == self.storemod.JobState.SUBMITTING for r in records))
            self.assertNotIn("dryRun", request.url.params)
            self.assertNotIn("projectId", request.url.params)
            self.paid.append(request)
            self.entered.set()
            self.assertTrue(self.release.wait(5))
            if self.lose_response:
                raise httpx.ReadTimeout("synthetic lost response", request=request)
            return httpx.Response(200, json={"job": {"jobId": f"remote-{len(self.paid)}"}})

        def adapter(credentials, **options):
            return api.SDKAdapter(credentials, transport=httpx.MockTransport(respond), **options)

        def session(*args, **options):
            value = session_type(*args, **options)
            self.sessions.append(value)
            return value

        self.enterContext(
            patch.object(
                self.runtime,
                "SDKCatalog",
                side_effect=lambda *a, **k: catalog_type(*a, adapter_factory=adapter, **k),
            )
        )
        self.enterContext(patch.object(self.runtime, "JobSession", side_effect=session))
        self.addCleanup(self.cleanup_jobs)
        self.store = self.runtime.ensure_job_store()
        record = submodule("core.api.catalog").ModelRecord.from_api(self.model)
        self.generation.set_catalog([record], [record])
        self.lane = bpy.context.scene.scenario.lane_state("image")
        self.lane.prompt = "a teapot"
        self.enterContext(
            patch.object(
                self.runtime, "ensure_manager", side_effect=AssertionError("Prototype manager used")
            )
        )

    def cleanup_jobs(self):
        self.release.set()
        self.runtime.state.reset()
        for session in self.sessions:
            session.shutdown()

    def ui_quote(self):
        self.generation.request_estimate(bpy.context.scene, "image")
        for ticket in tuple(self.runtime.state.model_previews.values()):
            ticket.task.result(5)
        self.runtime.sync_catalog_context()
        self.assertEqual(self.lane.estimate_state, "READY", self.lane.estimate_error)

    def mcp_quote(self):
        deferred = self.tools.estimate_cost(
            {"model_id": self.model["id"], "parameters": {"prompt": "a teapot"}}
        )
        return deferred.finish(deferred.run())

    def mcp_submit(self, quote, **changes):
        args = dict(
            lane="image",
            model_id=self.model["id"],
            parameters={"prompt": "a teapot"},
            quote_id=quote["quote_id"],
            approved_cost=quote["cu_cost_exact"],
        )
        return self.tools.generate(dict(args, **changes))

    def settle(self):
        owner = self.runtime.state.model_jobs
        for task in tuple(owner.submissions.values()):
            try:
                task.result(5)
            except Exception:
                pass  # Stored state and the assertions below establish the outcome.
        self.runtime.sync_catalog_context()

    def test_ui_and_mcp_use_same_exact_quote_claim_and_payload_once(self):
        self.ui_quote()
        ui = self.generation.submit_generation(bpy.context, "image")
        self.settle()
        with self.assertRaises((self.request_error, self.origin_error)):
            self.generation.submit_generation(bpy.context, "image")
        quote = self.mcp_quote()
        mcp = self.mcp_submit(quote)
        self.settle()
        with self.assertRaises((self.request_error, self.origin_error)):
            self.mcp_submit(quote)
        self.assertEqual(len(self.paid), 2)
        self.assertEqual(self.paid[0].content, self.paid[1].content)
        self.assertEqual(json.loads(self.paid[0].content), {"prompt": "a teapot"})
        for reference in (ui.local_id, mcp["local_id"]):
            saved = self.store.get(reference)
            self.assertEqual(saved.state, self.storemod.JobState.REMOTE)
            self.assertEqual(saved.intent.quote_cost, "0.1234567890123456789")
            self.assertEqual(
                self.tools.job_status({"job_id": reference})["job_id"], saved.remote_job_id
            )
        self.assertIsNone(self.runtime.state.manager)

    def test_native_generate_operator_consumes_the_displayed_quote(self):
        self.ui_quote()
        self.assertEqual(bpy.ops.scenario.generate(lane="image"), {"FINISHED"})
        self.settle()
        with self.assertRaisesRegex(RuntimeError, "fresh price"):
            bpy.ops.scenario.generate(lane="image")
        self.assertEqual(len(self.paid), 1)

    def test_failed_intent_receipt_consumes_quote_without_dispatch(self):
        quote = self.mcp_quote()
        create = self.store.create

        def committed_failure(intent):
            create(intent)
            raise self.storemod.StoreError("synthetic lost write acknowledgement")

        with patch.object(self.store, "create", side_effect=committed_failure):
            with self.assertRaises(self.storemod.StoreError):
                self.mcp_submit(quote)
        with self.assertRaises(self.request_error):
            self.mcp_submit(quote)
        self.assertEqual(len(self.store.records()), 1)
        self.assertEqual(self.store.records()[0].state, self.storemod.JobState.PREPARED)
        self.assertEqual(self.paid, [])

    def test_missing_changed_or_unapproved_quote_cannot_spend(self):
        with self.assertRaises((self.request_error, self.origin_error)):
            self.generation.submit_generation(bpy.context, "image")
        quote = self.mcp_quote()
        for changes in (
            {"quote_id": "unknown"},
            {"approved_cost": "0"},
            {"parameters": {"prompt": "changed"}},
            {"approved_cost": float(quote["cu_cost_exact"])},
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises((self.request_error, self.origin_error)),
            ):
                self.mcp_submit(quote, **changes)
        self.assertEqual(self.store.records(), ())
        self.assertEqual(self.paid, [])
        self.ui_quote()
        self.lane.prompt = "changed after display"
        with self.assertRaises((self.request_error, self.origin_error)):
            self.generation.submit_generation(bpy.context, "image")
        self.assertEqual(self.paid, [])

    def test_lost_response_is_durable_uncertainty_and_never_replays(self):
        self.lose_response = True
        quote = self.mcp_quote()
        result = self.mcp_submit(quote)
        self.settle()
        request_id = result["local_id"]
        self.assertEqual(self.store.get(request_id).state, self.storemod.JobState.UNCERTAIN)
        with self.assertRaises((self.request_error, self.origin_error)):
            self.mcp_submit(quote)
        self.runtime.state.reset()
        self.assertEqual(self.tools.job_status({"job_id": request_id})["status"], "uncertain")
        self.assertEqual(len(self.paid), 1)

    def test_storage_claim_failure_stops_sdk_dispatch(self):
        quote = self.mcp_quote()
        with patch.object(
            self.store,
            "transition",
            side_effect=self.storemod.StoreError("synthetic storage failure"),
        ):
            result = self.mcp_submit(quote)
            self.settle()
        self.assertEqual(self.paid, [])
        self.assertEqual(self.store.get(result["local_id"]).state, self.storemod.JobState.PREPARED)
        with self.assertRaises((self.request_error, self.origin_error)):
            self.mcp_submit(quote)

    def test_scene_change_and_retired_credentials_reject_quotes(self):
        quote = self.mcp_quote()
        self.runtime.state.job_session.invalidate_scene(bpy.context.scene)
        with self.assertRaises((self.request_error, self.origin_error)):
            self.mcp_submit(quote)
        quote = self.mcp_quote()
        self.prefs.api_secret = "other-synthetic-secret"
        with self.assertRaises((self.request_error, self.origin_error)):
            self.mcp_submit(quote)
        self.assertEqual(self.paid, [])

    def test_inflight_receipt_stays_in_original_scope_after_switch(self):
        quote = self.mcp_quote()
        self.release.clear()
        result = self.mcp_submit(quote)
        old_owner = self.runtime.state.model_jobs
        task = old_owner.submissions[result["local_id"]]
        self.assertTrue(self.entered.wait(5))
        self.prefs.api_secret = "other-synthetic-secret"
        self.release.set()
        task.result(5)
        self.assertEqual(self.store.get(result["local_id"]).state, self.storemod.JobState.REMOTE)
        self.assertEqual(self.tools.list_local_jobs({})["jobs"], [])
        self.assertEqual(self.runtime.state.jobs_view, [])
        self.assertEqual(len(self.paid), 1)
