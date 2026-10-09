# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Installed Film review controls share session handles, copies, claims and receipts."""

import hashlib
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

    def panel_labels(self):
        layout = MagicMock()
        self.ui.SCENARIO_PT_film_review.draw(SimpleNamespace(layout=layout), bpy.context)
        return [item.kwargs.get("text") for item in layout.box.return_value.label.call_args_list]

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
        # Like the timeline build, the once-consumed build declares Undo without REGISTER.
        timeline = submodule("blender.film_timeline_controls").SCENARIO_OT_build_film_timeline
        self.assertEqual(self.ui.SCENARIO_OT_build_film_review.bl_options, {"UNDO"})
        self.assertEqual(self.ui.SCENARIO_OT_build_film_review.bl_options, timeline.bl_options)
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

    def test_prepare_dialog_separates_saved_job_errors_from_recipe_errors(self):
        operator = SimpleNamespace(report=Mock(), include_master=False, layout=MagicMock())
        context = SimpleNamespace(
            scene=self.scene, window_manager=Mock(scenario_film_review_mode="final")
        )
        prepare = self.ui.SCENARIO_OT_prepare_film_review
        error = self.storage.StoreError(
            "Film task has conflicting saved identities; inspect storage"
        )
        with patch.object(self.store, "film_job", side_effect=error):
            self.assertEqual(prepare.invoke(operator, context, None), {"CANCELLED"})
        operator.report.assert_called_once_with(
            {"WARNING"},
            "Inspect saved jobs before preparing: "
            "Film task has conflicting saved identities; inspect storage",
        )
        operator.report.reset_mock()
        self.scene.scenario_film.recipe_json = ""
        self.assertEqual(prepare.invoke(operator, context, None), {"CANCELLED"})
        operator.report.assert_called_once_with(
            {"WARNING"}, "Load a valid Film recipe in the current scene first"
        )
        context.window_manager.invoke_props_dialog.assert_not_called()
        self.assertEqual(self.commands._reviews, {})
        self.assertFalse(self.copies())

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

    def test_panel_warns_that_selection_edits_or_history_discard_unbuilt_reviews(self):
        warning = "Selecting, editing or Undo here discards it"
        history = submodule("blender.job_session")._history_pre
        target = self.media.target
        for change in ("selection", "undo", "redo"):
            with self.subTest(change=change):
                identifier = self.mcp_prepare()
                # Only maintenance advances the phase, so this draw is still preparing.
                self.assertEqual(self.commands.status(identifier)["phase"], "PREPARING")
                self.assertIn(warning, self.panel_labels())
                self.assertEqual(self.settle(identifier)["phase"], "READY")
                self.assertIn(warning, self.panel_labels())
                self.assertEqual(len(self.copies()), 1)
                if change == "selection":
                    target.select_set(not target.select_get())
                    # A native click is followed by the window's dependency evaluation.
                    bpy.context.view_layer.update()
                else:
                    # The shared session's registered Undo/Redo handler, as Blender calls it.
                    handlers = getattr(bpy.app.handlers, change + "_pre")
                    self.assertIn(history, handlers)
                    history(self.scene)
                status = self.tools.film_review_status({"review_id": identifier})
                self.assertEqual(status["phase"], "ERROR")
                self.assertIn("prepare again", status["error"])
                self.assertFalse(self.copies())
                self.assertNotIn(warning, self.panel_labels())
                with self.assertRaisesRegex(ValueError, "fresh ready"):
                    self.tools.build_film_review({"review_id": identifier})
        self.assertEqual(self.state(), self.storage.JobState.READY)
        self.assertFalse(self.media.calls or self.media.downloads)

    def test_selecting_the_recipe_scene_again_requires_fresh_preparation(self):
        # The scene selector assigns window.scene; Blender then runs frame_change_pre
        # for the newly selected scene, which a context override never does.
        window = bpy.context.window
        other = bpy.data.scenes.new("Other review context")
        self.addCleanup(bpy.data.scenes.remove, other)
        self.addCleanup(setattr, window, "scene", self.scene)
        built = self.ready()
        self.assertEqual(self.tools.build_film_review({"review_id": built})["phase"], "BUILT")
        kept = self.copies()  # The built review scene still uses these copies.
        self.assertEqual(len(kept), 1)
        ready = self.ready()
        self.assertEqual(len(self.copies()), 2)
        window.scene = other
        self.commands.poll()
        # Leaving alone keeps the review and its copies.
        self.assertEqual(self.commands.status(ready)["phase"], "READY")
        self.assertEqual(len(self.copies()), 2)
        window.scene = self.scene
        self.commands.poll()
        status = self.commands.status(ready)
        self.assertEqual(status["phase"], "ERROR")
        self.assertIn("selected again", status["error"])
        self.assertEqual(self.copies(), kept)
        with self.assertRaisesRegex(ValueError, "fresh ready"):
            self.tools.build_film_review({"review_id": ready})
        # A built review keeps its scene, copies and outcome after the same round trip.
        status = self.commands.status(built)
        self.assertEqual(status["phase"], "BUILT")
        self.assertIn(status["review_scene"], bpy.data.scenes)
        # Preparation finishing while another scene is active waits, then fails on return.
        waiting = self.mcp_prepare()
        review = self.commands._reviews[waiting]
        window.scene = other
        review.task.result(5)
        self.commands.poll()
        self.assertEqual(review.phase, "WAITING")
        self.assertEqual(len(self.copies()), 2)
        window.scene = self.scene
        status = self.settle(waiting)
        self.assertEqual(status["phase"], "ERROR")
        self.assertIn("selected again", status["error"])
        self.assertEqual(self.copies(), kept)
        self.assertFalse(self.session._coordinator.film_review_cleanup_pending)
        self.assertEqual(self.state(), self.storage.JobState.APPLIED)
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

    def save_master(self, observations):
        """Save one downloaded final master bound to the composed current-source recipe."""
        draft = submodule("core.scene.film_finish").compose_recipe(
            self.media.raw,
            {
                source.task_id: submodule("core.scene.film_plan").TaskAssets(
                    source.scope, (source.asset_id,)
                )
                for source in observations
            },
            scope=self.session.scope,
            mode="final",
            score_task_id="score",
            audio_durations={},
        )
        self.save_video("master", draft, self.production, "final-master")

    def save_video(self, identifier, recipe, production, task_id):
        """Save one downloaded synthetic video result bound to a recipe model task."""
        storage, store = self.storage, self.store
        binding, tasks, *_ = submodule("core.jobs.film_tasks")._task_context(
            store, recipe, production_id=production, task_id=task_id, kind="model"
        )
        digest = hashlib.sha256(identifier.encode()).hexdigest()
        row = store.create(
            storage.JobIntent(
                identifier,
                self.media.scope,
                self.media.origin,
                "model",
                tasks[task_id]["model"],
                digest,
                digest[::-1],
                "1",
                film_task=binding,
            )
        )
        for state in (
            storage.JobState.SUBMITTING,
            storage.JobState.REMOTE,
            storage.JobState.SUCCEEDED,
        ):
            row = store.transition(
                identifier,
                expected_revision=row.revision,
                state=state,
                remote_job_id=identifier + "-remote" if state == storage.JobState.REMOTE else None,
            )
        asset = storage.ResultAsset(identifier + "-asset", identifier + ".mp4", "video/mp4")
        row = store.set_results(identifier, (asset,), expected_revision=row.revision)
        row = store.transition(
            identifier, expected_revision=row.revision, state=storage.JobState.DOWNLOADING
        )
        data = self.media.data
        (self.session._coordinator._results._directory(row) / asset.name).write_bytes(data)
        receipt = self.media.transfers.DownloadedResult(
            asset.name, len(data), hashlib.sha256(data).hexdigest()
        )
        row = store.record_download(
            identifier, asset.asset_id, receipt, expected_revision=row.revision
        )
        store.transition(identifier, expected_revision=row.revision, state=storage.JobState.READY)

    def test_previs_review_builds_beside_a_ready_final_review_which_then_fails(self):
        raw = {
            **self.media.raw,
            "tasks": [
                *self.media.raw["tasks"],
                {
                    "id": "shot-previs",
                    "title": "Previs",
                    "kind": "model",
                    "model": "fixture-model",
                    "parameters": {"prompt": "fixture previs"},
                },
            ],
        }
        props = self.scene.scenario_film
        props.production_id = ""  # A new production keeps the fixture's saved take apart.
        self.film.load_recipe(self.scene, raw)
        production = props.production_id
        self.assertNotEqual(production, self.production)
        self.save_video("final-take", raw, production, "shot-video")
        self.save_video("previs-take", raw, production, "shot-previs")
        final = self.ready(production_id=production)
        previs = self.ready(production_id=production, mode="previs")
        # Both modes stay ready for one scene until one of them is built.
        self.assertEqual(self.commands.status(final)["phase"], "READY")
        self.assertEqual(self.commands.current(self.scene, "final")["review_id"], final)
        self.assertEqual(self.commands.current(self.scene, "previs")["review_id"], previs)
        self.assertEqual(len(self.copies()), 2)
        status = self.commands.status(previs)
        self.assertEqual(
            (status["mode"], status["frames"], status["fps"], status["shots"], status["sources"]),
            ("previs", 48, 24, 1, 1),
        )
        self.assertEqual((status["audio_segments"], status["master"]), (0, False))
        before = set(bpy.data.scenes)
        self.assertEqual(bpy.ops.scenario.build_film_review(review_id=previs), {"FINISHED"})
        status = self.commands.status(previs)
        self.assertEqual(status["phase"], "BUILT", status["error"])
        (review,) = set(bpy.data.scenes) - before
        self.assertEqual(status["review_scene"], review.name)
        self.assertEqual(review["scenario_sequence_kind"], "downloaded_previs_review")
        strips = {strip.name: strip for strip in review.sequence_editor.strips}
        self.assertEqual(set(strips), {"shot / picture", "shot / native audio"})
        # Previs keeps the take untrimmed; the final cut trims one second.
        self.assertEqual(strips["shot / picture"].frame_offset_start, 0)
        self.assertEqual(bpy.context.scene, self.scene)
        self.assertEqual(self.store.get("previs-take").state, self.storage.JobState.APPLIED)
        self.assertEqual(self.store.get("final-take").state, self.storage.JobState.READY)
        # The window evaluates the build's dependency update before the next maintenance.
        bpy.context.view_layer.update()
        status = self.tools.film_review_status({"review_id": final})
        self.assertEqual(status["phase"], "ERROR")
        self.assertIn("prepare again", status["error"])
        self.assertEqual(len(self.copies()), 1)  # Only the built previs review keeps copies.
        with self.assertRaisesRegex(ValueError, "fresh ready"):
            self.tools.build_film_review({"review_id": final})
        final = self.ready(production_id=production)
        status = self.tools.build_film_review({"review_id": final})
        self.assertEqual(status["phase"], "BUILT", status["error"])
        self.assertEqual(self.store.get("final-take").state, self.storage.JobState.APPLIED)
        self.assertEqual(self.commands.status(previs)["phase"], "BUILT")
        self.assertEqual(self.state(), self.storage.JobState.READY)
        self.assertFalse(self.media.calls or self.media.downloads)

    def test_included_saved_master_builds_a_muted_alternate(self):
        first = self.ready()
        observations = self.commands._reviews[first].completion.result.observations
        self.tools.film_review_status({"review_id": first, "action": "discard"})
        self.assertFalse(self.copies())
        self.save_master(observations)
        self.assertTrue(self.commands.master_available(self.scene, "final"))
        self.assertFalse(self.commands.master_available(self.scene, "previs"))
        operator = SimpleNamespace(report=Mock(), include_master=False, layout=MagicMock())
        context = SimpleNamespace(
            scene=self.scene, window_manager=Mock(scenario_film_review_mode="final")
        )
        context.window_manager.invoke_props_dialog.return_value = {"RUNNING_MODAL"}
        prepare = self.ui.SCENARIO_OT_prepare_film_review
        self.assertEqual(prepare.invoke(operator, context, None), {"RUNNING_MODAL"})
        prepare.draw(operator, context)
        self.assertTrue(operator._master)
        self.assertIs(operator.layout.row.return_value.enabled, True)
        labels = [c.kwargs["text"] for c in operator.layout.label.call_args_list]
        self.assertNotIn("No saved master video for this recipe and mode", labels)
        operator.include_master = True
        self.assertEqual(prepare.execute(operator, bpy.context), {"FINISHED"})
        operator.report.assert_not_called()
        identifier = self.commands.current(self.scene, "final")["review_id"]
        status = self.settle(identifier)
        self.assertEqual(status["phase"], "READY", status["error"])
        self.assertTrue(status["include_master"] and status["master"])
        self.assertEqual((status["sources"], status["bytes"]), (1, 2 * len(self.media.data)))
        self.assertEqual(len(tuple(next(iter(self.copies())).iterdir())), 2)
        before = set(bpy.data.scenes)
        status = self.tools.build_film_review({"review_id": identifier})
        self.assertEqual(status["phase"], "BUILT", status["error"])
        self.assertTrue(status["master"])
        (review,) = set(bpy.data.scenes) - before
        strips = tuple(review.sequence_editor.strips)
        self.assertEqual(len(strips), 4)
        muted = [strip for strip in strips if strip.mute]
        self.assertEqual(sorted(strip.type for strip in muted), ["MOVIE", "SOUND"])
        self.assertTrue(all("muted alternate" in strip.name for strip in muted))
        self.assertEqual(self.state(), self.storage.JobState.APPLIED)
        self.assertEqual(self.store.get("master").state, self.storage.JobState.APPLIED)
        self.assertFalse(self.media.calls or self.media.downloads)

    def test_full_session_queue_reports_readable_admission_text(self):
        operator = SimpleNamespace(report=Mock(), include_master=False)
        with patch.object(self.session, "_completion_limit", 0):
            with self.assertRaisesRegex(ValueError, "Drain completed job outcomes"):
                self.mcp_prepare()
            self.assertEqual(
                self.ui.SCENARIO_OT_prepare_film_review.execute(operator, bpy.context),
                {"CANCELLED"},
            )
        operator.report.assert_called_once_with(
            {"WARNING"}, "Drain completed job outcomes before adding more commands"
        )
        self.assertEqual(self.commands._reviews, {})
        self.assertFalse(self.copies())

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
