# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Installed Film review controls share session handles, copies, claims and receipts."""

import json
import threading
import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, call, patch

import bpy
import test_film_review_preparation as preparation
from helpers import submodule


class FilmReviewControlTests(unittest.TestCase):
    def setUp(self):
        self.media = preparation.FilmReviewPreparationTests()
        self.media.setUp()
        # Cleanups run last-in first-out: tear the fixture down before its patches end.
        self.addCleanup(self.media.doCleanups)
        self.addCleanup(self.media.tearDown)
        media = self.media
        self.session, self.scene, self.store = media.session, media.scene, media.store
        self.storage, self.builder, self.probe = media.storage, media.builder, media.probe
        self.film, self.production = media.film, media.production
        bpy.context.window_manager.scenario_film_review_mode = "final"
        self.runtime = submodule("blender.runtime")
        self.tools = submodule("mcp.tools_scenario")
        self.ui = submodule("blender.film_review_controls")
        self.module = submodule("blender.film_review_commands")
        self.commands = self.session.film_review
        self.enterContext(patch.object(self.runtime, "state", self.runtime.RuntimeState()))
        self.runtime.state.job_session = self.session
        self.runtime.state.job_context_id = "fixture-context"
        self.runtime.state.catalog_credentials = ("fixture", "secret")
        self.enterContext(
            patch.object(self.runtime, "credentials", return_value=("fixture", "secret"))
        )
        self.owner = self.film.FilmJobs(SimpleNamespace(session=self.session, store=self.store))
        self.runtime.state.film_jobs = self.owner
        self.enterContext(patch.object(self.runtime, "ensure_film_jobs", return_value=self.owner))

    def copies(self):
        return sorted(self.media.review_root.glob("review-*"))

    def state(self):
        return self.store.get("picture").state

    def mcp_prepare(self, **options):
        status = self.tools.prepare_film_review(
            {"context_id": "fixture-context", "production_id": self.production, **options}
        )
        self.assertEqual(status["phase"], "PREPARING")
        return status["review_id"]

    def settle(self, identifier):
        task = self.commands._reviews[identifier].task
        if task is not None:
            try:
                task.result(5)
            except Exception:
                pass  # The review status records preparation failures.
        # Application-owned maintenance advances reviews without drawing a panel.
        self.runtime.sync_catalog_context()
        return self.tools.film_review_status({"review_id": identifier})

    def ready(self, **options):
        identifier = self.mcp_prepare(**options)
        status = self.settle(identifier)
        self.assertEqual(status["phase"], "READY", status["error"])
        return identifier

    def test_native_prepare_and_operator_build_create_one_scene_without_service_io(self):
        before = (set(bpy.data.scenes), self.film.snapshot(self.scene), self.scene.frame_current)
        self.assertEqual(bpy.ops.scenario.prepare_film_review(), {"FINISHED"})
        identifier = self.commands.current(self.scene, "final")["review_id"]
        status = self.settle(identifier)
        self.assertEqual(status["phase"], "READY", status["error"])
        self.assertEqual((status["frames"], status["fps"], status["shots"]), (48, 24, 1))
        self.assertEqual((status["sources"], status["master"]), (1, False))
        self.assertEqual(status["bytes"], len(self.media.data))
        self.assertEqual(len(self.copies()), 1)
        self.assertEqual(self.state(), self.storage.JobState.READY)
        self.assertEqual(bpy.ops.scenario.build_film_review(review_id=identifier), {"FINISHED"})
        status = self.tools.film_review_status({"review_id": identifier})
        self.assertEqual(status["phase"], "BUILT")
        created = set(bpy.data.scenes) - before[0]
        self.assertEqual(len(created), 1)
        (review,) = created
        self.assertEqual(status["review_scene"], review.name)
        self.assertEqual(review["scenario_sequence_kind"], "downloaded_final_review")
        self.assertEqual(len(review.sequence_editor.strips), 2)
        self.assertEqual(bpy.context.scene, self.scene)
        self.assertEqual(before[1:], (self.film.snapshot(self.scene), self.scene.frame_current))
        self.assertEqual(self.state(), self.storage.JobState.APPLIED)
        self.assertEqual(bpy.ops.scenario.build_film_review(review_id=identifier), {"CANCELLED"})
        self.assertEqual(set(bpy.data.scenes) - before[0], created)
        self.assertFalse(self.media.calls or self.media.downloads)

    def test_mcp_and_native_share_preparation_and_build_handles(self):
        identifier = self.ready()
        self.assertEqual(bpy.ops.scenario.build_film_review(review_id=identifier), {"FINISHED"})
        self.assertEqual(self.commands.status(identifier)["phase"], "BUILT")
        self.assertEqual(bpy.ops.scenario.prepare_film_review(), {"FINISHED"})
        second = self.commands.current(self.scene, "final")["review_id"]
        self.assertNotEqual(second, identifier)
        self.assertEqual(self.settle(second)["phase"], "READY")
        status = self.tools.build_film_review({"review_id": second})
        self.assertEqual(status["phase"], "BUILT")
        self.assertEqual(len(self.store.get("picture").local_applications), 1)
        with self.assertRaisesRegex(ValueError, "fresh ready"):
            self.tools.build_film_review({"review_id": second})
        self.assertFalse(self.media.calls or self.media.downloads)

    def test_dismissed_dialogs_create_no_review_claim_or_scene(self):
        operator = SimpleNamespace(report=Mock(), include_master=True, layout=MagicMock())
        context = SimpleNamespace(
            scene=self.scene, window_manager=Mock(scenario_film_review_mode="final")
        )
        context.window_manager.invoke_props_dialog.return_value = {"RUNNING_MODAL"}
        prepare = self.ui.SCENARIO_OT_prepare_film_review
        self.assertEqual(prepare.invoke(operator, context, None), {"RUNNING_MODAL"})
        prepare.draw(operator, context)
        self.assertFalse(operator._master or operator.include_master)
        self.assertEqual(self.commands._reviews, {})
        self.assertFalse(self.copies())
        identifier = self.ready()
        scenes = set(bpy.data.scenes)
        build = self.ui.SCENARIO_OT_build_film_review
        operator = SimpleNamespace(review_id=identifier, report=Mock(), layout=MagicMock())
        self.assertEqual(build.invoke(operator, context, None), {"RUNNING_MODAL"})
        build.draw(operator, context)
        labels = [c.kwargs["text"] for c in operator.layout.label.call_args_list]
        self.assertIn("Final review: 48 frames at 24 fps", labels)
        self.assertIn("Marks generated sources as applied in saved jobs.", labels)
        self.assertEqual(self.commands.status(identifier)["phase"], "READY")
        self.assertEqual(
            (set(bpy.data.scenes), self.state()), (scenes, self.storage.JobState.READY)
        )
        self.assertEqual(build.execute(operator, bpy.context), {"FINISHED"})
        self.assertEqual(self.commands.status(identifier)["phase"], "BUILT")
        self.assertFalse(self.media.calls or self.media.downloads)

    def test_cancel_during_probe_removes_copies_and_frees_the_local_slot(self):
        started, release = threading.Event(), threading.Event()
        measured = self.probe._run

        def blocked(command, **kwargs):
            started.set()
            release.wait(5)
            return measured(command, **kwargs)

        with patch.object(self.probe, "_run", side_effect=blocked):
            identifier = self.mcp_prepare()
            self.assertTrue(started.wait(5))
            with self.assertRaisesRegex(ValueError, "local media operation"):
                self.mcp_prepare(mode="previs")
            self.assertEqual(list(self.commands._reviews), [identifier])
            status = self.tools.film_review_status({"review_id": identifier, "action": "cancel"})
            self.assertEqual(status["phase"], "CANCELLING")
            release.set()
            status = self.settle(identifier)
        self.assertEqual(status["phase"], "CANCELLED")
        self.assertFalse(self.copies())
        self.assertFalse(self.session._coordinator.film_review_cleanup_pending)
        self.assertEqual(self.state(), self.storage.JobState.READY)
        self.ready()  # The single local media slot is free again.
        self.assertFalse(self.media.calls or self.media.downloads)

    def test_frame_or_recipe_change_after_ready_deletes_copies(self):
        for change in ("frame", "recipe"):
            with self.subTest(change=change):
                identifier = self.ready()
                self.assertEqual(len(self.copies()), 1)
                if change == "frame":
                    self.scene.frame_set(self.scene.frame_current + 1)
                else:
                    self.scene.scenario_film.recipe_json = json.dumps(
                        {**self.media.raw, "title": "Changed"}
                    )
                status = self.tools.film_review_status({"review_id": identifier})
                self.assertEqual(status["phase"], "ERROR")
                self.assertIn("prepare again", status["error"])
                self.assertFalse(self.copies())
                with self.assertRaises(ValueError):
                    self.tools.build_film_review({"review_id": identifier})
                self.assertEqual(self.state(), self.storage.JobState.READY)
                self.film.load_recipe(self.scene, self.media.raw)
        self.assertFalse(self.media.calls or self.media.downloads)

    def test_scene_switch_waits_then_becomes_ready_on_return(self):
        identifier = self.mcp_prepare()
        review = self.commands._reviews[identifier]
        review.task.result(5)
        other = bpy.data.scenes.new("Other review context")
        try:
            with bpy.context.temp_override(scene=other):
                self.commands.poll()
                self.assertEqual(review.phase, "WAITING")
                self.assertEqual(len(self.copies()), 1)
            self.commands.poll()
            self.assertEqual(review.phase, "READY", review.error)
        finally:
            bpy.data.scenes.remove(other)
        self.assertFalse(self.media.calls or self.media.downloads)

    def test_deleted_pending_scene_drains_and_removes_late_copies(self):
        other = bpy.data.scenes.new("Deleted review recipe")
        self.film.load_recipe(other, self.media.raw)
        other.scenario_film.production_id = self.production
        bpy.context.window.scene = other
        try:
            identifier = self.mcp_prepare()
            review = self.commands._reviews[identifier]
            review.task.result(5)
        finally:
            bpy.context.window.scene = self.scene
        bpy.data.scenes.remove(other)
        self.commands.poll()
        self.assertEqual(review.phase, "ERROR")
        self.assertIsNone(review.task)
        self.assertFalse(self.copies())
        self.assertIsNone(self.commands.current(self.scene, "final"))
        self.assertFalse(self.media.calls or self.media.downloads)

    def test_missing_master_or_probe_tool_fails_readably_without_copies(self):
        self.assertFalse(self.commands.master_available(self.scene, "final"))
        identifier = self.mcp_prepare(include_master=True)
        status = self.settle(identifier)
        self.assertEqual(status["phase"], "ERROR")
        self.assertIn("declared master", status["error"])
        self.assertFalse(self.copies())
        error = self.probe.MediaProbeError("Install ffprobe for this fixture")
        with patch.object(self.probe, "probe_tool", side_effect=error):
            status = self.settle(self.mcp_prepare())
        self.assertEqual((status["phase"], status["error"]), ("ERROR", str(error)))
        self.assertFalse(self.copies())
        with self.assertRaisesRegex(ValueError, "explicitly"):
            self.mcp_prepare(include_master="yes")
        self.assertFalse(self.media.calls or self.media.downloads)

    def test_builder_failure_rolls_back_and_saves_failed_claim(self):
        identifier = self.ready()
        with patch.object(self.builder, "_sound", side_effect=ValueError("decode fixture failure")):
            status = self.tools.build_film_review({"review_id": identifier})
        self.assertEqual(status["phase"], "ERROR")
        self.assertIn("rolled back", status["error"])
        self.assertEqual(self.builder._snapshot(), self.media.before)
        self.assertEqual(self.state(), self.storage.JobState.APPLY_FAILED)
        self.assertFalse(self.copies())
        self.assertEqual(
            self.tools.film_review_status({"review_id": identifier, "action": "discard"})["phase"],
            "DISCARDED",
        )

    def test_receipt_failure_is_uncertain_until_receipt_only_retry(self):
        identifier = self.ready()
        original = self.store.transition

        def lose(*args, **kwargs):
            result = original(*args, **kwargs)
            if kwargs.get("state") == self.storage.JobState.APPLIED:
                raise OSError("lost receipt acknowledgement")
            return result

        with patch.object(self.store, "transition", side_effect=lose):
            self.assertEqual(bpy.ops.scenario.build_film_review(review_id=identifier), {"FINISHED"})
        status = self.commands.status(identifier)
        self.assertEqual(status["phase"], "UNCERTAIN")
        self.assertTrue(status["receipt_retry_available"])
        self.assertTrue(status["review_scene"])
        with self.assertRaisesRegex(ValueError, "Save the known"):
            self.tools.film_review_status(
                {"review_id": identifier, "action": "dismiss_uncertain", "inspected": True}
            )
        with patch.object(
            self.builder, "build_prepared_review", side_effect=AssertionError("rebuild")
        ):
            self.assertEqual(
                bpy.ops.scenario.save_film_review_receipt(review_id=identifier), {"FINISHED"}
            )
        status = self.tools.film_review_status({"review_id": identifier})
        self.assertEqual(status["phase"], "BUILT")
        self.assertFalse(status["receipt_retry_available"] or status["inspection_required"])
        self.assertEqual(self.state(), self.storage.JobState.APPLIED)
        self.assertFalse(self.media.calls or self.media.downloads)

    def test_lost_claim_needs_inspected_dismissal_and_blocks_new_reviews(self):
        identifier = self.ready()
        original = self.session._claim_saved_application

        def lose(*args):
            original(*args)
            raise OSError("lost claim")

        with (
            patch.object(self.session, "_claim_saved_application", side_effect=lose),
            patch.object(
                self.builder, "build_prepared_review", side_effect=AssertionError("must not build")
            ),
        ):
            status = self.tools.build_film_review({"review_id": identifier})
        self.assertEqual(status["phase"], "UNCERTAIN")
        self.assertTrue(status["inspection_required"])
        self.assertFalse(status["receipt_retry_available"])
        self.assertEqual(self.commands.current(self.scene, "previs")["review_id"], identifier)
        for mode in ("final", "previs"):
            with self.assertRaisesRegex(ValueError, "uncertain"):
                self.mcp_prepare(mode=mode)
        self.assertEqual(
            bpy.ops.scenario.dismiss_film_review(review_id=identifier, inspected=False),
            {"CANCELLED"},
        )
        with self.assertRaisesRegex(ValueError, "inspection"):
            self.tools.film_review_status(
                {"review_id": identifier, "action": "dismiss_uncertain", "inspected": "yes"}
            )
        status = self.tools.film_review_status(
            {"review_id": identifier, "action": "dismiss_uncertain", "inspected": True}
        )
        self.assertEqual(status["phase"], "DISCARDED")
        self.assertEqual(self.state(), self.storage.JobState.APPLYING)
        self.settle(self.mcp_prepare())  # Dismissal no longer blocks explicit preparation.
        self.assertFalse(self.media.calls or self.media.downloads)

    def test_review_handles_are_bounded_and_shutdown_removes_ready_copies(self):
        def fill(phase):
            self.commands._reviews.clear()
            for _ in range(16):
                review = self.module._Review(
                    uuid.uuid4().hex,
                    self.scene,
                    self.scene.name,
                    self.film.snapshot(self.scene),
                    self.media.origin,
                    "previs",
                    "score",
                    False,
                    48,
                    24,
                    phase=phase,
                )
                self.commands._reviews[review.identifier] = review
            return next(iter(self.commands._reviews))

        oldest = fill("CANCELLING")
        with self.assertRaisesRegex(ValueError, "Finish or discard"):
            self.mcp_prepare()
        oldest = fill("CANCELLED")
        identifier = self.mcp_prepare()
        self.assertNotIn(oldest, self.commands._reviews)
        self.assertEqual(len(self.commands._reviews), 16)
        self.assertEqual(self.settle(identifier)["phase"], "READY")
        self.assertEqual(len(self.copies()), 1)
        self.session.shutdown()
        self.assertFalse(self.copies())
        self.assertFalse(self.commands._reviews)
        self.assertEqual(self.state(), self.storage.JobState.READY)

    def test_panel_and_studio_draw_only_read_cached_status(self):
        studio = submodule("blender.studio")
        view = bpy.context.window_manager.scenario_studio_view
        self.addCleanup(setattr, view, "page", view.page)
        self.addCleanup(setattr, view, "film_page", view.film_page)
        view.page, view.film_page = "FILM", "REVIEW"
        identifier = self.ready()
        review = self.commands._reviews[identifier]
        before = (self.film.snapshot(self.scene), review.phase, self.copies(), self.state())
        layout = MagicMock()
        with (
            patch.object(
                self.runtime, "ensure_film_jobs", side_effect=AssertionError("draw starts work")
            ),
            patch.object(self.commands, "poll", side_effect=AssertionError("draw polls work")),
            patch.object(self.session, "drain", side_effect=AssertionError("draw drains work")),
            patch.object(self.store, "film_job", side_effect=AssertionError("draw reads store")),
        ):
            self.ui.SCENARIO_PT_film_review.draw(SimpleNamespace(layout=layout), bpy.context)
            studio.draw_view(MagicMock(), bpy.context, width=400)
        box = layout.box.return_value
        self.assertIn(call(text="Assemble review", icon="SEQUENCE"), box.label.call_args_list)
        self.assertIn(
            call("scenario.build_film_review", icon="SCENE_DATA"), box.operator.call_args_list
        )
        self.assertEqual(
            before, (self.film.snapshot(self.scene), review.phase, self.copies(), self.state())
        )
        self.assertFalse(self.media.calls or self.media.downloads)

    def test_mode_navigation_is_unsaved_and_preserves_a_ready_review(self):
        manager = bpy.context.window_manager
        self.assertTrue(manager.bl_rna.properties["scenario_film_review_mode"].is_skip_save)
        identifier = self.ready()
        review = self.commands._reviews[identifier]
        for mode in ("previs", "final", "previs"):
            bpy.ops.wm.context_set_enum(
                data_path="window_manager.scenario_film_review_mode", value=mode
            )
            # Native property clicks tag their owner; Python assignment alone does not.
            manager.update_tag()
            bpy.context.view_layer.update()
            self.commands.poll()
            self.assertEqual(review.phase, "READY", review.error)
        self.assertIsNone(self.commands.current(self.scene, "previs"))
        self.assertEqual(manager.scenario_film_composition_mode, "final")
        manager.scenario_film_review_mode = "final"
        self.assertEqual(self.commands.current(self.scene, "final")["review_id"], identifier)

    def test_edit_mode_allows_preparation_but_blocks_build_without_consuming(self):
        bpy.ops.mesh.primitive_cube_add()
        bpy.ops.object.mode_set(mode="EDIT")
        try:
            identifier = self.ready()
            self.assertFalse(bpy.ops.scenario.build_film_review.poll())
            with self.assertRaisesRegex(ValueError, "Object Mode"):
                self.tools.build_film_review({"review_id": identifier})
            self.assertEqual(self.commands._reviews[identifier].phase, "READY")
            self.assertEqual(len(self.copies()), 1)
            self.assertEqual(self.builder._snapshot(), self.media.before)
            self.assertEqual(self.state(), self.storage.JobState.READY)
        finally:
            bpy.ops.object.mode_set(mode="OBJECT")
        self.assertTrue(bpy.ops.scenario.build_film_review.poll())

    def test_stale_context_and_retired_session_reject_commands(self):
        with self.assertRaisesRegex(ValueError, "connection"):
            self.tools.prepare_film_review({"context_id": "old", "production_id": self.production})
        with self.assertRaises(self.runtime.ScenarioError):
            self.tools.prepare_film_review(
                {"context_id": "fixture-context", "production_id": "other"}
            )
        self.assertEqual(self.commands._reviews, {})
        identifier = self.ready()
        self.session.deactivate()
        with self.assertRaisesRegex(ValueError, "fresh ready"):
            self.tools.build_film_review({"review_id": identifier})
        status = self.commands.status(identifier)
        self.assertEqual((status["phase"], self.copies()), ("ERROR", []))
        self.assertEqual(self.state(), self.storage.JobState.READY)
        self.assertFalse(self.media.calls or self.media.downloads)
