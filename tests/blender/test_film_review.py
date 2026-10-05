# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Real receipt-bound Film movie/audio strips, persistence and transactional rollback."""

import copy
import hashlib
import io
import json
import tempfile
import unittest
import wave
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from fractions import Fraction
from pathlib import Path
from unittest.mock import patch

import bpy
from helpers import FIXTURES, submodule


class FilmReviewTests(unittest.TestCase):
    def setUp(self):
        self.builder = submodule("blender.film_review")
        self.store = submodule("core.jobs.store")
        self.probe = submodule("core.jobs.media_probe")
        self.receipt = submodule("core.jobs.transfers").DownloadedResult
        self.before = self.builder._snapshot()
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        self.snapshots = self.root / "snapshots"
        self.snapshots.mkdir()
        self.enterContext(
            patch.object(bpy.utils, "extension_path_user", return_value=str(self.snapshots))
        )
        self.scope = self.store.JobScope("https://fixture.invalid/v1", "account")
        scene = submodule("core.scene.film_scene_plan").local_plan("studio", "", 2)
        self.recipe = {
            "title": "Film review fixture",
            "fps": 24,
            "audio_tracks": [],
            "shots": [
                {"id": "shot", "title": "Shot", "duration": 2, "source_trim": 1, "scene": scene}
            ],
            "tasks": [{"id": "shot-video", "title": "Video", "kind": "upload"}],
        }
        self.sources = {"shot-video": self.video()}
        self.old_scene = bpy.context.scene
        self.old_layer = bpy.context.view_layer
        self.selected = tuple(bpy.context.selected_objects)
        self.active = bpy.context.view_layer.objects.active
        self.frame = bpy.context.scene.frame_current

    def tearDown(self):
        self.builder._rollback(self.before)

    def video(self, *, audio=False, asset="picture"):
        filename = "film-four-seconds-audio.mp4" if audio else "film-four-seconds.mp4"
        path = self.root / (asset + ".mp4")
        data = (FIXTURES / "synthetic" / filename).read_bytes()
        path.write_bytes(data)
        receipt = self.receipt(path.name, len(data), hashlib.sha256(data).hexdigest())
        result = self.store.StoredResult(
            self.store.ResultAsset(asset, path.name, "video/mp4"), receipt
        )
        info = self.probe.MediaInfo(
            "video",
            receipt.sha256,
            receipt.size,
            Fraction(4),
            32,
            32,
            Fraction(24),
            Fraction(4) if audio else None,
        )
        return self.builder.ReviewSource(self.scope, result, path, info)

    def audio(self, *, frames=24000, rate=24000):
        stream = io.BytesIO()
        with wave.open(stream, "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(rate)
            output.writeframes(b"\0\0" * frames)
        path = self.root / "score.wav"
        path.write_bytes(stream.getvalue())
        receipt = self.receipt(
            path.name, path.stat().st_size, hashlib.sha256(path.read_bytes()).hexdigest()
        )
        result = self.store.StoredResult(
            self.store.ResultAsset("score-asset", path.name, "audio/wav"), receipt
        )
        info = self.probe.MediaInfo(
            "audio",
            receipt.sha256,
            receipt.size,
            Fraction(frames, rate),
            audio_duration=Fraction(frames, rate),
        )
        return self.builder.ReviewSource(self.scope, result, path, info)

    def add_score(self, **options):
        self.recipe["tasks"].append({"id": "music", "title": "Music", "kind": "upload"})
        self.recipe["audio_tracks"] = [
            {
                "id": "score",
                "task": "music",
                "kind": "music",
                "start": 0,
                "end": 2,
                "volume": 0.4,
                "loop": True,
                **options,
            }
        ]
        self.sources["music"] = self.audio()

    def build(self, **options):
        return self.builder.build_review_scene(
            self.recipe,
            scope=self.scope,
            production_id="production",
            sources=self.sources,
            **options,
        )

    def unchanged_context(self):
        self.assertEqual(bpy.context.scene, self.old_scene)
        self.assertEqual(bpy.context.view_layer, self.old_layer)
        self.assertEqual(tuple(bpy.context.selected_objects), self.selected)
        self.assertEqual(bpy.context.view_layer.objects.active, self.active)
        self.assertEqual(self.old_scene.frame_current, self.frame)

    def test_exact_picture_trim_silent_source_and_independent_persistent_copy(self):
        recipe = copy.deepcopy(self.recipe)
        result = self.build()
        self.assertEqual(
            (result.frames, result.fps, result.shots, result.audio_segments), (48, 24, 1, 0)
        )
        scene = result.scene
        self.assertEqual(
            (scene.frame_start, scene.frame_end, scene.render.fps, scene.render.fps_base),
            (1, 48, 24, 1),
        )
        self.assertEqual((scene.render.resolution_x, scene.render.resolution_y), (1920, 1080))
        (strip,) = scene.sequence_editor.strips
        self.assertEqual(
            (
                strip.type,
                strip.frame_final_start,
                strip.frame_final_end,
                strip.frame_offset_start,
                strip.channel,
            ),
            ("MOVIE", 1, 49, 24, 1),
        )
        self.assertEqual(scene["scenario_production_id"], "production")
        self.assertEqual(scene["scenario_sequence_kind"], "downloaded_final_review")
        self.assertEqual(strip["scenario_asset"], "picture")
        saved = Path(strip.filepath)
        self.assertIn(saved, result.paths)
        self.assertNotEqual(saved, self.sources["shot-video"].path)
        self.sources["shot-video"].path.unlink()
        self.assertTrue(saved.is_file())
        self.assertTrue(strip.reload_if_needed())
        self.assertEqual(self.recipe, recipe)
        self.unchanged_context()

    def test_native_sound_trim_and_volume_share_the_picture_cut(self):
        self.sources["shot-video"] = self.video(audio=True)
        self.recipe["shots"][0]["native_audio_volume"] = 0.25
        result = self.build()
        movie, sound = sorted(result.scene.sequence_editor.strips, key=lambda s: s.channel)
        self.assertEqual(sound.type, "SOUND")
        self.assertEqual(
            (sound.frame_final_start, sound.frame_final_end, sound.frame_offset_start),
            (movie.frame_final_start, movie.frame_final_end, movie.frame_offset_start),
        )
        self.assertEqual(sound.volume, 0.25)
        self.assertEqual(sound.sound.filepath, movie.filepath)
        self.unchanged_context()

    def test_loop_duck_segments_keep_phase_and_track_channel(self):
        self.add_score(duck=[{"start": 0.5, "end": 1.5, "volume": 0.1}])
        result = self.build()
        strips = sorted(
            (s for s in result.scene.sequence_editor.strips if s.type == "SOUND"),
            key=lambda s: s.frame_final_start,
        )
        self.assertEqual(result.audio_segments, 4)
        self.assertEqual(
            [
                (s.frame_final_start, s.frame_final_end, s.frame_offset_start, s.channel)
                for s in strips
            ],
            [(1, 13, 0, 3), (13, 25, 12, 3), (25, 37, 0, 3), (37, 49, 12, 3)],
        )
        for strip, volume in zip(strips, (0.4, 0.1, 0.1, 0.4), strict=True):
            self.assertAlmostEqual(strip.volume, volume)
        self.assertEqual(len(json.loads(result.scene["scenario_audio_mix"])), 4)

    def test_master_is_an_explicit_muted_alternate_in_same_scope(self):
        result = self.build(master=self.video(audio=True, asset="master"))
        alternate = [s for s in result.scene.sequence_editor.strips if "alternate" in s.name]
        self.assertTrue(result.master_imported)
        self.assertEqual(len(alternate), 2)
        self.assertTrue(all(s.mute for s in alternate))
        self.assertEqual({s.channel for s in alternate}, {10, 11})
        self.assertTrue(all((s.frame_final_start, s.frame_final_end) == (1, 49) for s in alternate))
        self.unchanged_context()

    def test_previs_uses_its_take_without_final_trim_or_editorial_score(self):
        self.recipe["tasks"] = [{"id": "shot-previs", "title": "Previs", "kind": "upload"}]
        self.sources = {"shot-previs": self.video()}
        result = self.build(mode="previs")
        (strip,) = result.scene.sequence_editor.strips
        self.assertEqual(strip.frame_offset_start, 0)
        self.assertEqual(result.audio_segments, 0)
        self.assertEqual(result.scene["scenario_sequence_kind"], "downloaded_previs_review")

    def test_two_shots_contiguous_and_repeated_source_copied_once(self):
        second = copy.deepcopy(self.recipe["shots"][0])
        second.update(id="second", title="Second", video_task="shot-video", source_trim=2)
        self.recipe["shots"].append(second)
        result = self.build()
        strips = sorted(result.scene.sequence_editor.strips, key=lambda s: s.frame_final_start)
        self.assertEqual(
            [(s.frame_final_start, s.frame_final_end, s.channel) for s in strips],
            [(1, 49, 1), (49, 97, 1)],
        )
        self.assertEqual(len(result.paths), 1)
        self.assertEqual(
            [(m.name, m.frame) for m in result.scene.timeline_markers],
            [("Shot", 1), ("Second", 49)],
        )
        self.assertEqual(result.frames, 96)

    def test_wrong_scope_measurement_type_and_rate_reject_before_files_or_scene(self):
        source = self.sources["shot-video"]
        changed = [
            replace(source, scope=replace(self.scope, account_id="other")),
            replace(source, media=replace(source.media, sha256="a" * 64)),
            replace(source, media=replace(source.media, frame_rate=Fraction(30))),
            replace(source, media=replace(source.media, duration=Fraction(1))),
            replace(source, result=replace(source.result, receipt=None)),
        ]
        for value in changed:
            with self.subTest(source=value):
                self.sources["shot-video"] = value
                with self.assertRaises(ValueError):
                    self.build()
                self.assertEqual(self.builder._snapshot(), self.before)
                self.assertFalse(tuple(self.snapshots.iterdir()))
        self.unchanged_context()

    def test_changed_missing_and_symlink_source_roll_back_copies(self):
        source = self.sources["shot-video"]
        for mode in ("changed", "missing", "symlink"):
            with self.subTest(mode=mode):
                source = self.video()
                if mode == "changed":
                    source.path.write_bytes(b"x" * source.path.stat().st_size)
                elif mode == "missing":
                    source.path.unlink()
                else:
                    target = self.root / "target.mp4"
                    source.path.rename(target)
                    source.path.symlink_to(target)
                self.sources["shot-video"] = source
                with self.assertRaises(self.builder.FilmReviewError):
                    self.build()
                self.assertEqual(self.builder._snapshot(), self.before)
                self.assertFalse(tuple(self.snapshots.iterdir()))
        self.unchanged_context()

    def test_late_decode_failure_removes_only_new_scene_sounds_and_files(self):
        self.sources["shot-video"] = self.video(audio=True)
        original = self.builder._sound

        def fail(*args, **kwargs):
            original(*args, **kwargs)
            raise ValueError("synthetic decode failure")

        with patch.object(self.builder, "_sound", side_effect=fail):
            with self.assertRaises(self.builder.FilmReviewError):
                self.build()
        self.assertEqual(self.builder._snapshot(), self.before)
        self.assertFalse(tuple(self.snapshots.iterdir()))
        self.assertTrue(self.sources["shot-video"].path.is_file())
        self.unchanged_context()

    def test_failed_rollback_keeps_media_for_partial_scene_inspection(self):
        with (
            patch.object(self.builder, "_movie", side_effect=ValueError("decode failed")),
            patch.object(
                self.builder, "_rollback", side_effect=RuntimeError("cleanup needs inspection")
            ),
        ):
            with self.assertRaisesRegex(RuntimeError, "cleanup needs inspection"):
                self.build()
        self.assertTrue(set(bpy.data.scenes) - self.before["scenes"])
        self.assertTrue(list(self.snapshots.rglob("*.mp4")))
        self.unchanged_context()

    def test_worker_and_over_budget_calls_cannot_create_scene_or_files(self):
        with ThreadPoolExecutor(max_workers=1) as pool:
            with self.assertRaisesRegex(RuntimeError, "main thread"):
                pool.submit(self.build).result(5)
        with patch.object(self.builder, "MAX_TOTAL_BYTES", 1):
            with self.assertRaisesRegex(ValueError, "2 GiB"):
                self.build()
        self.assertEqual(self.builder._snapshot(), self.before)
        self.assertFalse(tuple(self.snapshots.iterdir()))

    def test_saved_review_reopens_with_owned_media_and_original_scene_selected(self):
        result = self.build()
        name = result.scene.name
        filename = self.root / "review.blend"
        # Library round-trip reads only the new review and its sound dependencies;
        # it does not replace the test process's working file or other scenes.
        bpy.data.libraries.write(str(filename), {result.scene}, path_remap="ABSOLUTE")
        bpy.data.scenes.remove(result.scene)
        with bpy.data.libraries.load(str(filename), link=False) as (src, dst):
            dst.scenes = [name]
        reopened = dst.scenes[0]
        (strip,) = reopened.sequence_editor.strips
        self.assertTrue(Path(strip.filepath).is_file())
        self.assertTrue(strip.reload_if_needed())
        self.assertEqual((strip.frame_final_start, strip.frame_final_end), (1, 49))
        self.unchanged_context()

    def test_decoder_rejects_a_shorter_picture_than_its_supplied_measurement(self):
        source = self.sources["shot-video"]
        source.path.write_bytes((FIXTURES / "synthetic/video-six-frames.mp4").read_bytes())
        receipt = self.receipt(
            source.path.name,
            source.path.stat().st_size,
            hashlib.sha256(source.path.read_bytes()).hexdigest(),
        )
        self.sources["shot-video"] = replace(
            source,
            result=replace(source.result, receipt=receipt),
            media=replace(source.media, size=receipt.size, sha256=receipt.sha256),
        )
        with self.assertRaises(self.builder.FilmReviewError):
            self.build()
        self.assertEqual(self.builder._snapshot(), self.before)
        self.assertFalse(tuple(self.snapshots.iterdir()))
        self.unchanged_context()

    def test_decoder_rejects_a_shorter_sound_than_its_supplied_measurement(self):
        self.add_score(loop=False)
        source = self.sources["music"]
        self.sources["music"] = replace(
            source, media=replace(source.media, duration=Fraction(4), audio_duration=Fraction(4))
        )
        with self.assertRaises(self.builder.FilmReviewError):
            self.build()
        self.assertEqual(self.builder._snapshot(), self.before)
        self.assertFalse(tuple(self.snapshots.iterdir()))
        self.unchanged_context()
