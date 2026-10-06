# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Shared reference uploads through actual SDK/store/session with offline transport."""

import json
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

    def test_recovery_completion_is_owned_by_pump_even_without_mcp_finish(self):
        self.start()
        self.settle()
        record = self.tools.list_reference_uploads({})["uploads"][0]
        args = {
            "context_id": "fixture-context",
            "request_id": record["request_id"],
            "expected_revision": record["revision"],
            "action": "cleanup",
        }
        deferred = self.tools.recover_reference_upload(args)
        command = self.owner._recovering[record["request_id"]]
        with self.assertRaises(submodule("core.api.errors").ScenarioError):
            self.tools.recover_reference_upload(args)
        deferred.run()
        # Model a disconnected caller: no delivery callback is required for cleanup.
        self.owner.poll()
        self.assertTrue(command.done)
        self.assertEqual(self.owner._recovering, {})
        self.assertFalse(any(task is command.task for task, _ in self.fixture.session._pending))
        self.assertEqual(self.fixture.source.read_bytes(), b"data")
        self.assertEqual(deferred.finish(None)["state"], "imported")

    def test_failed_recovery_releases_admission_and_preserves_error_for_inspection(self):
        self.start()
        self.settle()
        record = self.tools.list_reference_uploads({})["uploads"][0]
        with patch.object(self.fixture.sources, "discard", side_effect=OSError("private details")):
            command = self.owner.recover(record["request_id"], record["revision"], "cleanup")
            with self.assertRaises(self.fixture.commands.UploadError):
                command.task.result(5)
            self.owner.poll()
        self.assertEqual(self.owner._recovering, {})
        self.assertIn(record["request_id"], self.owner.recovery_errors)
        with self.assertRaises(submodule("core.api.errors").ScenarioError):
            self.owner.recovery_result(command)
        command = self.owner.recover(record["request_id"], record["revision"], "cleanup")
        command.task.result(5)
        self.owner.poll()
        self.assertIsNone(command.error)
        self.assertEqual(self.fixture.source.read_bytes(), b"data")

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
                self.module,
                "bpy",
                SimpleNamespace(context=bpy.context, app=SimpleNamespace(background=False)),
            ),
            patch.object(capture, "capture_still", side_effect=RuntimeError("fixture")),
        ):
            with self.assertRaises(self.module.UploadNotStarted):
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
                    with self.assertRaises(self.module.UploadNotStarted):
                        self.module.capture_upload(bpy.context, source="RENDER")
                    self.assertEqual(set(self.fixture.root.iterdir()), before)
                else:
                    ticket = self.module.capture_upload(bpy.context, source="RENDER")
                    ticket.task.result(5)
                    self.settle()
                    self.assertEqual(ticket.record.state.value, "imported")
            self.assertEqual(settings.file_format, "OPEN_EXR")
            self.assertEqual(settings.color_depth, "32")

    def test_mesh_capture_stages_real_glb_and_restores_selection(self):
        bpy.ops.mesh.primitive_cube_add()
        cube = bpy.context.active_object
        self.addCleanup(lambda: bpy.data.objects.remove(cube, do_unlink=True))
        before = set(self.fixture.root.glob("reference-*"))
        with (
            patch.object(self.fixture.sources, "_max_bytes", 1024 * 1024),
            patch.object(self.fixture.sources, "_part_bytes", 1024 * 1024),
        ):
            result = self.tools.capture_reference({"source": "MESH"})
            ticket = self.owner.references[result["reference_id"]]
            record = ticket.task.result(5)
        self.assertEqual(record.intent.kind, "3d")
        self.assertEqual(record.intent.content_type, "model/gltf-binary")
        provenance = record.intent.mesh_source
        self.assertIsNotNone(provenance)
        self.assertEqual(provenance.file_sha256, record.intent.file_sha256)
        self.assertEqual(len(provenance.objects), 1)
        self.assertEqual(provenance.objects[0].target_id, record.intent.origin.target_id)
        self.assertEqual(
            provenance.objects[0].matrix_world, tuple(tuple(row) for row in cube.matrix_world)
        )
        staged = list((self.fixture.root / "sources").glob("*/source.bin"))
        self.assertEqual(staged[0].read_bytes()[:4], b"glTF")
        self.assertEqual(bpy.context.selected_objects, [cube])
        self.assertEqual(bpy.context.active_object, cube)
        self.fixture.session.drain(task=ticket.task)
        self.assertEqual(set(self.fixture.root.glob("reference-*")), before)
        self.assertEqual(self.fixture.calls, [])

    def test_clip_capture_uses_preview_range_and_restores_scene(self):
        capture = submodule("blender.capture")
        scene = self.fixture.scene
        scene.frame_start, scene.frame_end = 1, 100
        scene.use_preview_range = True
        scene.frame_preview_start, scene.frame_preview_end = 8, 12
        scene.frame_set(4)
        original = capture.capture_playblast
        camera_data = bpy.data.cameras.new("Reference camera")
        camera = bpy.data.objects.new("Reference camera", camera_data)
        scene.collection.objects.link(camera)
        scene.camera = camera
        self.addCleanup(lambda: bpy.data.cameras.remove(camera_data))
        self.addCleanup(lambda: bpy.data.objects.remove(camera, do_unlink=True))
        for source in ("VIEWPORT_CLIP", "CAMERA_CLIP"):
            for fail in (False, True):
                with self.subTest(source=source, fail=fail):
                    before = capture.RenderSettings.snapshot(scene)
                    directories = set(self.fixture.root.glob("reference-*"))
                    self.typed_source("video", ".mp4", "video/mp4")
                    self.fixture.remote.update(originalFileName="reference.mp4")

                    def runner(mode, context, current, fail=fail):
                        self.assertEqual(mode, "animation")
                        self.assertEqual((current.frame_start, current.frame_end), (8, 12))
                        self.assertEqual(current.render.ffmpeg.audio_codec, "NONE")
                        current.frame_set(12)
                        if fail:
                            raise RuntimeError("private capture failure")
                        Path(current.render.filepath).write_bytes(b"data")

                    def playblast(*args, **kwargs):
                        return original(*args, **kwargs, runner=runner)

                    with (
                        patch.object(
                            self.module,
                            "bpy",
                            SimpleNamespace(
                                context=bpy.context, app=SimpleNamespace(background=False)
                            ),
                        ),
                        patch.object(capture, "capture_playblast", side_effect=playblast),
                    ):
                        if fail:
                            with self.assertRaises(self.module.UploadNotStarted):
                                self.tools.capture_reference({"source": source})
                        else:
                            result = self.tools.capture_reference({"source": source})
                            self.settle()
                            status = self.tools.reference_upload_status(result)
                            self.assertEqual(status["state"], "imported", status)
                    self.assertEqual(capture.RenderSettings.snapshot(scene), before)
                    self.assertEqual(set(self.fixture.root.glob("reference-*")), directories)

    def test_capture_preconditions_do_not_send_or_leave_temporary_files(self):
        for source in ("MESH", "VIEWPORT_CLIP", "CAMERA_CLIP"):
            with self.subTest(source=source):
                before = set(self.fixture.root.iterdir())
                with self.assertRaises(self.module.UploadNotStarted):
                    self.tools.capture_reference({"source": source})
                self.assertEqual(set(self.fixture.root.iterdir()), before)
        self.assertEqual(self.fixture.calls, [])

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

    def typed_source(self, kind, suffix, content_type):
        path = self.fixture.root / f"media-{len(self.owner.references)}{suffix}"
        path.write_bytes(b"data")
        self.fixture.remote.update(
            id=f"upload-{len(self.owner.references)}",
            kind=kind,
            fileName=f"uploads/synthetic-storage/{path.name}",
            originalFileName=path.name,
            contentType=content_type,
            status="pending",
        )
        return path

    def test_typed_media_uploads_preserve_sdk_metadata_and_transfer_bytes_once(self):
        cases = (
            ("audio", ".mp3", "audio/mpeg"),
            ("audio", ".wav", "audio/wav"),
            ("audio", ".ogg", "audio/ogg"),
            ("audio", ".m4a", "audio/m4a"),
            ("video", ".MP4", "video/mp4"),
            ("video", ".webm", "video/webm"),
            ("3d", ".glb", "model/gltf-binary"),
            ("3d", ".gltf", "model/gltf+json"),
            ("3d", ".obj", "model/obj"),
            ("3d", ".fbx", "application/vnd.autodesk.fbx"),
            ("3d", ".stl", "model/stl"),
            ("3d", ".ply", "model/ply"),
            ("3d", ".vox", "model/x-3d-vox"),
        )
        for index, (kind, suffix, content_type) in enumerate(cases, 1):
            with self.subTest(kind=kind, suffix=suffix):
                path = self.typed_source(kind, suffix, content_type)
                result = self.tools.upload_reference({"path": str(path), "kind": kind})
                self.settle()
                status = self.tools.reference_upload_status(result)
                self.assertEqual(status["state"], "imported", status)
                self.assertEqual((status["kind"], status["content_type"]), (kind, content_type))
                self.assertEqual(self.fixture.uploader.upload.call_count, index)
                self.assertEqual(
                    self.fixture.uploader.upload.call_args.kwargs["content_type"], content_type
                )
                posts = [r for r, _ in self.fixture.calls if r.method == "POST"]
                self.assertEqual(len(posts), index * 2)
                self.assertEqual(
                    json.loads(posts[-2].content),
                    {
                        "kind": kind,
                        "fileName": path.name,
                        "contentType": content_type,
                        "fileSize": 4,
                        "parts": 1,
                    },
                )
                self.assertEqual(json.loads(posts[-1].content), {"action": "complete"})
                self.assertEqual(posts[-2].url.params["projectId"], "project")
                self.assertEqual(path.read_bytes(), b"data")
        self.assertTrue(all("/uploads" in r.url.path for r, _ in self.fixture.calls))

    def test_invalid_kind_or_extension_rejects_before_staging_or_network(self):
        before = set(self.fixture.root.rglob("*"))
        for kind in (None, [], {}, 3, "", "asset", "model", "audio", "video", "3d"):
            with self.subTest(kind=kind), self.assertRaises(self.module.UploadNotStarted):
                self.tools.upload_reference({"path": str(self.fixture.source), "kind": kind})
        for name in ("clip.mp4", "sound.exe", "mesh.glb"):
            with self.subTest(name=name), self.assertRaises(self.module.UploadNotStarted):
                self.tools.upload_reference({"path": str(self.fixture.root / name)})
        self.assertEqual(self.owner.references, {})
        self.assertEqual(self.fixture.session.upload_recovery_plan(), ())
        self.assertEqual(set(self.fixture.root.rglob("*")), before)
        self.assertEqual(self.fixture.calls, [])

    def test_audio_snapshot_survives_source_edit_and_remains_typed(self):
        path = self.typed_source("audio", ".wav", "audio/wav")
        ticket = self.owner.start(self.fixture.scene, path, kind="audio")
        ticket.task.result(5)
        path.write_bytes(b"edited source")
        self.settle()
        self.fixture.uploader.upload.assert_called_once()
        self.assertEqual(self.fixture.uploader.upload.call_args.args[1], b"data")
        self.assertEqual(ticket.record.intent.kind, "audio")
        self.assertEqual(path.read_bytes(), b"edited source")

    def test_video_metadata_change_stops_before_storage_put(self):
        path = self.typed_source("video", ".mp4", "video/mp4")
        self.fixture.remote["kind"] = "image"
        result = self.tools.upload_reference({"path": str(path), "kind": "video"})
        self.settle()
        status = self.tools.reference_upload_status(result)
        self.assertIsNotNone(status["error"])
        self.assertEqual(status["kind"], "video")
        self.fixture.uploader.upload.assert_not_called()
        calls = len(self.fixture.calls)
        for _ in range(3):
            self.owner.poll()
        self.assertEqual(len(self.fixture.calls), calls)

    def test_mesh_initialization_uncertainty_never_replays(self):
        path = self.typed_source("3d", ".glb", "model/gltf-binary")
        calls = []

        def fail(request):
            calls.append(request)
            raise httpx.ReadTimeout("synthetic private receipt", request=request)

        self.fixture.handler = fail
        result = self.tools.upload_reference({"path": str(path), "kind": "3d"})
        self.settle()
        status = self.tools.reference_upload_status(result)
        self.assertEqual(status["state"], "initialization_uncertain")
        self.assertEqual(status["kind"], "3d")
        for _ in range(4):
            self.owner.poll()
        self.assertEqual(len(calls), 1)
        self.fixture.uploader.upload.assert_not_called()
        self.assertEqual(self.tools.list_reference_uploads({})["uploads"][0]["kind"], "3d")

    def test_media_restart_preserves_kind_and_cleanup_keeps_original(self):
        path = self.typed_source("video", ".webm", "video/webm")
        result = self.tools.upload_reference({"path": str(path), "kind": "video"})
        self.settle()
        saved = self.tools.list_reference_uploads({})
        count = len(self.fixture.calls)
        self.fixture.session.shutdown()
        replacement = self.fixture.new_session()
        self.addCleanup(replacement.shutdown)
        self.runtime.state.job_session = replacement
        self.runtime.state.reference_uploads = None
        self.runtime.state.job_context_id = "restarted-context"
        with patch.object(self.runtime, "ensure_job_session", return_value=replacement):
            with self.assertRaises(submodule("core.api.errors").ScenarioError):
                self.tools.reference_upload_status(result)
            reopened = self.tools.list_reference_uploads({})
            self.assertEqual(reopened["uploads"], saved["uploads"])
            record = reopened["uploads"][0]
            self.assertEqual((record["kind"], record["content_type"]), ("video", "video/webm"))
            deferred = self.tools.recover_reference_upload(
                {
                    "context_id": reopened["context_id"],
                    "request_id": record["request_id"],
                    "expected_revision": record["revision"],
                    "action": "cleanup",
                }
            )
            outcome = deferred.finish(deferred.run())
            self.assertEqual((outcome["kind"], outcome["content_type"]), ("video", "video/webm"))
        self.assertEqual(len(self.fixture.calls), count)
        self.assertEqual(path.read_bytes(), b"data")

    def test_mesh_export_source_changes_are_rejected_before_upload_staging(self):
        bpy.ops.mesh.primitive_cube_add()
        cube = bpy.context.active_object
        self.addCleanup(lambda: bpy.data.objects.remove(cube, do_unlink=True))
        mesh_export = submodule("blender.mesh_export")
        original = mesh_export.export_glb

        def changed_source(*args, **kwargs):
            result = original(*args, **kwargs)
            cube.data.vertices[0].co.x += 1
            return result

        with patch.object(mesh_export, "export_glb", side_effect=changed_source):
            with self.assertRaises(self.module.UploadNotStarted):
                self.tools.capture_reference({"source": "MESH"})
        self.assertEqual(self.owner.references, {})
        self.assertEqual(self.fixture.calls, [])
        self.assertEqual(list(self.fixture.root.glob("reference-*")), [])

    def test_multi_mesh_capture_preserves_all_source_identities_without_primary_guess(self):
        meshes = []
        for location in ((3, 2, 1), (9, 8, 7)):
            bpy.ops.mesh.primitive_cube_add(location=location)
            meshes.append(bpy.context.active_object)
            self.addCleanup(lambda obj=meshes[-1]: bpy.data.objects.remove(obj, do_unlink=True))
        for obj in meshes:
            obj.select_set(True)
        with (
            patch.object(self.fixture.sources, "_max_bytes", 1024 * 1024),
            patch.object(self.fixture.sources, "_part_bytes", 1024 * 1024),
        ):
            result = self.tools.capture_reference({"source": "MESH"})
            ticket = self.owner.references[result["reference_id"]]
            record = ticket.task.result(5)
        self.assertIsNone(record.intent.origin.target_id)
        self.assertEqual(len(record.intent.mesh_source.objects), 2)
        self.assertEqual(
            {
                tuple(row[3] for row in obj.matrix_world[:3])
                for obj in record.intent.mesh_source.objects
            },
            {(3, 2, 1), (9, 8, 7)},
        )
        self.assertEqual(set(bpy.context.selected_objects), set(meshes))
        self.assertEqual(self.fixture.calls, [])

    def test_dense_mesh_snapshot_is_not_subject_to_mesh_edit_component_limit(self):
        bpy.ops.mesh.primitive_grid_add(x_subdivisions=384, y_subdivisions=384)
        obj = bpy.context.active_object
        mesh = obj.data
        self.addCleanup(lambda: bpy.data.meshes.remove(mesh))
        self.addCleanup(lambda: bpy.data.objects.remove(obj, do_unlink=True))
        components = sum(
            len(items) for items in (mesh.vertices, mesh.edges, mesh.loops, mesh.polygons)
        )
        components += sum(len(attribute.data) for attribute in mesh.attributes)
        self.assertGreater(components, submodule("blender.mesh_application").MAX_COMPONENTS)
        with (
            patch.object(self.fixture.sources, "_max_bytes", 256 * 1024 * 1024),
            patch.object(self.fixture.sources, "_part_bytes", 8 * 1024 * 1024),
        ):
            result = self.tools.capture_reference({"source": "MESH"})
            record = self.owner.references[result["reference_id"]].task.result(10)
        self.assertEqual(record.intent.mesh_source.file_sha256, record.intent.file_sha256)
        self.assertEqual(
            record.intent.mesh_source.objects[0].target_id, record.intent.origin.target_id
        )
        self.assertEqual(record.state.value, "prepared")
        self.assertEqual(self.fixture.calls, [])

    def test_mesh_capture_accepts_string_quaternion_matrix_and_short_vector_attributes(self):
        bpy.ops.mesh.primitive_cube_add()
        obj = bpy.context.active_object
        self.addCleanup(lambda: bpy.data.objects.remove(obj, do_unlink=True))
        for kind in ("STRING", "QUATERNION", "FLOAT4X4", "INT16_2D"):
            obj.data.attributes.new("capture_" + kind, kind, "POINT")
        with (
            patch.object(self.fixture.sources, "_max_bytes", 1024 * 1024),
            patch.object(self.fixture.sources, "_part_bytes", 1024 * 1024),
        ):
            result = self.tools.capture_reference({"source": "MESH"})
            record = self.owner.references[result["reference_id"]].task.result(5)
        self.assertIsNotNone(record.intent.mesh_source)
        self.assertEqual(self.fixture.calls, [])

    def test_extended_attribute_mutation_during_export_rejects_upload_and_cleans_export(self):
        from mathutils import Matrix

        bpy.ops.mesh.primitive_cube_add()
        obj = bpy.context.active_object
        self.addCleanup(lambda: bpy.data.objects.remove(obj, do_unlink=True))
        exporter = submodule("blender.mesh_export")
        original = exporter.export_glb
        for kind, initial, changed in (
            ("STRING", b"original", b"changed"),
            ("QUATERNION", (1, 0, 0, 0), (0, 1, 0, 0)),
            ("FLOAT4X4", Matrix.Identity(4), Matrix.Translation((1, 2, 3))),
            ("INT16_2D", (0, 0), (1, 2)),
        ):
            with self.subTest(kind=kind):
                attribute = obj.data.attributes.new("capture_" + kind, kind, "POINT")
                attribute.data[0].value = initial

                def mutate(*args, attribute=attribute, changed=changed, **kwargs):
                    result = original(*args, **kwargs)
                    attribute.data[0].value = changed
                    return result

                with patch.object(exporter, "export_glb", side_effect=mutate):
                    with self.assertRaises(self.module.UploadNotStarted):
                        self.tools.capture_reference({"source": "MESH"})
                self.assertEqual(self.owner.references, {})
                self.assertEqual(self.fixture.calls, [])
                self.assertEqual(list(self.fixture.root.glob("reference-*")), [])

    def test_mesh_capture_budget_covers_whole_selection_before_hashing_or_export(self):
        capture = submodule("blender.mesh_export_fingerprint")
        exporter = submodule("blender.mesh_export")
        objects = []
        for _ in range(2):
            bpy.ops.mesh.primitive_cube_add()
            obj = bpy.context.active_object
            objects.append(obj)
            self.addCleanup(lambda obj=obj: bpy.data.objects.remove(obj, do_unlink=True))
        for obj in objects:
            obj.select_set(True)
        single_size = capture._plan(objects[0].data)[2]
        with (
            patch.object(capture, "MAX_SNAPSHOT_BYTES", single_size + 1),
            patch.object(capture, "_hash", wraps=capture._hash) as read,
            patch.object(exporter, "export_glb") as export,
        ):
            with self.assertRaisesRegex(self.module.UploadNotStarted, "select fewer or simpler"):
                self.tools.capture_reference({"source": "MESH"})
        read.assert_not_called()
        export.assert_not_called()
        self.assertEqual(self.owner.references, {})
        self.assertEqual(self.fixture.calls, [])
        self.assertEqual(list(self.fixture.root.glob("reference-*")), [])

    def test_shared_mesh_capture_hashes_each_datablock_once_per_pass(self):
        capture = submodule("blender.mesh_export_fingerprint")
        bpy.ops.mesh.primitive_cube_add()
        obj = bpy.context.active_object
        self.addCleanup(lambda: bpy.data.objects.remove(obj, do_unlink=True))
        with (
            patch.object(capture, "MAX_SNAPSHOT_BYTES", capture._plan(obj.data)[2]),
            patch.object(capture, "_hash", wraps=capture._hash) as read,
        ):
            first, second = capture.fingerprints((obj.data, obj.data))
        self.assertEqual(first, second)
        read.assert_called_once()

    def test_parented_mesh_export_roundtrip_uses_blender_world_coordinates(self):
        bpy.ops.mesh.primitive_cube_add(location=(1, 2, 3))
        cube = bpy.context.active_object
        parent = bpy.data.objects.new("Export parent", None)
        bpy.context.scene.collection.objects.link(parent)
        cube.parent = parent
        parent.location = (4, 5, 6)
        parent.rotation_euler.z = 0.5
        cube.scale = (2, 3, 4)
        self.addCleanup(lambda: bpy.data.objects.remove(parent, do_unlink=True))
        self.addCleanup(lambda: bpy.data.objects.remove(cube, do_unlink=True))
        bpy.context.view_layer.update()
        expected = {
            tuple(round(v, 4) for v in cube.matrix_world @ vertex.co)
            for vertex in cube.data.vertices
        }
        with (
            patch.object(self.fixture.sources, "_max_bytes", 1024 * 1024),
            patch.object(self.fixture.sources, "_part_bytes", 1024 * 1024),
        ):
            result = self.tools.capture_reference({"source": "MESH"})
            ticket = self.owner.references[result["reference_id"]]
            record = ticket.task.result(5)
        provenance = record.intent.mesh_source
        self.assertEqual(provenance.convention, "blender-world-gltf-y-up")
        path = self.fixture.root / "roundtrip.glb"
        path.write_bytes(next((self.fixture.root / "sources").glob("*/source.bin")).read_bytes())
        kinds = ("objects", "collections", "meshes", "materials", "images")
        before = {name: set(getattr(bpy.data, name)) for name in kinds}

        def clean_import():
            for name in kinds:
                values = getattr(bpy.data, name)
                for item in set(values) - before[name]:
                    values.remove(item, do_unlink=True)

        self.addCleanup(clean_import)
        bpy.ops.import_scene.gltf(filepath=str(path))
        bpy.context.view_layer.update()
        imported = set(bpy.data.objects) - before["objects"]
        actual = {
            tuple(round(v, 4) for v in obj.matrix_world @ vertex.co)
            for obj in imported
            if obj.type == "MESH"
            for vertex in obj.data.vertices
        }
        self.assertEqual(actual, expected)
        self.assertEqual(self.fixture.calls, [])
