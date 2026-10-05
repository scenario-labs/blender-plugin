# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Explicit local timeline selection, stale-source guards and shared UI/MCP approval."""

import copy
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import bpy
import test_film_shot_controls as shot_tests
from helpers import submodule


class _Choices(list):
    def add(self):
        row = SimpleNamespace(choices=_Choices(), choice_index=0)
        self.append(row)
        return row


class FilmTimelineControlTests(unittest.TestCase):
    new_adapter = shot_tests.FilmShotControlTests.new_adapter
    new_session = shot_tests.FilmShotControlTests.new_session
    respond = shot_tests.FilmShotControlTests.respond
    saved = shot_tests.FilmShotControlTests.saved

    def setUp(self):
        shot_tests.FilmShotControlTests.setUp(self)
        self.ui = submodule("blender.film_timeline_controls")
        self.timeline = self.session.film_timeline
        self.raw["shots"][0]["actors"] = []
        second = copy.deepcopy(self.raw["shots"][0])
        second.update(id="second", title="Second", duration=2)
        self.raw["shots"].append(second)
        self.film.load_recipe(self.scene, self.raw)
        self.shots = {
            shot["id"]: self.builder.build_shot(
                self.raw, production_id=self.production, shot_id=shot["id"]
            ).scene
            for shot in self.raw["shots"]
        }
        bpy.context.view_layer.update()
        self.saved_before = self.store.records()

    def tearDown(self):
        shot_tests.FilmShotControlTests.tearDown(self)

    def inspect(self):
        result = self.tools.film_timeline_sources({"production_id": self.production})
        self.assertEqual(result["total_frames"], 180)
        return result, {row["shot_id"]: row["choices"][0]["source_id"] for row in result["shots"]}

    def prepare(self):
        result, selections = self.inspect()
        return self.tools.prepare_film_timeline(
            {
                "context_id": result["context_id"],
                "production_id": result["production_id"],
                "selections": selections,
            }
        )["review_id"]

    def dialog(self):
        operator = SimpleNamespace(shots=_Choices(), report=Mock())
        context = SimpleNamespace(
            scene=self.scene, view_layer=bpy.context.view_layer, window_manager=Mock()
        )
        context.window_manager.invoke_props_dialog.return_value = {"RUNNING_MODAL"}
        self.assertEqual(
            self.ui.SCENARIO_OT_build_film_timeline.invoke(operator, context, None),
            {"RUNNING_MODAL"},
        )
        return operator, context

    def test_mcp_requires_separate_single_use_approval_and_preserves_saved_jobs(self):
        before = self.builder._snapshot()
        identifier = self.prepare()
        self.assertEqual(self.builder._snapshot(), before)
        status = self.tools.build_film_timeline({"review_id": identifier})
        self.assertEqual(status["phase"], "BUILT", status)
        scene = bpy.data.scenes[status["scene"]]
        self.assertEqual(
            [strip.scene for strip in scene.sequence_editor.strips], list(self.shots.values())
        )
        self.assertEqual(
            [(s.frame_final_start, s.frame_final_end) for s in scene.sequence_editor.strips],
            [(1, 121), (121, 181)],
        )
        self.assertEqual(bpy.context.scene, self.scene)
        with self.assertRaises(ValueError):
            self.tools.build_film_timeline({"review_id": identifier})
        self.assertEqual(self.store.records(), self.saved_before)
        self.assertFalse(self.calls or self.downloads)

    def test_native_dialog_builds_using_shared_command_and_cancel_does_nothing(self):
        before = self.builder._snapshot()
        self.dialog()  # Cancel without executing.
        self.assertEqual(self.timeline._reviews, {})
        self.assertEqual(self.builder._snapshot(), before)
        operator, context = self.dialog()
        self.assertEqual(
            self.ui.SCENARIO_OT_build_film_timeline.execute(operator, context), {"FINISHED"}
        )
        status = self.timeline.current(self.scene)
        self.assertEqual(
            self.tools.film_timeline_review({"review_id": status["review_id"]})["phase"], "BUILT"
        )
        before = self.builder._snapshot()
        self.assertEqual(
            self.ui.SCENARIO_OT_build_film_timeline.execute(operator, context), {"CANCELLED"}
        )
        self.assertEqual(self.builder._snapshot(), before)
        self.assertFalse(self.calls or self.downloads)

    def test_native_dialog_rejects_changed_recipe_destination(self):
        operator, context = self.dialog()
        self.scene.frame_set(10)
        before = self.builder._snapshot()
        self.assertEqual(
            self.ui.SCENARIO_OT_build_film_timeline.execute(operator, context), {"CANCELLED"}
        )
        self.assertEqual(self.builder._snapshot(), before)

    def test_missing_shot_and_foreign_choices_cannot_prepare(self):
        _, selections = self.inspect()
        selections.pop("second")
        with self.assertRaisesRegex(ValueError, "every Film shot"):
            self.timeline.prepare(self.scene, selections=selections)
        _, selections = self.inspect()
        selections["second"] = selections["shot"]
        with self.assertRaisesRegex(ValueError, "changed"):
            self.timeline.prepare(self.scene, selections=selections)
        self.assertEqual(self.timeline._reviews, {})

    def test_deleted_same_name_replacement_cannot_redirect_ready_review(self):
        identifier = self.prepare()
        name = self.shots["second"].name
        bpy.data.scenes.remove(self.shots["second"])
        bpy.data.scenes.new(name)
        before = self.builder._snapshot()
        with self.assertRaises(ValueError):
            self.timeline.approve(identifier)
        self.assertEqual(self.builder._snapshot(), before)

    def test_changed_timing_and_camera_reject_stale_choices(self):
        for change in ("timing", "camera"):
            _, selections = self.inspect()
            shot = self.shots["second"]
            camera, frame_end = shot.camera, shot.frame_end
            if change == "timing":
                shot.frame_end += 1
            else:
                shot.camera = None
            with self.assertRaisesRegex(ValueError, "changed"):
                self.timeline.prepare(self.scene, selections=selections)
            shot.camera, shot.frame_end = camera, frame_end

    def test_origin_change_and_connection_retirement_reject_ready_build(self):
        identifier = self.prepare()
        self.session.invalidate_scene(self.shots["second"])
        with self.assertRaisesRegex(ValueError, "changed"):
            self.timeline.approve(identifier)
        identifier = self.prepare()
        self.session.deactivate()
        with self.assertRaisesRegex(RuntimeError, "connection"):
            self.timeline.approve(identifier)

    def test_fresh_inspection_invalidates_choices_but_not_prepared_reviews(self):
        _, old = self.inspect()
        identifier = self.timeline.prepare(self.scene, selections=old)["review_id"]
        self.inspect()
        with self.assertRaisesRegex(ValueError, "current Film"):
            self.timeline.prepare(self.scene, selections=old)
        self.assertEqual(self.timeline.approve(identifier)["phase"], "BUILT")

    def test_confirmed_rollback_consumes_review_and_preserves_existing_data(self):
        identifier = self.prepare()
        before = self.builder._snapshot()
        with patch.object(
            self.builder, "build_timeline", side_effect=RuntimeError("Before mutation")
        ):
            self.assertEqual(self.timeline.approve(identifier)["phase"], "ERROR")
        self.assertEqual(self.builder._snapshot(), before)
        with self.assertRaises(ValueError):
            self.timeline.approve(identifier)

    def test_uncertain_mutation_blocks_replay_until_explicit_inspection(self):
        identifier = self.prepare()

        def partial(*args, **kwargs):
            bpy.data.scenes.new("Partial fixture")
            raise RuntimeError("Incomplete cleanup")

        with patch.object(self.builder, "build_timeline", side_effect=partial):
            self.assertEqual(self.timeline.approve(identifier)["phase"], "UNCERTAIN")
        with self.assertRaisesRegex(ValueError, "uncertain"):
            self.prepare()
        for value in (False, 1, "true"):
            with self.assertRaisesRegex(ValueError, "Inspect"):
                self.timeline.discard(identifier, inspected=value)
        before = self.builder._snapshot()
        self.assertEqual(
            bpy.ops.scenario.discard_film_timeline(review_id=identifier, inspected=True),
            {"FINISHED"},
        )
        self.assertEqual(self.builder._snapshot(), before)
        self.assertEqual(self.timeline.status(self.prepare())["phase"], "READY")
        self.assertEqual(self.store.records(), self.saved_before)

    def test_same_recipe_saved_scenes_can_be_explicitly_selected_after_reload(self):
        path = self.root / "timeline-sources.blend"
        bpy.data.libraries.write(str(path), set(self.shots.values()))
        with bpy.data.libraries.load(str(path), link=False) as (source, target):
            target.scenes = source.scenes
        result = self.timeline.inspect(self.scene)
        self.assertEqual([len(row["choices"]) for row in result["shots"]], [2, 2])
        selections = {
            row["shot_id"]: next(
                choice["source_id"]
                for choice in row["choices"]
                if choice["scene"] in {s.name for s in target.scenes}
            )
            for row in result["shots"]
        }
        identifier = self.timeline.prepare(self.scene, selections=selections)["review_id"]
        self.assertEqual(self.timeline.approve(identifier)["phase"], "BUILT")

    def test_panel_drawing_does_not_activate_inspect_or_build(self):
        self.prepare()
        with (
            patch.object(
                self.runtime, "ensure_film_jobs", side_effect=AssertionError("Draw activation")
            ),
            patch.object(self.timeline, "inspect", side_effect=AssertionError("Draw inspection")),
            patch.object(self.store, "get", side_effect=AssertionError("Draw storage")),
        ):
            self.ui.SCENARIO_PT_film_timeline.draw(SimpleNamespace(layout=Mock()), bpy.context)
