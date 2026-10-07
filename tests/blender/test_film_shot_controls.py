# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Installed Film shot UI/MCP commands with real saved results and no service I/O."""

import copy
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import bpy
import test_film_application as application_tests
from helpers import submodule


class _Choices(list):
    def add(self):
        row = SimpleNamespace(assets=_Choices(), asset_index=0)
        self.append(row)
        return row


class FilmShotControlTests(unittest.TestCase):
    new_adapter = application_tests.FilmApplicationTests.new_adapter
    new_session = application_tests.FilmApplicationTests.new_session
    respond = application_tests.FilmApplicationTests.respond
    saved = application_tests.FilmApplicationTests.saved
    selections = application_tests.FilmApplicationTests.selections
    states = application_tests.FilmApplicationTests.states
    prepare = application_tests.FilmApplicationTests.prepare
    settle = application_tests.FilmApplicationTests.settle
    ready = application_tests.FilmApplicationTests.ready

    def setUp(self):
        application_tests.FilmApplicationTests.setUp(self)
        self.runtime = submodule("blender.runtime")
        self.ui = submodule("blender.film_scene_controls")
        self.tools = submodule("mcp.tools_scenario")
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

    def tearDown(self):
        application_tests.FilmApplicationTests.tearDown(self)

    def mcp_prepare(self):
        sources = self.tools.film_shot_sources(
            {"production_id": self.production, "shot_id": "shot"}
        )
        return self.tools.prepare_film_shot(
            {
                "context_id": sources["context_id"],
                "production_id": sources["production_id"],
                "shot_id": sources["shot_id"],
                "selections": {
                    hero["hero_id"]: {
                        "request_id": hero["request_id"],
                        "revision": hero["revision"],
                        "asset_id": hero["assets"][0]["asset_id"],
                    }
                    for hero in sources["heroes"]
                },
            }
        )["review_id"]

    def dialog(self):
        operator = SimpleNamespace(heroes=_Choices(), report=Mock())
        context = SimpleNamespace(scene=self.scene, window_manager=Mock())
        context.window_manager.invoke_props_dialog.return_value = {"RUNNING_MODAL"}
        self.assertEqual(
            self.ui.SCENARIO_OT_prepare_film_shot.invoke(operator, context, None),
            {"RUNNING_MODAL"},
        )
        return operator, context

    def test_mcp_preparation_native_build_consumes_same_handle(self):
        identifier = self.mcp_prepare()
        self.assertEqual(self.settle(identifier)["phase"], "READY")
        self.assertEqual(bpy.ops.scenario.build_film_shot(review_id=identifier), {"FINISHED"})
        status = self.tools.film_shot_review({"review_id": identifier})
        self.assertEqual(status["phase"], "BUILT")
        self.assertEqual(self.states(), [self.storage.JobState.APPLIED] * 2)
        self.assertEqual(bpy.context.scene, self.scene)
        before = self.builder._snapshot()
        self.assertEqual(bpy.ops.scenario.build_film_shot(review_id=identifier), {"CANCELLED"})
        self.assertEqual(self.builder._snapshot(), before)
        self.assertFalse(self.calls or self.downloads)

    def test_native_source_dialog_separates_verification_from_mcp_approval(self):
        operator, context = self.dialog()
        self.assertEqual(len(operator.heroes), 2)
        before = self.builder._snapshot()
        self.assertEqual(self.commands._reviews, {})
        self.assertEqual(
            self.ui.SCENARIO_OT_prepare_film_shot.execute(operator, context), {"FINISHED"}
        )
        identifier = self.commands.current(self.scene, "shot")["review_id"]
        review = self.commands._reviews[identifier]
        while review.phase == "VERIFYING":
            review.task.result(5)
            # Application-owned maintenance progresses without drawing a panel.
            self.runtime.sync_catalog_context()
        self.assertEqual(self.builder._snapshot(), before)
        self.assertEqual(self.tools.build_film_shot({"review_id": identifier})["phase"], "BUILT")
        self.assertFalse(self.calls or self.downloads)

    def test_cancelled_source_and_build_dialogs_do_not_claim_or_mutate(self):
        before = self.builder._snapshot()
        self.dialog()  # Do not execute: models were presented but not approved.
        self.assertEqual(self.commands._reviews, {})
        identifier = self.ready()
        operator = SimpleNamespace(review_id=identifier, report=Mock())
        context = SimpleNamespace(scene=self.scene, window_manager=Mock())
        self.ui.SCENARIO_OT_build_film_shot.invoke(operator, context, None)
        self.assertEqual(self.commands.status(identifier)["phase"], "READY")
        self.assertEqual(self.builder._snapshot(), before)
        self.assertEqual(self.states(), [self.storage.JobState.READY] * 2)

    def test_changed_source_dialog_destination_rejects_before_verification(self):
        operator, context = self.dialog()
        self.scene.frame_set(3)
        self.assertEqual(
            self.ui.SCENARIO_OT_prepare_film_shot.execute(operator, context), {"CANCELLED"}
        )
        self.assertEqual(self.commands._reviews, {})
        self.assertEqual(self.states(), [self.storage.JobState.READY] * 2)

    def test_mcp_rejects_wrong_production_and_context(self):
        with self.assertRaisesRegex(Exception, "production changed"):
            self.tools.film_shot_sources({"production_id": "wrong", "shot_id": "shot"})
        with self.assertRaisesRegex(Exception, "connection changed"):
            self.tools.prepare_film_shot(
                {
                    "production_id": self.production,
                    "context_id": "wrong",
                    "shot_id": "shot",
                    "selections": self.selections(),
                }
            )
        self.assertEqual(self.commands._reviews, {})

    def test_native_discard_is_visible_to_mcp_and_drains_verification(self):
        identifier = self.mcp_prepare()
        self.assertEqual(bpy.ops.scenario.discard_film_shot(review_id=identifier), {"FINISHED"})
        self.settle(identifier)
        self.assertEqual(
            self.tools.film_shot_review({"review_id": identifier})["phase"], "DISCARDED"
        )
        self.assertEqual(self.states(), [self.storage.JobState.READY] * 2)

    def test_mcp_and_native_dismissal_require_explicit_inspection(self):
        identifier = self.ready()
        with patch.object(
            self.session, "_claim_saved_application", side_effect=OSError("Before write")
        ):
            self.tools.build_film_shot({"review_id": identifier})
        with self.assertRaisesRegex(ValueError, "Confirm inspection"):
            self.tools.film_shot_review({"review_id": identifier, "action": "dismiss_uncertain"})
        self.assertEqual(bpy.ops.scenario.dismiss_film_shot(review_id=identifier), {"CANCELLED"})
        self.assertEqual(
            bpy.ops.scenario.dismiss_film_shot(review_id=identifier, inspected=True), {"FINISHED"}
        )
        self.assertEqual(
            self.tools.film_shot_review({"review_id": identifier})["phase"], "DISCARDED"
        )
        identifier = self.ready()
        with patch.object(
            self.session, "_claim_saved_application", side_effect=OSError("Before write")
        ):
            self.tools.build_film_shot({"review_id": identifier})
        self.assertEqual(
            self.tools.film_shot_review(
                {
                    "review_id": identifier,
                    "action": "dismiss_uncertain",
                    "inspected": True,
                }
            )["phase"],
            "DISCARDED",
        )
        self.assertEqual(self.states(), [self.storage.JobState.READY] * 2)

    def test_native_receipt_recovery_never_calls_builder_again(self):
        identifier = self.ready()
        original = self.store.transition
        failed = []

        def lost(*args, **kwargs):
            saved = original(*args, **kwargs)
            if kwargs.get("state") == self.storage.JobState.APPLIED and not failed:
                failed.append(True)
                raise OSError("Lost outcome acknowledgement")
            return saved

        with patch.object(self.store, "transition", side_effect=lost):
            result = self.tools.build_film_shot({"review_id": identifier})
        self.assertTrue(result["receipt_retry_available"])
        self.assertEqual(
            bpy.ops.scenario.dismiss_film_shot(review_id=identifier, inspected=True), {"CANCELLED"}
        )
        before = self.builder._snapshot()
        with patch.object(self.builder, "build_shot", side_effect=AssertionError("No rebuild")):
            self.assertEqual(
                bpy.ops.scenario.save_film_shot_receipt(review_id=identifier), {"FINISHED"}
            )
        self.assertEqual(self.commands.status(identifier)["phase"], "BUILT")
        self.assertEqual(self.builder._snapshot(), before)
        self.assertEqual(self.states(), [self.storage.JobState.APPLIED] * 2)

    def test_recipe_and_production_changes_keep_uncertain_recovery_visible(self):
        identifier = self.ready()
        selections = self.selections()
        with patch.object(
            self.session, "_claim_saved_application", side_effect=OSError("Before write")
        ):
            self.commands.approve(identifier)
        raw = copy.deepcopy(self.raw)
        raw["title"] = "Changed recipe"
        self.film.load_recipe(self.scene, raw)
        for production in (self.production, "new-production"):
            with self.subTest(production=production):
                self.scene.scenario_film.production_id = production
                status = self.commands.current(self.scene, "shot")
                self.assertEqual((status["review_id"], status["phase"]), (identifier, "UNCERTAIN"))
                with self.assertRaisesRegex(RuntimeError, "review"):
                    self.commands.prepare(self.scene, shot_id="shot", selections=selections)
        self.commands.dismiss_uncertain(identifier, inspected=True)
        self.assertIsNone(self.commands.current(self.scene, "shot"))
        self.assertEqual(self.states(), [self.storage.JobState.READY] * 2)

    def test_missing_error_review_copies_the_displayed_fallback(self):
        layout = Mock()
        self.ui.SCENARIO_OT_film_shot_error.draw(
            SimpleNamespace(review_id="missing", layout=layout), bpy.context
        )
        layout.label.assert_called_once_with(text="This review is no longer available")
        self.assertEqual(layout.operator.return_value.text, "This review is no longer available")

    def test_shot_list_persists_and_reload_preserves_selection_by_id(self):
        raw = copy.deepcopy(self.raw)
        raw["shots"].append({**raw["shots"][0], "id": "other", "title": "Other"})
        self.film.load_recipe(self.scene, raw)
        self.scene.scenario_film.shot_index = 1
        raw["shots"].reverse()
        self.film.load_recipe(self.scene, raw)
        self.assertEqual(self.ui.selected(self.scene), "other")
        self.assertEqual(self.scene.scenario_film.shot_index, 0)
        path = self.root / "film-shots.blend"
        bpy.data.libraries.write(str(path), {self.scene})
        with bpy.data.libraries.load(str(path), link=False) as (source, target):
            target.scenes = source.scenes
        saved = target.scenes[0]
        self.assertEqual(self.ui.selected(saved), "other")
        self.assertEqual([row.title for row in saved.scenario_film.shots], ["Other", "Shot"])
        self.assertEqual(self.tools.film_recipe({})["shots"][0]["shot_id"], "other")

    def test_panel_draw_only_reads_cached_status(self):
        self.ready()
        layout = Mock()
        with (
            patch.object(
                self.runtime, "ensure_film_jobs", side_effect=AssertionError("Draw activation")
            ),
            patch.object(self.store, "get", side_effect=AssertionError("Draw storage read")),
            patch.object(self.commands, "poll", side_effect=AssertionError("Draw polling")),
        ):
            self.ui.SCENARIO_PT_film_shots.draw(SimpleNamespace(layout=layout), bpy.context)
        box = layout.box.return_value
        self.assertIn(
            "scenario.build_film_shot", [call.args[0] for call in box.operator.call_args_list]
        )

    def test_changed_connection_hides_cached_review_during_draw(self):
        self.ready()
        self.runtime.state.catalog_credentials = ("other", "credentials")
        self.assertIsNone(self.ui.commands(create=False))

    def test_no_hero_shot_still_requires_explicit_build(self):
        raw = copy.deepcopy(self.raw)
        raw["shots"][0]["actors"] = []
        self.film.load_recipe(self.scene, raw)
        identifier = self.mcp_prepare()
        self.assertEqual(self.commands.status(identifier)["phase"], "READY")
        self.assertEqual(self.tools.build_film_shot({"review_id": identifier})["phase"], "BUILT")
        self.assertEqual(self.states(), [self.storage.JobState.READY] * 2)
        self.assertFalse(self.calls or self.downloads)
