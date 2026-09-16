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

        self.handler = respond
        adapter = self.api.SDKAdapter(
            self.api.Credentials("key", "secret"),
            online=lambda: True,
            account_id=self.scope.account_id,
            base_url=self.scope.service,
            transport=httpx.MockTransport(lambda request: self.handler(request)),
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
        origin = self.session.capture(self.scene, self.target)
        quote = self.session._coordinator._adapter.estimate_workflow(
            {"id": "fixture-workflow", "inputs": []}, {}
        )
        return self.session.prepare(quote, origin=origin)

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

    def test_scene_changed_during_estimate_cannot_be_rebound_to_new_revision(self):
        origin = self.session.capture(self.scene, self.target)
        quote = self.session._coordinator._adapter.estimate_workflow(
            {"id": "fixture-workflow", "inputs": []}, {}
        )
        self.target.location.x += 1
        bpy.context.view_layer.update()
        with self.assertRaises(self.module.OriginUnavailable):
            self.session.prepare(quote, origin=origin)
        self.assertEqual(self.store.records(), ())
        self.assertEqual(len(self.calls), 1)

    def test_timer_start_failure_releases_new_workers_and_connection(self):
        from unittest.mock import patch

        import httpx

        adapter = self.api.SDKAdapter(
            self.api.Credentials("key", "secret"),
            online=lambda: False,
            account_id=self.scope.account_id,
            base_url=self.scope.service,
            transport=httpx.MockTransport(lambda request: self.fail("Unexpected request")),
        )
        before_sessions = set(self.module._sessions)
        before_threads = set(threading.enumerate())
        with (
            patch.object(bpy.app.timers, "is_registered", return_value=False),
            patch.object(
                bpy.app.timers, "register", side_effect=RuntimeError("fixture timer exhaustion")
            ),
        ):
            with self.assertRaisesRegex(RuntimeError, "timer exhaustion"):
                self.module.JobSession(adapter, self.store)
        self.assertEqual(self.module._sessions, before_sessions)
        self.assertEqual(set(threading.enumerate()), before_threads)
        self.assertTrue(adapter._sdk.is_closed())

    def test_render_thread_handler_invalidates_without_blender_access(self):
        origin = self.session.capture(self.scene, self.target)
        with ThreadPoolExecutor(max_workers=1) as pool:
            pool.submit(self.module._scene_changed, None, None).result(5)
        self.assertFalse(self.session._origins.current(origin))

    def test_deleted_scene_invalidates_queued_spend_from_surviving_scene_update(self):
        from types import SimpleNamespace

        commands = submodule("core.jobs.coordinator")
        storage = submodule("core.jobs.store")
        first, second = self.prepare(), self.prepare()
        entered, release = threading.Event(), threading.Event()
        original = self.handler

        def blocked(request):
            entered.set()
            self.assertTrue(release.wait(5), "Fixture did not release claimed request")
            return original(request)

        self.handler = blocked
        running = self.session.submit(
            first, operation="workflow", target_id="fixture-workflow", payload={}
        )
        try:
            self.assertTrue(entered.wait(5))
            queued = self.session.submit(
                second, operation="workflow", target_id="fixture-workflow", payload={}
            )
            bpy.data.scenes.remove(self.scene)
            self.scene = None
            self.module._scene_changed(bpy.context.scene, SimpleNamespace(updates=()))
            self.assertFalse(self.session._origins.current(second.intent.origin))
            release.set()
            self.assertEqual(running.result(5).state, storage.JobState.REMOTE)
            with self.assertRaisesRegex(commands.QuoteError, "Origin changed"):
                queued.result(5)
            self.assertEqual(
                self.store.get(second.intent.request_id).state, storage.JobState.PREPARED
            )
            self.assertEqual(len(self.calls), 3)  # Two estimates, one already-claimed submission.
        finally:
            release.set()

    def test_frame_pre_with_empty_depsgraph_invalidates_origin(self):
        from types import SimpleNamespace

        origin = self.session.capture(self.scene, self.target)
        self.assertIn(self.module._frame_change_pre, bpy.app.handlers.frame_change_pre)
        self.module._frame_change_pre(self.scene, SimpleNamespace(updates=()))
        self.assertFalse(self.session._origins.current(origin))

    def test_frame_pre_on_render_thread_does_not_inspect_depsgraph(self):
        class Unevaluated:
            @property
            def updates(self):
                raise AssertionError("Render thread must not inspect Blender depsgraph")

        origin = self.session.capture(self.scene, self.target)
        with ThreadPoolExecutor(max_workers=1) as pool:
            pool.submit(self.module._frame_change_pre, None, Unevaluated()).result(5)
        self.assertFalse(self.session._origins.current(origin))

    def test_drain_keeps_valid_neighbors_and_reports_each_invalid_record(self):
        from dataclasses import replace

        workers = submodule("core.jobs.workers")
        prepared = self.prepare()
        record = self.store.get(prepared.intent.request_id)
        bad_origin = replace(
            record,
            intent=replace(record.intent, origin=replace(record.intent.origin, file_id="other")),
        )
        bad_scope = replace(
            record,
            intent=replace(record.intent, scope=replace(record.intent.scope, account_id="other")),
        )
        for result in (record, bad_origin, object(), bad_scope, record):
            task = workers.JobTask()
            task._future.set_result(result)
            self.session._pending.append((task, record.intent.origin))
        outcomes = self.session.drain()
        self.assertEqual(len(outcomes), 5)
        self.assertEqual(self.session._pending, [])
        self.assertEqual(self.session.drain(), ())
        for index in (0, 4):
            self.assertIsNone(outcomes[index].error)
            self.assertEqual(outcomes[index].result, record)
            self.assertEqual(
                self.session.deliver(outcomes[index], lambda result, scene, target: result), record
            )
        for index in (1, 3):
            self.assertIsInstance(outcomes[index].error, self.module.OriginUnavailable)
            with self.assertRaises(self.module.OriginUnavailable):
                self.session.deliver(
                    outcomes[index], lambda *args: self.fail("Delivered foreign result")
                )
        self.assertIsInstance(outcomes[2].error, AttributeError)

    def _second_session(self):
        import httpx

        adapter = self.api.SDKAdapter(
            self.api.Credentials("key", "secret"),
            online=lambda: False,
            account_id=self.scope.account_id,
            base_url=self.scope.service,
            transport=httpx.MockTransport(lambda request: self.fail("Unexpected request")),
        )
        self.addCleanup(adapter.close)
        session = self.module.JobSession(adapter, self.store, workers=1)
        self.addCleanup(session.shutdown)
        return session, adapter

    def test_unregister_isolates_failed_sdk_close_and_cleans_remaining_owner(self):
        from unittest.mock import patch

        second, adapter = self._second_session()
        first_sdk = self.session._coordinator._adapter._sdk
        try:
            with (
                patch.object(self.module, "_session_snapshot", return_value=(self.session, second)),
                patch.object(first_sdk, "close", side_effect=RuntimeError("private signed URL")),
                self.assertLogs("scenario.jobs", level="WARNING") as logs,
            ):
                self.module.unregister()
            self.assertNotIn("private", " ".join(logs.output))
            self.assertTrue(self.session._workers.stopped)
            self.assertTrue(second._workers.stopped)
            self.assertTrue(adapter._sdk.is_closed())
            self.assertNotIn(self.session, self.module._sessions)
            self.assertNotIn(second, self.module._sessions)
            self.assertFalse(self.module._registered)
            self.assertFalse(bpy.app.timers.is_registered(self.module._reap_inactive))
            for handlers, callback in self.module._HOOKS:
                self.assertNotIn(callback, handlers)
        finally:
            self.module.register()

    def test_reaper_close_failure_keeps_timer_service_for_other_owner(self):
        from unittest.mock import patch

        second, adapter = self._second_session()
        self.session.deactivate()
        first_sdk = self.session._coordinator._adapter._sdk
        with (
            patch.object(first_sdk, "close", side_effect=RuntimeError("private signed URL")),
            self.assertLogs("scenario.jobs", level="WARNING") as logs,
        ):
            self.assertEqual(self.module._reap_inactive(), 0.25)
        self.assertNotIn("private", " ".join(logs.output))
        self.assertNotIn(self.session, self.module._sessions)
        self.assertTrue(self.session._workers.stopped)
        self.assertIn(second, self.module._sessions)
        self.assertTrue(bpy.app.timers.is_registered(self.module._reap_inactive))
        second.deactivate()
        self.assertIsNone(self.module._reap_inactive())
        self.assertTrue(second._workers.stopped)
        self.assertTrue(adapter._sdk.is_closed())
        self.assertNotIn(second, self.module._sessions)

    def test_reaper_preserves_control_exception_after_local_cleanup(self):
        from unittest.mock import patch

        self.session.deactivate()
        first_sdk = self.session._coordinator._adapter._sdk
        with patch.object(first_sdk, "close", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.module._reap_inactive()
        self.assertTrue(self.session._workers.stopped)
        self.assertNotIn(self.session, self.module._sessions)
