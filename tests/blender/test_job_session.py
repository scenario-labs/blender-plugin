# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Installed shared session, main-thread origin checks and real Blender invalidation."""

import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import bpy
from helpers import submodule


class JobSessionTests(unittest.TestCase):
    def setUp(self):
        import httpx

        self.module = submodule("blender.job_session")
        self.api = submodule("core.api.sdk_adapter")
        storage = submodule("core.jobs.store")
        self.temp = tempfile.TemporaryDirectory(dir=bpy.utils.resource_path("USER"))
        self.addCleanup(self.temp.cleanup)
        self.previous = bpy.context.scene
        self.scene = bpy.data.scenes.new("Session fixture")
        bpy.context.window.scene = self.scene
        self.target = bpy.data.objects.new("Session target", None)
        self.scene.collection.objects.link(self.target)
        bpy.context.view_layer.update()
        self.scope = storage.JobScope("https://fixture.invalid/v1", "fixture-account")
        self.store = storage.JobStore(Path(self.temp.name) / "jobs.sqlite3", self.scope)
        self.calls = []

        def respond(request):
            self.calls.append(request)
            if request.url.params.get("dryRun") == "true":
                return httpx.Response(200, json={"creativeUnitsCost": 1})
            return httpx.Response(200, json={"job": {"jobId": "fixture-remote"}})

        adapter = self.api.SDKAdapter(
            self.api.Credentials("key", "secret"),
            online=lambda: True,
            account_id=self.scope.account_id,
            base_url=self.scope.service,
            transport=httpx.MockTransport(respond),
        )
        self.addCleanup(adapter.close)
        self.session = self.module.JobSession(adapter, self.store, workers=1)

    def tearDown(self):
        self.session.shutdown()
        if self.previous in tuple(bpy.data.scenes):
            bpy.context.window.scene = self.previous
        if self.target in tuple(bpy.data.objects):
            bpy.data.objects.remove(self.target, do_unlink=True)
        if self.scene in tuple(bpy.data.scenes):
            bpy.data.scenes.remove(self.scene)

    def prepare(self):
        quote = self.session._coordinator._adapter.estimate_workflow(
            {"id": "fixture-workflow", "inputs": []}, {}
        )
        return self.session.prepare(quote, scene=self.scene, target=self.target)

    def completion(self):
        prepared = self.prepare()
        task = self.session.submit(
            prepared, operation="workflow", target_id="fixture-workflow", payload={}
        )
        task.result(5)
        return self.session.drain()[0]

    def test_delivery_uses_captured_target_on_main_thread_once(self):
        completion = self.completion()
        observed = []
        self.session.deliver(
            completion,
            lambda result, scene, target: observed.append(
                (threading.current_thread(), scene, target, result.intent.origin)
            ),
        )
        self.assertEqual(
            observed, [(threading.main_thread(), self.scene, self.target, completion.origin)]
        )
        with self.assertRaises(self.module.OriginUnavailable):
            self.session.deliver(completion, lambda *args: self.fail("Delivered twice"))

    def test_real_dependency_update_invalidates_quote_and_result(self):
        completion = self.completion()
        self.target.location.x += 1
        bpy.context.view_layer.update()
        with self.assertRaises(self.module.OriginUnavailable):
            self.session.deliver(completion, lambda *args: self.fail("Applied stale result"))
        fresh = self.session.capture(self.scene, self.target)
        self.assertNotEqual(fresh.revision, completion.origin.revision)

    def test_deleted_target_is_not_rebound_by_name(self):
        completion = self.completion()
        name = self.target.name
        bpy.data.objects.remove(self.target, do_unlink=True)
        self.target = bpy.data.objects.new(name, None)
        self.scene.collection.objects.link(self.target)
        with self.assertRaises(self.module.OriginUnavailable):
            self.session.deliver(completion, lambda *args: self.fail("Rebound removed target"))

    def test_other_scene_selection_blocks_delivery(self):
        completion = self.completion()
        bpy.context.window.scene = self.previous
        with self.assertRaises(self.module.OriginUnavailable):
            self.session.deliver(completion, lambda *args: self.fail("Applied to another scene"))

    def test_frame_change_invalidates_origin(self):
        origin = self.session.capture(self.scene, self.target)
        self.scene.frame_set(self.scene.frame_current + 1)
        self.assertFalse(self.session._origins.current(origin))

    def test_file_load_hook_deactivates_and_preserves_stored_record(self):
        completion = self.completion()
        request_id = completion.result.intent.request_id
        self.assertIn(self.module._load_pre, bpy.app.handlers.load_pre)
        self.module._load_pre(None)
        self.assertEqual(self.store.get(request_id), completion.result)
        with self.assertRaises(self.module.OriginUnavailable):
            self.session.deliver(completion, lambda *args: self.fail("Applied after file switch"))

    def test_worker_cannot_access_blender_session(self):
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(self.session.capture, self.scene, self.target)
            with self.assertRaisesRegex(RuntimeError, "main thread"):
                future.result(5)

    def test_registration_is_idempotent_and_shutdown_removes_owner(self):
        self.module.register()
        self.module.register()
        for handlers, callback in self.module._HOOKS:
            self.assertEqual(handlers.count(callback), 1)
        self.session.shutdown()
        self.assertNotIn(self.session, self.module._sessions)
        self.assertTrue(all(not t.is_alive() for t in self.session._workers._threads))

    def test_undrained_outcomes_bound_admission_and_can_be_drained(self):
        self.session._completion_limit = 1
        first, second = self.prepare(), self.prepare()
        task = self.session.submit(
            first, operation="workflow", target_id="fixture-workflow", payload={}
        )
        task.result(5)
        with self.assertRaisesRegex(RuntimeError, "Drain completed"):
            self.session.submit(
                second, operation="workflow", target_id="fixture-workflow", payload={}
            )
        self.assertEqual(len(self.session.drain()), 1)
        self.session.submit(
            second, operation="workflow", target_id="fixture-workflow", payload={}
        ).result(5)

    def test_retired_owner_is_reaped_without_waiting_for_network(self):
        self.completion()
        self.session.deactivate()
        self.module._reap_inactive()
        self.assertNotIn(self.session, self.module._sessions)
        self.assertTrue(self.session._workers._closed)
