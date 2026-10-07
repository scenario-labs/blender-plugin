# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Installed worker copies, explicit native approval and receipt-only recovery."""

import hashlib
import json
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import bpy
import test_session_results as session_tests
from helpers import FIXTURES, submodule


class FilmReviewPreparationTests(unittest.TestCase):
    new_adapter = session_tests.SessionResultTests.new_adapter
    new_session = session_tests.SessionResultTests.new_session
    respond = session_tests.SessionResultTests.respond

    def setUp(self):
        session_tests.SessionResultTests.setUp(self)
        self.builder = submodule("blender.film_review")
        self.media = submodule("core.jobs.film_review_media")
        self.probe = submodule("core.jobs.media_probe")
        self.film = submodule("blender.film_jobs")
        self.before = self.builder._snapshot()
        self.review_root = self.root / "reviews"
        self.review_root.mkdir()
        self.enterContext(
            patch.object(bpy.utils, "extension_path_user", return_value=str(self.review_root))
        )
        self.raw = {
            "title": "Prepared cut",
            "fps": 24,
            "audio_tracks": [],
            "shots": [
                {
                    "id": "shot",
                    "title": "Shot",
                    "duration": 2,
                    "source_trim": 1,
                    "scene": submodule("core.scene.film_scene_plan").local_plan("studio", "", 2),
                }
            ],
            "tasks": [
                {
                    "id": "shot-video",
                    "title": "Video",
                    "kind": "model",
                    "model": "fixture-model",
                    "parameters": {"prompt": "fixture"},
                }
            ],
        }
        self.film.load_recipe(self.scene, self.raw)
        bpy.context.view_layer.update()
        self.production = self.scene.scenario_film.production_id
        self.origin = self.session.capture(self.scene)
        self.saved()
        self.enterContext(
            patch.object(self.probe, "probe_tool", return_value=self.root / "ffprobe")
        )

        def probe(command, *, stdout, **kwargs):
            self.assertIsNot(threading.current_thread(), threading.main_thread())
            path = Path(command[command.index("-i") + 1])
            self.assertEqual(path.read_bytes(), self.data)
            stdout.write_text(
                json.dumps(
                    {
                        "streams": [
                            {
                                "codec_type": "video",
                                "duration": "4",
                                "width": 32,
                                "height": 32,
                                "avg_frame_rate": "24/1",
                            },
                            {"codec_type": "audio", "duration": "4"},
                        ]
                    }
                )
            )

        self.enterContext(patch.object(self.probe, "_run", side_effect=probe))

    def saved(self):
        binding, *_ = submodule("core.jobs.film_tasks")._task_context(
            self.store, self.raw, production_id=self.production, task_id="shot-video", kind="model"
        )
        row = self.store.create(
            self.storage.JobIntent(
                "picture",
                self.scope,
                self.origin,
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
                "picture",
                expected_revision=row.revision,
                state=state,
                remote_job_id="picture-remote" if state == self.storage.JobState.REMOTE else None,
            )
        asset = self.storage.ResultAsset("picture-asset", "picture.mp4", "video/mp4")
        row = self.store.set_results("picture", (asset,), expected_revision=row.revision)
        row = self.store.transition(
            "picture", expected_revision=row.revision, state=self.storage.JobState.DOWNLOADING
        )
        self.data = (FIXTURES / "synthetic/film-four-seconds-audio.mp4").read_bytes()
        self.source = self.session._coordinator._results._directory(row) / asset.name
        self.source.write_bytes(self.data)
        receipt = self.transfers.DownloadedResult(
            asset.name, len(self.data), hashlib.sha256(self.data).hexdigest()
        )
        row = self.store.record_download(
            "picture", asset.asset_id, receipt, expected_revision=row.revision
        )
        self.store.transition(
            "picture", expected_revision=row.revision, state=self.storage.JobState.READY
        )

    def ready(self):
        bpy.context.view_layer.update()
        task = self.session.prepare_film_review(
            self.raw, production_id=self.production, origin=self.session.capture(self.scene)
        )
        prepared = task.result(5)
        (completion,) = self.session.drain(task=task)
        self.assertIsNone(completion.error)
        self.assertIs(completion.result, prepared)
        return completion

    def tearDown(self):
        bpy.context.window.scene = self.scene
        self.builder._rollback(self.before)
        session_tests.SessionResultTests.tearDown(self)

    def test_worker_copies_native_build_claims_and_reuses_without_recopying(self):
        completion = self.ready()
        prepared = completion.result
        before = self.film.snapshot(self.scene), self.scene.frame_current
        original = self.builder.build_prepared_review

        def build(value):
            self.assertEqual(self.store.get("picture").state, self.storage.JobState.APPLYING)
            return original(value)

        with (
            patch.object(self.builder, "build_prepared_review", side_effect=build),
            patch.object(self.probe, "_snapshot", side_effect=AssertionError("GUI copied media")),
        ):
            result = self.session.apply_film_review(completion)
        self.assertEqual(result.phase, "BUILT")
        self.assertEqual(self.store.get("picture").state, self.storage.JobState.APPLIED)
        self.assertEqual(len(result.application.scene.sequence_editor.strips), 2)
        self.assertEqual((result.application.frames, result.application.fps), (48, 24))
        self.assertEqual(before, (self.film.snapshot(self.scene), self.scene.frame_current))
        self.assertEqual(bpy.context.scene, self.scene)
        with self.assertRaises(self.module.OriginUnavailable):
            self.session.apply_film_review(completion)
        second = self.session.apply_film_review(self.ready())
        self.assertEqual(second.phase, "BUILT")
        self.assertEqual(len(self.store.get("picture").local_applications), 1)
        self.source.unlink()
        self.session.shutdown()
        self.assertTrue(prepared.directory.exists())
        self.assertFalse(self.calls or self.downloads)

    def test_changed_recipe_rejects_before_claim_and_can_discard(self):
        completion = self.ready()
        self.scene.scenario_film.recipe_json = json.dumps({**self.raw, "title": "Changed"})
        with self.assertRaises(self.module.OriginUnavailable):
            self.session.apply_film_review(completion)
        self.assertEqual(self.store.get("picture").state, self.storage.JobState.READY)
        self.session.discard_film_review(completion)
        self.assertFalse(completion.result.directory.exists())

    def test_foreign_completion_worker_and_changed_origin_cannot_apply(self):
        completion = self.ready()
        with self.assertRaises(self.module.OriginUnavailable):
            self.session.apply_film_review(replace(completion))
        with ThreadPoolExecutor(max_workers=1) as executor:
            with self.assertRaises(RuntimeError):
                executor.submit(self.session.apply_film_review, completion).result(3)
        self.session.invalidate_all()
        with self.assertRaises(self.module.OriginUnavailable):
            self.session.apply_film_review(completion)
        self.session.discard_film_review(completion)

    def test_changed_private_file_rejects_before_claim(self):
        completion = self.ready()
        completion.result.files[0][1].path.write_bytes(b"changed")
        with self.assertRaises(ValueError):
            self.session.apply_film_review(completion)
        self.assertEqual(self.store.get("picture").state, self.storage.JobState.READY)
        self.session.discard_film_review(completion)

    def test_decoder_failure_rolls_back_and_fails_claim_without_replaying(self):
        completion = self.ready()
        transition = self.store.transition

        def record(*args, **kwargs):
            if kwargs.get("state") == self.storage.JobState.APPLY_FAILED:
                self.assertTrue(completion.result.directory.exists())
                self.assertTrue(all(source.path.exists() for _, source in completion.result.files))
            return transition(*args, **kwargs)

        with (
            patch.object(self.builder, "_sound", side_effect=ValueError("decode fixture failure")),
            patch.object(self.store, "transition", side_effect=record),
        ):
            result = self.session.apply_film_review(completion)
        self.assertEqual(result.phase, "ERROR")
        self.assertEqual(self.builder._snapshot(), self.before)
        self.assertFalse(completion.result.directory.exists())
        self.assertEqual(self.store.get("picture").state, self.storage.JobState.APPLY_FAILED)
        with self.assertRaises(self.module.OriginUnavailable):
            self.session.apply_film_review(completion)

    def test_failed_receipt_retains_copies_until_retry_persists_without_rebuilding(self):
        completion = self.ready()
        transition = self.store.transition

        def fail_receipt(*args, **kwargs):
            if kwargs.get("state") == self.storage.JobState.APPLY_FAILED:
                raise OSError("fixture receipt unavailable")
            return transition(*args, **kwargs)

        with (
            patch.object(self.builder, "_sound", side_effect=ValueError("decode fixture failure")),
            patch.object(self.store, "transition", side_effect=fail_receipt),
        ):
            outcome = self.session.apply_film_review(completion)
        self.assertEqual(self.builder._snapshot(), self.before)
        self.assertEqual(self.store.get("picture").state, self.storage.JobState.APPLYING)
        self.assertTrue(outcome.receipt_retry_available)
        self.assertTrue(completion.result.directory.exists())
        with patch.object(
            self.builder, "build_prepared_review", side_effect=AssertionError("rebuild")
        ):
            result = self.session.retry_film_review_receipt(outcome)
        self.assertEqual(result.phase, "ERROR")
        self.assertFalse(result.receipt_retry_available or completion.result.directory.exists())
        self.assertEqual(self.store.get("picture").state, self.storage.JobState.APPLY_FAILED)
        self.assertTrue(self.source.exists())

    def test_changed_copy_during_native_decode_rolls_back(self):
        completion = self.ready()
        original = self.builder._sound

        def change(*args, **kwargs):
            value = original(*args, **kwargs)
            completion.result.files[0][1].path.write_bytes(b"changed")
            return value

        with patch.object(self.builder, "_sound", side_effect=change):
            result = self.session.apply_film_review(completion)
        self.assertEqual(result.phase, "ERROR")
        self.assertEqual(self.builder._snapshot(), self.before)

    def test_lost_claim_acknowledgement_never_builds(self):
        completion = self.ready()
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
            result = self.session.apply_film_review(completion)
        self.assertEqual(result.phase, "UNCERTAIN")
        self.assertTrue(result.inspection_required)
        self.assertFalse(result.receipt_retry_available or completion.result.directory.exists())
        self.assertEqual(self.store.get("picture").state, self.storage.JobState.APPLYING)

    def test_incomplete_native_cleanup_retains_media_and_uncertain_claim(self):
        completion = self.ready()
        with (
            patch.object(self.builder, "_sound", side_effect=ValueError("decode failed")),
            patch.object(self.builder, "_rollback", side_effect=RuntimeError("cleanup failed")),
        ):
            result = self.session.apply_film_review(completion)
        self.assertEqual(result.phase, "UNCERTAIN")
        self.assertTrue(result.inspection_required)
        self.assertTrue(completion.result.directory.exists())
        self.assertEqual(self.store.get("picture").state, self.storage.JobState.APPLYING)

    def test_receipt_retry_never_rebuilds_or_rehashes(self):
        completion = self.ready()
        original = self.store.transition

        def lose(*args, **kwargs):
            result = original(*args, **kwargs)
            if kwargs.get("state") == self.storage.JobState.APPLIED:
                raise OSError("lost receipt acknowledgement")
            return result

        with patch.object(self.store, "transition", side_effect=lose):
            outcome = self.session.apply_film_review(completion)
        self.assertEqual(outcome.phase, "UNCERTAIN")
        self.assertTrue(outcome.receipt_retry_available)
        with patch.object(
            self.builder, "build_prepared_review", side_effect=AssertionError("rebuild")
        ):
            result = self.session.retry_film_review_receipt(outcome)
        self.assertEqual(result.phase, "BUILT")
        self.assertIs(result.application, outcome.application)
        with self.assertRaises(ValueError):
            self.session.retry_film_review_receipt(outcome)

    def test_shutdown_removes_unused_completed_preparation(self):
        completion = self.ready()
        self.session.shutdown()
        self.assertFalse(completion.result.directory.exists())
        self.assertTrue(self.source.exists())

    def test_cleanup_failure_after_native_rollback_still_saves_failed_claim(self):
        completion = self.ready()
        with (
            patch.object(self.builder, "_sound", side_effect=ValueError("decode failed")),
            patch.object(self.builder.shutil, "rmtree", side_effect=OSError("cleanup denied")),
        ):
            result = self.session.apply_film_review(completion)
        self.assertEqual(self.builder._snapshot(), self.before)
        self.assertEqual(self.store.get("picture").state, self.storage.JobState.APPLY_FAILED)
        self.assertEqual(result.phase, "UNCERTAIN")
        self.assertTrue(result.inspection_required)
        self.assertFalse(result.receipt_retry_available)
        self.assertTrue(completion.result.directory.exists())

    def test_cleanup_failure_preserves_failed_receipt_recovery_without_rebuild(self):
        completion = self.ready()
        original = self.store.transition

        def lose(*args, **kwargs):
            result = original(*args, **kwargs)
            if kwargs.get("state") == self.storage.JobState.APPLY_FAILED:
                raise OSError("lost failed receipt acknowledgement")
            return result

        with (
            patch.object(self.store, "transition", side_effect=lose),
            patch.object(self.builder, "_sound", side_effect=ValueError("decode failed")),
            patch.object(self.builder.shutil, "rmtree", side_effect=OSError("cleanup denied")),
        ):
            result = self.session.apply_film_review(completion)
        self.assertTrue(result.receipt_retry_available)
        with (
            patch.object(
                self.builder, "build_prepared_review", side_effect=AssertionError("rebuild")
            ),
            patch.object(self.builder.shutil, "rmtree", side_effect=OSError("cleanup denied")),
        ):
            recovered = self.session.retry_film_review_receipt(result)
        self.assertEqual(self.store.get("picture").state, self.storage.JobState.APPLY_FAILED)
        self.assertEqual(recovered.phase, "UNCERTAIN")
        self.assertTrue(recovered.inspection_required)
        self.assertFalse(recovered.receipt_retry_available)
        self.assertTrue(completion.result.directory.exists())

    def test_cleanup_failure_does_not_mask_lost_claim_outcome(self):
        completion = self.ready()
        with (
            patch.object(
                self.session, "_claim_saved_application", side_effect=OSError("lost claim")
            ),
            patch.object(self.media, "discard", side_effect=OSError("cleanup denied")),
        ):
            result = self.session.apply_film_review(completion)
        self.assertEqual(result.phase, "UNCERTAIN")
        self.assertTrue(result.inspection_required)
        self.assertTrue(completion.result.directory.exists())
        self.assertEqual(self.builder._snapshot(), self.before)
