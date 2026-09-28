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
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

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
                    return httpx.Response(
                        200,
                        json={
                            "job": {
                                "jobId": request.url.path.rsplit("/", 1)[-1],
                                "status": self.remote_status,
                                "jobType": "custom",
                                "metadata": {"assetIds": ["result-image"]},
                            }
                        },
                    )
                if "/assets/" in request.url.path:
                    return httpx.Response(
                        200,
                        json={
                            "asset": {
                                "id": "result-image",
                                "status": "success",
                                "mimeType": self.result_media_type,
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
        with self.assertRaises(self.request_error):
            self.prepare_import(request_id)
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
