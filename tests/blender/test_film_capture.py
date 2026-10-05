# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Installed Film capture approval, shared worker ownership and upload byte binding."""

import hashlib
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import bpy
import test_session_uploads as upload_tests
from helpers import submodule


class _Choices(list):
    def add(self):
        item = SimpleNamespace()
        self.append(item)
        return item


class FilmCaptureTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixture = upload_tests.SessionUploadTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.addCleanup(fixture.tearDown)
        self.session, self.scene = fixture.session, fixture.scene
        self.runtime = submodule("blender.runtime")
        self.film = submodule("blender.film_jobs")
        self.builder = submodule("blender.film_scene")
        self.render = submodule("core.jobs.local_render")
        self.controls = submodule("blender.film_capture_controls")
        self.tools = submodule("mcp.tools_scenario")
        self.owner = self.session.film_capture
        before = self.builder._snapshot()
        self.addCleanup(lambda: self.builder._rollback(before))
        self.raw = {
            "title": "Capture fixture",
            "fps": 30,
            "tasks": [],
            "heroes": {},
            "shots": [
                {
                    "id": "shot",
                    "title": "First shot",
                    "duration": 4,
                    "scene": submodule("core.scene.film_scene_plan").local_plan("studio", "", 4),
                    "actors": [],
                }
            ],
        }
        self.film.load_recipe(self.scene, self.raw)
        self.production = self.scene.scenario_film.production_id
        self.shot = self.builder.build_shot(
            self.raw, production_id=self.production, shot_id="shot"
        ).scene
        bpy.context.view_layer.update()
        self.enterContext(patch.object(self.runtime, "state", self.runtime.RuntimeState()))
        self.runtime.state.job_session = self.session
        self.runtime.state.job_context_id = "fixture-context"
        self.runtime.state.catalog_credentials = ("fixture", "secret")
        self.enterContext(
            patch.object(self.runtime, "credentials", return_value=("fixture", "secret"))
        )
        self.enterContext(
            patch.object(self.runtime, "ensure_job_session", return_value=self.session)
        )
        self.enterContext(
            patch.object(
                self.runtime, "ensure_film_jobs", return_value=SimpleNamespace(session=self.session)
            )
        )
        self.enterContext(patch.object(self.runtime, "online", return_value=True))
        self.references = self.runtime.ensure_reference_uploads()
        fixture.remote["originalFileName"] = "capture.png"
        self.render_calls = []
        self.enterContext(patch.object(self.render, "render", side_effect=self.render_fixture))
        original = fixture.handler

        def respond(request):
            response = original(request)
            if request.url.path.endswith("/action"):
                fixture.remote.update(status="imported", entityId="captured-asset")
            return response

        fixture.handler = respond

    def tearDown(self):
        bpy.context.window.scene = self.scene
        self.session.shutdown()

    def render_fixture(self, spec, *, cancel):
        self.assertIsNot(threading.current_thread(), threading.main_thread())
        self.render_calls.append(spec)
        path = spec.directory / ("capture.png" if spec.kind == "STILL" else "capture.mp4")
        path.write_bytes(b"data")
        return self.render.RenderedMedia(
            path,
            hashlib.sha256(b"data").hexdigest(),
            4,
            "image/png" if spec.kind == "STILL" else "video/mp4",
            spec.frames,
            spec.fps,
            spec.width,
            spec.height,
        )

    def prepare(self, **options):
        choices = self.tools.film_capture_sources(
            {"production_id": self.production, "shot_id": "shot"}
        )
        return self.tools.prepare_film_capture(
            {
                "context_id": choices["context_id"],
                "production_id": self.production,
                "shot_id": "shot",
                "source_id": choices["choices"][0]["source_id"],
                "kind": "STILL",
                "width": 64,
                "height": 64,
                **options,
            }
        )["review_id"]

    def settle(self, identifier):
        review = self.owner._reviews[identifier]
        if review.task:
            try:
                review.task.result(5)
            except Exception:
                pass
        self.owner.poll()
        return self.owner.status(identifier)

    def captured(self):
        identifier = self.prepare()
        self.tools.render_film_capture({"review_id": identifier})
        self.assertEqual(self.settle(identifier)["phase"], "CAPTURED")
        return identifier

    def settle_upload(self, identifier):
        review = self.owner._reviews[identifier]
        for _ in range(12):
            ticket = review.upload
            if ticket.task:
                try:
                    ticket.task.result(5)
                except Exception:
                    pass
            ticket.next_poll = 0
            self.references.poll()
            self.owner.poll()
            if review.phase in {"UPLOADED", "UPLOAD_REVIEW"}:
                return self.owner.status(identifier)
        self.fail("Capture upload did not settle")

    def test_mcp_separates_preparation_render_and_upload_and_consumes_approvals(self):
        identifier = self.prepare()
        self.assertEqual(self.owner.status(identifier)["phase"], "READY")
        self.assertEqual(self.owner.status(identifier)["directory"], "")
        self.assertEqual(self.render_calls, [])
        self.assertEqual(self.fixture.calls, [])
        self.tools.render_film_capture({"review_id": identifier})
        status = self.settle(identifier)
        self.assertEqual(status["phase"], "CAPTURED")
        self.assertEqual((status["frames"], status["fps"]), (1, 30))
        self.assertEqual(self.fixture.calls, [])
        with self.assertRaises(ValueError):
            self.owner.approve(identifier)
        self.tools.upload_film_capture({"review_id": identifier})
        status = self.settle_upload(identifier)
        self.assertEqual(status["phase"], "UPLOADED", status)
        self.assertTrue(status["request_id"])
        with self.assertRaises(ValueError):
            self.owner.upload(identifier, self.references)
        self.assertEqual(len(self.render_calls), 1)
        self.assertEqual(sum(r.method == "POST" for r, _ in self.fixture.calls), 2)
        self.assertEqual(self.scene, bpy.context.scene)

    def test_tampered_capture_fails_staging_before_any_remote_request(self):
        identifier = self.captured()
        Path(self.owner.status(identifier)["path"]).write_bytes(b"evil")
        self.owner.upload(identifier, self.references)
        self.assertEqual(self.settle_upload(identifier)["phase"], "UPLOAD_REVIEW")
        self.assertEqual(self.fixture.calls, [])
        self.fixture.uploader.upload.assert_not_called()
        self.assertEqual(self.session.upload_recovery_plan(), ())

    def test_changed_recipe_or_shot_rejects_approval_before_snapshot(self):
        for which in ("recipe", "shot"):
            identifier = self.prepare()
            self.session.invalidate_scene(self.scene if which == "recipe" else self.shot)
            with self.assertRaises(ValueError):
                self.owner.approve(identifier)
            self.owner.discard(identifier)
        self.assertEqual(self.render_calls, [])

    def test_deleted_camera_replacement_never_redirects_approval(self):
        identifier = self.prepare()
        camera = self.shot.camera
        name = camera.name
        bpy.data.objects.remove(camera, do_unlink=True)
        replacement = bpy.data.objects.new(name, bpy.data.cameras.new("Replacement"))
        self.shot.collection.objects.link(replacement)
        self.shot.camera = replacement
        with self.assertRaises(ValueError):
            self.owner.approve(identifier)
        self.assertEqual(self.render_calls, [])

    def test_transient_other_scene_context_waits_without_misdelivery(self):
        other = bpy.data.scenes.new("Unrelated capture view")
        identifier = self.prepare()
        self.owner.approve(identifier)
        with bpy.context.temp_override(scene=other):
            status = self.settle(identifier)
        self.assertEqual(status["phase"], "WAITING", status)
        self.assertEqual(status["path"], "")
        self.owner.poll()
        self.assertEqual(self.owner.status(identifier)["phase"], "CAPTURED")
        self.assertEqual(self.fixture.calls, [])

    def test_edit_after_capture_blocks_upload(self):
        identifier = self.captured()
        self.session.invalidate_scene(self.shot)
        with self.assertRaises(ValueError):
            self.owner.upload(identifier, self.references)
        self.assertEqual(self.fixture.calls, [])

    def test_cancel_active_capture_reaps_shared_task_without_deleting_live_files(self):
        entered = threading.Event()

        def hold(spec, *, cancel):
            entered.set()
            self.assertTrue(cancel.wait(5))
            self.assertTrue((spec.directory / "snapshot.blend").exists())
            raise self.render.RenderCancelled("Fixture cancelled")

        with patch.object(self.render, "render", side_effect=hold):
            identifier = self.prepare()
            self.owner.approve(identifier)
            self.assertTrue(entered.wait(3))
            directory = Path(self.owner.status(identifier)["directory"])
            with self.assertRaises(ValueError):
                self.owner.discard(identifier)
            self.owner.cancel(identifier)
            self.assertEqual(self.settle(identifier)["phase"], "CANCELLED")
            self.assertTrue(directory.exists())
            self.owner.discard(identifier)
            self.assertFalse(directory.exists())

    def test_retirement_cancels_render_and_shutdown_cleans_owned_files(self):
        entered = threading.Event()

        def hold(spec, *, cancel):
            entered.set()
            self.assertTrue(cancel.wait(5))
            raise self.render.RenderCancelled("Fixture retired")

        with patch.object(self.render, "render", side_effect=hold):
            identifier = self.prepare()
            self.owner.approve(identifier)
            self.assertTrue(entered.wait(3))
            directory = Path(self.owner.status(identifier)["directory"])
            self.session.deactivate()
            self.session.shutdown()
            self.assertFalse(directory.exists())
            self.assertTrue(self.session._workers.stopped)
        self.assertEqual(self.fixture.calls, [])

    def test_queue_admission_failure_consumes_approval_and_keeps_local_cleanup(self):
        identifier = self.prepare()
        with patch.object(self.session, "render_local", side_effect=RuntimeError("Queue full")):
            status = self.owner.approve(identifier)
        self.assertEqual(status["phase"], "ERROR")
        directory = Path(status["directory"])
        self.assertTrue(directory.exists())
        with self.assertRaises(ValueError):
            self.owner.approve(identifier)
        self.owner.discard(identifier)
        self.assertFalse(directory.exists())

    def test_discard_keeps_staged_upload_and_unrelated_files(self):
        identifier = self.captured()
        self.owner.upload(identifier, self.references)
        self.assertEqual(self.settle_upload(identifier)["phase"], "UPLOADED")
        record = self.owner._reviews[identifier].upload.record
        directory = Path(self.owner.status(identifier)["directory"])
        sentinel = directory.parent / "capture-kept"
        sentinel.write_text("keep")
        self.addCleanup(lambda: sentinel.unlink(missing_ok=True))
        self.owner.discard(identifier)
        self.assertFalse(directory.exists())
        self.assertEqual(sentinel.read_text(), "keep")
        self.assertEqual(self.session.inspect_upload(record.intent.request_id), record)
        self.fixture.sources.verify(record.intent)

    def test_video_settings_use_exact_editorial_range_and_missing_tools_reject_before_snapshot(
        self,
    ):
        module = submodule("blender.film_capture")
        with patch.object(module, "media_tools", side_effect=RuntimeError("No tools")):
            with self.assertRaisesRegex(RuntimeError, "No tools"):
                self.prepare(kind="VIDEO")
        self.assertEqual(self.owner._reviews, {})
        with patch.object(module, "media_tools"):
            identifier = self.prepare(kind="VIDEO")
        status = self.owner.status(identifier)
        self.assertEqual((status["frames"], status["fps"]), (120, 30))
        self.assertEqual(status["directory"], "")

    def test_native_dialog_cancel_is_inert_and_confirmation_uses_shared_command(self):
        operator = SimpleNamespace(
            choices=_Choices(),
            choice_index=0,
            kind="STILL",
            width=64,
            height=64,
            color_type="MATERIAL",
            report=Mock(),
        )
        context = SimpleNamespace(
            scene=self.scene, view_layer=bpy.context.view_layer, window_manager=Mock()
        )
        context.window_manager.invoke_props_dialog.return_value = {"RUNNING_MODAL"}
        self.assertEqual(
            self.controls.SCENARIO_OT_capture_film_shot.invoke(operator, context, None),
            {"RUNNING_MODAL"},
        )
        self.assertEqual(self.owner._reviews, {})
        self.assertEqual(self.render_calls, [])
        self.assertEqual(
            self.controls.SCENARIO_OT_capture_film_shot.execute(operator, context), {"FINISHED"}
        )
        identifier = next(iter(self.owner._reviews))
        self.assertEqual(self.settle(identifier)["phase"], "CAPTURED")
        self.assertEqual(
            self.controls.SCENARIO_OT_capture_film_shot.execute(operator, context), {"CANCELLED"}
        )
        self.assertEqual(len(self.render_calls), 1)

    def test_panel_draw_never_starts_or_polls_work(self):
        self.prepare()
        panel = SimpleNamespace(layout=Mock())
        with patch.object(self.owner, "poll", side_effect=AssertionError("Drawing polled work")):
            self.controls.SCENARIO_PT_film_capture.draw(panel, SimpleNamespace(scene=self.scene))
        self.assertEqual(self.render_calls, [])

    def test_worker_cannot_prepare_capture_or_change_ui(self):
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=1) as worker:
            with self.assertRaisesRegex(RuntimeError, "main thread"):
                worker.submit(self.owner.inspect, self.scene, shot_id="shot").result()
        self.assertEqual(self.owner._sources, {})

    def test_explicit_foreign_recipe_project_rejects_capture_inspection(self):
        raw = dict(self.raw, project_id="another-project")
        self.film.load_recipe(self.scene, raw)
        with self.assertRaisesRegex(ValueError, "project"):
            self.owner.inspect(self.scene, shot_id="shot")
        self.assertEqual(self.owner._sources, {})
        self.assertEqual(self.render_calls, [])

    def test_offline_upload_admission_retains_capture_without_remote_work(self):
        identifier = self.captured()
        with patch.object(self.references, "_online", return_value=False):
            with self.assertRaises(submodule("blender.reference_uploads").UploadNotStarted):
                self.owner.upload(identifier, self.references)
        self.assertEqual(self.owner.status(identifier)["phase"], "CAPTURED")
        self.assertEqual(self.fixture.calls, [])
        self.assertEqual(self.references.references, {})

    def test_uncertain_upload_is_saved_once_and_not_restarted_by_capture_status(self):
        import httpx

        identifier = self.captured()

        def timeout(request):
            self.fixture.calls.append((request, threading.current_thread()))
            raise httpx.ReadTimeout("Fixture lost response", request=request)

        self.fixture.handler = timeout
        self.owner.upload(identifier, self.references)
        self.assertEqual(self.settle_upload(identifier)["phase"], "UPLOAD_REVIEW")
        with self.assertRaises(ValueError):
            self.owner.upload(identifier, self.references)
        for _ in range(3):
            self.references.poll()
            self.owner.poll()
        self.assertEqual(len(self.fixture.calls), 1)
        records = self.session.upload_recovery_plan()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].record.state.value, "initialization_uncertain")
