# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Shared reference uploads through actual SDK/store/session with offline transport."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import bpy
import httpx
import test_session_uploads as fixture_module
from helpers import submodule


class ReferenceUploadTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixture = fixture_module.SessionUploadTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.addCleanup(fixture.tearDown)
        self.runtime = submodule("blender.runtime")
        self.tools = submodule("mcp.tools_scenario")
        self.module = submodule("blender.reference_uploads")
        self.enterContext(patch.object(self.runtime, "state", self.runtime.RuntimeState()))
        self.runtime.state.job_session = fixture.session
        self.runtime.state.job_context_id = "fixture-context"
        self.enterContext(
            patch.object(self.runtime, "ensure_job_session", return_value=fixture.session)
        )
        self.enterContext(patch.object(self.runtime, "online", return_value=True))
        self.enterContext(
            patch.object(
                self.runtime, "paths", return_value=SimpleNamespace(state_dir=fixture.root)
            )
        )
        self.enterContext(
            patch.object(
                self.runtime,
                "make_client",
                side_effect=AssertionError("Prototype upload client used"),
            )
        )
        self.owner = self.runtime.ensure_reference_uploads()
        original = fixture.handler

        def response(request):
            result = original(request)
            if request.url.path.endswith("/action"):
                fixture.remote.update(status="imported", entityId="reference-asset")
            return result

        fixture.handler = response

    def start(self):
        return self.tools.upload_reference({"path": str(self.fixture.source)})

    def settle(self):
        for _ in range(12):
            for ticket in self.owner.references.values():
                if ticket.task is not None:
                    try:
                        ticket.task.result(5)
                    except Exception:
                        # poll() records the completion error; tests assert the
                        # resulting ticket error and durable state below.
                        pass
                ticket.next_poll = 0
            self.owner.poll()
            if all(
                ticket.task is None and (ticket.error or ticket.record.state.value == "imported")
                for ticket in self.owner.references.values()
            ):
                return
        self.fail("Reference upload did not settle")

    def test_mcp_upload_uses_one_initialization_part_and_completion(self):
        result = self.start()
        self.settle()
        status = self.tools.reference_upload_status(result)
        self.assertEqual(status["state"], "imported", status)
        self.assertEqual(status["asset_id"], "reference-asset")
        self.assertEqual(self.owner.imported(result["reference_id"]), "reference-asset")
        calls = [request for request, _ in self.fixture.calls]
        self.assertEqual(sum(request.method == "POST" for request in calls), 2)
        self.fixture.uploader.upload.assert_called_once()
        self.assertTrue(all("/uploads" in request.url.path for request in calls))
        before = len(calls)
        for _ in range(4):
            self.tools.reference_upload_status(result)
        self.assertEqual(len(self.fixture.calls), before)
        self.assertEqual(self.fixture.source.read_bytes(), b"data")

    def test_source_edit_after_staging_does_not_change_transferred_snapshot(self):
        ticket = self.owner.start(self.fixture.scene, self.fixture.source)
        ticket.task.result(5)
        self.fixture.source.write_bytes(b"changed source")
        self.settle()
        self.fixture.uploader.upload.assert_called_once()
        self.assertEqual(self.fixture.uploader.upload.call_args.args[1], b"data")
        self.assertEqual(ticket.record.state.value, "imported")

    def test_origin_change_after_staging_stops_before_network(self):
        ticket = self.owner.start(self.fixture.scene, self.fixture.source)
        ticket.task.result(5)
        self.fixture.session.invalidate_scene(self.fixture.scene)
        self.owner.poll()
        self.assertIsNotNone(ticket.error)
        self.assertEqual(ticket.record.state.value, "prepared")
        self.assertEqual(self.fixture.calls, [])
        self.fixture.uploader.upload.assert_not_called()

    def test_lost_initialization_response_is_saved_and_never_replayed(self):
        calls = []

        def fail(request):
            calls.append(request)
            raise httpx.ReadTimeout("synthetic private detail", request=request)

        self.fixture.handler = fail
        result = self.start()
        self.settle()
        status = self.tools.reference_upload_status(result)
        self.assertEqual(status["state"], "initialization_uncertain", status)
        self.assertNotIn("private", status["error"])
        for _ in range(5):
            self.owner.poll()
        self.assertEqual(len(calls), 1)
        saved = self.tools.list_reference_uploads({})["uploads"]
        self.assertEqual(saved[0]["state"], "initialization_uncertain")
        self.fixture.uploader.upload.assert_not_called()

    def test_recovery_after_lost_completion_observes_asset_without_another_put(self):
        original = self.fixture.handler

        def fail(request):
            if request.url.path.endswith("/action"):
                self.fixture.remote.update(status="imported", entityId="reference-asset")
                raise httpx.ReadTimeout("synthetic completion loss", request=request)
            return original(request)

        self.fixture.handler = fail
        result = self.start()
        self.settle()
        saved = self.tools.list_reference_uploads({})
        record = saved["uploads"][0]
        self.assertEqual(record["state"], "finalization_uncertain")
        self.fixture.session.invalidate_all()
        deferred = self.tools.recover_reference_upload(
            {
                "context_id": saved["context_id"],
                "request_id": record["request_id"],
                "expected_revision": record["revision"],
                "action": "refresh",
            }
        )
        status = deferred.finish(deferred.run())
        self.assertEqual(status["state"], "imported")
        self.assertEqual(status["asset_id"], "reference-asset")
        status = self.tools.reference_upload_status(result)
        self.assertEqual(status["state"], "imported")
        self.assertIsNone(status["error"])
        self.fixture.uploader.upload.assert_called_once()

    def test_imported_reference_cannot_attach_after_scene_change(self):
        result = self.start()
        self.settle()
        self.fixture.session.invalidate_scene(self.fixture.scene)
        with self.assertRaises(self.fixture.module.OriginUnavailable):
            self.owner.imported(result["reference_id"])
        self.runtime.state.job_context_id = "replacement-context"
        with self.assertRaises(submodule("core.api.errors").ScenarioError):
            self.tools.reference_upload_status(result)

    def test_recovery_processing_resumes_only_status_reads(self):
        original = self.fixture.handler

        def fail(request):
            if request.url.path.endswith("/action"):
                self.fixture.remote["status"] = "validating"
                raise httpx.ReadTimeout("completion loss", request=request)
            return original(request)

        self.fixture.handler = fail
        result = self.start()
        self.settle()
        record = self.tools.list_reference_uploads({})["uploads"][0]
        self.assertEqual(record["state"], "finalization_uncertain")
        args = {
            "context_id": result["context_id"],
            "request_id": record["request_id"],
            "expected_revision": record["revision"],
            "action": "refresh",
        }
        deferred = self.tools.recover_reference_upload(args)
        self.assertEqual(deferred.finish(deferred.run())["state"], "processing")
        self.fixture.remote.update(status="imported", entityId="reference-asset")
        self.settle()
        self.assertEqual(self.tools.reference_upload_status(result)["state"], "imported")
        self.fixture.uploader.upload.assert_called_once()
        self.assertEqual(
            sum(request.method == "POST" for request, _ in self.fixture.calls), 1
        )  # The failed completion mock above does not delegate to the request recorder.

    def test_cancel_prepared_observes_new_state_before_automatic_admission(self):
        ticket = self.owner.start(self.fixture.scene, self.fixture.source)
        ticket.task.result(5)
        with patch.object(self.owner, "_online", return_value=False):
            self.owner.poll()
        record = ticket.record
        with patch.object(
            self.fixture.session, "initialize_upload", wraps=self.fixture.session.initialize_upload
        ) as initialize:
            result = self.tools.recover_reference_upload(
                {
                    "context_id": "fixture-context",
                    "request_id": record.intent.request_id,
                    "expected_revision": record.revision,
                    "action": "cancel_prepared",
                }
            )
            self.assertEqual(result["state"], "canceled")
            self.owner.poll()
            initialize.assert_not_called()
        self.assertEqual(ticket.record.state.value, "canceled")
        self.assertIsNone(ticket.task)
        self.assertEqual(self.fixture.calls, [])

    def test_admission_capacity_miss_is_retried_without_duplicate_requests(self):
        ticket = self.owner.start(self.fixture.scene, self.fixture.source)
        ticket.task.result(5)
        for error in (
            submodule("core.jobs.workers").WorkerError("queue full"),
            self.fixture.module.SessionBusy("drain outcomes"),
        ):
            ticket.retry_admission_at = 0
            with patch.object(self.fixture.session, "initialize_upload", side_effect=error):
                self.owner.poll()
            self.assertIsNone(ticket.task)
            self.assertIsNone(ticket.error)
            self.assertEqual(ticket.record.state.value, "prepared")
            self.assertEqual(self.fixture.calls, [])
        ticket.retry_admission_at = 0
        self.settle()
        self.assertEqual(ticket.record.state.value, "imported")
        self.assertEqual(sum(r.method == "POST" for r, _ in self.fixture.calls), 2)
        self.fixture.uploader.upload.assert_called_once()

    def test_temporary_capture_is_removed_after_staging_and_on_retirement(self):
        for retire in (False, True):
            directory = tempfile.TemporaryDirectory(dir=self.fixture.root)
            path = Path(directory.name) / "reference.png"
            path.write_bytes(b"data")
            ticket = self.owner.start(self.fixture.scene, path, temporary=directory)
            ticket.task.result(5)
            if retire:
                self.fixture.session.shutdown()
            else:
                self.fixture.session.drain(task=ticket.task)
            self.assertFalse(path.parent.exists())

    def test_capture_failure_removes_private_directory_without_network(self):
        capture = submodule("blender.capture")
        before = set(self.fixture.root.iterdir())
        with (
            patch.object(
                self.module, "bpy", SimpleNamespace(app=SimpleNamespace(background=False))
            ),
            patch.object(capture, "capture_still", side_effect=RuntimeError("fixture")),
        ):
            with self.assertRaises(RuntimeError):
                self.tools.capture_reference({"source": "VIEWPORT"})
        self.assertEqual(set(self.fixture.root.iterdir()), before)
        self.assertEqual(self.fixture.calls, [])

    def test_render_capture_uses_png_and_restores_format_after_success_or_failure(self):
        scene = self.fixture.scene
        settings = scene.render.image_settings
        for fail in (False, True):
            settings.file_format = "OPEN_EXR"
            settings.color_depth = "32"
            before = set(self.fixture.root.iterdir())

            def save(path, *, scene, fail=fail):
                self.assertEqual(scene.render.image_settings.file_format, "PNG")
                if fail:
                    raise RuntimeError("synthetic save failure")
                Path(path).write_bytes(b"data")

            image = SimpleNamespace(has_data=True, save_render=save)
            fake = SimpleNamespace(
                context=bpy.context, data=SimpleNamespace(images={"Render Result": image})
            )
            with patch.object(self.module, "bpy", fake):
                if fail:
                    with self.assertRaises(RuntimeError):
                        self.module.capture_upload(bpy.context, source="RENDER")
                    self.assertEqual(set(self.fixture.root.iterdir()), before)
                else:
                    ticket = self.module.capture_upload(bpy.context, source="RENDER")
                    ticket.task.result(5)
                    self.settle()
                    self.assertEqual(ticket.record.state.value, "imported")
            self.assertEqual(settings.file_format, "OPEN_EXR")
            self.assertEqual(settings.color_depth, "32")

    def test_restart_lists_saved_upload_without_resubmission_and_cleans_only_copy(self):
        self.start()
        self.settle()
        saved = self.tools.list_reference_uploads({})
        count = len(self.fixture.calls)
        self.fixture.session.shutdown()
        replacement = self.fixture.new_session()
        self.addCleanup(replacement.shutdown)
        self.runtime.state.job_session = replacement
        self.runtime.state.reference_uploads = None
        with patch.object(self.runtime, "ensure_job_session", return_value=replacement):
            reopened = self.tools.list_reference_uploads({})
            self.assertEqual(reopened, saved)
            self.assertEqual(len(self.fixture.calls), count)
            record = reopened["uploads"][0]
            deferred = self.tools.recover_reference_upload(
                {
                    "context_id": reopened["context_id"],
                    "request_id": record["request_id"],
                    "expected_revision": record["revision"],
                    "action": "cleanup",
                }
            )
            self.assertEqual(deferred.finish(deferred.run())["state"], "imported")
        self.assertEqual(self.fixture.source.read_bytes(), b"data")
        self.assertEqual(len(self.fixture.calls), count)
