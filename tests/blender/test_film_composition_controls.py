# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Installed composition controls share exact quotes, source checks and saved jobs."""

import copy
import json
import os
import threading
import unittest
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import bpy
import httpx
import test_film_finishing
from helpers import submodule


class FilmCompositionControlsTests(unittest.TestCase):
    def setUp(self):
        self.media = test_film_finishing.FilmMediaSessionTests()
        self.media.setUp()
        self.addCleanup(self.media.doCleanups)
        self.fixture = self.media.fixture
        self.session, self.scene = self.media.session, self.media.scene
        self.store = self.fixture.store
        self.film = submodule("blender.film_jobs")
        self.runtime = submodule("blender.runtime")
        self.tools = submodule("mcp.tools_scenario")
        self.ui = submodule("blender.film_composition_controls")
        self.film.load_recipe(self.scene, self.media.raw)
        self.scene.scenario_film.production_id = "production"
        self.models = submodule("blender.model_jobs").ModelJobs(self.session, self.store)
        self.owner = self.film.FilmJobs(self.models)
        self.commands = self.owner.compositions
        self.enterContext(patch.object(self.runtime, "state", self.runtime.RuntimeState()))
        self.runtime.state.film_jobs = self.owner
        self.runtime.state.model_jobs = self.models
        self.runtime.state.job_session = self.session
        self.runtime.state.job_context_id = "context"
        self.runtime.state.catalog_credentials = self.runtime.credentials()
        self.enterContext(patch.object(self.runtime, "ensure_film_jobs", return_value=self.owner))
        self.paid = []
        self.lose_response = False
        self.parameters = None

        def respond(request):
            self.assertIsNot(threading.current_thread(), threading.main_thread())
            self.fixture.calls.append((request, threading.current_thread()))
            self.assertEqual(request.url.params.get("projectId"), self.session.scope.project_id)
            if request.method == "GET":
                fields = [
                    {
                        "name": name,
                        "type": "array"
                        if isinstance(value, list)
                        else "string"
                        if isinstance(value, str)
                        else "number",
                        "required": True,
                    }
                    for name, value in self.parameters.items()
                ]
                return httpx.Response(
                    200,
                    json={
                        "model": {
                            "id": "model_scenario-compose-video",
                            "type": "custom",
                            "inputs": fields,
                        }
                    },
                )
            self.assertEqual(json.loads(request.content)["layers"][0]["source"], "picture")
            if request.url.params.get("dryRun") == "true":
                return httpx.Response(269, content=b'{"creativeUnitsCost":0.10000000000000001}')
            self.assertEqual(json.loads(request.content), self.parameters)
            row = self.store.film_job("production", "final-master")
            self.assertEqual(row.state, self.fixture.jobs.JobState.SUBMITTING)
            self.paid.append(request)
            if self.lose_response:
                raise httpx.ReadTimeout("private synthetic failure", request=request)
            return httpx.Response(200, json={"job": {"jobId": "master"}})

        self.fixture.handler = respond

    def prepare(self, *, native=False):
        if native:
            self.assertEqual(bpy.ops.scenario.prepare_film_composition(), {"FINISHED"})
            status = self.commands.current(self.scene, "final")
        else:
            inspected = self.tools.film_recipe({})
            status = self.tools.prepare_film_composition(
                {"context_id": inspected["context_id"], "production_id": inspected["production_id"]}
            )
        self.assertEqual(status["phase"], "PREPARING")
        self.identifier = status["review_id"]
        return self.commands._get(self.identifier)

    def ready(self, *, native=False):
        review = self.prepare(native=native)
        review.task.result(5)
        status = self.status()
        self.assertEqual(status["phase"], "READY", status)
        self.parameters = status["parameters"]
        return review

    def quoted(self, *, native=False):
        review = self.ready(native=native)
        if native:
            self.assertEqual(
                bpy.ops.scenario.estimate_film_composition(review_id=self.identifier), {"FINISHED"}
            )
            review.task.result(5)
            status = self.status()
        else:
            task = self.tools.estimate_film_composition({"review_id": self.identifier})
            status = task.finish(task.run())
        self.assertEqual(status["phase"], "QUOTED", status)
        self.assertEqual(status["cu_cost_exact"], "0.10000000000000001")
        self.parameters = status["parameters"]
        return review

    def status(self, action="status"):
        return self.tools.film_composition_review({"review_id": self.identifier, "action": action})

    def approve(self):
        return self.tools.generate_film_composition(
            {"review_id": self.identifier, "approved_cost": "0.10000000000000001"}
        )

    def settle(self):
        for task in self.models.submissions.values():
            try:
                task.result(5)
            except Exception:
                pass  # Assertions inspect the persisted outcome, including uncertainty.
        for task in self.models.submissions.values():
            self.session.drain(task=task)

    def test_native_preparation_and_price_mcp_approval_preserve_recipe_and_scene(self):
        before = (self.film.snapshot(self.scene), tuple(bpy.data.scenes), tuple(bpy.data.objects))
        self.quoted(native=True)
        self.assertFalse(self.paid)
        result = self.approve()
        self.settle()
        row = self.store.get(result["request_id"])
        self.assertEqual(row.state, self.fixture.jobs.JobState.REMOTE)
        self.assertEqual(row.intent.film_task.task_id, "final-master")
        self.assertEqual(len(self.paid), 1)
        self.assertEqual(
            before,
            (self.film.snapshot(self.scene), tuple(bpy.data.scenes), tuple(bpy.data.objects)),
        )
        self.assertFalse(self.models._automatic_application)
        with self.assertRaisesRegex(ValueError, "fresh composition"):
            self.approve()
        self.assertEqual(len(self.paid), 1)

    def test_mcp_preparation_native_confirmation_and_cancel_share_exact_approval(self):
        self.quoted()
        operator = self.ui.SCENARIO_OT_generate_film_composition
        fake = SimpleNamespace(review_id=self.identifier, layout=MagicMock(), report=MagicMock())
        wm = MagicMock()
        wm.invoke_props_dialog.return_value = {"RUNNING_MODAL"}
        context = SimpleNamespace(window_manager=wm)
        self.assertEqual(operator.invoke(fake, context, None), {"RUNNING_MODAL"})
        operator.draw(fake, context)
        self.assertFalse(self.paid)  # Dismissing the dialog runs no execute.
        self.assertEqual(fake._cost, "0.10000000000000001")
        self.assertEqual(operator.execute(fake, bpy.context), {"FINISHED"})
        self.settle()
        self.assertEqual(len(self.paid), 1)
        self.assertEqual(operator.execute(fake, bpy.context), {"CANCELLED"})

    def test_master_saved_identity_visible_after_review_discard_and_owner_restart(self):
        self.quoted()
        result = self.approve()
        self.settle()
        self.status("discard")
        reopened = self.film.FilmJobs(
            submodule("blender.model_jobs").ModelJobs(self.session, self.store)
        )
        rows = reopened.inspect(self.scene)["tasks"]
        masters = [row for row in rows if row["task_id"] == "final-master"]
        self.assertEqual(len(masters), 1)
        self.assertEqual(masters[0]["request_id"], result["request_id"])
        self.assertEqual(masters[0]["cu_cost_exact"], "0.10000000000000001")
        self.scene.scenario_film.production_id = "different"
        self.assertFalse(
            any(row["task_id"] == "final-master" for row in reopened.inspect(self.scene)["tasks"])
        )
        self.assertEqual(len(self.paid), 1)

    def test_uncertain_submission_is_saved_and_approval_cannot_repeat(self):
        self.quoted()
        self.lose_response = True
        result = self.approve()
        self.settle()
        self.assertEqual(
            self.store.get(result["request_id"]).state, self.fixture.jobs.JobState.UNCERTAIN
        )
        with self.assertRaises(ValueError):
            self.approve()
        self.assertEqual(len(self.paid), 1)
        self.assertEqual(self.owner.inspect(self.scene)["tasks"][-1]["state"], "uncertain")

    def test_lost_preparation_ack_preserves_saved_id_without_submitting(self):
        self.quoted()
        original = self.store.create

        def lose_ack(*args, **kwargs):
            original(*args, **kwargs)
            raise OSError("private acknowledgement lost")

        with patch.object(self.store, "create", side_effect=lose_ack):
            with self.assertRaises(OSError):
                self.approve()
        status = self.status()
        self.assertEqual(status["phase"], "SUBMISSION_REVIEW")
        self.assertTrue(status["request_id"])
        self.assertEqual(
            self.store.get(status["request_id"]).state, self.fixture.jobs.JobState.PREPARED
        )
        with self.assertRaises(ValueError):
            self.approve()
        self.assertFalse(self.paid)

    def test_wrong_exact_price_offline_and_gui_probe_do_not_consume_quote(self):
        review = self.quoted()
        with self.assertRaisesRegex(ValueError, "exact"):
            self.commands.approve(self.identifier, approved_cost="0.1")
        with patch.object(self.owner, "_online", return_value=False):
            with self.assertRaises(ValueError):
                self.approve()
        with patch.dict(os.environ, {"SCENARIO_GUI_PROBE": "1"}):
            with self.assertRaises(PermissionError):
                self.approve()
        self.assertEqual(review.phase, "QUOTED")
        self.assertFalse(self.store.records())
        self.assertFalse(self.paid)

    def test_recipe_change_then_revert_cannot_restore_observed_old_approval(self):
        review = self.quoted()
        changed = copy.deepcopy(self.media.raw)
        changed["title"] = "Changed recipe"
        self.film.load_recipe(self.scene, changed)
        self.owner.poll()
        self.assertEqual(review.phase, "ERROR")
        self.film.load_recipe(self.scene, self.media.raw)
        with self.assertRaises(ValueError):
            self.approve()
        self.assertFalse(self.paid)

    def test_foreground_scene_change_waits_without_losing_preparation(self):
        review = self.prepare()
        review.task.result(5)
        other = bpy.data.scenes.new("Other composition context")
        try:
            with bpy.context.temp_override(scene=other):
                self.owner.poll()
                self.assertEqual(review.phase, "WAITING")
            self.owner.poll()
            self.assertEqual(review.phase, "READY", review.error)
        finally:
            bpy.data.scenes.remove(other)
        self.assertFalse(self.fixture.calls)

    def test_deleted_pending_scene_drains_without_rebinding_same_name(self):
        review = self.prepare()
        review.task.result(5)
        name = self.scene.name
        bpy.context.window.scene = self.fixture.previous
        bpy.data.scenes.remove(self.scene)
        replacement = bpy.data.scenes.new(name)
        try:
            self.owner.poll()
            self.assertEqual(review.phase, "ERROR")
            self.assertIsNone(review.task)
            self.assertIsNone(self.commands.current(replacement, "final"))
        finally:
            bpy.data.scenes.remove(replacement)
        self.assertFalse(self.fixture.calls)

    def test_cancel_completed_probe_before_delivery_and_discard_preserve_sources(self):
        before = self.fixture.upload_store.records()
        review = self.prepare()
        review.task.result(5)
        self.commands.cancel(self.identifier)
        self.owner.poll()
        self.assertEqual(review.phase, "CANCELLED")
        self.status("discard")
        self.assertEqual(before, self.fixture.upload_store.records())
        self.assertFalse(self.fixture.calls)
        self.assertIsNone(self.commands.current(self.scene, "final"))

    def test_cancel_completed_price_never_exposes_approval(self):
        review = self.ready()
        self.commands.estimate(self.identifier)
        review.task.result(5)
        self.commands.cancel(self.identifier)
        self.owner.poll()
        self.assertEqual(review.phase, "CANCELLED")
        self.assertIsNone(review.quote)
        with self.assertRaises(ValueError):
            self.approve()
        self.assertFalse(self.paid)

    def test_changed_media_after_price_cannot_spend_or_restore_review(self):
        review = self.quoted()
        row = self.fixture.upload_store.get("picture")
        with patch.object(
            self.fixture.upload_store, "get", return_value=replace(row, revision=row.revision + 1)
        ):
            with self.assertRaises(ValueError):
                self.approve()
        self.assertEqual(review.phase, "SUBMISSION_REVIEW")
        self.assertFalse(self.paid)
        self.assertFalse(self.store.records())

    def test_draw_and_returned_payload_do_not_mutate_or_activate_any_owner(self):
        review = self.quoted()
        original = copy.deepcopy(review.parameters)
        result = self.status()
        result["parameters"]["layers"].clear()
        self.assertEqual(review.parameters, original)
        before = self.film.snapshot(self.scene)
        with (
            patch.object(
                self.runtime, "ensure_film_jobs", side_effect=AssertionError("draw starts no work")
            ),
            patch.object(
                self.store, "film_job", side_effect=AssertionError("draw reads no storage")
            ),
            patch.object(self.commands, "poll", side_effect=AssertionError("draw polls no work")),
        ):
            self.ui.SCENARIO_PT_film_composition.draw(
                SimpleNamespace(layout=MagicMock()), bpy.context
            )
        self.assertEqual(before, self.film.snapshot(self.scene))
        self.assertFalse(self.paid)

    def test_stale_context_and_retired_session_reject_commands(self):
        with self.assertRaisesRegex(ValueError, "connection"):
            self.tools.prepare_film_composition(
                {"context_id": "old", "production_id": "production"}
            )
        self.quoted()
        self.session.shutdown()
        with self.assertRaises(ValueError):
            self.approve()
        self.assertFalse(self.paid)

    def test_missing_probe_exposes_safe_error_and_allows_fresh_preparation(self):
        with patch.object(
            self.media.media,
            "probe_tool",
            side_effect=self.media.probe.MediaProbeError("Install ffprobe"),
        ):
            review = self.prepare()
            with self.assertRaises(self.media.probe.MediaProbeError):
                review.task.result(5)
            status = self.status()
        self.assertEqual(status["phase"], "ERROR")
        self.assertEqual(status["error"], "Install ffprobe")
        self.ready()
        self.assertFalse(self.fixture.calls)

    def test_idle_updates_and_mode_navigation_preserve_price_but_frame_changes_invalidate(self):
        review = self.quoted()
        calls = len(self.fixture.calls)
        for mode in ("previs", "final", "previs", "final"):
            self.scene.scenario_film.composition_mode = mode
            bpy.context.view_layer.update()
            self.owner.poll()
            self.assertEqual(review.phase, "QUOTED", review.error)
        self.assertEqual(len(self.fixture.calls), calls)
        self.scene.frame_set(self.scene.frame_current + 1)
        self.owner.poll()
        self.assertEqual(review.phase, "ERROR")
        self.assertFalse(self.paid)
