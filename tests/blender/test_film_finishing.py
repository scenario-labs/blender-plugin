# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Installed unpaid composition planning on Blender's bundled Python."""

import tempfile
import unittest
from fractions import Fraction
from pathlib import Path

import bpy
from helpers import submodule


class FilmFinishingTests(unittest.TestCase):
    def test_installed_draft_uses_saved_video_and_preserves_scope_and_scene(self):
        jobs = submodule("core.jobs.store")
        tasks = submodule("core.jobs.film_tasks")
        finish = submodule("core.jobs.film_finishing")
        raw = {
            "title": "Native composition",
            "fps": 30,
            "audio_tracks": [],
            "shots": [
                {
                    "id": "shot",
                    "title": "Shot",
                    "duration": 4,
                    "scene": submodule("core.scene.film_scene_plan").local_plan("studio", "", 4),
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
        scene, filepath, frame = (
            bpy.context.scene,
            bpy.data.filepath,
            bpy.context.scene.frame_current,
        )
        with tempfile.TemporaryDirectory(dir=bpy.utils.resource_path("USER")) as directory:
            store = jobs.JobStore(
                Path(directory) / "jobs.sqlite3",
                jobs.JobScope("https://fixture.invalid/v1", "account"),
            )
            binding, *_ = tasks._task_context(
                store, raw, production_id="production", task_id="shot-video", kind="model"
            )
            row = store.create(
                jobs.JobIntent(
                    "request",
                    store.scope,
                    jobs.JobOrigin("file", "scene", "revision"),
                    "model",
                    "fixture-model",
                    "a" * 64,
                    "b" * 64,
                    "1",
                    film_task=binding,
                )
            )
            for state in (jobs.JobState.SUBMITTING, jobs.JobState.REMOTE, jobs.JobState.SUCCEEDED):
                row = store.transition(
                    "request",
                    expected_revision=row.revision,
                    state=state,
                    remote_job_id="remote" if state == jobs.JobState.REMOTE else None,
                )
            row = store.set_results(
                "request",
                (jobs.ResultAsset("asset", "video.mp4", "video/mp4"),),
                expected_revision=row.revision,
            )
            draft = finish.prepare_composition(store, raw, production_id="production")
            self.assertEqual(store.records(), (row,))
            current = finish.validate_composition_draft(store, draft)
            binding, model, parameters = tasks.model_task_request(
                store, current, production_id="production", task_id="final-master"
            )
            self.assertEqual(model, "model_scenario-compose-video")
            self.assertEqual(parameters["layers"][0]["source"], "asset")
            self.assertEqual((parameters["duration"], parameters["fps"]), (4, 30))
            self.assertEqual(binding.task_id, "final-master")
            self.assertIsNone(store.scope.project_id)
            self.assertIsNone(store.film_job("production", "final-master"))
        self.assertEqual(
            (bpy.context.scene, bpy.data.filepath, scene.frame_current), (scene, filepath, frame)
        )

    def test_exact_audio_duration_uses_bundled_fraction_without_loading_media(self):
        finish = submodule("core.scene.film_finish")
        jobs = submodule("core.jobs.store")
        scope = jobs.JobScope("https://fixture.invalid/v1", "account")
        observation = finish.AudioDuration(scope, "audio-asset", Fraction(48001, 48000))
        self.assertEqual(observation.seconds * 30, Fraction(48001, 1600))
        with self.assertRaises(ValueError):
            finish.AudioDuration(scope, "audio-asset", 1.5)
