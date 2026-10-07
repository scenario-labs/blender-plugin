# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Active UI/MCP model spend boundary against the bundled SDK and real storage."""

import hashlib
import io
import json
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import bpy
import httpx
from helpers import animated_glb, online_access, reset_scene, submodule, temp_credentials


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
            patch.object(
                self.runtime,
                "paths",
                return_value=SimpleNamespace(
                    state_dir=Path(root), registry_file=Path(root) / "jobs.json"
                ),
            )
        )
        self.calls, self.paid, self.sessions = [], [], []
        self.downloads = []
        self.remote_status = "in-progress"
        self.result_bytes = b""
        self.result_media_type = "image/png"
        self.before_images = set(bpy.data.images)
        self.download_error = False
        self.cancel_calls = []
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
                if "/jobs/" in request.url.path:
                    if getattr(self, "block_cloud_read", False):
                        self.entered.set()
                        self.assertTrue(self.release.wait(5))
                    return httpx.Response(
                        200,
                        json={
                            "job": {
                                "jobId": request.url.path.rsplit("/", 1)[-1],
                                "status": self.remote_status,
                                "jobType": "custom",
                                "metadata": {
                                    "input": {"modelId": self.model["id"]},
                                    "assetIds": list(
                                        getattr(self, "result_assets", ["result-image"])
                                    ),
                                },
                            }
                        },
                    )
                if "/assets/" in request.url.path:
                    asset_id = request.url.path.rsplit("/", 1)[-1]
                    return httpx.Response(
                        200,
                        json={
                            "asset": {
                                "id": asset_id,
                                "status": "success",
                                "mimeType": self.result_media_type,
                                "metadata": getattr(self, "result_assets", {}).get(
                                    asset_id, getattr(self, "result_metadata", {})
                                ),
                                "properties": {"size": len(self.result_bytes)},
                                "url": "https://cdn.cloud.scenario.com/fixture.png",
                            }
                        },
                    )
                return httpx.Response(200, json={"model": self.model})
            if "/jobs/" in request.url.path:
                self.assertEqual(json.loads(request.content), {"action": "cancel"})
                self.cancel_calls.append(request)
                self.remote_status = "canceled"
                return httpx.Response(200, json={"job": {"jobId": "remote-1"}})
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
        transfer = submodule("core.jobs.transfers")

        def connect(host, **kwargs):
            self.assertIsNot(threading.current_thread(), threading.main_thread())
            self.assertEqual(host, "cdn.cloud.scenario.com")
            if self.download_error:
                raise OSError("synthetic private transfer failure")
            response = Mock(status=200)
            response.getheader.side_effect = lambda name, default=None: (
                str(len(self.result_bytes)) if name == "Content-Length" else default
            )
            response.read1.side_effect = io.BytesIO(self.result_bytes).read1
            connection = Mock()
            connection.sock.fileno.return_value = 1
            connection.getresponse.return_value = response
            self.downloads.append(connection)
            return connection

        self.enterContext(
            patch.object(transfer.http.client, "HTTPSConnection", side_effect=connect)
        )
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
        for image in set(bpy.data.images) - self.before_images:
            bpy.data.images.remove(image)

    def result_fixture(self):
        image = bpy.data.images.new("Pipeline fixture", width=3, height=5)
        try:
            image.pixels[:] = [0.5, 0.25, 0.125, 1.0] * 15
            image.file_format = "PNG"
            path = self.runtime.paths().state_dir / "fixture.png"
            image.filepath_raw = str(path)
            image.save()
            self.result_bytes = path.read_bytes()
        finally:
            bpy.data.images.remove(image)
        self.remote_status = "success"

    def deliver_results(self):
        owner = self.runtime.state.model_jobs
        self.settle()
        for _ in range(10):
            if not owner._commands:
                return
            for _, task in tuple(owner._commands.values()):
                try:
                    task.result(5)
                except Exception:
                    pass  # Assert persisted outcome and main-thread delivery below.
            self.runtime.sync_catalog_context()
        self.fail("Result pipeline did not settle")

    def test_ui_and_mcp_deliver_verified_packed_results_without_another_submission(self):
        self.result_fixture()
        self.ui_quote()
        ui = self.generation.submit_generation(bpy.context, "image")
        self.deliver_results()
        mcp = self.mcp_submit(self.mcp_quote())
        self.deliver_results()
        self.assertEqual(len(self.paid), 2)
        self.assertEqual(len(self.downloads), 2)
        self.assertIsNone(ui.error)
        for reference in (ui.local_id, mcp["local_id"]):
            status = self.tools.job_status({"job_id": reference})
            self.assertEqual(status["status"], "applied", status)
            self.assertFalse(status["delivery_paused"])
            self.assertEqual(len(status["images"]), 1)
            image = bpy.data.images[status["images"][0]]
            self.assertEqual(tuple(image.size), (3, 5))
            self.assertTrue(image.use_fake_user)
            self.assertEqual(image.filepath, "")
            self.assertEqual(
                hashlib.sha256(image.packed_file.data).digest(),
                hashlib.sha256(self.result_bytes).digest(),
            )
        for connection in self.downloads:
            connection.request.assert_called_once_with(
                "GET",
                "/fixture.png",
                headers={"Accept-Encoding": "identity", "Connection": "close"},
            )

    def test_cloud_job_adoption_restarts_and_uses_explicit_download_and_application(self):
        self.result_fixture()
        before = set(bpy.data.images)
        session = self.runtime.ensure_job_session()
        task = session.adopt_cloud_job(
            "cloud-job", expected_model_id=self.model["id"], scene=bpy.context.scene
        )
        saved = task.result(5)
        self.assertIsNone(session.drain(task=task)[0].error)
        self.assertEqual(saved.intent.source, "cloud")
        self.assertIsNone(saved.intent.quote_cost)
        self.assertEqual(self.paid, [])
        self.assertEqual(self.downloads, [])
        self.assertEqual(set(bpy.data.images), before)
        self.runtime.state.reset()
        row = self.tools.list_local_jobs({})["jobs"][0]
        self.assertEqual(row["source"], "cloud")
        self.assertIsNone(row["cu_cost_exact"])
        owner = self.runtime.inspect_model_jobs()
        status = owner.status(saved.intent.request_id)
        self.assertIsNone(status["cu_cost"])
        self.assertTrue(status["delivery_paused"])
        with self.assertRaisesRegex(ValueError, "explicit destination approval"):
            self.tools.import_result({"job_id": "cloud-job"})
        owner.control(saved.intent.request_id, saved.revision, "resume")
        self.deliver_results()
        ready = owner.store.get(saved.intent.request_id)
        self.assertEqual(ready.state, self.storemod.JobState.READY)
        self.assertEqual(set(bpy.data.images), before)
        ticket = owner.prepare_image_application(
            saved.intent.request_id, ready.revision, bpy.context.scene
        )
        owner.apply_saved_images(ticket.identifier)
        self.deliver_results()
        applied = owner.store.get(saved.intent.request_id)
        self.assertEqual(applied.state, self.storemod.JobState.APPLIED)
        self.assertEqual(len(set(bpy.data.images) - before), 1)
        self.assertEqual(self.paid, [])
        self.assertTrue(all(request.method == "GET" for request in self.calls))

    def test_native_cloud_recovery_and_mcp_repeat_use_one_saved_record_without_application(self):
        self.result_fixture()
        before = set(bpy.data.images)
        self.assertEqual(
            bpy.ops.scenario.import_result(job_id="cloud-ui", model_id=self.model["id"]),
            {"FINISHED"},
        )
        owner = self.runtime.state.model_jobs
        owner.cloud_reads["cloud-ui"].task.result(5)
        self.generation.process_model_jobs()
        record = self.store.records()[0]
        self.assertEqual(record.intent.source, "cloud")
        self.assertEqual(record.state, self.storemod.JobState.SUCCEEDED)
        self.assertTrue(owner.status(record.intent.request_id)["delivery_paused"])
        self.assertIs(self.runtime.state.jobs_view[0], owner.views[record.intent.request_id])
        self.runtime.state.reset()
        deferred = self.tools.recover_cloud_job(
            {"job_id": "cloud-ui", "model_id": self.model["id"]}
        )
        result = deferred.finish(deferred.run())
        self.assertEqual(result["request_id"], record.intent.request_id)
        self.assertEqual(self.store.records(), (record,))
        self.assertEqual(set(bpy.data.images), before)
        self.assertFalse(self.downloads or self.paid)
        self.assertEqual(len(self.calls), 2)

    def test_pending_native_and_mcp_cloud_reads_share_one_worker(self):
        self.result_fixture()
        self.block_cloud_read = True
        self.release.clear()
        try:
            bpy.ops.scenario.import_result(job_id="cloud-pending", model_id=self.model["id"])
            self.assertTrue(self.entered.wait(5))
            owner = self.runtime.state.model_jobs
            item = owner.cloud_reads["cloud-pending"]
            deferred = self.tools.recover_cloud_job(
                {"job_id": "cloud-pending", "model_id": self.model["id"]}
            )
            self.assertIs(owner.cloud_reads["cloud-pending"], item)
            self.assertEqual(len(self.calls), 1)
        finally:
            self.release.set()
        result = deferred.finish(deferred.run())
        self.assertEqual(len(self.store.records()), 1)
        self.assertEqual(result["state"], "succeeded")
        self.assertFalse(self.downloads or self.paid)

    def test_cloud_recovery_operator_works_in_edit_sculpt_and_pose_modes(self):
        self.result_fixture()
        for mode in ("EDIT", "SCULPT", "POSE"):
            with self.subTest(mode=mode):
                if mode == "POSE":
                    bpy.ops.object.armature_add()
                else:
                    bpy.ops.mesh.primitive_cube_add()
                obj = bpy.context.object
                bpy.ops.object.mode_set(mode=mode)
                try:
                    before = tuple(bpy.data.objects), tuple(bpy.data.images), bpy.context.mode
                    self.assertTrue(bpy.ops.scenario.import_result.poll())
                    self.assertEqual(
                        bpy.ops.scenario.import_result(job_id=mode, model_id=self.model["id"]),
                        {"FINISHED"},
                    )
                    owner = self.runtime.state.model_jobs
                    item = owner.cloud_reads[mode]
                    item.task.result(5)
                    self.generation.process_model_jobs()
                    self.assertIs(owner.finish_cloud(item), item.record)
                    self.assertTrue(owner.status(item.record.intent.request_id)["delivery_paused"])
                    self.assertEqual(
                        (tuple(bpy.data.objects), tuple(bpy.data.images), bpy.context.mode), before
                    )
                    self.assertIs(bpy.context.object, obj)
                finally:
                    bpy.ops.object.mode_set(mode="OBJECT")
        self.assertEqual(len(self.calls), 3)
        self.assertFalse(self.downloads or self.paid)
        with online_access(False):
            self.assertFalse(bpy.ops.scenario.import_result.poll())
        with patch.object(self.runtime, "credentials", return_value=SimpleNamespace(valid=False)):
            self.assertFalse(bpy.ops.scenario.import_result.poll())

    def test_native_and_mcp_cloud_read_deliver_after_scene_switch_without_application(self):
        self.result_fixture()
        original = bpy.context.scene
        other = bpy.data.scenes.new("Other cloud reader scene")
        self.block_cloud_read = True
        self.release.clear()
        try:
            bpy.ops.scenario.import_result(job_id="cloud-switch", model_id=self.model["id"])
            self.assertTrue(self.entered.wait(5))
            deferred = self.tools.recover_cloud_job(
                {"job_id": "cloud-switch", "model_id": self.model["id"]}
            )
            owner = self.runtime.state.model_jobs
            item = owner.cloud_reads["cloud-switch"]
            bpy.context.window.scene = other
            self.runtime.sync_catalog_context()
            before = tuple(bpy.data.objects), tuple(bpy.data.images)
            self.release.set()
            deferred.run()
            self.generation.process_model_jobs()
            result = deferred.finish(None)
            self.assertEqual(result["request_id"], item.record.intent.request_id)
            self.assertEqual(item.error, "")
            self.assertTrue(owner.status(result["request_id"])["delivery_paused"])
            self.assertEqual(self.runtime.state.jobs_view[0].local_id, result["request_id"])
            self.assertEqual((tuple(bpy.data.objects), tuple(bpy.data.images)), before)
            self.assertIs(bpy.context.scene, other)
            self.assertEqual(len(self.calls), 1)
            self.assertFalse(self.downloads or self.paid)
        finally:
            self.release.set()
            bpy.context.window.scene = original
            bpy.data.scenes.remove(other)

    def test_cloud_recovery_operator_reports_pending_conflict_and_sanitizes_unexpected_errors(self):
        self.result_fixture()
        operator = submodule("blender.operators").SCENARIO_OT_import_result
        self.block_cloud_read = True
        self.release.clear()
        owner = self.runtime.ensure_model_jobs()
        try:
            item = owner.recover_cloud("cloud-conflict", self.model["id"], bpy.context.scene)
            self.assertTrue(self.entered.wait(5))
            op = SimpleNamespace(job_id="cloud-conflict", model_id="another-model", report=Mock())
            self.assertEqual(operator.execute(op, bpy.context), {"CANCELLED"})
            op.report.assert_called_once_with(
                {"ERROR"}, "This cloud job already has a different model read pending"
            )
            self.assertEqual(len(self.calls), 1)
        finally:
            self.release.set()
        item.task.result(5)
        op = SimpleNamespace(job_id="cloud-unexpected", model_id=self.model["id"], report=Mock())
        with patch.object(owner, "recover_cloud", side_effect=RuntimeError("private fixture")):
            self.assertEqual(operator.execute(op, bpy.context), {"CANCELLED"})
        op.report.assert_called_once_with(
            {"ERROR"}, "Could not inspect saved jobs or start the cloud read"
        )
        self.assertFalse(self.downloads or self.paid)

    def test_cloud_read_failure_is_sanitized_and_explicit_retry_is_read_only(self):
        self.result_fixture()
        deferred = self.tools.recover_cloud_job(
            {"job_id": "cloud-retry", "model_id": "wrong-model"}
        )
        deferred.run()
        with self.assertRaisesRegex(self.request_error, "Could not read this cloud job"):
            deferred.finish(None)
        self.assertFalse(self.store.records())
        deferred = self.tools.recover_cloud_job(
            {"job_id": "cloud-retry", "model_id": self.model["id"]}
        )
        result = deferred.finish(deferred.run())
        self.assertEqual(result["source"], "cloud")
        self.assertEqual(len(self.calls), 2)
        self.assertFalse(self.downloads or self.paid)

    def test_completed_cloud_reads_survive_cache_eviction_before_mcp_delivery(self):
        self.result_fixture()
        pending = []
        for index in range(17):
            deferred = self.tools.recover_cloud_job(
                {"job_id": f"cloud-batch-{index}", "model_id": self.model["id"]}
            )
            owner = self.runtime.state.model_jobs
            item = owner.cloud_reads[f"cloud-batch-{index}"]
            deferred.run()
            self.generation.process_model_jobs()
            pending.append((deferred, item))
        self.assertLessEqual(len(owner.cloud_reads), 16)
        self.assertNotIn("cloud-batch-0", owner.cloud_reads)
        foreign = type(owner)(owner.session, owner.store)
        with self.assertRaisesRegex(self.request_error, "context changed"):
            foreign.finish_cloud(pending[0][1])
        for index, (deferred, _) in enumerate(pending):
            result = deferred.finish(None)
            self.assertEqual(result["job_id"], f"cloud-batch-{index}")
            self.assertEqual(result["state"], "succeeded")
        self.assertEqual(len(self.store.records()), 17)
        self.assertEqual(len(self.calls), 17)
        self.assertFalse(self.downloads or self.paid)

    def test_repeated_completed_read_preserves_each_mcp_callers_result(self):
        self.result_fixture()
        calls = []
        for _ in range(2):
            deferred = self.tools.recover_cloud_job(
                {"job_id": "cloud-repeat", "model_id": self.model["id"]}
            )
            deferred.run()
            self.generation.process_model_jobs()
            calls.append(deferred)
        results = [deferred.finish(None) for deferred in calls]
        self.assertEqual(results[0], results[1])
        self.assertEqual(len(self.store.records()), 1)
        self.assertEqual(len(self.calls), 2)
        self.assertFalse(self.downloads or self.paid)

    def test_prototype_updates_keep_shared_rows_stable_and_limit_only_prototype_rows(self):
        owner = self.runtime.ensure_model_jobs()
        records = submodule("core.jobs.records").JobRecord
        handlers = submodule("blender.handlers")
        shared = [
            records(
                local_id=f"shared-{index}",
                lane="model",
                kind="model",
                model_id="fixture-model",
                body={},
                meta={"shared_job": True},
            )
            for index in range(55)
        ]
        owner.views.update((record.local_id, record) for record in shared)
        with patch.object(owner, "poll"):
            self.generation.process_model_jobs()
            for index in range(60):
                prototype = records(
                    local_id=f"prototype-{index}",
                    lane="image",
                    kind="image",
                    model_id="old",
                    body={},
                )
                handlers._on_job("job_progress", prototype)
                after_event = tuple(self.runtime.state.jobs_view)
                self.generation.process_model_jobs()
                self.assertEqual(tuple(self.runtime.state.jobs_view), after_event)
            for _ in range(5):
                self.generation.process_model_jobs()
                self.assertEqual(tuple(self.runtime.state.jobs_view), after_event)
        rows = self.runtime.state.jobs_view
        self.assertEqual(len(rows), 105)
        self.assertEqual(len({row.local_id for row in rows}), len(rows))
        self.assertEqual([row for row in rows if row.meta.get("shared_job")], shared[::-1])
        self.assertEqual(
            {row.local_id for row in rows if not row.meta.get("shared_job")},
            {f"prototype-{index}" for index in range(10, 60)},
        )
        self.assertFalse(self.calls or self.downloads or self.paid)

    def test_shared_projection_replaces_a_colliding_legacy_row_without_duplicates(self):
        owner = self.runtime.ensure_model_jobs()
        records = submodule("core.jobs.records").JobRecord
        legacy = records(local_id="same-id", lane="image", kind="image", model_id="old", body={})
        shared = replace(legacy, meta={"shared_job": True})
        self.runtime.state.jobs_view.append(legacy)
        owner.views[shared.local_id] = shared
        with patch.object(owner, "poll"):
            self.generation.process_model_jobs()
            submodule("blender.handlers")._on_job("job_progress", legacy)
            self.generation.process_model_jobs()
        self.assertEqual(len(self.runtime.state.jobs_view), 1)
        self.assertIs(self.runtime.state.jobs_view[0], shared)
        self.assertFalse(self.calls or self.downloads or self.paid)

    def test_cloud_read_completion_cannot_follow_changed_credentials(self):
        self.result_fixture()
        deferred = self.tools.recover_cloud_job(
            {"job_id": "cloud-scope", "model_id": self.model["id"]}
        )
        deferred.run()
        saved = self.store.records()
        self.assertEqual(len(saved), 1)
        self.prefs.api_secret = "different-fixture-secret"
        with self.assertRaisesRegex(self.request_error, "context changed"):
            deferred.finish(None)
        self.assertEqual(self.store.records(), saved)
        self.assertFalse(self.runtime.ensure_job_store().records())
        self.assertFalse(self.downloads or self.paid)

    def test_cloud_read_completes_after_view_closure_without_applying(self):
        self.result_fixture()
        owner = self.runtime.ensure_model_jobs()
        item = owner.recover_cloud("cloud-closed", self.model["id"], bpy.context.scene)
        self.runtime.state.jobs_view.clear()
        item.task.result(5)
        self.runtime.sync_catalog_context()
        self.assertFalse(item.pending)
        self.assertIsNone(item.record.intent.quote_cost)
        self.assertEqual(self.runtime.state.jobs_view[0].local_id, item.record.intent.request_id)
        self.assertTrue(owner.status(item.record.intent.request_id)["delivery_paused"])
        self.assertFalse(self.downloads or self.paid)

    def test_stale_origin_downloads_but_does_not_apply_or_resubmit(self):
        self.result_fixture()
        result = self.mcp_submit(self.mcp_quote())
        owner = self.runtime.state.model_jobs
        owner.submissions[result["local_id"]].result(5)
        owner.session.invalidate_scene(bpy.context.scene)
        before = set(bpy.data.images)
        self.deliver_results()
        status = self.tools.job_status({"job_id": result["local_id"]})
        self.assertEqual(status["status"], "ready")
        self.assertTrue(status["delivery_paused"])
        self.assertEqual(set(bpy.data.images), before)
        self.assertEqual(len(self.paid), 1)
        self.assertEqual(len(self.downloads), 1)

    def test_failed_download_stops_without_automatic_retry_or_paid_replay(self):
        self.result_fixture()
        self.download_error = True
        result = self.mcp_submit(self.mcp_quote())
        self.deliver_results()
        status = self.tools.job_status({"job_id": result["local_id"]})
        self.assertEqual(status["status"], "download_failed")
        self.assertTrue(status["delivery_paused"])
        count = len(self.calls)
        self.download_error = False
        for _ in range(5):
            self.runtime.sync_catalog_context()
        self.assertEqual(len(self.calls), count)
        self.assertEqual(len(self.paid), 1)
        self.assertEqual(self.downloads, [])

    def recovery_args(self, request_id, action):
        inspection = self.tools.list_local_jobs({})
        item = next(job for job in inspection["jobs"] if job["request_id"] == request_id)
        return dict(
            context_id=inspection["context_id"],
            request_id=request_id,
            expected_revision=item["revision"],
            action=action,
        )

    def recover(self, request_id, action):
        deferred = self.tools.recover_local_job(self.recovery_args(request_id, action))
        if isinstance(deferred, dict):
            return deferred
        return deferred.finish(deferred.run())

    def test_restart_inspection_and_resume_download_do_not_rebind_application(self):
        self.result_fixture()
        self.remote_status = "in-progress"
        result = self.mcp_submit(self.mcp_quote())
        self.deliver_results()
        self.runtime.state.reset()
        before, calls = set(bpy.data.images), len(self.calls)
        self.assertEqual(bpy.ops.scenario.inspect_saved_jobs(), {"FINISHED"})
        self.assertEqual(len(self.calls), calls)
        self.assertEqual(len(self.runtime.state.jobs_view), 1)
        self.remote_status = "success"
        self.recover(result["local_id"], "resume")
        self.deliver_results()
        self.assertEqual(self.store.get(result["local_id"]).state, self.storemod.JobState.READY)
        self.assertEqual(set(bpy.data.images), before)
        self.assertEqual(len(self.downloads), 1)
        self.assertEqual(len(self.paid), 1)

    def test_native_download_retry_uses_same_saved_job_without_generation(self):
        self.result_fixture()
        self.download_error = True
        result = self.mcp_submit(self.mcp_quote())
        self.deliver_results()
        self.download_error = False
        before = set(bpy.data.images)
        args = self.recovery_args(result["local_id"], "resume")
        self.assertEqual(bpy.ops.scenario.recover_job(**args), {"FINISHED"})
        self.deliver_results()
        self.assertEqual(self.store.get(result["local_id"]).state, self.storemod.JobState.READY)
        self.assertEqual(set(bpy.data.images), before)
        self.assertEqual(len(self.paid), 1)
        self.assertEqual(len(self.downloads), 1)

    def recovered_images(self):
        self.result_fixture()
        result = self.mcp_submit(self.mcp_quote())
        owner = self.runtime.state.model_jobs
        owner.submissions[result["local_id"]].result(5)
        owner.session.invalidate_scene(bpy.context.scene)
        self.deliver_results()
        self.runtime.state.reset()
        self.runtime.inspect_model_jobs()
        self.assertEqual(self.store.get(result["local_id"]).state, self.storemod.JobState.READY)
        return result["local_id"]

    def prepare_import(self, request_id):
        args = self.recovery_args(request_id, "import_images")
        del args["action"]
        return self.tools.prepare_result_application(args)

    def import_args(self, approval):
        return {key: approval[key] for key in ("context_id", "application_id")}

    def test_mcp_recovered_images_require_destination_approval_and_import_once(self):
        request_id = self.recovered_images()
        original = self.store.get(request_id)
        before, calls = set(bpy.data.images), len(self.calls)
        approval = self.prepare_import(request_id)
        self.assertEqual(approval["scene"], bpy.context.scene.name)
        self.assertEqual(len(approval["images"]), 1)
        self.assertEqual(set(bpy.data.images), before)
        self.assertEqual(self.store.get(request_id), original)
        self.assertEqual(len(self.calls), calls)
        with self.assertRaises(self.request_error):
            self.tools.recover_local_job(self.recovery_args(request_id, "import_images"))
        deferred = self.tools.apply_result_application(self.import_args(approval))
        status = deferred.finish(deferred.run())
        saved = self.store.get(request_id)
        self.assertEqual(status["status"], "applied", status)
        self.assertEqual(len(status["images"]), 1)
        self.assertEqual(saved.intent, original.intent)
        self.assertNotEqual(saved.application_origin.file_id, saved.intent.origin.file_id)
        self.assertIsNotNone(bpy.data.images[status["images"][0]].packed_file)
        with self.assertRaises(self.request_error):
            self.tools.apply_result_application(self.import_args(approval))
        fresh = self.prepare_import(request_id)
        self.assertTrue(fresh["reuse"])
        self.assertEqual(self.store.get(request_id), saved)
        self.assertEqual(len(self.calls), calls)
        self.assertEqual(len(self.paid), 1)

    def test_recovered_application_rejects_scene_change_before_and_during_verification(self):
        request_id = self.recovered_images()
        before = set(bpy.data.images)
        for after_queue in (False, True):
            approval = self.prepare_import(request_id)
            owner = self.runtime.state.model_jobs
            if after_queue:
                deferred = self.tools.apply_result_application(self.import_args(approval))
                result = deferred.run()
            owner.session.invalidate_scene(bpy.context.scene)
            if after_queue:
                status = deferred.finish(result)
                self.assertEqual(status["status"], "ready", status)
                self.assertTrue(status["error"])
            else:
                with self.assertRaises(submodule("blender.job_session").OriginUnavailable):
                    self.tools.apply_result_application(self.import_args(approval))
            with self.assertRaises(self.request_error):
                self.tools.apply_result_application(self.import_args(approval))
            self.assertEqual(set(bpy.data.images), before)
            self.assertEqual(self.store.get(request_id).state, self.storemod.JobState.READY)
        self.assertEqual(len(self.paid), 1)

    def test_recovered_application_rejects_file_context_change(self):
        request_id = self.recovered_images()
        approval = self.prepare_import(request_id)
        before = set(bpy.data.images)
        self.runtime.state.reset()
        with self.assertRaises(self.request_error):
            self.tools.apply_result_application(self.import_args(approval))
        self.assertEqual(set(bpy.data.images), before)
        self.assertEqual(self.store.get(request_id).state, self.storemod.JobState.READY)

    def test_native_import_requires_a_prepared_destination_and_preserves_original_origin(self):
        request_id = self.recovered_images()
        original = self.store.get(request_id)
        args = self.recovery_args(request_id, "import_images")
        del args["action"]
        with self.assertRaises(RuntimeError):
            bpy.ops.scenario.import_saved_images(**args)
        approval = self.prepare_import(request_id)
        self.assertEqual(
            bpy.ops.scenario.import_saved_images(**args, application_id=approval["application_id"]),
            {"FINISHED"},
        )
        self.deliver_results()
        saved = self.store.get(request_id)
        self.assertEqual(saved.state, self.storemod.JobState.APPLIED)
        self.assertEqual(saved.intent, original.intent)
        self.assertNotEqual(saved.application_origin, original.intent.origin)
        self.assertEqual(len(self.paid), 1)

    def test_recovered_import_receipt_failure_never_repeats_blender_mutation(self):
        request_id = self.recovered_images()
        approval = self.prepare_import(request_id)
        selected_store = self.runtime.state.job_store
        transition = selected_store.transition

        def fail(*args, **kwargs):
            if kwargs.get("state") == self.storemod.JobState.APPLIED:
                raise self.storemod.StoreError("synthetic receipt failure")
            return transition(*args, **kwargs)

        deferred = self.tools.apply_result_application(self.import_args(approval))
        with patch.object(selected_store, "transition", side_effect=fail):
            status = deferred.finish(deferred.run())
        self.assertEqual(status["status"], "applying", status)
        self.assertIn("retry_receipt", status["actions"])
        before = set(bpy.data.images)
        with self.assertRaises(self.request_error):
            self.prepare_import(request_id)
        status = self.recover(request_id, "retry_receipt")
        self.assertEqual(status["status"], "applied", status)
        self.assertEqual(set(bpy.data.images), before)
        self.assertEqual(len(self.paid), 1)

    def test_recovery_rejects_stale_revision_and_context_before_network(self):
        result = self.mcp_submit(self.mcp_quote())
        self.deliver_results()
        args = self.recovery_args(result["local_id"], "refresh")
        calls = len(self.calls)
        with self.assertRaises(self.request_error):
            self.tools.recover_local_job(
                dict(args, expected_revision=args["expected_revision"] + 1)
            )
        with self.assertRaises(self.request_error):
            self.tools.recover_local_job(dict(args, expected_revision=True))
        self.prefs.api_secret = "different-fixture-secret"
        with self.assertRaises(self.request_error):
            self.tools.recover_local_job(args)
        self.assertEqual(len(self.calls), calls)
        self.assertEqual(len(self.paid), 1)

    def test_remote_cancel_observes_terminal_status_and_cannot_repeat(self):
        result = self.mcp_submit(self.mcp_quote())
        self.deliver_results()
        status = self.recover(result["local_id"], "cancel")
        self.assertEqual(status["status"], "canceled", status)
        with self.assertRaises(self.request_error):
            self.recover(result["local_id"], "cancel")
        self.assertEqual(len(self.cancel_calls), 1)
        self.assertEqual(len(self.paid), 1)

    def test_uncertain_submission_has_no_recovery_dispatch_action(self):
        self.lose_response = True
        result = self.mcp_submit(self.mcp_quote())
        self.settle()
        calls = len(self.calls)
        for action in ("refresh", "resume", "cancel", "recover_download", "retry_receipt"):
            with self.subTest(action=action), self.assertRaises(self.request_error):
                self.recover(result["local_id"], action)
        self.assertEqual(len(self.calls), calls)
        self.assertEqual(len(self.paid), 1)

    def test_shared_wait_does_not_block_main_thread_result_delivery(self):
        self.result_fixture()
        result = self.mcp_submit(self.mcp_quote())
        deferred = self.tools.wait_for_job({"job_id": result["local_id"], "timeout": 5})
        with ThreadPoolExecutor(max_workers=1) as worker:
            waiting = worker.submit(deferred.run)
            self.assertFalse(waiting.done())
            self.deliver_results()
            waiting.result(5)
        self.assertEqual(deferred.finish(None)["status"], "applied")
        self.assertEqual(len(self.paid), 1)

    def test_shared_wait_rejects_context_change_without_cancelling_generation(self):
        result = self.mcp_submit(self.mcp_quote())
        self.deliver_results()
        deferred = self.tools.wait_for_job({"job_id": result["local_id"], "timeout": 0.01})
        with ThreadPoolExecutor(max_workers=1) as worker:
            worker.submit(deferred.run).result(5)
        self.prefs.api_secret = "different-fixture-secret"
        with self.assertRaises(self.request_error):
            deferred.finish(None)
        self.assertEqual(self.cancel_calls, [])
        self.assertEqual(len(self.paid), 1)

    def test_shared_wait_stops_with_mcp_without_cancelling_generation(self):
        result = self.mcp_submit(self.mcp_quote())
        self.deliver_results()
        server = Mock(running=True)
        self.runtime.state.mcp = server
        deferred = self.tools.wait_for_job({"job_id": result["local_id"], "timeout": 5})
        with ThreadPoolExecutor(max_workers=1) as worker:
            waiting = worker.submit(deferred.run)
            server.running = False
            with self.assertRaisesRegex(self.request_error, "wait stopped"):
                waiting.result(2)
        with self.assertRaises(self.request_error):
            deferred.finish(None)
        self.assertEqual(self.cancel_calls, [])
        self.assertEqual(len(self.paid), 1)
        self.assertEqual(self.store.get(result["local_id"]).state, self.storemod.JobState.REMOTE)

    def test_explicit_interrupted_download_recovery_uses_receipts_without_network(self):
        self.result_fixture()
        result = self.mcp_submit(self.mcp_quote())
        transition = self.store.transition

        def fail(*args, **kwargs):
            if kwargs.get("state") == self.storemod.JobState.READY:
                raise self.storemod.StoreError("synthetic interrupted final receipt")
            return transition(*args, **kwargs)

        with patch.object(self.store, "transition", side_effect=fail):
            self.deliver_results()
        self.assertEqual(
            self.store.get(result["local_id"]).state, self.storemod.JobState.DOWNLOADING
        )
        before = set(bpy.data.images), len(self.calls), len(self.downloads)
        with online_access(False):
            status = self.recover(result["local_id"], "recover_download")
        self.assertEqual(status["status"], "ready")
        self.assertEqual((set(bpy.data.images), len(self.calls), len(self.downloads)), before)
        self.assertEqual(len(self.paid), 1)

    def test_mcp_import_receipt_retry_never_reimports_images(self):
        self.result_fixture()
        result = self.mcp_submit(self.mcp_quote())
        transition = self.store.transition

        def fail(*args, **kwargs):
            if kwargs.get("state") == self.storemod.JobState.APPLIED:
                raise self.storemod.StoreError("synthetic interrupted application receipt")
            return transition(*args, **kwargs)

        with patch.object(self.store, "transition", side_effect=fail):
            self.deliver_results()
        self.assertEqual(self.store.get(result["local_id"]).state, self.storemod.JobState.APPLYING)
        before = set(bpy.data.images), len(self.calls), len(self.downloads)
        status = self.recover(result["local_id"], "retry_receipt")
        self.assertEqual(status["status"], "applied")
        self.assertEqual((set(bpy.data.images), len(self.calls), len(self.downloads)), before)
        with self.assertRaises(self.request_error):
            self.recover(result["local_id"], "retry_receipt")
        self.assertEqual(len(self.paid), 1)

    def ui_quote(self, lane="image"):
        self.generation.request_estimate(bpy.context.scene, lane)
        for ticket in tuple(self.runtime.state.model_previews.values()):
            ticket.task.result(5)
        self.runtime.sync_catalog_context()
        state = bpy.context.scene.scenario.lane_state(lane)
        self.assertEqual(state.estimate_state, "READY", state.estimate_error)

    def configure_ui_lane(self, lane):
        inputs = [{"name": "prompt", "type": "string", "required": True, "prompt": True}]
        if lane == "edit3d":
            inputs.append({"name": "mesh", "type": "file", "kind": "3d", "required": True})
            bpy.ops.mesh.primitive_cube_add()
        elif lane in ("render_image", "render_video"):
            inputs.append(
                {
                    "name": "reference",
                    "type": "file_array",
                    "kind": "image" if lane == "render_image" else "video",
                }
            )
        self.model["inputs"] = inputs
        record = submodule("core.api.catalog").ModelRecord.from_api(self.model)
        self.runtime.state.records[record.id] = record
        self.generation._schemas.pop(record.id, None)
        self.runtime.set_enum_items(("models", lane), [(record.id, record.name, "")])
        state = bpy.context.scene.scenario.lane_state(lane)
        state.model_id = record.id
        self.generation.on_model_changed(bpy.context, state)
        state.prompt = "a teapot"
        if lane == "edit3d":
            ref = state.references.add()
            ref.param_name, ref.source, ref.asset_id = "mesh", "ASSET", "uploaded-mesh"
        return state

    def mcp_quote(self, lane="image"):
        deferred = self.tools.estimate_cost(
            {"model_id": self.model["id"], "parameters": {"prompt": "a teapot"}, "lane": lane}
        )
        return deferred.finish(deferred.run())

    def mcp_submit(self, quote, **changes):
        args = dict(
            lane=quote["lane"],
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

    def test_confirmed_receipt_clears_transient_submission_warning(self):
        self.ui_quote()
        self.release.clear()
        view = self.generation.submit_generation(bpy.context, "image")
        self.assertTrue(self.entered.wait(5))
        self.runtime.sync_catalog_context()
        self.assertIsNotNone(view.error)
        self.release.set()
        self.settle()
        self.assertIsNone(view.error)
        self.assertEqual(view.status, "in-progress")
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

    def test_rejected_ui_quote_requires_explicit_repricing(self):
        self.ui_quote()
        self.runtime.state.job_session.invalidate_scene(bpy.context.scene)
        with self.assertRaises(self.request_error):
            self.generation.submit_generation(bpy.context, "image")
        self.assertEqual(self.lane.estimate_state, "ERROR")
        self.assertNotIn(self.lane.estimate_key, self.runtime.state.estimates)
        with self.assertRaisesRegex(self.request_error, "fresh price"):
            self.generation.submit_generation(bpy.context, "image")
        self.assertEqual(self.store.records(), ())
        self.assertEqual(self.paid, [])
        self.ui_quote()
        self.generation.submit_generation(bpy.context, "image")
        self.settle()
        self.assertEqual(len(self.paid), 1)

    def test_lost_ui_intent_receipt_clears_ready_price_without_replay(self):
        self.ui_quote()
        create = self.store.create

        def committed_failure(intent):
            create(intent)
            raise self.storemod.StoreError("synthetic lost write acknowledgement")

        with patch.object(self.store, "create", side_effect=committed_failure):
            with self.assertRaises(self.request_error):
                self.generation.submit_generation(bpy.context, "image")
        self.assertEqual(self.lane.estimate_state, "ERROR")
        with self.assertRaisesRegex(self.request_error, "fresh price"):
            self.generation.submit_generation(bpy.context, "image")
        self.assertEqual(len(self.store.records()), 1)
        self.assertEqual(self.paid, [])

    def test_cache_pressure_preserves_ui_and_mcp_approvals(self):
        self.ui_quote()
        quotes = [self.mcp_quote() for _ in range(127)]
        with self.assertRaisesRegex(self.request_error, "retained estimates"):
            self.mcp_quote()
        self.generation.submit_generation(bpy.context, "image")
        self.settle()
        # The consumed UI handle can be reclaimed; the oldest MCP approval
        # remains valid after another quote is admitted.
        self.mcp_quote()
        self.mcp_submit(quotes[0])
        self.settle()
        self.assertEqual(len(self.paid), 2)

    def test_ui_repricing_releases_superseded_approval(self):
        self.ui_quote()
        owner = self.runtime.state.model_jobs
        previous = self.runtime.state.estimates[self.lane.estimate_key]
        self.ui_quote()
        self.assertNotIn(previous.identifier, owner.quotes)
        self.assertEqual(len(owner.quotes), 1)

    def test_repeated_form_edits_release_only_obsolete_ui_quotes(self):
        video = self.configure_ui_lane("video")
        self.configure_ui_lane("audio")
        self.ui_quote("audio")
        audio_key = bpy.context.scene.scenario.lane_state("audio").estimate_key
        audio_ticket = self.runtime.state.estimates[audio_key]
        mcp = self.mcp_quote()
        owner = self.runtime.state.model_jobs
        for index in range(130):
            video.prompt = f"edited prompt {index}"
            self.assertEqual(video.estimate_key, "")
            self.ui_quote("video")
            self.assertEqual(len(owner.quotes), 3)
            self.assertEqual(len(self.runtime.state.estimates), 2)
        self.assertIs(owner.quotes[audio_ticket.identifier], audio_ticket)
        self.assertIn(mcp["quote_id"], owner.quotes)
        video.prompt = "unfinished next edit"
        self.generation.process_model_jobs()
        self.assertEqual(len(owner.quotes), 2)
        self.assertEqual(set(self.runtime.state.estimates), {audio_key})
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

    def test_every_mcp_lane_requires_exact_single_use_quote_before_sdk_submission(self):
        lanes = submodule("core.api.catalog").GENERATION_LANES
        for count, lane in enumerate(lanes, 1):
            with self.subTest(lane=lane):
                with self.assertRaises(self.request_error):
                    self.tools.generate({"lane": lane, "model_id": self.model["id"]})
                quote = self.mcp_quote(lane)
                for changes in ({"approved_cost": "0"}, {"parameters": {"prompt": "changed"}}):
                    with self.assertRaises(self.request_error):
                        self.mcp_submit(quote, **changes)
                result = self.mcp_submit(quote)
                self.settle()
                with self.assertRaises(self.request_error):
                    self.mcp_submit(quote)
                saved = self.store.get(result["local_id"])
                self.assertEqual(saved.state, self.storemod.JobState.REMOTE)
                self.assertEqual(saved.intent.quote_cost, quote["cu_cost_exact"])
                self.assertEqual(len(self.paid), count)
                self.assertEqual(json.loads(self.paid[-1].content), {"prompt": "a teapot"})
                self.assertEqual(self.runtime.state.jobs_view[0].lane, lane)
        self.assertIsNone(self.runtime.state.manager)

    def test_mcp_quote_cannot_change_lane_even_with_identical_payload_and_cost(self):
        for lane in submodule("core.api.catalog").GENERATION_LANES:
            with self.subTest(lane=lane):
                quote = self.mcp_quote(lane)
                other = "image" if lane != "image" else "video"
                with self.assertRaises(self.request_error):
                    self.mcp_submit(quote, lane=other)
        self.assertEqual(self.paid, [])
        self.assertEqual(self.store.records(), ())

    def test_non_image_lanes_preserve_uncertainty_after_restart_without_retry(self):
        self.lose_response = True
        references = []
        for lane in submodule("core.api.catalog").GENERATION_LANES:
            if lane == "image":
                continue
            with self.subTest(lane=lane):
                quote = self.mcp_quote(lane)
                result = self.mcp_submit(quote)
                references.append(result["local_id"])
                self.settle()
                with self.assertRaises(self.request_error):
                    self.mcp_submit(quote)
        self.runtime.state.reset()
        for reference in references:
            self.assertEqual(self.tools.job_status({"job_id": reference})["status"], "uncertain")
        self.assertEqual(len(self.paid), len(references))

    def test_non_image_downloads_remain_saved_without_scene_application(self):
        before = set(bpy.data.images), set(bpy.data.objects), set(bpy.data.materials)
        references = []
        for lane, media_type in (
            ("video", "video/mp4"),
            ("render_video", "video/mp4"),
            ("audio", "audio/wav"),
            ("3d", "model/gltf-binary"),
            ("edit3d", "model/gltf-binary"),
            ("material", "image/png"),
            ("render_image", "image/png"),
        ):
            with self.subTest(lane=lane):
                self.result_media_type = media_type
                self.result_bytes = b"synthetic saved output, never passed to a decoder"
                self.remote_status = "success"
                result = self.mcp_submit(self.mcp_quote(lane))
                reference = result["local_id"]
                references.append((reference, media_type))
                self.deliver_results()
                status = self.tools.job_status({"job_id": reference})
                self.assertEqual(status["status"], "ready", status)
                self.assertIsNone(status["error"])
                self.assertEqual(status["images"], [])
                self.assertEqual(status["files"], [])
                with self.assertRaisesRegex(ValueError, "prepare_result_application"):
                    self.tools.import_result({"job_id": reference})
                self.assertEqual(status["results"][0]["media_type"], media_type)
                self.assertTrue(status["results"][0]["downloaded"])
                self.assertEqual(status["results"][0]["size"], len(self.result_bytes))
                self.assertEqual(
                    (set(bpy.data.images), set(bpy.data.objects), set(bpy.data.materials)), before
                )
                deferred = self.tools.wait_for_job({"job_id": reference, "timeout": 0.01})
                self.assertEqual(deferred.finish(deferred.run())["status"], "ready")
        self.runtime.state.reset()
        calls = len(self.calls)
        self.runtime.inspect_model_jobs()
        for reference, media_type in references:
            status = self.tools.job_status({"job_id": reference})
            self.assertEqual(status["status"], "ready")
            self.assertEqual(status["kind"], "model")
            self.assertEqual(status["results"][0]["media_type"], media_type)
        self.assertEqual(len(self.calls), calls)
        self.assertEqual(len(self.paid), len(references))

    def test_video_remote_cancel_uses_shared_revision_guard_without_replay(self):
        result = self.mcp_submit(self.mcp_quote("video"))
        self.deliver_results()
        status = self.recover(result["local_id"], "cancel")
        self.assertEqual(status["status"], "canceled")
        with self.assertRaises(self.request_error):
            self.recover(result["local_id"], "cancel")
        self.assertEqual(len(self.cancel_calls), 1)
        self.assertEqual(len(self.paid), 1)

    def test_non_image_quote_rejects_changed_scene_and_credentials(self):
        for lane in ("video", "3d", "material", "audio", "render_image", "render_video", "edit3d"):
            with self.subTest(lane=lane):
                # Credential retirement clears catalog metadata. Seed the next
                # context's fixture rather than invoking a separate catalog worker.
                self.runtime.ensure_catalog()
                record = submodule("core.api.catalog").ModelRecord.from_api(self.model)
                self.generation.set_catalog([record], [record])
                quote = self.mcp_quote(lane)
                self.runtime.state.job_session.invalidate_scene(bpy.context.scene)
                with self.assertRaises((self.request_error, self.origin_error)):
                    self.mcp_submit(quote)
                quote = self.mcp_quote(lane)
                self.prefs.api_secret += "-changed"
                with self.assertRaises(self.request_error):
                    self.mcp_submit(quote)
        self.assertEqual(self.paid, [])

    def test_ui_lanes_use_exact_shared_quotes_and_match_mcp_payloads(self):
        panels = submodule("blender.panels")
        for lane in ("image", "video", "3d", "material", "audio", "edit3d"):
            with self.subTest(lane=lane):
                state = self.configure_ui_lane(lane)
                self.assertFalse(panels.generate_enabled(state, lane))
                self.ui_quote(lane)
                self.assertTrue(panels.generate_enabled(state, lane))
                request = self.generation.build_request(bpy.context.scene, lane, for_estimate=True)
                ticket = self.runtime.state.estimates[state.estimate_key]
                self.assertEqual(ticket.lane, lane)
                self.assertEqual(bpy.ops.scenario.generate(lane=lane), {"FINISHED"})
                self.assertFalse(panels.generate_enabled(state, lane))
                self.settle()
                view = self.runtime.state.jobs_view[0]
                saved = self.store.get(view.local_id)
                self.assertEqual(saved.intent.quote_cost, "0.1234567890123456789")
                self.assertEqual(saved.state, self.storemod.JobState.REMOTE)
                self.assertEqual(view.lane, lane)
                ui_payload = self.paid[-1].content
                with self.assertRaises(self.request_error):
                    self.generation.submit_generation(bpy.context, lane)
                args = {"lane": lane, "model_id": self.model["id"], "parameters": request.body}
                deferred = self.tools.estimate_cost(args)
                quote = deferred.finish(deferred.run())
                self.tools.generate(
                    dict(args, quote_id=quote["quote_id"], approved_cost=quote["cu_cost_exact"])
                )
                self.settle()
                self.assertEqual(self.paid[-1].content, ui_payload)
        self.assertEqual(len(self.paid), 12)
        self.assertIsNone(self.runtime.state.manager)

    def test_ui_quote_delivery_stays_in_its_form_after_tab_switch(self):
        video = self.configure_ui_lane("video")
        audio = self.configure_ui_lane("audio")
        for lane in ("video", "audio"):
            self.generation.request_estimate(bpy.context.scene, lane)
        for ticket in tuple(self.runtime.state.model_previews.values()):
            ticket.task.result(5)
        bpy.context.scene.scenario.lane = "image"
        self.runtime.sync_catalog_context()
        self.assertEqual((video.estimate_state, audio.estimate_state), ("READY", "READY"))
        self.assertNotEqual(video.estimate_key, audio.estimate_key)
        previous = self.runtime.state.estimates[video.estimate_key]
        self.ui_quote("video")
        self.assertNotIn(previous.identifier, self.runtime.state.model_jobs.quotes)
        self.assertIn(audio.estimate_key, self.runtime.state.estimates)
        # Copying a ready handle cannot change its original lane.
        video.estimate_key = audio.estimate_key
        self.assertFalse(submodule("blender.panels").generate_enabled(video, "video"))
        with self.assertRaisesRegex(self.request_error, "changed"):
            self.generation.submit_generation(bpy.context, "video")
        self.assertEqual(self.paid, [])

    def test_non_image_ui_lost_responses_remain_uncertain_without_resubmission(self):
        self.lose_response = True
        references = []
        for lane in ("video", "3d", "material", "audio", "edit3d"):
            with self.subTest(lane=lane):
                self.configure_ui_lane(lane)
                self.ui_quote(lane)
                view = self.generation.submit_generation(bpy.context, lane)
                references.append(view.local_id)
                self.settle()
                with self.assertRaisesRegex(self.request_error, "fresh price"):
                    self.generation.submit_generation(bpy.context, lane)
        self.runtime.state.reset()
        for reference in references:
            self.assertEqual(
                self.runtime.ensure_model_jobs().status(reference)["status"], "uncertain"
            )
        self.assertEqual(len(self.paid), len(references))

    def test_non_image_ui_changed_payload_or_origin_cannot_spend(self):
        state = self.configure_ui_lane("audio")
        self.ui_quote("audio")
        state.prompt = "edited after quote"
        with self.assertRaises(self.request_error):
            self.generation.submit_generation(bpy.context, "audio")
        self.ui_quote("audio")
        self.runtime.state.job_session.invalidate_scene(bpy.context.scene)
        with self.assertRaises(self.request_error):
            self.generation.submit_generation(bpy.context, "audio")
        self.assertEqual(self.paid, [])
        self.assertEqual(self.store.records(), ())

    def test_ui_pending_files_captures_and_spark_cannot_quote_or_dispatch(self):
        for lane in submodule("core.api.catalog").GENERATION_LANES:
            for pending in ("files", "captures", "spark"):
                with self.subTest(lane=lane, pending=pending):
                    state = self.configure_ui_lane(lane)
                    request = self.generation.Request(
                        lane, "model", self.model["id"], {"prompt": "a teapot"}
                    )
                    setattr(
                        request,
                        pending,
                        {"input": ["fixture"]} if pending != "captures" else [{"source": "MESH"}],
                    )
                    with patch.object(self.generation, "build_request", return_value=request):
                        self.generation.request_estimate(bpy.context.scene, lane)
                        self.assertEqual(state.estimate_state, "UNAVAILABLE")
                        with self.assertRaisesRegex(self.request_error, "uploaded"):
                            self.generation.submit_generation(bpy.context, lane)
        self.assertEqual(self.calls, [])
        self.assertEqual(self.store.records(), ())

    def test_render_form_capture_is_not_performed_by_quote_or_submit(self):
        for lane in ("render_image", "render_video"):
            with self.subTest(lane=lane):
                state = self.configure_ui_lane(lane)
                with patch.object(
                    self.generation,
                    "perform_captures",
                    side_effect=AssertionError("Implicit capture"),
                ):
                    self.generation.request_estimate(bpy.context.scene, lane)
                    self.assertEqual(state.estimate_state, "UNAVAILABLE")
                    with self.assertRaises(self.request_error):
                        self.generation.submit_generation(bpy.context, lane)
        self.assertEqual(self.calls, [])
        self.assertEqual(self.paid, [])

    def test_prepared_render_forms_submit_exact_uploaded_payload_once(self):
        prepared = submodule("blender.render_references")
        for lane_name in ("render_image", "render_video"):
            with self.subTest(lane=lane_name):
                lane = self.configure_ui_lane(lane_name)
                ref = lane.references.add()
                ref.param_name, ref.source, ref.asset_id = "reference", "ASSET", "scene-snapshot"
                ref[prepared.ROLE] = prepared.SCENE
                self.ui_quote(lane_name)
                payload = self.generation.build_request(
                    bpy.context.scene, lane_name, for_estimate=True
                ).body
                with patch.object(
                    self.generation,
                    "perform_captures",
                    side_effect=AssertionError("Implicit capture"),
                ):
                    self.assertEqual(bpy.ops.scenario.generate(lane=lane_name), {"FINISHED"})
                self.settle()
                self.assertEqual(json.loads(self.paid[-1].content), payload)
                self.assertEqual(payload["reference"], ["scene-snapshot"])
                self.assertEqual(
                    self.store.records()[-1].intent.quote_cost, "0.1234567890123456789"
                )
                with self.assertRaises(self.request_error):
                    self.generation.submit_generation(bpy.context, lane_name)
        self.assertEqual(len(self.paid), 2)

    def test_render_reference_change_invalidates_approved_request(self):
        prepared = submodule("blender.render_references")
        lane = self.configure_ui_lane("render_image")
        ref = lane.references.add()
        ref.param_name, ref.source, ref.asset_id = "reference", "ASSET", "scene-before"
        ref[prepared.ROLE] = prepared.SCENE
        self.ui_quote("render_image")
        ref.asset_id = "scene-after"
        with self.assertRaises(self.request_error):
            self.generation.submit_generation(bpy.context, "render_image")
        self.assertEqual(self.paid, [])

    def recovered_media(self):
        from test_media_application import wav_bytes

        self.result_bytes, self.result_media_type = wav_bytes(), "audio/wav"
        self.remote_status = "success"
        result = self.mcp_submit(self.mcp_quote())
        owner = self.runtime.state.model_jobs
        owner.submissions[result["local_id"]].result(5)
        owner.session.invalidate_scene(bpy.context.scene)
        self.deliver_results()
        self.runtime.state.reset()
        self.runtime.inspect_model_jobs()
        self.assertEqual(self.store.get(result["local_id"]).state, self.storemod.JobState.READY)
        return result["local_id"]

    def prepare_media(self, request_id):
        args = self.recovery_args(request_id, "import_media")
        del args["action"]
        args["asset_id"] = "result-image"
        return self.tools.prepare_result_application(args)

    def test_mcp_media_recovery_requires_scene_frame_approval_without_spending(self):
        request_id = self.recovered_media()
        bpy.context.scene.frame_set(27)
        before = len(self.calls), len(self.paid)
        approval = self.prepare_media(request_id)
        self.assertEqual(approval["kind"], "audio")
        self.assertEqual(approval["frame"], 27)
        self.assertFalse(
            bpy.context.scene.sequence_editor and bpy.context.scene.sequence_editor.strips
        )
        deferred = self.tools.apply_result_application(self.import_args(approval))
        status = deferred.finish(deferred.run())
        self.assertEqual(status["status"], "applied", status)
        strips = bpy.context.scene.sequence_editor.strips
        self.assertEqual(len(strips), 1)
        self.assertEqual(strips[0].frame_final_start, 27)
        self.assertEqual((len(self.calls), len(self.paid)), before)
        with self.assertRaises(self.request_error):
            self.tools.apply_result_application(self.import_args(approval))

    def test_media_frame_change_during_verification_keeps_saved_result_ready(self):
        request_id = self.recovered_media()
        approval = self.prepare_media(request_id)
        deferred = self.tools.apply_result_application(self.import_args(approval))
        result = deferred.run()
        bpy.context.scene.frame_set(50)
        status = deferred.finish(result)
        self.assertEqual(status["status"], "ready", status)
        self.assertTrue(status["error"])
        self.assertFalse(
            bpy.context.scene.sequence_editor and bpy.context.scene.sequence_editor.strips
        )

    def test_native_media_execution_needs_the_same_prepared_approval(self):
        request_id = self.recovered_media()
        approval = self.prepare_media(request_id)
        args = self.import_args(approval)
        args.update(
            request_id=request_id,
            expected_revision=approval["revision"],
            asset_id=approval["asset_id"],
        )
        self.assertEqual(bpy.ops.scenario.import_saved_media(**args), {"FINISHED"})
        self.deliver_results()
        self.assertEqual(self.store.get(request_id).state, self.storemod.JobState.APPLIED)
        self.assertEqual(len(bpy.context.scene.sequence_editor.strips), 1)
        with self.assertRaisesRegex(RuntimeError, "Media insertion was not started"):
            bpy.ops.scenario.import_saved_media(**args)

    def recovered_model(self, body=None):
        from helpers import FIXTURES

        module = submodule("blender.model_application")
        # Native undo can replace RNA wrappers for preexisting fixture data.
        # Names are only for cleanup of this disposable test scene, never targets.
        before = {name: {value.name for value in getattr(bpy.data, name)} for name in module._DATA}

        def cleanup():
            for name in module._DATA:
                if name == "images":
                    continue  # Existing fixture cleanup owns images after session shutdown.
                values = getattr(bpy.data, name)
                for value in tuple(values):
                    if value.name not in before[name]:
                        values.remove(value, do_unlink=True)

        self.addCleanup(cleanup)
        self.result_bytes = (
            body if body is not None else (FIXTURES / "synthetic/static-triangle.glb").read_bytes()
        )
        self.result_media_type, self.remote_status = "model/gltf-binary", "success"
        result = self.mcp_submit(self.mcp_quote())
        owner = self.runtime.state.model_jobs
        owner.submissions[result["local_id"]].result(5)
        owner.session.invalidate_scene(bpy.context.scene)
        self.deliver_results()
        self.runtime.state.reset()
        self.runtime.inspect_model_jobs()
        self.assertEqual(self.store.get(result["local_id"]).state, self.storemod.JobState.READY)
        return result["local_id"]

    def prepare_model(self, request_id):
        args = self.recovery_args(request_id, "import_model")
        del args["action"]
        args["asset_id"] = "result-image"
        return self.tools.prepare_result_application(args)

    def test_mcp_model_recovery_imports_one_group_without_more_requests(self):
        request_id = self.recovered_model()
        bpy.context.scene.cursor.location = (4, 5, 6)
        before = len(self.calls), len(self.paid)
        approval = self.prepare_model(request_id)
        self.assertEqual(approval["kind"], "model")
        self.assertEqual(approval["cursor"], [4, 5, 6])
        deferred = self.tools.apply_result_application(self.import_args(approval))
        status = deferred.finish(deferred.run())
        self.assertEqual(status["status"], "applied", status)
        self.assertEqual(len(status["objects"]), 2)
        self.assertEqual((len(self.calls), len(self.paid)), before)
        with self.assertRaises(self.request_error):
            self.tools.apply_result_application(self.import_args(approval))

    def test_shared_animated_model_import_retains_rig_and_clips_without_more_requests(self):
        request_id = self.recovered_model(animated_glb())
        before = len(self.calls), len(self.paid)
        approval = self.prepare_model(request_id)
        deferred = self.tools.apply_result_application(self.import_args(approval))
        status = deferred.finish(deferred.run())
        self.assertEqual(status["status"], "applied", status)
        rig = next(
            bpy.data.objects[name]
            for name in status["objects"]
            if bpy.data.objects[name].type == "ARMATURE"
        )
        self.assertEqual(len(rig.data.bones), 2)
        self.assertEqual(len(rig.animation_data.nla_tracks), 2)
        self.assertEqual((len(self.calls), len(self.paid)), before)
        with self.assertRaises(self.request_error):
            self.tools.apply_result_application(self.import_args(approval))

    def headless_saved_application(self, request_id, *, mesh_edit=False):
        self.assertTrue(bpy.app.background)
        service = submodule("blender.mcp_service")
        server_type = service.McpServer
        serve = server_type.serve_blocking
        context = bpy.context.window, bpy.context.scene, bpy.context.view_layer
        before = len(self.calls), len(self.paid), len(self.downloads)
        arguments = self.recovery_args(request_id, "import_model")
        del arguments["action"]
        arguments["asset_id"] = "result-image"
        if mesh_edit:
            arguments["purpose"] = "mesh_edit"
        completed = []

        def serve_once(server, stop_event, *, before_process):
            # Port zero is test-only; connect to the OS-assigned listening port.
            url = f"http://127.0.0.1:{server._httpd.server_address[1]}/mcp"

            def client():
                try:
                    with httpx.Client(trust_env=False, timeout=10) as connection:

                        def call(name, arguments):
                            response = connection.post(
                                url,
                                headers={"Authorization": "Bearer synthetic-cli-token"},
                                json={
                                    "jsonrpc": "2.0",
                                    "id": 1,
                                    "method": "tools/call",
                                    "params": {"name": name, "arguments": arguments},
                                },
                            )
                            response.raise_for_status()
                            value = response.json()
                            self.assertNotIn("error", value)
                            return value["result"]

                        prepared = call("prepare_result_application", arguments)
                        self.assertFalse(prepared.get("isError"), prepared)
                        approval = json.loads(prepared["content"][0]["text"])
                        applied = call("apply_result_application", self.import_args(approval))
                        self.assertFalse(applied.get("isError"), applied)
                        completed.append(json.loads(applied["content"][0]["text"]))
                        replay = call("apply_result_application", self.import_args(approval))
                        self.assertTrue(replay.get("isError"), replay)
                finally:
                    stop_event.set()

            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(client)
                serve(server, stop_event, before_process=before_process)
                future.result(15)

        def ephemeral_server(host, port, *args, **kwargs):
            return server_type(host, 0, *args, **kwargs)

        with (
            patch.object(server_type, "serve_blocking", serve_once),
            patch.object(service, "McpServer", side_effect=ephemeral_server),
        ):
            self.assertEqual(service.cli(["--token", "synthetic-cli-token"]), 0)
        self.assertEqual((bpy.context.window, bpy.context.scene, bpy.context.view_layer), context)
        self.assertEqual((len(self.calls), len(self.paid), len(self.downloads)), before)
        self.assertEqual(len(completed), 1)
        self.assertEqual(completed[0]["status"], "applied", completed[0])
        return completed[0]

    def test_headless_mcp_loop_imports_saved_rig_and_animation_without_replay(self):
        request_id = self.recovered_model(animated_glb())
        active = bpy.context.view_layer.objects.active
        status = self.headless_saved_application(request_id)
        rig = next(
            bpy.data.objects[name]
            for name in status["objects"]
            if bpy.data.objects[name].type == "ARMATURE"
        )
        self.assertEqual(len(rig.data.bones), 2)
        self.assertEqual(len(rig.animation_data.nla_tracks), 2)
        self.assertEqual(bpy.context.view_layer.objects.active, active)

    def test_headless_mcp_loop_applies_saved_mesh_without_replay(self):
        request_id = self.recovered_mesh_edit()
        source = bpy.context.view_layer.objects.active
        original = source.data
        status = self.headless_saved_application(request_id, mesh_edit=True)
        self.assertEqual(status["mesh_edit"]["target"], source.name)
        self.assertEqual(len(source.data.vertices), 3)
        self.assertEqual(bpy.data.objects[status["mesh_edit"]["original"]].data, original)
        self.assertEqual(bpy.context.view_layer.objects.active, source)

    def test_native_animated_model_import_uses_shared_approval(self):
        request_id = self.recovered_model(animated_glb())
        before = len(self.calls), len(self.paid)
        approval = self.prepare_model(request_id)
        args = self.import_args(approval)
        args.update(
            request_id=request_id,
            expected_revision=approval["revision"],
            asset_id=approval["asset_id"],
        )
        self.assertEqual(bpy.ops.scenario.import_saved_model(**args), {"FINISHED"})
        self.deliver_results()
        self.assertEqual(self.store.get(request_id).state, self.storemod.JobState.APPLIED)
        self.assertEqual(sum(obj.type == "ARMATURE" for obj in bpy.context.scene.objects), 1)
        self.assertEqual((len(self.calls), len(self.paid)), before)

    def test_changed_model_cursor_during_verification_prevents_import(self):
        request_id = self.recovered_model()
        approval = self.prepare_model(request_id)
        before = set(bpy.data.objects)
        deferred = self.tools.apply_result_application(self.import_args(approval))
        result = deferred.run()
        bpy.context.scene.cursor.location.x += 1
        status = deferred.finish(result)
        self.assertEqual(status["status"], "ready", status)
        self.assertTrue(status["error"])
        self.assertEqual(set(bpy.data.objects), before)

    def test_native_model_import_uses_the_same_single_approval(self):
        request_id = self.recovered_model()
        approval = self.prepare_model(request_id)
        args = self.import_args(approval)
        args.update(
            request_id=request_id,
            expected_revision=approval["revision"],
            asset_id=approval["asset_id"],
        )
        self.assertEqual(bpy.ops.scenario.import_saved_model(**args), {"FINISHED"})
        self.deliver_results()
        self.assertEqual(self.store.get(request_id).state, self.storemod.JobState.APPLIED)
        with self.assertRaisesRegex(RuntimeError, "Model import was not started"):
            bpy.ops.scenario.import_saved_model(**args)

    def test_model_receipt_retry_does_not_repeat_scene_import(self):
        request_id = self.recovered_model()
        approval = self.prepare_model(request_id)
        deferred = self.tools.apply_result_application(self.import_args(approval))
        result = deferred.run()
        active_store = self.runtime.state.model_jobs.store
        original = active_store.transition

        def fail_receipt(*args, **kwargs):
            if kwargs.get("state") == self.storemod.JobState.APPLIED:
                raise OSError("synthetic receipt failure")
            return original(*args, **kwargs)

        with patch.object(active_store, "transition", side_effect=fail_receipt):
            status = deferred.finish(result)
        self.assertEqual(status["status"], "applying", status)
        self.assertIn("retry_receipt", status["actions"])
        before = set(bpy.data.objects)
        with patch.object(
            submodule("blender.job_session"),
            "apply_model",
            side_effect=AssertionError("Repeated import"),
        ):
            status = self.tools.recover_local_job(self.recovery_args(request_id, "retry_receipt"))
        self.assertEqual(status["status"], "applied", status)
        self.assertEqual(set(bpy.data.objects), before)
        self.assertEqual(len(status["objects"]), 2)

    def test_model_shutdown_rejects_receipt_retry_without_changing_saved_claim(self):
        request_id = self.recovered_model()
        approval = self.prepare_model(request_id)
        deferred = self.tools.apply_result_application(self.import_args(approval))
        result = deferred.run()
        owner = self.runtime.state.model_jobs
        original = owner.store.transition

        def fail_receipt(*args, **kwargs):
            if kwargs.get("state") == self.storemod.JobState.APPLIED:
                raise OSError("synthetic receipt failure")
            return original(*args, **kwargs)

        with patch.object(owner.store, "transition", side_effect=fail_receipt):
            status = deferred.finish(result)
        self.assertEqual(status["status"], "applying", status)
        pending = owner._receipts[request_id]
        record, before = owner.store.get(request_id), set(bpy.data.objects)
        owner.session.shutdown()
        with self.assertRaises(self.origin_error):
            owner.session.retry_model_receipt(pending)
        self.assertEqual(owner.store.get(request_id), record)
        self.assertEqual(set(bpy.data.objects), before)

    def test_model_mode_change_during_verification_preserves_ready_claim(self):
        request_id = self.recovered_model()
        bpy.ops.mesh.primitive_cube_add()
        approval = self.prepare_model(request_id)
        deferred = self.tools.apply_result_application(self.import_args(approval))
        result = deferred.run()
        before = self.store.get(request_id), set(bpy.data.objects)
        bpy.ops.object.mode_set(mode="EDIT")
        try:
            status = deferred.finish(result)
            self.assertEqual(status["status"], "ready", status)
            self.assertEqual((self.store.get(request_id), set(bpy.data.objects)), before)
        finally:
            bpy.ops.object.mode_set(mode="OBJECT")

    def test_model_incomplete_rollback_retains_claim_and_forbids_reimport(self):
        request_id = self.recovered_model()
        approval = self.prepare_model(request_id)
        deferred = self.tools.apply_result_application(self.import_args(approval))
        result = deferred.run()
        module = submodule("blender.model_application")
        original = module._publish

        def fail(*args):
            original(*args)
            raise RuntimeError("synthetic publication failure")

        with (
            patch.object(module, "_publish", side_effect=fail),
            patch.object(module, "_remove_new_data"),
        ):
            status = deferred.finish(result)
        self.assertEqual(status["status"], "applying", status)
        self.assertNotIn("retry_receipt", status["actions"])
        self.assertNotIn("import_model", status["actions"])
        with self.assertRaises(self.request_error):
            self.prepare_model(request_id)

    def test_model_temporary_cleanup_failure_still_saves_success_once(self):
        request_id = self.recovered_model()
        approval = self.prepare_model(request_id)
        deferred = self.tools.apply_result_application(self.import_args(approval))
        result = deferred.run()
        before = len(self.calls), len(self.paid)
        cleanup = tempfile.TemporaryDirectory.cleanup

        def fail(directory):
            cleanup(directory)
            raise OSError("synthetic cleanup failure")

        with patch.object(tempfile.TemporaryDirectory, "cleanup", fail):
            status = deferred.finish(result)
        self.assertEqual(status["status"], "applied", status)
        self.assertEqual(len(status["objects"]), 2)
        self.assertEqual((len(self.calls), len(self.paid)), before)
        fresh = self.prepare_model(request_id)
        self.assertTrue(fresh["reuse"])
        self.assertEqual((len(self.calls), len(self.paid)), before)

    def recovered_panorama(self):
        before_worlds = set(bpy.data.worlds)

        def cleanup():
            for world in set(bpy.data.worlds) - before_worlds:
                bpy.data.worlds.remove(world, do_unlink=True)

        self.addCleanup(cleanup)
        image = bpy.data.images.new("Synthetic panorama", width=8, height=4)
        try:
            image.pixels[:] = [0.25, 0.5, 0.75, 1.0] * 32
            image.file_format = "PNG"
            path = self.runtime.paths().state_dir / "panorama.png"
            image.filepath_raw = str(path)
            image.save()
            self.result_bytes = path.read_bytes()
        finally:
            bpy.data.images.remove(image)
        self.remote_status = "success"
        with patch.object(self, "result_fixture", return_value=None):
            return self.recovered_images()

    def prepare_world(self, request_id, *, restore=False):
        args = self.recovery_args(request_id, "restore_world" if restore else "apply_world")
        del args["action"]
        args["purpose"] = "restore_world" if restore else "world"
        if not restore:
            args["asset_id"] = "result-image"
        return self.tools.prepare_result_application(args)

    def test_world_application_and_restore_share_approval_without_new_requests(self):
        request_id = self.recovered_panorama()
        scene, previous = bpy.context.scene, bpy.context.scene.world
        before = len(self.calls), len(self.paid)
        approval = self.prepare_world(request_id)
        self.assertEqual(approval["purpose"], "world")
        self.assertEqual(scene.world, previous)
        deferred = self.tools.apply_result_application(self.import_args(approval))
        status = deferred.finish(deferred.run())
        self.assertEqual(status["status"], "applied", status)
        self.assertNotEqual(scene.world, previous)
        self.assertIn("restore_world", status["actions"])
        restore = self.prepare_world(request_id, restore=True)
        status = self.tools.apply_result_application(self.import_args(restore))
        self.assertEqual(scene.world, previous)
        self.assertEqual(status["status"], "applied")
        self.assertNotIn("restore_world", status["actions"])
        self.assertEqual((len(self.calls), len(self.paid)), before)
        with self.assertRaises(self.request_error):
            self.tools.apply_result_application(self.import_args(restore))

    def test_world_changed_during_verification_keeps_saved_panorama_unapplied(self):
        request_id = self.recovered_panorama()
        approval = self.prepare_world(request_id)
        deferred = self.tools.apply_result_application(self.import_args(approval))
        result = deferred.run()
        changed = bpy.data.worlds.new("Changed destination")
        bpy.context.scene.world = changed
        status = deferred.finish(result)
        self.assertEqual(status["status"], "ready", status)
        self.assertTrue(status["error"])
        self.assertEqual(bpy.context.scene.world, changed)

    def assert_world_reuse_restores_each_scene(self, *, lose_receipt=False):
        request_id = self.recovered_panorama()
        first, previous = bpy.context.scene, bpy.context.scene.world
        second = bpy.data.scenes.new("Second panorama destination")
        before = len(self.calls), len(self.paid), len(self.downloads)
        try:
            self.finish_application(self.prepare_world(request_id))
            first_applied = first.world
            bpy.context.window.scene = second
            deferred = self.tools.apply_result_application(
                self.import_args(self.prepare_world(request_id))
            )
            result = deferred.run()
            if lose_receipt:
                owner = self.runtime.state.model_jobs
                with patch.object(
                    owner.store,
                    "finish_local_application",
                    side_effect=OSError("synthetic World receipt failure"),
                ):
                    status = deferred.finish(result)
                self.assertEqual(status["actions"], ("retry_receipt",))
                bpy.context.window.scene = first
                with patch.object(
                    submodule("blender.job_session"),
                    "apply_world",
                    side_effect=AssertionError("Repeated World assignment"),
                ):
                    self.recover(request_id, "retry_receipt")
            else:
                deferred.finish(result)
            second_applied = second.world
            saved = self.store.get(request_id)
            self.assertEqual(saved.local_applications[0].state.value, "applied")
            self.assertNotEqual(first_applied, second_applied)
            second.name = "Renamed panorama destination"
            bpy.context.window.scene = first
            approval = self.prepare_world(request_id, restore=True)
            status = self.tools.apply_result_application(self.import_args(approval))
            self.assertEqual(first.world, previous)
            self.assertEqual(second.world, second_applied)
            self.assertIn("restore_world", status["actions"])
            with self.assertRaises(self.request_error):
                self.tools.apply_result_application(self.import_args(approval))
            bpy.context.window.scene = second
            status = self.tools.apply_result_application(
                self.import_args(self.prepare_world(request_id, restore=True))
            )
            self.assertIsNone(second.world)
            self.assertNotIn("restore_world", status["actions"])
            self.assertEqual(self.store.get(request_id), saved)
            self.assertEqual((len(self.calls), len(self.paid), len(self.downloads)), before)
        finally:
            bpy.context.window.scene = first
            bpy.data.scenes.remove(second)

    def test_reused_panorama_keeps_independent_restore_handles_after_scene_rename(self):
        self.assert_world_reuse_restores_each_scene()

    def test_reused_panorama_receipt_retry_keeps_both_scene_restore_handles(self):
        self.assert_world_reuse_restores_each_scene(lose_receipt=True)

    def test_world_restore_rejects_recreated_scene_without_losing_other_destination(self):
        request_id = self.recovered_panorama()
        first, previous = bpy.context.scene, bpy.context.scene.world
        second = bpy.data.scenes.new("Temporary panorama destination")
        try:
            self.finish_application(self.prepare_world(request_id))
            bpy.context.window.scene = second
            self.finish_application(self.prepare_world(request_id))
            name = second.name
            bpy.context.window.scene = first
            bpy.data.scenes.remove(second)
            self.runtime.state.job_session.prune_missing_scenes()
            second = bpy.data.scenes.new(name)
            bpy.context.window.scene = second
            with self.assertRaises(self.request_error):
                self.prepare_world(request_id, restore=True)
            self.assertIsNone(second.world)
            bpy.context.window.scene = first
            self.tools.apply_result_application(
                self.import_args(self.prepare_world(request_id, restore=True))
            )
            self.assertEqual(first.world, previous)
            owner = self.runtime.state.model_jobs
            self.assertNotIn("restore_world", owner.status(request_id)["actions"])
            owner.poll()
            self.assertNotIn(request_id, owner._worlds)
        finally:
            bpy.context.window.scene = first
            bpy.data.scenes.remove(second)

    def test_world_restore_survives_render_thread_revision_reset(self):
        request_id = self.recovered_panorama()
        scene, previous = bpy.context.scene, bpy.context.scene.world
        self.finish_application(self.prepare_world(request_id))
        before = len(self.calls), len(self.paid), len(self.downloads)
        callback = submodule("blender.job_session")._scene_changed
        with ThreadPoolExecutor(max_workers=1) as pool:
            pool.submit(callback, None).result(5)
        self.tools.apply_result_application(
            self.import_args(self.prepare_world(request_id, restore=True))
        )
        self.assertEqual(scene.world, previous)
        self.assertEqual((len(self.calls), len(self.paid), len(self.downloads)), before)

    def test_history_invalidation_retires_world_restore_without_renewing_authority(self):
        request_id = self.recovered_panorama()
        self.finish_application(self.prepare_world(request_id))
        approval = self.prepare_world(request_id, restore=True)
        world = bpy.context.scene.world
        owner = self.runtime.state.model_jobs
        before = self.store.get(request_id), len(self.calls), len(self.paid), len(self.downloads)
        submodule("blender.job_session")._history_pre(None)
        self.assertNotIn("restore_world", owner.status(request_id)["actions"])
        with self.assertRaises(self.request_error):
            self.tools.apply_result_application(self.import_args(approval))
        with self.assertRaises(self.request_error):
            self.prepare_world(request_id, restore=True)
        owner.poll()
        self.assertNotIn(request_id, owner._worlds)
        self.assertEqual(bpy.context.scene.world, world)
        self.assertEqual(
            (self.store.get(request_id), len(self.calls), len(self.paid), len(self.downloads)),
            before,
        )

    def test_world_restore_preserves_edited_world_data(self):
        request_id = self.recovered_panorama()
        deferred = self.tools.apply_result_application(
            self.import_args(self.prepare_world(request_id))
        )
        deferred.finish(deferred.run())
        world = bpy.context.scene.world
        world.node_tree.nodes.get("Background").inputs["Strength"].default_value = 2
        approval = self.prepare_world(request_id, restore=True)
        with self.assertRaises(submodule("blender.world_application").WorldApplicationError):
            self.tools.apply_result_application(self.import_args(approval))
        self.assertEqual(bpy.context.scene.world, world)
        self.assertEqual(
            world.node_tree.nodes.get("Background").inputs["Strength"].default_value, 2
        )

    def test_nonpanoramic_saved_image_reports_local_failure_without_replacing_world(self):
        request_id = self.recovered_images()
        previous = bpy.context.scene.world
        before = len(self.calls), len(self.paid)
        deferred = self.tools.apply_result_application(
            self.import_args(self.prepare_world(request_id))
        )
        status = deferred.finish(deferred.run())
        self.assertEqual(status["status"], "apply_failed", status)
        self.assertEqual(bpy.context.scene.world, previous)
        self.assertEqual((len(self.calls), len(self.paid)), before)

    def test_native_world_operator_uses_prepared_mcp_approval_for_apply_and_restore(self):
        request_id = self.recovered_panorama()
        previous = bpy.context.scene.world
        for restore in (False, True):
            approval = self.prepare_world(request_id, restore=restore)
            args = self.import_args(approval)
            args.update(
                request_id=request_id,
                expected_revision=approval["revision"],
                asset_id=approval["asset_id"],
                purpose=approval["purpose"],
            )
            self.assertEqual(bpy.ops.scenario.apply_saved_world(**args), {"FINISHED"})
            self.deliver_results()
            self.assertEqual(bpy.context.scene.world == previous, restore)
        self.assertEqual(len(self.paid), 1)

    def test_world_receipt_retry_preserves_one_assignment(self):
        request_id = self.recovered_panorama()
        deferred = self.tools.apply_result_application(
            self.import_args(self.prepare_world(request_id))
        )
        result = deferred.run()
        owner = self.runtime.state.model_jobs
        transition = owner.store.transition

        def fail_receipt(*args, **kwargs):
            if kwargs.get("state") == self.storemod.JobState.APPLIED:
                raise OSError("synthetic World receipt failure")
            return transition(*args, **kwargs)

        with patch.object(owner.store, "transition", side_effect=fail_receipt):
            status = deferred.finish(result)
        self.assertEqual(status["status"], "applying", status)
        world = bpy.context.scene.world
        with patch.object(
            submodule("blender.job_session"),
            "apply_world",
            side_effect=AssertionError("Repeated assignment"),
        ):
            status = self.tools.recover_local_job(self.recovery_args(request_id, "retry_receipt"))
        self.assertEqual(status["status"], "applied")
        self.assertEqual(bpy.context.scene.world, world)

    def recovered_material(self, metadata_types=None):
        before = set(bpy.data.materials)

        def cleanup():
            for material in set(bpy.data.materials) - before:
                bpy.data.materials.remove(material, do_unlink=True)

        self.addCleanup(cleanup)
        self.result_metadata = {"type": "texture-albedo"}
        if metadata_types is not None:
            self.result_assets = {
                f"result-map-{index}": {"type": kind} for index, kind in enumerate(metadata_types)
            }
        bpy.ops.mesh.primitive_cube_add()
        return self.recovered_images()

    def prepare_material(self, request_id):
        args = self.recovery_args(request_id, "apply_material")
        del args["action"]
        args["purpose"] = "material"
        return self.tools.prepare_result_application(args)

    def test_material_actions_require_the_same_supported_texture_set_as_approval(self):
        request_id = self.recovered_material()
        owner = self.runtime.state.model_jobs
        record = self.store.get(request_id)
        albedo = record.results[0]
        before = len(self.calls), len(self.paid), len(self.downloads)
        for media_type in ("image/png", "image/exr", "image/x-exr", "image/jpeg", "image/webp"):
            with self.subTest(media_type=media_type):
                changed = replace(albedo, asset=replace(albedo.asset, media_type=media_type))
                proposed = replace(record, results=(changed,))
                self.assertEqual(
                    "apply_material" in owner.actions(proposed),
                    media_type in {"image/png", "image/exr", "image/x-exr"},
                )
        invalid_sets = (
            (replace(albedo, receipt=None),),
            (albedo, replace(albedo, asset=replace(albedo.asset, asset_id="second-albedo"))),
            (
                albedo,
                replace(
                    albedo,
                    asset=replace(
                        albedo.asset,
                        asset_id="normal",
                        texture_role="normal",
                        media_type="image/webp",
                    ),
                ),
            ),
        )
        for results in invalid_sets:
            with self.subTest(results=tuple(item.asset.asset_id for item in results)):
                self.assertNotIn("apply_material", owner.actions(replace(record, results=results)))
        self.assertEqual(self.store.get(request_id), record)
        self.assertEqual((len(self.calls), len(self.paid), len(self.downloads)), before)

    def test_saved_webp_texture_does_not_offer_an_unusable_material_action(self):
        self.result_media_type = "image/webp"
        request_id = self.recovered_material()
        owner = self.runtime.state.model_jobs
        before = self.store.get(request_id)
        self.assertNotIn("apply_material", owner.status(request_id)["actions"])
        with patch.object(owner.session, "verify_results") as verify:
            with self.assertRaises(self.request_error):
                self.prepare_material(request_id)
        verify.assert_not_called()
        self.assertEqual(self.store.get(request_id), before)
        self.assertFalse(owner._application_approvals)

    def test_material_mcp_applies_to_captured_mesh_without_additional_requests(self):
        request_id = self.recovered_material()
        target = bpy.context.active_object
        bpy.ops.mesh.primitive_cube_add(location=(3, 0, 0))
        other = bpy.context.active_object
        bpy.context.view_layer.objects.active = target
        before = len(self.calls), len(self.paid)
        approval = self.prepare_material(request_id)
        self.assertEqual(approval["roles"], ["albedo"])
        deferred = self.tools.apply_result_application(self.import_args(approval))
        result = deferred.run()
        bpy.context.view_layer.objects.active = other
        status = deferred.finish(result)
        self.assertEqual(status["status"], "applied", status)
        self.assertEqual(status["materials"], [target.active_material.name])
        self.assertIsNone(other.active_material)
        self.assertEqual((len(self.calls), len(self.paid)), before)
        with self.assertRaises(self.request_error):
            self.tools.apply_result_application(self.import_args(approval))

    def test_material_slot_change_during_verification_keeps_ready_job(self):
        request_id = self.recovered_material()
        approval = self.prepare_material(request_id)
        deferred = self.tools.apply_result_application(self.import_args(approval))
        result = deferred.run()
        chosen = bpy.data.materials.new("Changed slot")
        bpy.context.active_object.data.materials.append(chosen)
        status = deferred.finish(result)
        self.assertEqual(status["status"], "ready", status)
        self.assertEqual(bpy.context.active_object.active_material, chosen)

    def test_complete_material_job_uses_albedo_and_preserves_saved_preview(self):
        request_id = self.recovered_material(
            (
                "inference-txt2img-texture",
                "texture-albedo",
                "texture-normal",
                "texture-smoothness",
                "texture-metallic",
                "texture-height",
                "texture-ao",
                "texture-edge",
            )
        )
        saved = self.store.get(request_id).results
        self.assertEqual(
            [item.asset.texture_role for item in saved],
            ["base", "albedo", "normal", "smoothness", "metallic", "height", "ao", "edge"],
        )
        before = len(self.calls), len(self.paid)
        approval = self.prepare_material(request_id)
        self.assertEqual(
            approval["roles"],
            ["albedo", "normal", "smoothness", "metallic", "height", "ao", "edge"],
        )
        deferred = self.tools.apply_result_application(self.import_args(approval))
        status = deferred.finish(deferred.run())
        self.assertEqual(status["status"], "applied", status)
        self.assertEqual(self.store.get(request_id).results, saved)
        self.assertEqual((len(self.calls), len(self.paid)), before)
        tree = bpy.context.active_object.active_material.node_tree
        bsdf = next(node for node in tree.nodes if node.type == "BSDF_PRINCIPLED")
        self.assertEqual(bsdf.inputs["Base Color"].links[0].from_node.label, "Albedo")
        self.assertEqual(len([node for node in tree.nodes if node.type == "TEX_IMAGE"]), 7)

    def test_material_failed_assignment_preserves_files_and_allows_local_review(self):
        request_id = self.recovered_material()
        target = bpy.context.active_object
        deferred = self.tools.apply_result_application(
            self.import_args(self.prepare_material(request_id))
        )
        result = deferred.run()
        module = submodule("blender.material_application")
        original = module._assign

        def fail(*args):
            original(*args)
            raise RuntimeError("synthetic assignment failure")

        with patch.object(module, "_assign", side_effect=fail):
            status = deferred.finish(result)
        self.assertEqual(status["status"], "apply_failed", status)
        self.assertIn("apply_material", status["actions"])
        self.assertIsNone(target.active_material)
        self.assertTrue(all(item.receipt for item in self.store.get(request_id).results))

    def test_material_receipt_retry_does_not_repeat_assignment(self):
        request_id = self.recovered_material()
        deferred = self.tools.apply_result_application(
            self.import_args(self.prepare_material(request_id))
        )
        result = deferred.run()
        owner = self.runtime.state.model_jobs
        transition = owner.store.transition

        def fail_receipt(*args, **kwargs):
            if kwargs.get("state") == self.storemod.JobState.APPLIED:
                raise OSError("synthetic material receipt failure")
            return transition(*args, **kwargs)

        with patch.object(owner.store, "transition", side_effect=fail_receipt):
            status = deferred.finish(result)
        self.assertEqual(status["status"], "applying", status)
        material = bpy.context.active_object.active_material
        with patch.object(
            submodule("blender.job_session"),
            "apply_material",
            side_effect=AssertionError("Repeated assignment"),
        ):
            status = self.tools.recover_local_job(self.recovery_args(request_id, "retry_receipt"))
        self.assertEqual(status["status"], "applied")
        self.assertEqual(bpy.context.active_object.active_material, material)
        self.assertEqual(status["materials"], [material.name])

    def test_material_shutdown_rejects_pending_receipt_retry(self):
        request_id = self.recovered_material()
        deferred = self.tools.apply_result_application(
            self.import_args(self.prepare_material(request_id))
        )
        result = deferred.run()
        owner = self.runtime.state.model_jobs
        transition = owner.store.transition

        def fail_receipt(*args, **kwargs):
            if kwargs.get("state") == self.storemod.JobState.APPLIED:
                raise OSError("synthetic material receipt failure")
            return transition(*args, **kwargs)

        with patch.object(owner.store, "transition", side_effect=fail_receipt):
            deferred.finish(result)
        pending = owner._receipts[request_id]
        before = owner.store.get(request_id), bpy.context.active_object.active_material
        owner.session.shutdown()
        with self.assertRaises(self.origin_error):
            owner.session.retry_material_receipt(pending)
        self.assertEqual(
            (owner.store.get(request_id), bpy.context.active_object.active_material), before
        )

    def test_native_material_operator_consumes_the_same_single_approval(self):
        request_id = self.recovered_material(("texture-albedo", "inference-txt2img-texture"))
        approval = self.prepare_material(request_id)
        self.assertEqual(approval["roles"], ["albedo"])
        args = self.import_args(approval)
        args.update(request_id=request_id, expected_revision=approval["revision"])
        self.assertEqual(bpy.ops.scenario.apply_saved_material(**args), {"FINISHED"})
        self.deliver_results()
        self.assertEqual(self.store.get(request_id).state, self.storemod.JobState.APPLIED)
        with self.assertRaisesRegex(RuntimeError, "Material assignment was not started"):
            bpy.ops.scenario.apply_saved_material(**args)

    def test_material_scene_edit_during_verification_keeps_job_ready(self):
        request_id = self.recovered_material()
        deferred = self.tools.apply_result_application(
            self.import_args(self.prepare_material(request_id))
        )
        result = deferred.run()
        bpy.ops.mesh.primitive_cube_add(location=(3, 0, 0))
        status = deferred.finish(result)
        self.assertEqual(status["status"], "ready", status)
        self.assertFalse(status["materials"])

    def test_material_incomplete_rollback_retains_uncertain_claim(self):
        request_id = self.recovered_material()
        deferred = self.tools.apply_result_application(
            self.import_args(self.prepare_material(request_id))
        )
        result = deferred.run()
        module = submodule("blender.material_application")
        original = module._assign

        def fail(*args):
            original(*args)
            raise RuntimeError("synthetic assignment failure")

        with (
            patch.object(module, "_assign", side_effect=fail),
            patch.object(
                module,
                "_restore_slots",
                side_effect=module.MaterialApplicationError("synthetic cleanup failure"),
            ),
        ):
            status = deferred.finish(result)
        self.assertEqual(status["status"], "applying", status)
        self.assertNotIn("retry_receipt", status["actions"])
        self.assertNotIn("apply_material", status["actions"])
        self.assertIsNotNone(bpy.context.active_object.active_material)

    def finish_application(self, approval):
        deferred = self.tools.apply_result_application(self.import_args(approval))
        return deferred.finish(deferred.run())

    def test_completed_image_reuses_as_world_after_restart_without_network(self):
        request_id = self.recovered_panorama()
        self.finish_application(self.prepare_import(request_id))
        original = self.store.get(request_id)
        images = set(bpy.data.images)
        previous = bpy.context.scene.world
        self.runtime.state.reset()
        self.runtime.inspect_model_jobs()
        before = len(self.calls), len(self.paid), len(self.downloads)
        approval = self.prepare_world(request_id)
        self.assertTrue(approval["reuse"])
        self.assertEqual(bpy.context.scene.world, previous)
        self.assertEqual(self.store.get(request_id), original)
        status = self.finish_application(approval)
        self.assertEqual(status["status"], "applied", status)
        self.assertEqual(status["local_applications"][0]["state"], "applied")
        self.assertEqual(status["local_applications"][0]["purpose"], "world")
        self.assertEqual(status["local_applications"][0]["asset_ids"], ["result-image"])
        self.assertNotEqual(bpy.context.scene.world, previous)
        self.assertLessEqual(images, set(bpy.data.images))
        saved = self.store.get(request_id)
        self.assertEqual(
            (saved.intent, saved.application_origin, saved.results),
            (original.intent, original.application_origin, original.results),
        )
        restore = self.prepare_world(request_id, restore=True)
        self.assertFalse(restore["reuse"])
        self.tools.apply_result_application(self.import_args(restore))
        self.assertEqual(bpy.context.scene.world, previous)
        self.assertEqual(self.store.get(request_id), saved)
        self.assertEqual((len(self.calls), len(self.paid), len(self.downloads)), before)

    def test_completed_image_can_apply_saved_material_to_captured_mesh(self):
        request_id = self.recovered_material()
        self.finish_application(self.prepare_import(request_id))
        before = len(self.calls), len(self.paid), len(self.downloads)
        target = bpy.context.active_object
        approval = self.prepare_material(request_id)
        self.assertTrue(approval["reuse"])
        status = self.finish_application(approval)
        self.assertEqual(status["local_applications"][0]["purpose"], "material")
        self.assertEqual(status["local_applications"][0]["state"], "applied")
        first_material = target.active_material
        bpy.ops.mesh.primitive_cube_add(location=(3, 0, 0))
        second = bpy.context.active_object
        approval = self.prepare_material(request_id)
        deferred = self.tools.apply_result_application(self.import_args(approval))
        result = deferred.run()
        bpy.context.view_layer.objects.active = target
        status = deferred.finish(result)
        self.assertIsNotNone(second.active_material)
        self.assertEqual(target.active_material, first_material)
        self.assertEqual(len(status["local_applications"]), 2)
        self.assertCountEqual(
            status["materials"], [first_material.name, second.active_material.name]
        )
        bpy.data.materials.remove(first_material, do_unlink=True)
        self.assertEqual(
            self.runtime.state.model_jobs.status(request_id)["materials"],
            [second.active_material.name],
        )
        self.assertEqual((len(self.calls), len(self.paid), len(self.downloads)), before)

    def test_material_reuse_scene_switch_before_admission_requires_fresh_approval(self):
        self.assert_material_reuse_scene_switch_requires_fresh_approval("admission")

    def test_material_reuse_scene_switch_during_verification_requires_fresh_approval(self):
        self.assert_material_reuse_scene_switch_requires_fresh_approval("verification")

    def assert_material_reuse_scene_switch_requires_fresh_approval(self, phase):
        request_id = self.recovered_material()
        self.finish_application(self.prepare_import(request_id))
        original = self.store.get(request_id)
        scene, target = bpy.context.scene, bpy.context.active_object
        other_scene = bpy.data.scenes.new("Unapproved reuse scene")
        try:
            approval = self.prepare_material(request_id)
            before = (
                set(bpy.data.materials),
                set(bpy.data.images),
                len(self.calls),
                len(self.paid),
                len(self.downloads),
            )
            if phase == "verification":
                deferred = self.tools.apply_result_application(self.import_args(approval))
                result = deferred.run()
            bpy.context.window.scene = other_scene
            if phase == "admission":
                args = self.import_args(approval)
                args.update(request_id=request_id, expected_revision=approval["revision"])
                with self.assertRaisesRegex(RuntimeError, "Material assignment was not started"):
                    bpy.ops.scenario.apply_saved_material(**args)
            else:
                status = deferred.finish(result)
                self.assertTrue(status["error"])
                self.assertFalse(status["local_applications"])
            self.assertEqual(self.store.get(request_id), original)
            self.assertIsNone(target.active_material)
            self.assertEqual(bpy.context.scene, other_scene)
            self.assertFalse(tuple(other_scene.objects))
            self.assertEqual(
                (
                    set(bpy.data.materials),
                    set(bpy.data.images),
                    len(self.calls),
                    len(self.paid),
                    len(self.downloads),
                ),
                before,
            )
            bpy.context.window.scene = scene
            with self.assertRaises(self.request_error):
                self.tools.apply_result_application(self.import_args(approval))
            fresh = self.prepare_material(request_id)
            args = self.import_args(fresh)
            args.update(request_id=request_id, expected_revision=fresh["revision"])
            self.assertEqual(bpy.ops.scenario.apply_saved_material(**args), {"FINISHED"})
            self.deliver_results()
            saved = self.store.get(request_id)
            self.assertEqual(saved.state, self.storemod.JobState.APPLIED)
            self.assertEqual(len(saved.local_applications), 1)
            self.assertEqual(saved.local_applications[0].state.value, "applied")
            self.assertEqual(
                (saved.intent, saved.application_origin, saved.results),
                (original.intent, original.application_origin, original.results),
            )
            self.assertIsNotNone(target.active_material)
            self.assertEqual((len(self.calls), len(self.paid), len(self.downloads)), before[2:])
        finally:
            bpy.context.window.scene = scene
            bpy.data.scenes.remove(other_scene)

    def test_completed_audio_can_be_reused_at_another_approved_frame(self):
        request_id = self.recovered_media()
        self.finish_application(self.prepare_media(request_id))
        before = len(self.calls), len(self.paid), len(self.downloads)
        strips = tuple(bpy.context.scene.sequence_editor.strips)
        bpy.context.scene.frame_set(30)
        approval = self.prepare_media(request_id)
        self.assertTrue(approval["reuse"])
        status = self.finish_application(approval)
        added = [strip for strip in bpy.context.scene.sequence_editor.strips if strip not in strips]
        self.assertEqual(len(added), 1)
        self.assertEqual(added[0].frame_start, 30)
        self.assertEqual(status["local_applications"][0]["purpose"], "media")
        self.assertEqual(status["local_applications"][0]["state"], "applied")
        self.assertEqual((len(self.calls), len(self.paid), len(self.downloads)), before)

    def test_completed_model_reuse_creates_another_group_only_after_new_approval(self):
        request_id = self.recovered_model()
        original_status = self.finish_application(self.prepare_model(request_id))
        before = len(self.calls), len(self.paid), len(self.downloads)
        objects = set(bpy.data.objects)
        bpy.context.scene.cursor.location = (5, 0, 0)
        approval = self.prepare_model(request_id)
        self.assertTrue(approval["reuse"])
        self.assertEqual(set(bpy.data.objects), objects)
        status = self.finish_application(approval)
        added = set(bpy.data.objects) - objects
        self.assertEqual(len(added), 3)  # Two GLB nodes plus the placement group.
        self.assertCountEqual(
            status["objects"],
            [
                *original_status["objects"],
                *(obj.name for obj in added if obj.type == "MESH" or obj.parent in added),
            ],
        )
        self.assertEqual(len(status["objects"]), 4)
        self.assertEqual(sum(obj.parent not in added for obj in added), 1)
        self.assertEqual(status["local_applications"][0]["state"], "applied")
        with self.assertRaises(self.request_error):
            self.tools.apply_result_application(self.import_args(approval))
        removed = original_status["objects"][0]
        bpy.data.objects.remove(bpy.data.objects[removed], do_unlink=True)
        self.assertCountEqual(
            self.runtime.state.model_jobs.status(request_id)["objects"],
            [name for name in status["objects"] if name != removed],
        )
        self.assertEqual((len(self.calls), len(self.paid), len(self.downloads)), before)

    def test_completed_image_reuse_rejects_other_prepared_approval_after_claim(self):
        request_id = self.recovered_images()
        self.finish_application(self.prepare_import(request_id))
        first, second = self.prepare_import(request_id), self.prepare_import(request_id)
        before = len(self.calls), len(self.paid), len(self.downloads)
        status = self.finish_application(first)
        images = set(bpy.data.images)
        self.assertEqual(len(status["local_applications"]), 1)
        with self.assertRaises(self.request_error):
            self.tools.apply_result_application(self.import_args(second))
        self.assertEqual(set(bpy.data.images), images)
        self.assertEqual((len(self.calls), len(self.paid), len(self.downloads)), before)

    def test_uncertain_local_application_blocks_reuse_after_restart(self):
        request_id = self.recovered_images()
        self.finish_application(self.prepare_import(request_id))
        deferred = self.tools.apply_result_application(
            self.import_args(self.prepare_import(request_id))
        )
        result = deferred.run()
        with patch.object(
            submodule("blender.job_session"),
            "apply_images",
            side_effect=RuntimeError("synthetic uncertain application"),
        ):
            status = deferred.finish(result)
        self.assertEqual(status["status"], "applied")
        self.assertEqual(status["local_applications"][0]["state"], "applying")
        self.assertEqual(status["actions"], ())
        self.runtime.state.reset()
        self.runtime.inspect_model_jobs()
        before = len(self.calls), len(self.paid), len(self.downloads), set(bpy.data.images)
        status = self.runtime.state.model_jobs.status(request_id)
        self.assertEqual(status["actions"], ())
        self.assertIn("do not repeat", status["error"])
        with self.assertRaises(self.request_error):
            self.prepare_import(request_id)
        self.assertEqual(
            (len(self.calls), len(self.paid), len(self.downloads), set(bpy.data.images)), before
        )

    def test_local_receipt_retry_recognizes_committed_success_without_another_import(self):
        request_id = self.recovered_images()
        original_status = self.finish_application(self.prepare_import(request_id))
        deferred = self.tools.apply_result_application(
            self.import_args(self.prepare_import(request_id))
        )
        result = deferred.run()
        owner = self.runtime.state.model_jobs
        finish = owner.store.finish_local_application

        def lose_receipt(*args, **kwargs):
            finish(*args, **kwargs)
            raise OSError("synthetic lost receipt response")

        with patch.object(owner.store, "finish_local_application", side_effect=lose_receipt):
            status = deferred.finish(result)
        self.assertEqual(status["status"], "applied")
        self.assertEqual(status["local_applications"][0]["state"], "applied")
        self.assertEqual(status["actions"], ("retry_receipt",))
        self.assertEqual(len(status["images"]), 2)
        self.assertIn(original_status["images"][0], status["images"])
        imported_names = status["images"]
        before = set(bpy.data.images), len(self.calls), len(self.paid), len(self.downloads)
        with patch.object(
            submodule("blender.job_session"),
            "apply_images",
            side_effect=AssertionError("Repeated scene mutation"),
        ):
            status = self.recover(request_id, "retry_receipt")
        self.assertEqual(status["local_applications"][0]["state"], "applied")
        self.assertIn("import_images", status["actions"])
        self.assertEqual(status["images"], imported_names)
        self.assertEqual(
            (set(bpy.data.images), len(self.calls), len(self.paid), len(self.downloads)), before
        )
        removed = original_status["images"][0]
        bpy.data.images.remove(bpy.data.images[removed], do_unlink=True)
        self.assertEqual(
            owner.status(request_id)["images"], [name for name in imported_names if name != removed]
        )
        status = self.finish_application(self.prepare_import(request_id))
        self.assertEqual(len(status["images"]), 2)
        self.assertIn(next(name for name in imported_names if name != removed), status["images"])
        self.assertEqual((len(self.calls), len(self.paid), len(self.downloads)), before[1:])

    def test_failed_reuse_keeps_completed_generation_and_original_images(self):
        request_id = self.recovered_images()
        self.finish_application(self.prepare_import(request_id))
        before = set(bpy.data.images), bpy.context.scene.world, len(self.calls), len(self.paid)
        status = self.finish_application(self.prepare_world(request_id))
        self.assertEqual(status["status"], "applied")
        self.assertEqual(status["local_applications"][0]["state"], "failed")
        self.assertIn("apply_world", status["actions"])
        self.assertEqual(
            (set(bpy.data.images), bpy.context.scene.world, len(self.calls), len(self.paid)), before
        )

    def recovered_mesh_edit(self, body=None):
        request_id = self.recovered_model(body)
        bpy.ops.mesh.primitive_cube_add()
        return request_id

    def prepare_mesh_edit(self, request_id, **options):
        return self.tools.prepare_result_application(
            {
                "context_id": self.runtime.state.job_context_id,
                "request_id": request_id,
                "expected_revision": self.store.get(request_id).revision,
                "purpose": "mesh_edit",
                "asset_id": "result-image",
                **options,
            }
        )

    def test_saved_mesh_edit_requires_explicit_target_review_before_replacement(self):
        request_id = self.recovered_mesh_edit()
        source = bpy.context.view_layer.objects.active
        old_mesh = source.data
        before = len(self.calls), len(self.paid), len(self.downloads)
        approval = self.prepare_mesh_edit(request_id)
        self.assertEqual(approval["target"], source.name)
        self.assertEqual(approval["mesh_policy"], "REMESH")
        self.assertEqual(approval["mesh_placement"], "WORLD")
        self.assertTrue(approval["keep_original"])
        self.assertEqual(source.data, old_mesh)
        self.assertEqual((len(self.calls), len(self.paid), len(self.downloads)), before)
        status = self.finish_application(approval)
        self.assertEqual(status["status"], "applied", status)
        self.assertNotEqual(source.data, old_mesh)
        self.assertEqual(status["mesh_edit"]["target"], source.name)
        self.assertEqual(bpy.data.objects[status["mesh_edit"]["original"]].data, old_mesh)
        self.assertFalse(bpy.data.objects[status["mesh_edit"]["original"]].select_get())
        self.assertEqual((len(self.calls), len(self.paid), len(self.downloads)), before)
        with self.assertRaises(self.request_error):
            self.tools.apply_result_application(self.import_args(approval))

    def test_mesh_edit_world_placement_preserves_imported_positions_with_transformed_source(self):
        request_id = self.recovered_mesh_edit()
        source = bpy.context.view_layer.objects.active
        source.location.x = 10
        source.scale = (2, 2, 2)
        approval = self.prepare_mesh_edit(request_id, keep_original=False)
        status = self.finish_application(approval)
        self.assertEqual(status["status"], "applied", status)
        self.assertIsNone(status["mesh_edit"]["original"])
        self.assertEqual(min((source.matrix_world @ v.co).x for v in source.data.vertices), 2)
        self.assertEqual(source.location.x, 10)
        self.assertEqual(tuple(source.scale), (2, 2, 2))

    def test_mesh_edit_rejects_geometry_changed_after_approval(self):
        request_id = self.recovered_mesh_edit()
        approval = self.prepare_mesh_edit(request_id)
        source = bpy.context.view_layer.objects.active
        source.data.vertices[0].co.x += 1
        old = self.store.get(request_id)
        with self.assertRaises(submodule("blender.mesh_application").MeshApplicationError):
            self.tools.apply_result_application(self.import_args(approval))
        self.assertEqual(self.store.get(request_id), old)

    def test_mesh_dialog_reviews_local_coordinates_for_mirrored_or_zero_scale_sources(self):
        request_id = self.recovered_mesh_edit()
        source = bpy.context.view_layer.objects.active
        operator = submodule("blender.job_recovery").SCENARIO_OT_apply_saved_mesh
        jobs = self.runtime.state.model_jobs
        before = self.store.get(request_id)
        requests = len(self.calls), len(self.paid), len(self.downloads)
        for scale, placement in (
            ((-1, 1, 1), "LOCAL"),
            ((0, 1, 1), "LOCAL"),
            ((-1, -1, 1), "WORLD"),
        ):
            with self.subTest(scale=scale):
                source.scale = scale
                dialog = Mock(return_value={"RUNNING_MODAL"})
                context = SimpleNamespace(
                    scene=bpy.context.scene,
                    view_layer=bpy.context.view_layer,
                    window_manager=SimpleNamespace(invoke_props_dialog=dialog),
                )
                op = SimpleNamespace(
                    context_id=self.runtime.state.job_context_id,
                    request_id=request_id,
                    expected_revision=before.revision,
                    asset_id="result-image",
                    policy="REMESH",
                    placement="WORLD",
                    keep_original=True,
                    original_source=False,
                    report=Mock(),
                )
                self.assertEqual(operator.invoke(op, context, None), {"RUNNING_MODAL"})
                dialog.assert_called_once_with(op, width=580)
                op.report.assert_not_called()
                ticket = jobs._application_approvals[op.application_id]
                self.assertEqual(op.placement, placement)
                self.assertEqual(ticket.placement, placement)
                self.assertEqual(ticket.target.obj, source)
                self.assertEqual(op.local_placement_required, placement == "LOCAL")
                if placement == "LOCAL":
                    op._sync_options = lambda op=op: operator._sync_options(op)
                    op.placement = "WORLD"
                    operator.check(op, context)
                    self.assertTrue(op.review_error)
                    self.assertIs(jobs._application_approvals[op.application_id], ticket)
                    op.placement = "LOCAL"
                    operator.check(op, context)
                    self.assertFalse(op.review_error)
                operator.cancel(op, context)
                self.assertFalse(jobs._application_approvals)
        self.assertEqual(self.store.get(request_id), before)
        self.assertEqual((len(self.calls), len(self.paid), len(self.downloads)), requests)
        self.assertFalse(jobs._commands)

    def test_mirrored_mesh_requires_explicit_local_mapping_and_preserves_source_transform(self):
        request_id = self.recovered_mesh_edit()
        source = bpy.context.view_layer.objects.active
        source.scale = (-1, 2, 1)
        bpy.context.view_layer.update()
        transform = source.matrix_world.copy()
        with self.assertRaises(submodule("blender.mesh_application").MeshApplicationError):
            self.prepare_mesh_edit(request_id, mesh_placement="WORLD")
        jobs = self.runtime.state.model_jobs
        self.assertFalse(jobs._application_approvals)
        self.assertFalse(jobs._commands)
        status = self.finish_application(self.prepare_mesh_edit(request_id, mesh_placement="LOCAL"))
        self.assertEqual(status["status"], "applied", status)
        self.assertEqual(source.matrix_world, transform)
        self.assertEqual(len(source.data.vertices), 3)
        self.assertEqual(min(v.co.x for v in source.data.vertices), 2)

    def test_retired_mesh_approval_cannot_queue_verification_or_change_the_scene(self):
        request_id = self.recovered_mesh_edit()
        approval = self.prepare_mesh_edit(request_id)
        owner = self.runtime.state.model_jobs
        before = self.store.get(request_id)
        source = bpy.context.view_layer.objects.active
        mesh = source.data
        objects = set(bpy.data.objects)
        requests = len(self.calls), len(self.paid), len(self.downloads)
        owner.session.deactivate()
        with patch.object(owner.session, "verify_results") as verify:
            with self.assertRaises(self.origin_error):
                owner.apply_saved_result(approval["application_id"])
        verify.assert_not_called()
        self.assertNotIn(approval["application_id"], owner._application_approvals)
        self.assertNotIn(request_id, owner._commands)
        self.assertEqual(self.store.get(request_id), before)
        self.assertEqual(source.data, mesh)
        self.assertEqual(set(bpy.data.objects), objects)
        self.assertEqual((len(self.calls), len(self.paid), len(self.downloads)), requests)

    def test_mesh_edit_options_keep_same_captured_target_and_invalidate_old_ticket(self):
        request_id = self.recovered_mesh_edit()
        source = bpy.context.view_layer.objects.active
        approval = self.prepare_mesh_edit(request_id)
        jobs = self.runtime.state.model_jobs
        ticket = jobs._application_approvals[approval["application_id"]]
        updated = self.runtime.revise_mesh_application(
            self.runtime.state.job_context_id,
            ticket.identifier,
            policy="REMESH",
            placement="LOCAL",
            keep_original=False,
        )
        self.assertEqual(updated.target, ticket.target)
        self.assertEqual(updated.destination, ticket.destination)
        self.assertNotEqual(updated.identifier, ticket.identifier)
        with self.assertRaises(self.request_error):
            self.tools.apply_result_application(self.import_args(approval))
        approval["application_id"] = updated.identifier
        status = self.finish_application(approval)
        self.assertEqual(status["status"], "applied", status)
        self.assertEqual(status["mesh_edit"]["target"], source.name)
        self.assertEqual(bpy.context.view_layer.objects.active, source)

    def test_mesh_edit_uv_mismatch_is_a_known_local_failure(self):
        request_id = self.recovered_mesh_edit()
        source = bpy.context.view_layer.objects.active
        mesh = source.data
        status = self.finish_application(self.prepare_mesh_edit(request_id, mesh_policy="UV"))
        self.assertEqual(status["status"], "apply_failed", status)
        self.assertEqual(source.data, mesh)
        self.assertIn("apply_mesh", status["actions"])

    def test_mesh_edit_wrong_part_count_reports_a_paused_failure_without_replay(self):
        request_id = self.recovered_mesh_edit()
        source = bpy.context.view_layer.objects.active
        before = (
            source.data,
            set(bpy.data.objects),
            len(self.calls),
            len(self.paid),
            len(self.downloads),
        )
        status = self.finish_application(self.prepare_mesh_edit(request_id, mesh_policy="PARTS"))
        self.assertEqual(status["status"], "apply_failed", status)
        self.assertTrue(status["delivery_paused"])
        self.assertEqual(
            status["error"],
            "Mesh application stopped; inspect the saved GLB, source and edit policy",
        )
        saved = self.store.get(request_id)
        for _ in range(3):
            self.runtime.state.model_jobs.poll()
        self.assertEqual(self.store.get(request_id), saved)
        self.assertEqual(
            (
                source.data,
                set(bpy.data.objects),
                len(self.calls),
                len(self.paid),
                len(self.downloads),
            ),
            before,
        )
        self.assertIn("apply_mesh", status["actions"])

    def test_mesh_edit_retexture_mismatch_is_a_known_local_failure(self):
        request_id = self.recovered_mesh_edit()
        source = bpy.context.view_layer.objects.active
        before = source.data, len(self.calls), len(self.paid), len(self.downloads)
        approval = self.prepare_mesh_edit(request_id, mesh_policy="RETEXTURE")
        self.assertEqual(approval["mesh_policy"], "RETEXTURE")
        status = self.finish_application(approval)
        self.assertEqual(status["status"], "apply_failed", status)
        self.assertEqual(
            (source.data, len(self.calls), len(self.paid), len(self.downloads)), before
        )
        self.assertIn("apply_mesh", status["actions"])

    def test_mesh_edit_retexture_shared_approval_preserves_geometry_and_records_success(self):
        request_id = self.recovered_mesh_edit()
        source = bpy.context.view_layer.objects.active
        # Establish exact GLB indexing with the existing explicitly approved remesh.
        self.assertEqual(
            self.finish_application(self.prepare_mesh_edit(request_id))["status"], "applied"
        )
        material = bpy.data.materials.new("Retexture source material")
        source.data.materials.clear()
        source.data.materials.append(material)
        old_mesh = source.data
        geometry = [tuple(vertex.co) for vertex in old_mesh.vertices]
        calls = len(self.calls), len(self.paid), len(self.downloads)
        approval = self.prepare_mesh_edit(request_id, mesh_policy="RETEXTURE")
        self.assertTrue(approval["reuse"])
        status = self.finish_application(approval)
        self.assertEqual(status["status"], "applied", status)
        self.assertEqual(status["mesh_edit"]["policy"], "RETEXTURE")
        self.assertEqual(status["local_applications"][-1]["state"], "applied")
        self.assertEqual([tuple(vertex.co) for vertex in source.data.vertices], geometry)
        self.assertNotEqual(source.data.materials[0], material)
        self.assertEqual(list(old_mesh.materials), [material])
        self.assertEqual((len(self.calls), len(self.paid), len(self.downloads)), calls)
        with self.assertRaises(self.request_error):
            self.tools.apply_result_application(self.import_args(approval))

    def mesh_native_history(self, policy, *, keep_original):
        from helpers import parts_glb

        request_id = self.recovered_mesh_edit(parts_glb() if policy == "PARTS" else None)
        source = bpy.context.view_layer.objects.active
        if policy not in {"REMESH", "PARTS"}:
            self.finish_application(self.prepare_mesh_edit(request_id, keep_original=False))
        names = bpy.context.scene.name, source.name
        source["retain_user_value"] = "before application"
        source.location = (0, 0, 0)
        before = [tuple(vertex.co) for vertex in source.data.vertices]
        material = bpy.data.materials.new("History original material")
        source.data.materials.clear()
        source.data.materials.append(material)
        before_materials = [item.name for item in source.data.materials]
        module = submodule("blender.mesh_result_application")
        preferences = bpy.context.preferences.edit
        settings = preferences.use_global_undo, preferences.undo_steps
        preferences.use_global_undo, preferences.undo_steps = True, 32
        try:
            # Exercise real native memfile history in the installed background
            # runner; production enables automatic checkpoints on desktop only.
            with patch.object(module, "_undo_enabled", return_value=True):
                status = self.finish_application(
                    self.prepare_mesh_edit(
                        request_id, mesh_policy=policy, keep_original=keep_original
                    )
                )
            self.assertEqual(status["status"], "applied", status)
            self.assertTrue(status["mesh_edit"]["undo_available"])
            after = [tuple(vertex.co) for vertex in source.data.vertices]
            after_materials = [item.name for item in source.data.materials]
            original_name = status["mesh_edit"]["original"]
            part_names = status["mesh_edit"]["parts"]
            record = self.store.get(request_id)
            pending = self.prepare_mesh_edit(request_id)
            calls = len(self.calls), len(self.paid), len(self.downloads)
            self.assertEqual(bpy.ops.ed.undo(), {"FINISHED"})
            scene = bpy.data.scenes[names[0]]
            source = bpy.data.objects[names[1]]
            bpy.context.window.scene = scene
            self.assertEqual([tuple(vertex.co) for vertex in source.data.vertices], before)
            self.assertEqual([item.name for item in source.data.materials], before_materials)
            self.assertEqual(source["retain_user_value"], "before application")
            if original_name:
                self.assertNotIn(original_name, bpy.data.objects)
            self.assertTrue(all(name not in bpy.data.objects for name in part_names))
            self.assertEqual(self.store.get(request_id), record)
            self.assertIsNone(self.tools.job_status({"job_id": request_id})["mesh_edit"])
            with self.assertRaises(
                (
                    self.origin_error,
                    self.request_error,
                    submodule("blender.mesh_application").MeshApplicationError,
                )
            ):
                self.tools.apply_result_application(self.import_args(pending))
            self.assertEqual(bpy.ops.ed.redo(), {"FINISHED"})
            source = bpy.data.objects[names[1]]
            self.assertEqual([tuple(vertex.co) for vertex in source.data.vertices], after)
            self.assertEqual([item.name for item in source.data.materials], after_materials)
            if original_name:
                self.assertIn(original_name, bpy.data.objects)
            self.assertTrue(all(bpy.data.objects[name].parent == source for name in part_names))
            self.assertEqual(self.store.get(request_id), record)
            self.assertEqual((len(self.calls), len(self.paid), len(self.downloads)), calls)
            self.assertIsNone(self.tools.job_status({"job_id": request_id})["mesh_edit"])
            self.assertFalse(
                any(scene.name.startswith("Scenario import staging") for scene in bpy.data.scenes)
            )
            self.assertFalse(
                any(obj.name.startswith("Scenario rollback") for obj in bpy.data.objects)
            )
        finally:
            preferences.use_global_undo, preferences.undo_steps = settings

    def test_mesh_native_undo_redo_preserves_job_without_replaying_remesh(self):
        self.mesh_native_history("REMESH", keep_original=False)

    def test_mesh_native_undo_redo_restores_uv_edit_and_original_copy(self):
        self.mesh_native_history("UV", keep_original=True)

    def test_mesh_native_undo_redo_restores_grouped_parts_and_original_copy(self):
        self.mesh_native_history("PARTS", keep_original=True)

    def test_mesh_native_undo_redo_restores_retexture_materials(self):
        self.mesh_native_history("RETEXTURE", keep_original=True)

    def test_mesh_failed_undo_preparation_preserves_source_and_allows_local_review(self):
        request_id = self.recovered_mesh_edit()
        source = bpy.context.view_layer.objects.active
        before = source.data
        module = submodule("blender.mesh_result_application")
        with (
            patch.object(module, "_undo_enabled", return_value=True),
            patch.object(
                module, "_undo_push", side_effect=RuntimeError("fixture unavailable history")
            ),
        ):
            status = self.finish_application(self.prepare_mesh_edit(request_id))
        self.assertEqual(status["status"], "apply_failed", status)
        self.assertEqual(source.data, before)
        self.assertIn("apply_mesh", status["actions"])

    def test_mesh_failed_import_does_not_automatically_undo_latest_user_state(self):
        request_id = self.recovered_mesh_edit()
        source = bpy.context.view_layer.objects.active
        source_name = source.name
        before = source.data
        module = submodule("blender.mesh_result_application")
        preferences = bpy.context.preferences.edit
        settings = preferences.use_global_undo, preferences.undo_steps
        preferences.use_global_undo, preferences.undo_steps = True, 32
        try:
            self.assertEqual(bpy.ops.ed.undo_push(message="Fixture prior state"), {"FINISHED"})
            source["latest_user_edit"] = "must survive failed application"
            with (
                patch.object(module, "_undo_enabled", return_value=True),
                patch.object(
                    module.model_application,
                    "_import",
                    side_effect=RuntimeError("fixture decode failure"),
                ),
            ):
                status = self.finish_application(self.prepare_mesh_edit(request_id))
            self.assertEqual(status["status"], "apply_failed", status)
            self.assertEqual(source.data, before)
            self.assertEqual(source["latest_user_edit"], "must survive failed application")
            record = self.store.get(request_id)
            calls = len(self.calls), len(self.paid), len(self.downloads)
            # Only the user's explicit undo traverses history and retires guards.
            self.assertEqual(bpy.ops.ed.undo(), {"FINISHED"})
            self.assertNotIn("latest_user_edit", bpy.data.objects[source_name])
            self.assertEqual(self.store.get(request_id), record)
            self.assertEqual((len(self.calls), len(self.paid), len(self.downloads)), calls)
        finally:
            preferences.use_global_undo, preferences.undo_steps = settings

    def test_mesh_failed_final_undo_checkpoint_keeps_success_without_replay(self):
        request_id = self.recovered_mesh_edit()
        source = bpy.context.view_layer.objects.active
        module = submodule("blender.mesh_result_application")
        with (
            patch.object(module, "_undo_enabled", return_value=True),
            patch.object(
                module,
                "_undo_push",
                side_effect=[None, RuntimeError("fixture unavailable history")],
            ),
        ):
            status = self.finish_application(self.prepare_mesh_edit(request_id))
        self.assertEqual(status["status"], "applied", status)
        self.assertFalse(status["mesh_edit"]["undo_available"])
        self.assertEqual(len(source.data.vertices), 3)
        self.assertNotIn("retry_receipt", status["actions"])

    def test_mesh_edit_receipt_recovery_saves_success_without_replacement(self):
        request_id = self.recovered_mesh_edit()
        approval = self.prepare_mesh_edit(request_id)
        deferred = self.tools.apply_result_application(self.import_args(approval))
        result = deferred.run()
        store = self.runtime.state.job_store
        transition = store.transition

        def fail_receipt(*args, **kwargs):
            if kwargs.get("state") == self.storemod.JobState.APPLIED:
                raise OSError("synthetic receipt failure")
            return transition(*args, **kwargs)

        with patch.object(store, "transition", side_effect=fail_receipt):
            status = deferred.finish(result)
        self.assertEqual(status["status"], "applying", status)
        self.assertEqual(status["actions"], ("retry_receipt",))
        mesh = bpy.context.view_layer.objects.active.data
        self.assertEqual(status["mesh_edit"]["policy"], "REMESH")
        self.runtime.state.model_jobs.session.invalidate_all()
        self.assertIsNone(self.tools.job_status({"job_id": request_id})["mesh_edit"])
        with patch.object(
            submodule("blender.job_session"),
            "apply_saved_mesh",
            side_effect=AssertionError("repeated"),
        ):
            status = self.recover(request_id, "retry_receipt")
        self.assertEqual(status["status"], "applied", status)
        self.assertIsNone(status["mesh_edit"])
        self.assertEqual(bpy.context.view_layer.objects.active.data, mesh)

    def test_completed_mesh_can_be_reused_for_an_explicit_mesh_edit(self):
        request_id = self.recovered_mesh_edit()
        self.finish_application(self.prepare_model(request_id))
        original = self.store.get(request_id)
        approval = self.prepare_mesh_edit(request_id, mesh_placement="LOCAL")
        self.assertTrue(approval["reuse"])
        status = self.finish_application(approval)
        saved = self.store.get(request_id)
        self.assertEqual(saved.intent, original.intent)
        self.assertEqual(saved.application_origin, original.application_origin)
        self.assertEqual(status["local_applications"][0]["state"], "applied")
        self.assertEqual(status["local_applications"][0]["purpose"], "mesh_edit")
        self.assertEqual(status["mesh_edit"]["target"], bpy.context.view_layer.objects.active.name)
        reopened = self.storemod.JobStore(self.store._path, self.store.scope)
        self.assertEqual(reopened.get(request_id), saved)
        self.finish_application(self.prepare_model(request_id))
        purposes = [item.purpose for item in reopened.get(request_id).local_applications]
        self.assertEqual(purposes, ["mesh_edit", "model"])

    def test_mesh_edit_unknown_outcome_blocks_another_application(self):
        request_id = self.recovered_mesh_edit()
        deferred = self.tools.apply_result_application(
            self.import_args(self.prepare_mesh_edit(request_id))
        )
        result = deferred.run()
        with patch.object(
            submodule("blender.job_session"),
            "apply_saved_mesh",
            side_effect=RuntimeError("uncertain"),
        ):
            status = deferred.finish(result)
        self.assertEqual(status["status"], "applying", status)
        self.assertEqual(status["actions"], ())
        with self.assertRaises(self.request_error):
            self.prepare_mesh_edit(request_id)

    def test_mesh_edit_invalid_keep_original_is_rejected_before_verification(self):
        request_id = self.recovered_mesh_edit()
        before = len(self.calls), len(self.paid), len(self.downloads), self.store.get(request_id)
        with self.assertRaises(
            submodule("blender.mesh_result_application").MeshResultApplicationError
        ):
            self.prepare_mesh_edit(request_id, keep_original=1)
        self.assertEqual(
            (len(self.calls), len(self.paid), len(self.downloads), self.store.get(request_id)),
            before,
        )

    def test_mesh_operator_uses_prepared_approval_and_consumes_it_once(self):
        request_id = self.recovered_mesh_edit()
        approval = self.prepare_mesh_edit(request_id)
        source = bpy.context.view_layer.objects.active
        previous = source.data
        args = self.import_args(approval)
        self.assertEqual(bpy.ops.scenario.apply_saved_mesh(**args), {"FINISHED"})
        jobs = self.runtime.state.model_jobs
        jobs._commands[request_id][1].result(5)
        status = jobs.status(request_id)
        self.assertEqual(status["status"], "applied", status)
        self.assertNotEqual(source.data, previous)
        with self.assertRaisesRegex(RuntimeError, "Mesh edit was not started"):
            bpy.ops.scenario.apply_saved_mesh(**args)

    def test_mesh_edit_target_changed_during_verification_is_not_claimed(self):
        request_id = self.recovered_mesh_edit()
        approval = self.prepare_mesh_edit(request_id)
        source = bpy.context.view_layer.objects.active
        previous = source.data
        before = self.store.get(request_id)
        deferred = self.tools.apply_result_application(self.import_args(approval))
        verified = deferred.run()
        source.data.vertices[0].co.x += 1
        status = deferred.finish(verified)
        self.assertEqual(self.store.get(request_id), before)
        self.assertEqual(status["status"], "ready", status)
        self.assertEqual(source.data, previous)
        self.assertTrue(status["delivery_paused"])
        self.assertIn("Mesh application stopped", status["error"])

    def captured_mesh_upload(self, *, live=False):
        session = self.runtime.ensure_job_session()
        origin = session.capture(bpy.context.scene, bpy.context.object)
        source_types = submodule("core.jobs.mesh_source")
        uploads = submodule("core.jobs.upload_store")
        source = source_types.MeshSource(
            "a" * 64,
            (
                source_types.MeshSourceObject(
                    origin.target_id,
                    "b" * 64,
                    tuple(tuple(row) for row in bpy.context.object.matrix_world),
                ),
            ),
        )
        size, digest = 11, "a" * 64
        if live:
            with tempfile.TemporaryDirectory(dir=bpy.utils.resource_path("USER")) as directory:
                path = Path(directory) / "source.glb"
                origin, source = submodule("blender.mesh_provenance").export_with_source(
                    bpy.context, (bpy.context.object,), path, session
                )
                size, digest = path.stat().st_size, source.file_sha256
        store = session._coordinator._uploads._store
        record = store.create(
            uploads.UploadIntent(
                "captured-mesh",
                store.scope,
                origin,
                "3d",
                "source.glb",
                "model/gltf-binary",
                size,
                digest,
                size,
                (digest,),
                source,
            )
        )

        def advance(state, **changes):
            nonlocal record
            record = store.transition(
                record.intent.request_id, expected_revision=record.revision, state=state, **changes
            )

        advance(uploads.UploadState.INITIALIZING)
        advance(uploads.UploadState.UPLOADING, upload_id="remote-upload")
        record = store.claim_part(record.intent.request_id, expected_revision=record.revision)
        record = store.record_part(
            record.intent.request_id,
            uploads.UploadedPart(1, size, digest),
            expected_revision=record.revision,
        )
        advance(uploads.UploadState.FINALIZING)
        advance(uploads.UploadState.PROCESSING)
        advance(uploads.UploadState.IMPORTED, asset_id="uploaded-mesh")
        return record

    def test_ui_and_mcp_persist_same_captured_mesh_binding_without_sending_it(self):
        self.configure_ui_lane("edit3d")
        upload = self.captured_mesh_upload()
        self.ui_quote("edit3d")
        self.assertEqual(bpy.ops.scenario.generate(lane="edit3d"), {"FINISHED"})
        self.settle()
        ui = self.store.records()[0]
        self.assertEqual(ui.state, self.storemod.JobState.REMOTE)
        self.assertEqual(ui.intent.mesh_sources[0].mesh_source, upload.intent.mesh_source)
        self.assertEqual(ui.intent.mesh_sources[0].origin, upload.intent.origin)
        args = {
            "lane": "edit3d",
            "model_id": self.model["id"],
            "parameters": {"prompt": "a teapot", "mesh": "uploaded-mesh"},
        }
        deferred = self.tools.estimate_cost(args)
        quote = deferred.finish(deferred.run())
        self.assertEqual(
            quote["mesh_sources"], [asdict(source) for source in ui.intent.mesh_sources]
        )
        result = self.tools.generate(
            dict(args, quote_id=quote["quote_id"], approved_cost=quote["cu_cost_exact"])
        )
        self.settle()
        saved = self.store.get(result["local_id"])
        self.assertEqual(saved.intent.mesh_sources, ui.intent.mesh_sources)
        status = self.tools.job_status({"job_id": result["local_id"]})
        self.assertEqual(status["mesh_sources"], quote["mesh_sources"])
        self.assertEqual(len(self.paid), 2)
        self.assertEqual(self.paid[0].content, self.paid[1].content)
        self.assertNotIn("mesh_sources", json.loads(self.paid[0].content))
        self.runtime.state.reset()
        self.assertEqual(
            self.runtime.ensure_job_store().get(result["local_id"]).intent.mesh_sources,
            saved.intent.mesh_sources,
        )

    def captured_source_result(self, body=None, *, source_geometry=None, scale=(1, 1, 1)):
        from helpers import FIXTURES

        self.configure_ui_lane("edit3d")
        source = bpy.context.object
        if source_geometry is not None:
            data = bpy.data.meshes.new("Captured source geometry")
            data.from_pydata(source_geometry, [], [(0, 1, 2)])
            data.update()
            source.data = data
        source.scale = scale
        bpy.context.view_layer.update()
        self.captured_mesh_upload(live=True)
        self.result_bytes = (
            body if body is not None else (FIXTURES / "synthetic/static-triangle.glb").read_bytes()
        )
        self.result_media_type, self.remote_status = "model/gltf-binary", "success"
        self.ui_quote("edit3d")
        result = self.generation.submit_generation(bpy.context, "edit3d")
        self.deliver_results()
        self.assertEqual(self.store.get(result.local_id).state, self.storemod.JobState.READY)
        return result.local_id, source

    def captured_source_dialog(self, source_scale, selected_scale, placement):
        request_id, source = self.captured_source_result(scale=source_scale)
        bpy.ops.mesh.primitive_cube_add(location=(9, 0, 0))
        selected = bpy.context.object
        selected.scale = selected_scale
        before = self.store.get(request_id)
        requests = len(self.calls), len(self.paid), len(self.downloads)
        objects = set(bpy.data.objects)
        meshes = source.data, selected.data
        if placement == "LOCAL":
            with self.assertRaises(
                (submodule("blender.mesh_application").MeshApplicationError, self.request_error)
            ):
                self.prepare_mesh_edit(request_id, purpose="mesh_source", mesh_placement="WORLD")
        dialog = Mock(return_value={"RUNNING_MODAL"})
        context = SimpleNamespace(
            scene=bpy.context.scene,
            view_layer=bpy.context.view_layer,
            window_manager=SimpleNamespace(invoke_props_dialog=dialog),
        )
        op = SimpleNamespace(
            context_id=self.runtime.state.job_context_id,
            request_id=request_id,
            expected_revision=before.revision,
            asset_id="result-image",
            policy="REMESH",
            placement="WORLD",
            keep_original=True,
            original_source=True,
            report=Mock(),
        )
        operator = submodule("blender.job_recovery").SCENARIO_OT_apply_saved_mesh
        self.assertEqual(operator.invoke(op, context, None), {"RUNNING_MODAL"})
        dialog.assert_called_once_with(op, width=580)
        op.report.assert_not_called()
        jobs = self.runtime.state.model_jobs
        ticket = jobs._application_approvals[op.application_id]
        self.assertIs(ticket.target.obj, source)
        self.assertEqual((op.placement, ticket.placement), (placement, placement))
        self.assertEqual(op.local_placement_required, placement == "LOCAL")
        self.assertEqual(op.target_name, source.name)
        operator.cancel(op, context)
        self.assertFalse(jobs._application_approvals)
        self.assertFalse(jobs._commands)
        self.assertEqual(self.store.get(request_id), before)
        self.assertEqual((len(self.calls), len(self.paid), len(self.downloads)), requests)
        self.assertEqual(set(bpy.data.objects), objects)
        self.assertEqual((source.data, selected.data), meshes)
        self.assertIs(bpy.context.object, selected)

    def test_captured_mirrored_source_dialog_ignores_positive_selected_transform(self):
        self.captured_source_dialog((-1, 2, 1), (1, 1, 1), "LOCAL")

    def test_captured_zero_scale_dialog_ignores_positive_selected_transform(self):
        self.captured_source_dialog((0, 1, 1), (1, 1, 1), "LOCAL")

    def test_captured_positive_source_dialog_ignores_mirrored_selected_transform(self):
        self.captured_source_dialog((1, 2, 1), (-1, 1, 1), "WORLD")

    def captured_rig_result(self):
        return self.captured_source_result(
            animated_glb(morph=False), source_geometry=[(0, 0, 0), (1, 0, 0), (0, 0, 1)]
        )

    def test_captured_rig_uses_original_source_and_native_history_without_new_spending(self):
        request_id, source = self.captured_rig_result()
        source_name = source.name
        bpy.ops.mesh.primitive_cube_add(location=(9, 0, 0))
        other_name = bpy.context.object.name
        calls = len(self.calls), len(self.paid), len(self.downloads)
        approval = self.prepare_mesh_edit(request_id, purpose="mesh_source", mesh_policy="RIG")
        self.assertEqual(approval["target"], source_name)
        module = submodule("blender.mesh_result_application")
        prefs = bpy.context.preferences.edit
        settings = prefs.use_global_undo, prefs.undo_steps
        prefs.use_global_undo, prefs.undo_steps = True, 32
        try:
            with patch.object(module, "_undo_enabled", return_value=True):
                status = self.finish_application(approval)
            self.assertEqual(status["status"], "applied", status)
            rig_name = status["mesh_edit"]["rig"]
            self.assertEqual(source.modifiers[0].object.name, rig_name)
            self.assertEqual(bpy.context.object.name, other_name)
            self.assertEqual(bpy.ops.ed.undo(), {"FINISHED"})
            source = bpy.data.objects[source_name]
            self.assertFalse(source.modifiers)
            self.assertFalse(source.vertex_groups)
            self.assertNotIn(rig_name, bpy.data.objects)
            self.assertIsNone(self.tools.job_status({"job_id": request_id})["mesh_edit"])
            self.assertEqual(bpy.ops.ed.redo(), {"FINISHED"})
            self.assertEqual(bpy.data.objects[source_name].modifiers[0].object.name, rig_name)
            self.assertEqual(self.store.get(request_id).state, self.storemod.JobState.APPLIED)
            self.assertEqual((len(self.calls), len(self.paid), len(self.downloads)), calls)
        finally:
            prefs.use_global_undo, prefs.undo_steps = settings

    def test_native_rig_command_uses_the_shared_captured_source_approval(self):
        request_id, source = self.captured_rig_result()
        approval = self.prepare_mesh_edit(request_id, purpose="mesh_source", mesh_policy="RIG")
        args = self.import_args(approval)
        args.update(
            request_id=request_id,
            expected_revision=approval["revision"],
            asset_id=approval["asset_id"],
            original_source=True,
            policy="RIG",
        )
        before = len(self.calls), len(self.paid)
        self.assertEqual(bpy.ops.scenario.apply_saved_mesh(**args), {"FINISHED"})
        self.deliver_results()
        self.assertEqual(self.store.get(request_id).state, self.storemod.JobState.APPLIED)
        self.assertEqual(source.modifiers[0].type, "ARMATURE")
        self.assertEqual((len(self.calls), len(self.paid)), before)

    def test_rig_receipt_retry_does_not_attach_another_armature(self):
        request_id, source = self.captured_rig_result()
        approval = self.prepare_mesh_edit(request_id, purpose="mesh_source", mesh_policy="RIG")
        deferred = self.tools.apply_result_application(self.import_args(approval))
        result = deferred.run()
        owner = self.runtime.state.model_jobs
        transition = owner.store.transition

        def fail(*args, **kwargs):
            if kwargs.get("state") == self.storemod.JobState.APPLIED:
                raise OSError("synthetic rig receipt persistence failure")
            return transition(*args, **kwargs)

        with patch.object(owner.store, "transition", side_effect=fail):
            status = deferred.finish(result)
        self.assertEqual(status["status"], "applying", status)
        rig = source.modifiers[0].object
        before = len(self.calls), len(self.paid), set(bpy.data.armatures)
        with patch.object(
            submodule("blender.mesh_result_application"),
            "apply_saved_mesh",
            side_effect=AssertionError("Repeated rig application"),
        ):
            status = self.tools.recover_local_job(self.recovery_args(request_id, "retry_receipt"))
        self.assertEqual(status["status"], "applied", status)
        self.assertEqual(source.modifiers[0].object, rig)
        self.assertEqual((len(self.calls), len(self.paid), set(bpy.data.armatures)), before)

    def test_captured_parts_apply_preserves_other_selection_and_records_no_new_spending(self):
        from helpers import parts_glb

        request_id, source = self.captured_source_result(parts_glb())
        original = source.data
        bpy.ops.mesh.primitive_cube_add(location=(9, 0, 0))
        other = bpy.context.object
        other_mesh = other.data
        calls = len(self.calls), len(self.paid), len(self.downloads)
        approval = self.prepare_mesh_edit(request_id, purpose="mesh_source", mesh_policy="PARTS")
        self.assertEqual(approval["target"], source.name)
        self.assertEqual(approval["mesh_policy"], "PARTS")
        status = self.finish_application(approval)
        self.assertEqual(status["status"], "applied", status)
        self.assertEqual(len(source.data.vertices), 0)
        self.assertEqual(len(status["mesh_edit"]["parts"]), 2)
        self.assertTrue(
            all(bpy.data.objects[name].parent == source for name in status["mesh_edit"]["parts"])
        )
        self.assertEqual(bpy.data.objects[status["mesh_edit"]["original"]].data, original)
        self.assertEqual(bpy.context.object, other)
        self.assertEqual(other.data, other_mesh)
        self.assertEqual((len(self.calls), len(self.paid), len(self.downloads)), calls)
        with self.assertRaises(self.request_error):
            self.tools.apply_result_application(self.import_args(approval))

    def test_captured_source_review_ignores_selection_and_preserves_original(self):
        request_id, source = self.captured_source_result()
        previous = source.data
        bpy.ops.mesh.primitive_cube_add(location=(9, 0, 0))
        other = bpy.context.object
        other_data = other.data
        before = len(self.calls), len(self.paid), len(self.downloads)
        approval = self.prepare_mesh_edit(request_id, purpose="mesh_source")
        self.assertEqual(approval["target"], source.name)
        self.assertIn(
            "apply_mesh_source", self.runtime.state.model_jobs.actions(self.store.get(request_id))
        )
        status = self.finish_application(approval)
        self.assertEqual(status["status"], "applied", status)
        self.assertEqual(len(source.data.vertices), 3)
        self.assertEqual(other.data, other_data)
        self.assertEqual(bpy.context.object, other)
        original = bpy.data.objects[status["mesh_edit"]["original"]]
        self.assertEqual(len(original.data.vertices), len(previous.vertices))
        self.assertEqual((len(self.calls), len(self.paid), len(self.downloads)), before)
        with self.assertRaises(submodule("blender.mesh_application").MeshApplicationError):
            self.prepare_mesh_edit(request_id, purpose="mesh_source")

    def test_captured_source_rejects_geometry_edit_before_review(self):
        request_id, source = self.captured_source_result()
        before = self.store.get(request_id)
        source.data.vertices[0].co.x += 1
        with self.assertRaises(submodule("blender.mesh_application").MeshApplicationError):
            self.prepare_mesh_edit(request_id, purpose="mesh_source")
        self.assertEqual(self.store.get(request_id), before)

    def test_captured_source_rejects_deleted_object_with_same_name(self):
        request_id, source = self.captured_source_result()
        name = source.name
        bpy.data.objects.remove(source, do_unlink=True)
        bpy.ops.mesh.primitive_cube_add()
        bpy.context.object.name = name
        with self.assertRaises(submodule("blender.mesh_application").MeshApplicationError):
            self.prepare_mesh_edit(request_id, purpose="mesh_source")
        self.assertEqual(self.store.get(request_id).state, self.storemod.JobState.READY)

    def test_captured_source_rejects_history_reset_and_restart_but_allows_manual_review(self):
        request_id, source = self.captured_source_result()
        session = self.runtime.state.model_jobs.session
        submodule("blender.job_session")._history_pre(None)
        self.assertEqual(session._mesh_sources, {})
        with self.assertRaises(self.origin_error):
            self.prepare_mesh_edit(request_id, purpose="mesh_source")
        self.runtime.state.reset()
        self.runtime.inspect_model_jobs()
        with self.assertRaises(self.origin_error):
            self.prepare_mesh_edit(request_id, purpose="mesh_source")
        approval = self.prepare_mesh_edit(request_id)
        self.assertEqual(approval["target"], source.name)
        self.assertEqual(self.store.get(request_id).state, self.storemod.JobState.READY)

    def test_captured_source_changed_during_verification_keeps_job_ready(self):
        request_id, source = self.captured_source_result()
        approval = self.prepare_mesh_edit(request_id, purpose="mesh_source")
        before, mesh = self.store.get(request_id), source.data
        deferred = self.tools.apply_result_application(self.import_args(approval))
        verified = deferred.run()
        source.location.x += 1
        status = deferred.finish(verified)
        self.assertEqual(self.store.get(request_id), before)
        self.assertEqual(source.data, mesh)
        self.assertEqual(status["status"], "ready", status)
        self.assertTrue(status["delivery_paused"])

    def test_metadata_without_live_export_cannot_authorize_original_source(self):
        self.configure_ui_lane("edit3d")
        self.captured_mesh_upload()
        self.ui_quote("edit3d")
        quote = next(iter(self.runtime.state.model_jobs.quotes.values()))
        binding = quote.task.result(5).mesh_sources[0]
        with self.assertRaises(self.origin_error):
            self.runtime.state.model_jobs.session.mesh_source_target(binding)

    def test_multiple_captured_inputs_cannot_guess_an_original_target(self):
        request_id, _ = self.captured_source_result()
        jobs = self.runtime.state.model_jobs
        record = self.store.get(request_id)
        binding = record.intent.mesh_sources[0]
        ambiguous = replace(
            record,
            intent=replace(
                record.intent, mesh_sources=(binding, replace(binding, parameter="another_mesh"))
            ),
        )
        with patch.object(jobs.store, "get", return_value=ambiguous):
            with self.assertRaises(self.request_error):
                self.prepare_mesh_edit(request_id, purpose="mesh_source")
        self.assertEqual(self.store.get(request_id), record)

    def test_modified_mesh_remains_uploadable_without_original_source_authority(self):
        self.configure_ui_lane("edit3d")
        bpy.context.object.modifiers.new("Keep modifier", "BEVEL")
        upload = self.captured_mesh_upload(live=True)
        self.assertIsNotNone(upload.intent.mesh_source)
        self.assertEqual(self.runtime.ensure_job_session()._mesh_sources, {})

    def test_retired_credentials_cannot_retain_or_restore_source_authority(self):
        request_id, _ = self.captured_source_result()
        jobs = self.runtime.state.model_jobs
        binding = self.store.get(request_id).intent.mesh_sources[0]
        jobs.session.deactivate()
        self.assertEqual(jobs.session._mesh_sources, {})
        with self.assertRaises(self.origin_error):
            jobs.session.mesh_source_target(binding)

    def test_source_authority_requires_exact_export_metadata(self):
        request_id, _ = self.captured_source_result()
        jobs = self.runtime.state.model_jobs
        binding = self.store.get(request_id).intent.mesh_sources[0]
        forged = replace(binding, mesh_source=replace(binding.mesh_source, file_sha256="f" * 64))
        with self.assertRaises(self.origin_error):
            jobs.session.mesh_source_target(forged)
        self.assertIsNotNone(jobs.session.mesh_source_target(binding))

    def test_source_authority_rejects_edit_fingerprint_as_export_provenance(self):
        request_id, _ = self.captured_source_result()
        session = self.runtime.state.model_jobs.session
        binding = self.store.get(request_id).intent.mesh_sources[0]
        target = session.mesh_source_target(binding)
        item = binding.mesh_source.objects[0]
        self.assertNotEqual(item.geometry_sha256, target.geometry.hex())
        forged = replace(
            binding,
            mesh_source=replace(
                binding.mesh_source,
                objects=(replace(item, geometry_sha256=target.geometry.hex()),),
            ),
        )
        before = dict(session._mesh_sources)
        with self.assertRaises(self.origin_error):
            session.retain_mesh_source(forged.origin, forged.mesh_source, target)
        self.assertEqual(session._mesh_sources, before)
        with self.assertRaises(self.origin_error):
            session.mesh_source_target(forged)
        self.assertIs(session.mesh_source_target(binding), target)
