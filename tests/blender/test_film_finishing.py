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


class FilmMediaSessionTests(unittest.TestCase):
    def setUp(self):
        import json
        import threading
        from unittest.mock import patch

        import test_session_uploads

        self.fixture = fixture = test_session_uploads.SessionUploadTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.addCleanup(fixture.tearDown)
        self.session, self.scene = fixture.session, fixture.scene
        self.origin = self.session.capture(self.scene)
        self.probe = submodule("core.jobs.media_probe")
        self.media = submodule("core.jobs.film_media")
        self.raw = {
            "title": "Measured composition",
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
            "tasks": [{"id": "shot-video", "title": "Picture", "kind": "upload"}],
        }
        intent = fixture.sources.stage(
            fixture.source,
            request_id="picture",
            scope=fixture.scope,
            origin=self.origin,
            kind="video",
            content_type="video/mp4",
        )
        row = fixture.upload_store.create(intent)
        for state in (
            fixture.uploads.UploadState.INITIALIZING,
            fixture.uploads.UploadState.UPLOADING,
            fixture.uploads.UploadState.IMPORTED,
        ):
            row = fixture.upload_store.transition(
                "picture",
                expected_revision=row.revision,
                state=state,
                upload_id="upload" if state == fixture.uploads.UploadState.UPLOADING else None,
                asset_id="picture" if state == fixture.uploads.UploadState.IMPORTED else None,
            )
        self.session._coordinator.bind_film_upload(
            self.raw,
            production_id="production",
            task_id="shot-video",
            request_id="picture",
            expected_revision=row.revision,
            origin=self.origin,
        )
        self.enterContext(
            patch.object(self.probe, "probe_tool", return_value=fixture.root / "ffprobe")
        )
        self.enterContext(
            patch.object(self.media, "probe_tool", return_value=fixture.root / "ffprobe")
        )
        self.probes = []

        def run(command, *, stdout, **kwargs):
            self.assertIsNot(threading.current_thread(), threading.main_thread())
            source = Path(command[command.index("-i") + 1])
            self.assertEqual(source.read_bytes(), b"data")
            self.probes.append(source.parent)
            stdout.write_text(
                json.dumps(
                    {
                        "streams": [
                            {
                                "codec_type": "video",
                                "duration": "4",
                                "width": 128,
                                "height": 128,
                                "avg_frame_rate": "30/1",
                            }
                        ]
                    }
                )
            )

        self.enterContext(patch.object(self.probe, "_run", side_effect=run))

    def prepare(self):
        return self.session.prepare_film_composition(
            self.raw, production_id="production", origin=self.origin
        )

    def test_installed_session_delivers_verified_draft_without_scene_edit_or_service_calls(self):
        before = (
            self.scene.frame_current,
            bpy.data.filepath,
            self.fixture.store.records(),
            self.fixture.upload_store.records(),
        )
        task = self.prepare()
        result = task.result(5)
        (completion,) = self.session.drain()
        self.assertIsNone(completion.error)
        self.assertIs(completion.result, result)
        delivered = self.session.deliver(completion, lambda result, scene, target: (result, scene))
        self.assertEqual(delivered, (result, self.scene))
        self.assertEqual((result.scope, result.origin), (self.session.scope, self.origin))
        self.assertEqual(dict(result.media)["shot-video"].duration, Fraction(4))
        self.assertEqual(result.draft.recipe["tasks"][-1]["id"], "final-master")
        self.assertEqual(
            before,
            (
                self.scene.frame_current,
                bpy.data.filepath,
                self.fixture.store.records(),
                self.fixture.upload_store.records(),
            ),
        )
        self.assertFalse(self.fixture.calls)
        self.assertTrue(self.probes and all(not path.exists() for path in self.probes))

    def test_scene_invalidated_after_completion_cannot_receive_draft(self):
        task = self.prepare()
        task.result(5)
        self.session.invalidate_scene(self.scene)
        (completion,) = self.session.drain()
        with self.assertRaises(self.fixture.module.OriginUnavailable):
            self.session.deliver(completion, lambda *args: self.fail("Stale draft delivered"))
        self.assertFalse(self.fixture.calls)

    def test_session_rejects_invalidated_origin_before_queueing(self):
        self.session.invalidate_scene(self.scene)
        with self.assertRaises(self.fixture.module.OriginUnavailable):
            self.prepare()
        self.assertFalse(self.probes)

    def test_missing_tool_is_sanitized_and_preserves_imported_upload(self):
        from unittest.mock import patch

        before = self.fixture.upload_store.records()
        with patch.object(
            self.media,
            "probe_tool",
            side_effect=self.probe.MediaProbeError("Install ffprobe on PATH"),
        ):
            task = self.prepare()
            with self.assertRaises(self.probe.MediaProbeError):
                task.result(5)
        (completion,) = self.session.drain()
        self.assertIsNotNone(completion.error)
        self.assertIsNone(completion.result)
        self.assertEqual(before, self.fixture.upload_store.records())
        self.assertFalse(self.fixture.calls)
