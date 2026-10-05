# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Shared Film verification, multi-job claims and receipt-only recovery in Blender."""

import copy
import hashlib
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import bpy
import test_session_results as session_tests
from helpers import FIXTURES, submodule


class FilmApplicationTests(unittest.TestCase):
    new_adapter = session_tests.SessionResultTests.new_adapter
    new_session = session_tests.SessionResultTests.new_session
    respond = session_tests.SessionResultTests.respond

    def setUp(self):
        session_tests.SessionResultTests.setUp(self)
        self.builder = submodule("blender.film_scene")
        self.before = self.builder._snapshot()
        self.film = submodule("blender.film_jobs")
        self.source_contract = submodule("core.jobs.film_tasks")
        self.raw = {
            "title": "Application fixture",
            "fps": 30,
            "heroes": {
                f"hero{i}": {
                    "name": f"Hero {i}",
                    "description": "Fixture",
                    "mesh": f"mesh{i}",
                    "reference": "reference",
                }
                for i in range(2)
            },
            "tasks": [
                {
                    "id": f"mesh{i}",
                    "title": f"Mesh {i}",
                    "kind": "model",
                    "model": "fixture-model",
                    "parameters": {"prompt": "fixture"},
                }
                for i in range(2)
            ],
            "shots": [
                {
                    "id": "shot",
                    "title": "Shot",
                    "duration": 4,
                    "scene": submodule("core.scene.film_scene_plan").local_plan("studio", "", 4),
                    "actors": [
                        {"hero": f"hero{i}", "name": f"Actor {i}", "location": [3 * i, 0, 0]}
                        for i in range(2)
                    ],
                }
            ],
        }
        self.film.load_recipe(self.scene, self.raw)
        bpy.context.view_layer.update()
        self.production = self.scene.scenario_film.production_id
        self.commands = self.session.film_shots
        self.paths = {}
        self.rows = [self.saved(i) for i in range(2)]

    def tearDown(self):
        bpy.context.window.scene = self.scene
        self.builder._rollback(self.before)
        session_tests.SessionResultTests.tearDown(self)

    def saved(self, index):
        request_id, task_id = f"hero-request{index}", f"mesh{index}"
        binding, *_ = self.source_contract._task_context(
            self.store, self.raw, production_id=self.production, task_id=task_id, kind="model"
        )
        row = self.store.create(
            self.storage.JobIntent(
                request_id,
                self.scope,
                self.session.capture(self.scene),
                "model",
                "fixture-model",
                "a" * 64,
                "b" * 64,
                "1",
                film_task=binding,
            )
        )
        for state in (
            self.storage.JobState.SUBMITTING,
            self.storage.JobState.REMOTE,
            self.storage.JobState.SUCCEEDED,
        ):
            row = self.store.transition(
                request_id,
                expected_revision=row.revision,
                state=state,
                remote_job_id=f"hero-remote{index}"
                if state == self.storage.JobState.REMOTE
                else None,
            )
        asset = self.storage.ResultAsset(f"hero-asset{index}", "hero.glb", "model/gltf-binary")
        row = self.store.set_results(request_id, (asset,), expected_revision=row.revision)
        row = self.store.transition(
            request_id, expected_revision=row.revision, state=self.storage.JobState.DOWNLOADING
        )
        data = (FIXTURES / "synthetic/static-triangle.glb").read_bytes()
        path = self.session._coordinator._results._directory(row) / asset.name
        path.write_bytes(data)
        receipt = self.transfers.DownloadedResult(
            asset.name, len(data), hashlib.sha256(data).hexdigest()
        )
        row = self.store.record_download(
            request_id, asset.asset_id, receipt, expected_revision=row.revision
        )
        self.paths[request_id] = path
        return self.store.transition(
            request_id, expected_revision=row.revision, state=self.storage.JobState.READY
        )

    def selections(self):
        return {
            item["hero_id"]: {
                "request_id": item["request_id"],
                "revision": item["revision"],
                "asset_id": item["assets"][0]["asset_id"],
            }
            for item in self.commands.inspect(self.scene, shot_id="shot")
        }

    def prepare(self):
        return self.commands.prepare(self.scene, shot_id="shot", selections=self.selections())[
            "review_id"
        ]

    def settle(self, identifier):
        for _ in range(50):
            review = self.commands._reviews[identifier]
            if review.task is not None:
                try:
                    review.task.result(5)
                except Exception:
                    pass
            self.commands.poll()
            status = self.commands.status(identifier)
            if status["phase"] != "VERIFYING":
                return status
        self.fail("Film verification did not settle")

    def ready(self):
        identifier = self.prepare()
        self.assertEqual(self.settle(identifier)["phase"], "READY")
        return identifier

    def states(self):
        return [self.store.get(row.intent.request_id).state for row in self.rows]

    def test_all_jobs_claimed_before_build_and_repeat_requires_new_local_claims(self):
        identifier = self.ready()
        before = self.builder._snapshot()
        original = self.builder.build_shot

        def checked(*args, **kwargs):
            self.assertEqual(self.states(), [self.storage.JobState.APPLYING] * 2)
            self.assertEqual(self.builder._snapshot(), before)
            return original(*args, **kwargs)

        with patch.object(self.builder, "build_shot", side_effect=checked):
            result = self.commands.approve(identifier)
        self.assertEqual(result["phase"], "BUILT", result)
        self.assertEqual(self.states(), [self.storage.JobState.APPLIED] * 2)
        self.assertEqual(bpy.context.scene, self.scene)
        self.assertEqual(self.calls, [])
        self.assertEqual(self.downloads, [])
        with self.assertRaisesRegex(ValueError, "fresh"):
            self.commands.approve(identifier)
        second = self.commands.approve(self.ready())
        self.assertEqual(second["phase"], "BUILT", second)
        self.assertNotEqual(second["scene"], result["scene"])
        for row in self.rows:
            saved = self.store.get(row.intent.request_id)
            self.assertEqual(len(saved.local_applications), 1)
            self.assertEqual(
                saved.local_applications[0].state, self.storage.LocalApplicationState.APPLIED
            )

    def test_no_hero_scene_is_local_single_use_without_job_changes(self):
        self.raw["shots"][0]["actors"] = []
        self.film.load_recipe(self.scene, self.raw)
        before = self.store.records()
        identifier = self.ready()
        self.assertEqual(self.commands.approve(identifier)["phase"], "BUILT")
        self.assertEqual(self.store.records(), before)
        self.assertEqual(self.calls, [])

    def test_two_heroes_using_one_result_share_one_claim(self):
        self.raw["heroes"]["hero1"]["mesh"] = "mesh0"
        self.film.load_recipe(self.scene, self.raw)
        identifier = self.ready()
        self.assertEqual(len(self.commands._reviews[identifier].completions), 1)
        result = self.commands.approve(identifier)
        self.assertEqual(result["phase"], "BUILT", result)
        self.assertEqual(
            self.states(), [self.storage.JobState.APPLIED, self.storage.JobState.READY]
        )
        self.assertEqual(len(self.commands._reviews[identifier].application.actors), 2)

    def test_restart_reuses_downloads_with_fresh_destination_review(self):
        old = self.ready()
        self.session.shutdown()
        self.session = self.new_session()
        self.commands = self.session.film_shots
        with self.assertRaises(ValueError):
            self.commands.approve(old)
        result = self.commands.approve(self.ready())
        self.assertEqual(result["phase"], "BUILT", result)
        self.assertEqual(self.calls, [])

    def test_changed_recipe_or_frame_rejects_without_claim(self):
        for change in ("recipe", "frame"):
            identifier = self.ready()
            if change == "recipe":
                edited = copy.deepcopy(self.raw)
                edited["title"] = "Changed"
                self.film.load_recipe(self.scene, edited)
            else:
                self.scene.frame_set(2)
            with self.assertRaises((ValueError, self.module.OriginUnavailable)):
                self.commands.approve(identifier)
            self.commands.poll()
            self.assertEqual(self.commands.status(identifier)["phase"], "ERROR")
            self.assertEqual(self.states(), [self.storage.JobState.READY] * 2)
            self.film.load_recipe(self.scene, self.raw)

    def test_retired_context_cannot_build(self):
        identifier = self.ready()
        before = self.builder._snapshot()
        self.session.deactivate()
        with self.assertRaisesRegex(RuntimeError, "connection"):
            self.commands.approve(identifier)
        self.assertEqual(self.builder._snapshot(), before)
        self.assertEqual(self.states(), [self.storage.JobState.READY] * 2)

    def test_transient_other_scene_context_defers_delivery_without_losing_review(self):
        identifier = self.prepare()
        review = self.commands._reviews[identifier]
        review.task.result(5)
        other = bpy.data.scenes.new("Other timer context")
        with bpy.context.temp_override(scene=other):
            self.commands.poll()
        self.assertEqual(review.phase, "VERIFYING")
        self.assertIsNotNone(review.task)
        self.assertEqual(self.settle(identifier)["phase"], "READY")
        self.assertEqual(self.commands.approve(identifier)["phase"], "BUILT")

    def test_deleted_recipe_scene_retires_review_without_using_same_name_replacement(self):
        other = bpy.data.scenes.new("Temporary Film recipe")
        bpy.context.window.scene = other
        self.film.load_recipe(other, self.raw)
        other.scenario_film.production_id = self.production
        selections = self.selections()
        identifier = self.commands.prepare(other, shot_id="shot", selections=selections)[
            "review_id"
        ]
        review = self.commands._reviews[identifier]
        review.task.result(5)
        bpy.context.window.scene = self.scene
        name = other.name
        bpy.data.scenes.remove(other)
        bpy.data.scenes.new(name)
        self.commands.poll()
        self.assertEqual(self.commands.status(identifier)["phase"], "ERROR")
        self.assertEqual(self.states(), [self.storage.JobState.READY] * 2)

    def test_discard_pending_verification_drains_without_claiming(self):
        identifier = self.prepare()
        self.commands.discard(identifier)
        self.settle(identifier)
        self.assertEqual(self.commands.status(identifier)["phase"], "DISCARDED")
        self.assertEqual(self.session._pending, [])
        self.assertEqual(self.states(), [self.storage.JobState.READY] * 2)

    def test_tampered_download_fails_before_native_build(self):
        next(iter(self.paths.values())).write_bytes(b"changed")
        identifier = self.prepare()
        self.assertEqual(self.settle(identifier)["phase"], "ERROR")
        self.assertEqual(self.states(), [self.storage.JobState.READY] * 2)

    def test_post_verification_tamper_does_not_claim(self):
        identifier = self.ready()
        next(iter(self.paths.values())).write_bytes(b"changed")
        with self.assertRaises(self.builder.model_application.ModelApplicationError):
            self.commands.approve(identifier)
        self.assertEqual(self.states(), [self.storage.JobState.READY] * 2)

    def test_changed_record_revision_rejects_old_approval(self):
        identifier = self.ready()
        row = self.rows[0]
        self.store.transition(
            row.intent.request_id,
            expected_revision=row.revision,
            state=self.storage.JobState.APPLYING,
        )
        with self.assertRaises(ValueError):
            self.commands.approve(identifier)
        self.assertEqual(self.states()[1], self.storage.JobState.READY)

    def test_failed_second_claim_never_builds_and_releases_known_first_claim(self):
        identifier = self.ready()
        original = self.session._claim_saved_application
        count = []

        def fail(*args):
            count.append(True)
            if len(count) == 2:
                original(*args)
                raise OSError("Lost durable claim acknowledgement")
            return original(*args)

        before = self.builder._snapshot()
        with patch.object(self.session, "_claim_saved_application", side_effect=fail):
            result = self.commands.approve(identifier)
        self.assertEqual(result["phase"], "UNCERTAIN")
        self.assertTrue(result["inspection_required"])
        self.assertEqual(self.builder._snapshot(), before)
        self.assertEqual(
            self.states(), [self.storage.JobState.APPLY_FAILED, self.storage.JobState.APPLYING]
        )
        with self.assertRaises(ValueError):
            self.commands.approve(identifier)

    def test_confirmed_native_rollback_fails_all_claims(self):
        identifier = self.ready()
        before = self.builder._snapshot()
        with patch.object(
            self.builder, "_lighting", side_effect=RuntimeError("Fixture build failure")
        ):
            result = self.commands.approve(identifier)
        self.assertEqual(result["phase"], "ERROR", result)
        self.assertEqual(self.builder._snapshot(), before)
        self.assertEqual(self.states(), [self.storage.JobState.APPLY_FAILED] * 2)

    def test_partial_native_mutation_leaves_uncertain_claims(self):
        identifier = self.ready()

        def incomplete(*args, **kwargs):
            bpy.data.worlds.new("Fixture incomplete cleanup")
            raise RuntimeError("Fixture unknown mutation")

        with patch.object(self.builder, "build_shot", side_effect=incomplete):
            result = self.commands.approve(identifier)
        self.assertEqual(result["phase"], "UNCERTAIN")
        self.assertTrue(result["inspection_required"])
        self.assertFalse(result["receipt_retry_available"])
        self.assertEqual(self.states(), [self.storage.JobState.APPLYING] * 2)

    def test_lost_success_acknowledgement_retries_only_receipt(self):
        identifier = self.ready()
        original = self.store.transition
        failed = []

        def lost(*args, **kwargs):
            result = original(*args, **kwargs)
            if kwargs.get("state") == self.storage.JobState.APPLIED and not failed:
                failed.append(True)
                raise OSError("Fixture lost success acknowledgement")
            return result

        with patch.object(self.store, "transition", side_effect=lost):
            result = self.commands.approve(identifier)
        self.assertEqual(result["phase"], "UNCERTAIN", result)
        self.assertTrue(result["receipt_retry_available"])
        self.assertFalse(result["inspection_required"])
        before = self.builder._snapshot()
        with patch.object(self.builder, "build_shot", side_effect=AssertionError("Do not rebuild")):
            recovered = self.commands.retry_receipts(identifier)
        self.assertEqual(recovered["phase"], "BUILT", recovered)
        self.assertEqual(self.builder._snapshot(), before)
        self.assertEqual(recovered["scene"], result["scene"])
        self.assertEqual(self.states(), [self.storage.JobState.APPLIED] * 2)

    def test_lost_failure_receipt_can_recover_without_building(self):
        identifier = self.ready()
        original = self.store.transition

        def reject(*args, **kwargs):
            if kwargs.get("state") == self.storage.JobState.APPLY_FAILED:
                raise OSError("Fixture failed receipt write")
            return original(*args, **kwargs)

        with (
            patch.object(self.store, "transition", side_effect=reject),
            patch.object(
                self.builder, "_lighting", side_effect=RuntimeError("Fixture build failure")
            ),
        ):
            result = self.commands.approve(identifier)
        self.assertEqual(result["phase"], "UNCERTAIN")
        self.assertEqual(self.states(), [self.storage.JobState.APPLYING] * 2)
        with patch.object(self.builder, "build_shot", side_effect=AssertionError("Do not rebuild")):
            recovered = self.commands.retry_receipts(identifier)
        self.assertEqual(recovered["phase"], "ERROR", recovered)
        self.assertEqual(self.states(), [self.storage.JobState.APPLY_FAILED] * 2)

    def test_full_queue_rejection_does_not_leave_a_stuck_review(self):
        with patch.object(
            self.session,
            "verify_results",
            side_effect=self.module.SessionBusy("Fixture full queue"),
        ):
            with self.assertRaises(self.module.SessionBusy):
                self.prepare()
        self.assertEqual(self.commands._reviews, {})
        self.assertEqual(self.commands.status(self.ready())["phase"], "READY")

    def test_worker_cannot_prepare_or_approve(self):
        identifier = self.ready()
        with ThreadPoolExecutor(max_workers=1) as pool:
            with self.assertRaisesRegex(RuntimeError, "main thread"):
                pool.submit(self.commands.approve, identifier).result()
        self.assertEqual(self.states(), [self.storage.JobState.READY] * 2)
