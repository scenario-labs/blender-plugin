# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Native and MCP Film actions share scoped exact quotes and durable recovery."""

import copy
import os
import unittest
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import bpy
import test_model_generation as model_tests
from helpers import online_access, submodule


class FilmControlsTests(unittest.TestCase):
    cleanup_jobs = model_tests.ModelGenerationTests.cleanup_jobs
    result_fixture = model_tests.ModelGenerationTests.result_fixture
    settle = model_tests.ModelGenerationTests.settle
    deliver_results = model_tests.ModelGenerationTests.deliver_results

    def setUp(self):
        model_tests.ModelGenerationTests.setUp(self)
        self.film = submodule("blender.film_jobs")
        self.scene = bpy.context.scene
        self.recipe = {
            "title": "Film control fixture",
            "shots": [
                {
                    "id": "shot",
                    "title": "Shot",
                    "duration": 4,
                    "scene": submodule("core.scene.film_scene_plan").local_plan("studio", "", 4),
                }
            ],
            "tasks": [
                {"id": "source", "title": "Reference", "kind": "upload"},
                {
                    "id": "take",
                    "title": "First take",
                    "kind": "model",
                    "model": self.model["id"],
                    "parameters": {"prompt": "a teapot"},
                },
            ],
        }
        self.tools.film_recipe({"action": "load", "recipe": self.recipe})
        self.scene.scenario_film.task_index = 1
        self.production = self.scene.scenario_film.production_id

    def owner(self):
        return self.runtime.ensure_film_jobs()

    def quote(self):
        self.assertEqual(bpy.ops.scenario.quote_film(), {"FINISHED"})
        item = self.owner().current(self.scene, "take")
        item.task.result(5)
        self.owner().finish(item, self.scene)
        self.assertEqual(item.phase, "READY", item.error)
        return item

    def estimate(self):
        result = self.tools.estimate_film_task(
            {"production_id": self.production, "task_id": "take"}
        )
        return result.finish(result.run())

    def approve(self, item):
        return self.tools.approve_film_task(
            {"quote_id": item.identifier, "approved_cost": item.cost}
        )

    def drawn_operators(self):
        layout = MagicMock()
        panel = submodule("blender.film").SCENARIO_PT_film
        panel.draw(type("Panel", (), {"layout": layout})(), bpy.context)
        return [
            call.args[0]
            for call in layout.mock_calls
            if call[0] == "operator" or call[0].endswith(".operator")
        ]

    def interrupted_estimate(self):
        owner = self.owner()
        deferred = self.tools.estimate_film_task(
            {"production_id": self.production, "task_id": "take"}
        )
        completed = deferred.run()
        item = owner.current(self.scene, "take")
        other = bpy.data.scenes.new("Other current Film scene")
        try:
            self.film.load_recipe(other, self.recipe)
            # Even a copied production must not expose another scene's quote.
            other.scenario_film.production_id = self.production
            with bpy.context.temp_override(scene=other):
                with self.assertRaisesRegex(self.request_error, "context changed"):
                    deferred.finish(completed)
                inspection = self.tools.film_recipe({})
                self.assertNotIn("quote_id", inspection["tasks"][1])
                self.assertEqual(item.phase, "QUOTING")
        finally:
            bpy.data.scenes.remove(other)
        return item

    def test_inspection_recovers_interrupted_quote_for_discard_without_repricing(self):
        item = self.interrupted_estimate()
        calls = len(self.calls)
        inspection = self.tools.film_recipe({})
        row = inspection["tasks"][1]
        self.assertEqual(row["state"], "quoted")
        self.assertEqual(row["quote_id"], item.identifier)
        self.assertEqual(row["model_id"], self.model["id"])
        self.assertEqual(row["parameters"], {"prompt": "a teapot"})
        self.assertEqual(row["cu_cost_exact"], "0.1234567890123456789")
        self.assertEqual(self.tools.film_recipe({}), inspection)
        self.assertEqual(len(self.calls), calls)
        self.assertEqual(self.store.records(), ())
        self.tools.discard_film_estimate({"quote_id": row["quote_id"]})
        self.assertNotIn("quote_id", self.tools.film_recipe({})["tasks"][1])
        self.assertNotEqual(self.estimate()["quote_id"], item.identifier)
        self.assertEqual(self.paid, [])

    def test_inspection_recovers_interrupted_quote_for_one_exact_approval(self):
        self.interrupted_estimate()
        row = self.tools.film_recipe({})["tasks"][1]
        args = {"quote_id": row["quote_id"], "approved_cost": row["cu_cost_exact"]}
        self.tools.approve_film_task(args)
        self.settle()
        with self.assertRaises(self.request_error):
            self.tools.approve_film_task(args)
        self.assertNotIn("quote_id", self.tools.film_recipe({})["tasks"][1])
        self.assertEqual(len(self.paid), 1)

    def test_inspection_never_exposes_an_interrupted_quote_after_origin_change(self):
        self.interrupted_estimate()
        self.scene.frame_set(self.scene.frame_current + 1)
        calls = len(self.calls)
        row = self.tools.film_recipe({})["tasks"][1]
        self.assertEqual(row["state"], "unstarted")
        self.assertNotIn("quote_id", row)
        self.assertEqual(len(self.calls), calls)
        self.assertEqual(self.store.records(), ())
        self.assertEqual(self.paid, [])

    def test_native_quote_mcp_approval_downloads_without_automatic_application(self):
        self.result_fixture()
        before = set(bpy.data.images)
        item = self.quote()
        self.assertEqual(item.cost, "0.1234567890123456789")
        self.assertEqual(self.paid, [])
        submitted = self.approve(item)
        self.deliver_results()
        saved = self.store.get(submitted["request_id"])
        self.assertEqual(saved.state, self.storemod.JobState.READY)
        self.assertEqual(saved.intent.film_task.production_id, self.production)
        self.assertEqual(saved.intent.film_task.task_id, "take")
        self.assertEqual(len(self.paid), 1)
        self.assertEqual(len(self.downloads), 1)
        self.assertEqual(set(bpy.data.images), before)
        with self.assertRaises(self.request_error):
            self.approve(item)
        inspection = self.tools.film_recipe({})
        self.assertEqual(inspection["tasks"][1]["request_id"], submitted["request_id"])

    def test_mcp_quote_native_approval_uses_same_handle_and_exact_cost(self):
        quote = self.estimate()
        self.assertEqual(quote["parameters"], {"prompt": "a teapot"})
        self.assertEqual(
            bpy.ops.scenario.approve_film(
                quote_id=quote["quote_id"], approved_cost=quote["cu_cost_exact"]
            ),
            {"FINISHED"},
        )
        self.settle()
        self.assertEqual(len(self.paid), 1)
        self.assertEqual(
            bpy.ops.scenario.approve_film(
                quote_id=quote["quote_id"], approved_cost=quote["cu_cost_exact"]
            ),
            {"CANCELLED"},
        )
        self.assertIs(self.owner().models, self.runtime.state.model_jobs)

    def test_film_and_generic_results_cannot_reload_into_an_unrelated_form(self):
        self.result_fixture()
        submitted = self.approve(self.quote())
        self.deliver_results()
        view = self.owner().models.views[submitted["request_id"]]
        self.runtime.show_job_views((view,))
        records = submodule("core.jobs.records")
        generic = records.JobRecord.new(
            lane="model", kind="model", model_id="fixture-video", body={"prompt": "a take"}
        )
        generic.status = "success"
        self.runtime.state.jobs_view.append(generic)
        self.scene.scenario.lane = "video"
        image = self.scene.scenario.lane_state("image")
        image.prompt = "Keep my image form"
        image.model_key = "keep-image-model"
        before = (image.model_id, image.model_key, image.prompt)
        panels = submodule("blender.panels")
        for record in (view, generic):
            with self.subTest(kind=record.kind):
                layout = MagicMock()
                panels.draw_result(layout, record)
                operators = [
                    call.args[0]
                    for call in layout.mock_calls
                    if call[0] == "operator" or call[0].endswith(".operator")
                ]
                self.assertNotIn("scenario.reload_generation", operators)
                self.assertIn("scenario.result_details", operators)
                self.assertEqual(
                    bpy.ops.scenario.reload_generation(local_id=record.local_id),
                    {"CANCELLED"},
                )
                self.assertEqual(self.scene.scenario.lane, "video")
                self.assertEqual((image.model_id, image.model_key, image.prompt), before)
        self.assertEqual(len(self.paid), 1)

    def test_result_reload_retains_explicit_generation_lane_and_kind_fallback(self):
        records = submodule("core.jobs.records")
        panels = submodule("blender.panels")
        for lane, kind, expected in (("edit3d", "3d", "edit3d"), ("model", "video", "video")):
            with self.subTest(lane=lane, kind=kind):
                record = records.JobRecord.new(lane=lane, kind=kind, model_id="fixture", body={})
                self.assertEqual(self.generation.reload_lane(record), expected)
                layout = MagicMock()
                panels.draw_result(layout, record)
                self.assertTrue(
                    any(
                        call.args and call.args[0] == "scenario.reload_generation"
                        for call in layout.mock_calls
                    )
                )

    def test_automated_gui_probe_cannot_approve_through_native_or_mcp(self):
        item = self.quote()
        with patch.dict(os.environ, {"SCENARIO_GUI_PROBE": "1"}):
            with self.assertRaises(PermissionError):
                self.approve(item)
            self.assertEqual(
                bpy.ops.scenario.approve_film(quote_id=item.identifier, approved_cost=item.cost),
                {"CANCELLED"},
            )
        self.assertEqual(item.phase, "READY")
        self.assertEqual(self.paid, [])
        self.assertEqual(self.store.records(), ())

    def test_changed_exact_price_rejected_without_consuming_valid_approval(self):
        item = self.quote()
        with self.assertRaisesRegex(Exception, "exact Film price"):
            self.owner().approve(item.identifier, self.scene, approved_cost="0.123")
        self.assertEqual(item.phase, "READY")
        self.assertEqual(self.paid, [])

    def test_ready_quote_is_discarded_after_frame_or_dependency_revision_changes(self):
        owner = self.owner()
        for change in ("frame", "dependency"):
            with self.subTest(change=change):
                item = self.quote()
                if change == "frame":
                    self.scene.frame_set(self.scene.frame_current + 1)
                else:
                    owner.session.invalidate_scene(self.scene)
                calls = len(self.calls)
                owner.poll()
                self.assertEqual(item.phase, "DISCARDED")
                self.assertIsNone(item.quote)
                self.assertNotIn("scenario.approve_film", self.drawn_operators())
                self.assertIn("scenario.quote_film", self.drawn_operators())
                self.assertEqual(len(self.calls), calls)
                self.assertEqual(self.store.records(), ())
                self.assertEqual(self.paid, [])

    def test_approval_discards_changed_origin_before_persistence_without_waiting_for_pump(self):
        item = self.quote()
        self.scene.frame_set(self.scene.frame_current + 1)
        with patch.object(
            self.owner().session, "prepare_quote", side_effect=AssertionError("No stale write")
        ) as prepare:
            with self.assertRaisesRegex(Exception, "fresh Film estimate"):
                self.approve(item)
            prepare.assert_not_called()
        self.assertEqual(item.phase, "DISCARDED")
        self.assertEqual(item.error, "")
        self.assertEqual(self.store.records(), ())
        self.assertEqual(self.paid, [])

    def test_ready_quote_waits_through_another_current_scene_without_revision_change(self):
        other = bpy.data.scenes.new("Temporary current Film scene")
        try:
            item = self.quote()
            with bpy.context.temp_override(scene=other):
                self.owner().poll()
                self.assertEqual(item.phase, "READY")
                self.assertIsNotNone(item.quote)
            self.approve(item)
            self.settle()
            self.assertEqual(len(self.paid), 1)
        finally:
            bpy.data.scenes.remove(other)

    def test_submitted_task_keeps_saved_status_when_another_estimate_is_requested(self):
        item = self.quote()
        self.approve(item)
        self.settle()
        self.assertEqual(item.phase, "SUBMITTED")
        operators = self.drawn_operators()
        self.assertNotIn("scenario.quote_film", operators)
        self.assertNotIn("scenario.approve_film", operators)
        self.assertIn("scenario.inspect_saved_jobs", operators)
        owner = self.owner()
        count = len(owner.actions)
        # The submitted job can still poll; only a new quote must be blocked.
        with patch.object(
            owner.session, "quote_film_task", wraps=owner.session.quote_film_task
        ) as quote:
            with self.assertRaisesRegex(Exception, "already has saved work"):
                self.estimate()
            quote.assert_not_called()
        self.assertIs(self.owner().current(self.scene, "take"), item)
        self.assertEqual(item.phase, "SUBMITTED")
        self.assertEqual(item.error, "")
        self.assertEqual(len(self.owner().actions), count)
        self.assertEqual(len(self.paid), 1)

    def test_reloading_recipe_preserves_identity_but_rejects_changed_quote(self):
        item = self.quote()
        changed = copy.deepcopy(self.recipe)
        changed["tasks"][1]["parameters"]["prompt"] = "another teapot"
        self.tools.film_recipe({"action": "load", "recipe": changed})
        self.assertEqual(self.scene.scenario_film.production_id, self.production)
        with self.assertRaisesRegex(self.request_error, "fresh Film estimate"):
            self.approve(item)
        self.assertEqual(self.paid, [])

    def test_stale_native_approval_reports_a_preflight_rejection(self):
        item = self.quote()
        self.scene.frame_set(self.scene.frame_current + 1)
        operator = SimpleNamespace(
            quote_id=item.identifier, approved_cost=item.cost, report=MagicMock()
        )
        self.assertEqual(
            submodule("blender.film").SCENARIO_OT_approve_film.execute(operator, bpy.context),
            {"CANCELLED"},
        )
        operator.report.assert_called_once_with(
            {"WARNING"}, "The estimate changed or is unavailable; review the task again"
        )
        self.assertEqual(self.store.records(), ())
        self.assertFalse(self.paid)

    def test_submitted_status_survives_action_eviction_without_storage_reads_during_draw(self):
        raw = copy.deepcopy(self.recipe)
        raw["tasks"].append({**raw["tasks"][1], "id": "next"})
        self.film.load_recipe(self.scene, raw)
        item = self.quote()
        self.approve(item)
        self.settle()
        owner = self.owner()
        for index in range(127):
            filler = replace(
                item, identifier=f"expired-{index}", phase="DISCARDED", task_id="expired"
            )
            owner.actions[filler.identifier] = filler
        next_action = owner.quote(self.scene, "next")
        next_action.task.result(5)
        owner.finish(next_action, self.scene)
        self.assertNotIn(item.identifier, owner.actions)
        self.assertEqual(len(owner.actions), 128)
        with patch.object(self.store, "film_job", side_effect=AssertionError("No draw I/O")):
            saved = owner.current(self.scene, "take")
            self.assertEqual((saved.phase, saved.request_id), ("SUBMITTED", item.request_id))
            self.assertIsNone(saved.task)
            self.assertIsNone(saved.quote)
            self.assertNotIn("scenario.quote_film", self.drawn_operators())
        with self.assertRaisesRegex(Exception, "already has saved work"):
            owner.quote(self.scene, "take")
        self.assertEqual(len(self.paid), 1)

    def test_bound_status_cache_is_scene_local_and_retires_changed_recipes(self):
        item = self.quote()
        owner = self.owner()
        item.phase, item.request_id = "BOUND", "saved-upload"
        owner._retain_saved_status(item)
        del owner.actions[item.identifier]
        self.assertEqual(owner.current(self.scene, "take").phase, "BOUND")
        other = bpy.data.scenes.new("Other Film status scene")
        try:
            self.film.load_recipe(other, self.recipe)
            self.assertIsNone(owner.current(other, "take"))
        finally:
            bpy.data.scenes.remove(other)
        changed = copy.deepcopy(self.recipe)
        changed["title"] = "Edited recipe"
        self.film.load_recipe(self.scene, changed)
        owner._retain_saved_status(replace(item, phase="DISCARDED"))
        self.assertEqual(owner._saved_actions, {})

    def test_observed_recipe_change_discards_old_approval_even_if_reverted(self):
        item = self.quote()
        changed = copy.deepcopy(self.recipe)
        changed["title"] = "Edited title"
        self.film.load_recipe(self.scene, changed)
        self.owner().poll()
        self.assertEqual(item.phase, "DISCARDED")
        self.assertIsNone(item.quote)
        self.film.load_recipe(self.scene, self.recipe)
        with self.assertRaisesRegex(Exception, "fresh Film estimate"):
            self.approve(item)
        self.assertNotEqual(self.quote().identifier, item.identifier)
        self.assertEqual(self.paid, [])

    def test_changed_production_requires_new_quote(self):
        item = self.quote()
        self.tools.film_recipe({"action": "new_production"})
        self.assertNotEqual(self.scene.scenario_film.production_id, self.production)
        with self.assertRaisesRegex(self.request_error, "fresh Film estimate"):
            self.approve(item)
        with self.assertRaisesRegex(Exception, "production changed"):
            self.estimate()
        self.assertEqual(self.paid, [])

    def test_changed_scene_and_retired_credentials_reject_approval(self):
        item = self.quote()
        second = bpy.data.scenes.new("Other Film scene")
        try:
            with self.assertRaisesRegex(Exception, "changed"):
                self.owner().approve(item.identifier, second, approved_cost=item.cost)
        finally:
            bpy.data.scenes.remove(second)
        previous = self.owner()
        self.runtime.state.reset()
        with self.assertRaisesRegex(Exception, "changed"):
            previous.approve(item.identifier, self.scene, approved_cost=item.cost)
        with self.assertRaisesRegex(Exception, "fresh Film estimate"):
            self.approve(item)
        self.assertEqual(self.paid, [])

    def test_discard_releases_quote_and_repricing_cannot_use_old_handle(self):
        item = self.quote()
        with self.assertRaisesRegex(Exception, "discard"):
            self.owner().quote(self.scene, "take")
        self.tools.discard_film_estimate({"quote_id": item.identifier})
        with self.assertRaisesRegex(Exception, "fresh Film estimate"):
            self.approve(item)
        replacement = self.quote()
        self.assertNotEqual(replacement.identifier, item.identifier)
        self.assertEqual(self.paid, [])

    def test_uncertain_submission_reopens_for_inspection_without_repeat(self):
        self.lose_response = True
        item = self.quote()
        submitted = self.approve(item)
        self.settle()
        self.assertEqual(
            self.store.get(submitted["request_id"]).state, self.storemod.JobState.UNCERTAIN
        )
        self.runtime.state.reset()
        calls = len(self.calls)
        inspection = self.tools.film_recipe({})
        self.assertEqual(len(self.calls), calls)
        self.assertEqual(inspection["tasks"][1]["state"], "uncertain")
        action = self.owner().quote(self.scene, "take")
        with self.assertRaises(self.storemod.StoreConflict):
            action.task.result(5)
        self.owner().poll()
        self.assertEqual(action.phase, "ERROR")
        self.assertEqual(len(self.paid), 1)
        self.assertEqual(len(self.calls), calls)

    def test_lost_persistence_acknowledgement_consumes_approval(self):
        item = self.quote()
        original = self.owner().session.prepare_quote

        def fail_after_write(quote):
            original(quote)
            raise OSError("Synthetic lost acknowledgement")

        with patch.object(self.owner().session, "prepare_quote", side_effect=fail_after_write):
            with self.assertRaises(OSError):
                self.approve(item)
        with self.assertRaisesRegex(Exception, "fresh Film estimate"):
            self.approve(item)
        self.assertEqual(len(self.store.records()), 1)
        self.assertEqual(self.paid, [])

    def test_stale_completion_does_not_replace_current_recipe(self):
        item = self.owner().quote(self.scene, "take")
        item.task.result(5)
        changed = copy.deepcopy(self.recipe)
        changed["title"] = "Changed production title"
        self.film.load_recipe(self.scene, changed)
        self.owner().poll()
        self.assertEqual(item.phase, "ERROR")
        self.assertEqual(self.scene.scenario_film.title, "Changed production title")
        self.assertEqual(self.paid, [])

    def test_invalid_recipe_does_not_mutate_saved_scene(self):
        before = self.film.snapshot(self.scene)
        with self.assertRaises(ValueError):
            self.tools.film_recipe({"action": "load", "recipe": {"title": "invalid"}})
        self.assertEqual(self.film.snapshot(self.scene), before)
        self.assertEqual(len(self.scene.scenario_film.tasks), 2)

    def test_offline_read_allowed_but_price_and_approval_blocked(self):
        item = self.quote()
        with online_access(False):
            self.assertEqual(self.tools.film_recipe({})["production_id"], self.production)
            with self.assertRaisesRegex(Exception, "online"):
                self.approve(item)
        self.assertEqual(self.paid, [])

    def test_scene_storage_preserves_recipe_task_selection_and_identity(self):
        # Load the saved scene as a separate datablock, without replacing the running test file.
        path = self.runtime.paths().state_dir / "film.blend"
        bpy.data.libraries.write(str(path), {self.scene})
        with bpy.data.libraries.load(str(path), link=False) as (source, target):
            target.scenes = source.scenes
        loaded = target.scenes[0]
        try:
            self.assertEqual(self.film.snapshot(loaded), self.film.snapshot(self.scene))
            self.assertEqual(loaded.scenario_film.task_index, 1)
            self.assertEqual(loaded.scenario_film.tasks[1].name, "take")
        finally:
            bpy.data.scenes.remove(loaded)

    def imported_upload(self, request_id="film-upload", asset_id="source-asset"):
        owner = self.owner()
        uploads = submodule("core.jobs.upload_store")
        store = owner.session._coordinator._uploads._store
        saved = store.create(
            uploads.UploadIntent(
                request_id,
                store.scope,
                owner.session.capture(self.scene),
                "image",
                "source.png",
                "image/png",
                4,
                "a" * 64,
                4,
                ("a" * 64,),
            )
        )
        for state, values in [
            (uploads.UploadState.INITIALIZING, {}),
            (uploads.UploadState.UPLOADING, {"upload_id": "remote-upload"}),
            (uploads.UploadState.IMPORTED, {"asset_id": asset_id}),
        ]:
            saved = store.transition(
                request_id, expected_revision=saved.revision, state=state, **values
            )
        return saved

    def test_imported_upload_binding_is_local_and_feeds_price(self):
        owner = self.owner()
        saved = self.imported_upload()
        info = self.tools.list_reference_uploads({})
        args = dict(
            production_id=self.production,
            task_id="source",
            context_id=info["context_id"],
            request_id="film-upload",
            expected_revision=saved.revision,
        )
        with self.assertRaisesRegex(Exception, "context changed"):
            self.tools.bind_film_upload(dict(args, context_id="stale"))
        deferred = self.tools.bind_film_upload(args)
        result = deferred.run()
        other = bpy.data.scenes.new("Other upload timer context")
        try:
            with bpy.context.temp_override(scene=other):
                owner.poll()
                self.assertEqual(owner.current(self.scene, "source").phase, "BINDING")
                self.assertEqual(owner.session._pending, [])
            self.assertEqual(deferred.finish(result)["state"], "bound")
        finally:
            bpy.data.scenes.remove(other)
        self.scene.scenario_film.task_index = 0
        self.assertNotIn("scenario.bind_film_upload", self.drawn_operators())
        self.assertNotIn("scenario.quote_film", self.drawn_operators())
        # Explicit MCP retries still revalidate and return the same saved association.
        repeated = self.tools.bind_film_upload(args)
        self.assertEqual(repeated.finish(repeated.run())["state"], "bound")
        self.assertEqual(owner.current(self.scene, "source").phase, "BOUND")
        self.assertEqual(self.calls, [])
        changed = copy.deepcopy(self.recipe)
        changed["tasks"][1]["parameters"]["prompt"] = "$source"
        self.film.load_recipe(self.scene, changed)
        self.assertEqual(self.estimate()["parameters"], {"prompt": "source-asset"})
        self.assertEqual(self.paid, [])

    def test_conflicting_upload_retry_preserves_bound_status_without_starting_work(self):
        owner = self.owner()
        saved = self.imported_upload()
        other = self.imported_upload("other-upload", "other-asset")
        args = dict(
            production_id=self.production,
            task_id="source",
            context_id=self.runtime.state.job_context_id,
            request_id=saved.intent.request_id,
            expected_revision=saved.revision,
        )
        deferred = self.tools.bind_film_upload(args)
        deferred.finish(deferred.run())
        item = owner.current(self.scene, "source")
        reference = self.store.film_upload(self.production, "source")
        self.scene.scenario_film.task_index = 0
        for evicted in (False, True):
            with self.subTest(evicted=evicted):
                if evicted:
                    owner._retain_saved_status(item)
                    del owner.actions[item.identifier]
                count = len(owner.actions)
                for changes in (
                    {"request_id": other.intent.request_id},
                    {"expected_revision": saved.revision + 1},
                ):
                    with self.subTest(changes=changes):
                        with patch.object(
                            owner.session,
                            "bind_film_upload",
                            side_effect=AssertionError("No new work"),
                        ) as bind:
                            with self.assertRaisesRegex(self.request_error, "already bound"):
                                self.tools.bind_film_upload(dict(args, **changes))
                            bind.assert_not_called()
                        self.assertEqual(len(owner.actions), count)
                        current = owner.current(self.scene, "source")
                        self.assertEqual(
                            (current.phase, current.request_id), ("BOUND", "film-upload")
                        )
                        self.assertEqual(current.error, "")
                        self.assertNotIn("scenario.bind_film_upload", self.drawn_operators())
                        self.assertEqual(
                            self.store.film_upload(self.production, "source"), reference
                        )
        self.assertEqual(self.calls, [])
        self.assertEqual(self.paid, [])

    def test_interrupted_upload_association_is_inspectable_and_retryable(self):
        saved = self.imported_upload()
        args = dict(
            production_id=self.production,
            task_id="source",
            context_id=self.runtime.state.job_context_id,
            request_id=saved.intent.request_id,
            expected_revision=saved.revision,
        )
        deferred = self.tools.bind_film_upload(args)
        completed = deferred.run()
        other = bpy.data.scenes.new("Other current upload scene")
        try:
            with bpy.context.temp_override(scene=other):
                with self.assertRaisesRegex(self.request_error, "context changed"):
                    deferred.finish(completed)
                self.owner().poll()
                self.assertEqual(self.owner().current(self.scene, "source").phase, "BINDING")
        finally:
            bpy.data.scenes.remove(other)
        reference = self.store.film_upload(self.production, "source")
        row = self.tools.film_recipe({})["tasks"][0]
        self.assertEqual(row["state"], "bound")
        self.assertEqual(row["upload_request_id"], saved.intent.request_id)
        self.assertEqual(self.owner().current(self.scene, "source").phase, "BOUND")
        retry = self.tools.bind_film_upload(args)
        self.assertEqual(retry.finish(retry.run())["state"], "bound")
        self.assertEqual(self.store.film_upload(self.production, "source"), reference)
        self.assertEqual(self.calls, [])
        self.assertEqual(self.paid, [])

    def test_deleted_scene_does_not_break_lookup_or_panel_drawing(self):
        from unittest.mock import MagicMock

        owner = self.owner()
        item = self.quote()
        other = bpy.data.scenes.new("Surviving Film scene")
        bpy.context.window.scene = other
        self.film.load_recipe(other, self.recipe)
        bpy.data.scenes.remove(self.scene)
        self.assertIsNone(owner.current(other, "take"))
        panel = submodule("blender.film").SCENARIO_PT_film
        panel.draw(type("Panel", (), {"layout": MagicMock()})(), bpy.context)
        owner.poll()
        self.assertEqual(item.phase, "DISCARDED")
        self.assertEqual(self.paid, [])

    def test_finished_quote_waits_for_unchanged_origin_scene_before_delivery(self):
        other = bpy.data.scenes.new("Temporary current scene")
        owner = self.owner()
        item = owner.quote(self.scene, "take")
        item.task.result(5)
        calls = len(self.calls)
        try:
            # Timer context may name another scene without altering this origin.
            # Actual dependency revisions remain subject to the session guard.
            with bpy.context.temp_override(scene=other):
                owner.poll()
                self.assertEqual(item.phase, "QUOTING")
                self.assertIsNone(item.quote)
                self.assertFalse(any(task is item.task for task, _ in owner.session._pending))
                owner.session._completion_limit = 1
                owner.session._check_capacity()
            owner.poll()
            self.assertEqual(item.phase, "READY", item.error)
            self.assertEqual(item.cost, "0.1234567890123456789")
            self.assertEqual(len(self.calls), calls)
            self.approve(item)
            self.settle()
            self.assertEqual(len(self.paid), 1)
        finally:
            bpy.data.scenes.remove(other)

    def test_waiting_quote_still_rejects_a_changed_origin_revision(self):
        other = bpy.data.scenes.new("Temporary current scene")
        owner = self.owner()
        item = owner.quote(self.scene, "take")
        item.task.result(5)
        try:
            with bpy.context.temp_override(scene=other):
                owner.poll()
                self.assertEqual(item.phase, "QUOTING")
            self.scene.frame_set(self.scene.frame_current + 1)
            owner.poll()
            self.assertEqual(item.phase, "ERROR")
            with self.assertRaises(self.request_error):
                self.approve(item)
            self.assertEqual(self.paid, [])
        finally:
            bpy.data.scenes.remove(other)

    def test_deleted_pending_origin_drains_completion_without_delivery(self):
        owner = self.owner()
        item = owner.quote(self.scene, "take")
        item.task.result(5)
        other = bpy.data.scenes.new("Remaining scene")
        bpy.context.window.scene = other
        bpy.data.scenes.remove(self.scene)
        owner.poll()
        self.assertEqual(item.phase, "ERROR")
        self.assertFalse(any(task is item.task for task, _ in owner.session._pending))
        self.assertIsNone(owner.current(other, "take"))
        self.assertEqual(self.paid, [])

    def test_draw_does_not_load_storage_or_mutate_scene(self):
        from unittest.mock import MagicMock

        before = self.film.snapshot(self.scene)
        panel = submodule("blender.film").SCENARIO_PT_film
        with patch.object(
            self.runtime, "ensure_film_jobs", side_effect=AssertionError("draw owns no commands")
        ):
            panel.draw(type("Panel", (), {"layout": MagicMock()})(), bpy.context)
        self.assertEqual(self.film.snapshot(self.scene), before)
