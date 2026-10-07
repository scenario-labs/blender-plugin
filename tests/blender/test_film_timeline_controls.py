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

    def test_edit_mode_allows_preparation_but_blocks_timeline_build(self):
        bpy.ops.mesh.primitive_cube_add()
        bpy.ops.object.mode_set(mode="EDIT")
        try:
            before = self.builder._snapshot()
            identifier = self.prepare()
            self.assertEqual(self.timeline.status(identifier)["phase"], "READY")
            self.assertFalse(bpy.ops.scenario.build_film_timeline.poll())
            with self.assertRaisesRegex(ValueError, "Object Mode"):
                self.tools.build_film_timeline({"review_id": identifier})
            self.assertEqual(self.timeline.status(identifier)["phase"], "READY")
            self.assertEqual(self.builder._snapshot(), before)
            self.assertEqual(self.store.records(), self.saved_before)
            self.assertFalse(self.calls or self.downloads)
        finally:
            bpy.ops.object.mode_set(mode="OBJECT")
        self.assertTrue(bpy.ops.scenario.build_film_timeline.poll())

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

    def test_missing_shot_dialog_names_the_scene_to_build(self):
        bpy.data.scenes.remove(self.shots["second"])
        operator = SimpleNamespace(shots=_Choices(), report=Mock())
        context = SimpleNamespace(
            scene=self.scene, view_layer=bpy.context.view_layer, window_manager=Mock()
        )
        self.assertEqual(
            self.ui.SCENARIO_OT_build_film_timeline.invoke(operator, context, None), {"CANCELLED"}
        )
        context.window_manager.invoke_props_dialog.assert_not_called()
        operator.report.assert_called_once_with(
            {"WARNING"}, "Build a matching scene for shot 'Second' first"
        )
        self.assertEqual(self.timeline._reviews, {})

    def test_invalid_scene_selection_does_not_prepare_a_timeline(self):
        operator, context = self.dialog()
        operator.shots[1].choice_index = 10
        self.assertEqual(
            self.ui.SCENARIO_OT_build_film_timeline.execute(operator, context), {"CANCELLED"}
        )
        operator.report.assert_called_once_with(
            {"WARNING"}, "Select a matching scene for shot 'Second' first"
        )
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

    def test_deleted_camera_replacement_rejects_preparation_and_approval_cleanly(self):
        for phase in ("prepare", "approve"):
            _, selections = self.inspect()
            identifier = (
                self.timeline.prepare(self.scene, selections=selections)["review_id"]
                if phase == "approve"
                else None
            )
            shot = self.shots["second"]
            name = shot.camera.name
            bpy.data.objects.remove(shot.camera, do_unlink=True)
            replacement = bpy.data.objects.new(name, bpy.data.cameras.new("Replacement camera"))
            shot.collection.objects.link(replacement)
            shot.camera = replacement
            before = self.builder._snapshot()
            # A non-current scene can retain an unchanged revision until depsgraph delivery.
            with patch.object(self.session._origins, "current", return_value=True):
                with self.assertRaisesRegex(ValueError, "A selected Film shot changed"):
                    if identifier:
                        self.timeline.approve(identifier)
                    else:
                        self.timeline.prepare(self.scene, selections=selections)
            self.assertEqual(self.builder._snapshot(), before)

    def test_invalidated_source_reference_rejects_without_building(self):
        _, selections = self.inspect()
        identifier = self.timeline.prepare(self.scene, selections=selections)["review_id"]
        before = self.builder._snapshot()
        with patch.object(self.builder, "matching_shot", side_effect=ReferenceError("Removed RNA")):
            with self.assertRaisesRegex(ValueError, "A selected Film shot changed"):
                self.timeline.prepare(self.scene, selections=selections)
            with self.assertRaisesRegex(ValueError, "A selected Film shot changed"):
                self.timeline.approve(identifier)
        self.assertEqual(self.builder._snapshot(), before)
        self.assertEqual(self.timeline.status(identifier)["phase"], "READY")

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

    def test_older_uncertainty_stays_visible_and_blocks_another_ready_review(self):
        first = self.prepare()
        second = self.prepare()

        def partial(*args, **kwargs):
            bpy.data.scenes.new("Partial older timeline")
            raise RuntimeError("Incomplete cleanup")

        with patch.object(self.builder, "build_timeline", side_effect=partial):
            self.assertEqual(self.timeline.approve(first)["phase"], "UNCERTAIN")
        self.assertEqual(self.timeline.current(self.scene)["review_id"], first)
        before = self.builder._snapshot()
        with self.assertRaisesRegex(ValueError, "uncertain"):
            self.timeline.approve(second)
        self.assertEqual(self.builder._snapshot(), before)
        self.assertEqual(self.timeline.status(second)["phase"], "READY")
        self.timeline.discard(first, inspected=True)
        self.assertEqual(self.timeline.current(self.scene)["review_id"], second)

    def test_dismissed_errors_leave_the_panel_but_remain_inspectable(self):
        for uncertain in (False, True):
            with self.subTest(uncertain=uncertain):
                identifier = self.prepare()

                def fail(*args, uncertain=uncertain, **kwargs):
                    if uncertain:
                        bpy.data.scenes.new("Partial dismissed timeline")
                    raise RuntimeError("Build fixture failure")

                with patch.object(self.builder, "build_timeline", side_effect=fail):
                    status = self.timeline.approve(identifier)
                self.assertEqual(status["phase"], "UNCERTAIN" if uncertain else "ERROR")
                error = status["error"]
                before = self.builder._snapshot()
                self.assertEqual(
                    bpy.ops.scenario.discard_film_timeline(
                        review_id=identifier, inspected=uncertain
                    ),
                    {"FINISHED"},
                )
                status = self.tools.film_timeline_review({"review_id": identifier})
                self.assertEqual((status["phase"], status["error"]), ("DISCARDED", error))
                layout = Mock()
                self.ui.SCENARIO_PT_film_timeline.draw(SimpleNamespace(layout=layout), bpy.context)
                self.assertEqual(
                    [call.args[0] for call in layout.operator.call_args_list],
                    ["scenario.build_film_timeline"],
                )
                self.assertEqual(
                    [call.kwargs["text"] for call in layout.label.call_args_list],
                    ["Choose a completed scene for every shot."],
                )
                self.assertEqual(self.builder._snapshot(), before)
                self.assertEqual(self.store.records(), self.saved_before)

    def test_recipe_reload_hides_old_status_without_losing_review_history(self):
        replacement = copy.deepcopy(self.raw)
        replacement["title"] = "Replacement recipe"
        for phase in ("READY", "BUILT", "ERROR", "DISCARDED"):
            with self.subTest(phase=phase):
                self.tools.film_recipe({"action": "load", "recipe": self.raw})
                identifier = self.prepare()
                if phase == "BUILT":
                    self.timeline.approve(identifier)
                elif phase == "ERROR":
                    with patch.object(self.builder, "build_timeline", side_effect=RuntimeError):
                        self.timeline.approve(identifier)
                elif phase == "DISCARDED":
                    self.timeline.discard(identifier)
                original = self.timeline.status(identifier)
                self.assertEqual(original["phase"], phase)
                self.assertEqual(self.timeline.current(self.scene), original)
                self.tools.film_recipe({"action": "load", "recipe": replacement})
                before = self.builder._snapshot()
                self.assertIsNone(self.timeline.current(self.scene))
                layout = Mock()
                self.ui.SCENARIO_PT_film_timeline.draw(SimpleNamespace(layout=layout), bpy.context)
                self.assertEqual(
                    [call.args[0] for call in layout.operator.call_args_list],
                    ["scenario.build_film_timeline"],
                )
                self.assertEqual(
                    [call.kwargs["text"] for call in layout.label.call_args_list],
                    ["Choose a completed scene for every shot."],
                )
                self.assertEqual(
                    self.tools.film_timeline_review({"review_id": identifier}), original
                )
                self.assertEqual(self.builder._snapshot(), before)
                self.assertEqual(self.store.records(), self.saved_before)
                self.assertFalse(self.calls or self.downloads)

    def test_recipe_reload_keeps_uncertain_cleanup_visible_and_blocking(self):
        first, second = self.prepare(), self.prepare()

        def partial(*args, **kwargs):
            bpy.data.scenes.new("Partial previous recipe timeline")
            raise RuntimeError("Incomplete cleanup")

        with patch.object(self.builder, "build_timeline", side_effect=partial):
            self.assertEqual(self.timeline.approve(first)["phase"], "UNCERTAIN")
        replacement = copy.deepcopy(self.raw)
        replacement["title"] = "Replacement recipe"
        self.tools.film_recipe({"action": "load", "recipe": replacement})
        before = self.builder._snapshot()
        self.assertEqual(self.timeline.current(self.scene)["review_id"], first)
        with self.assertRaisesRegex(ValueError, "uncertain"):
            self.timeline.prepare(self.scene, selections={})
        with self.assertRaisesRegex(ValueError, "uncertain"):
            self.timeline.approve(second)
        with self.assertRaisesRegex(ValueError, "Inspect"):
            self.timeline.discard(first)
        self.timeline.discard(first, inspected=True)
        self.assertIsNone(self.timeline.current(self.scene))
        self.assertEqual(self.builder._snapshot(), before)
        self.assertEqual(self.store.records(), self.saved_before)
        self.assertFalse(self.calls or self.downloads)

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
