# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Native local video insertion, preserved scene settings and failure rollback."""

import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import bpy
from helpers import FIXTURES, isolated_manager, submodule


class VideoApplicationTests(unittest.TestCase):
    def setUp(self):
        self.video = submodule("blender.apply_video")
        self.runtime = submodule("blender.runtime")
        self.manager = self.enterContext(isolated_manager())
        self.scene = bpy.data.scenes.new("Video insertion fixture")
        self.addCleanup(bpy.data.scenes.remove, self.scene)
        self.path = FIXTURES / "synthetic" / "video-six-frames.mp4"
        self.record = submodule("core.jobs.records").JobRecord.new("video", "video", "fixture", {})
        self.record.status = "success"
        self.record.files = [str(self.path)]
        self.manager.registry.add(self.record)

    def settings(self):
        scene = self.scene
        return (
            scene.frame_current,
            scene.frame_start,
            scene.frame_end,
            scene.render.fps,
            scene.render.fps_base,
            scene.render.resolution_x,
            scene.render.resolution_y,
            scene.render.use_sequencer,
            scene.view_settings.view_transform,
        )

    def color(self, channel=1, start=1, end=100):
        editor = self.scene.sequence_editor or self.scene.sequence_editor_create()
        return editor.strips.new_effect("existing", "COLOR", channel, start, length=end - start)

    def test_imports_real_movie_frames_at_current_frame_without_changing_scene_settings(self):
        self.scene.frame_set(13)
        self.scene.render.fps = 30
        self.scene.render.use_sequencer = False
        before = self.settings()
        strip = self.video.add_to_sequencer(self.scene, str(self.path))
        self.assertEqual(strip.type, "MOVIE")
        self.assertEqual(strip.frame_final_start, 13)
        self.assertEqual(strip.frame_duration, 6)
        self.assertEqual(strip.channel, 1)
        self.assertEqual(self.settings(), before)
        self.assertEqual(Path(strip.filepath), self.path)
        self.assertEqual(len(self.scene.sequence_editor.strips), 1)

    def test_existing_strips_selection_and_active_strip_are_preserved(self):
        first, third = self.color(1), self.color(3)
        editor = self.scene.sequence_editor
        editor.active_strip = third
        first.select, third.select = True, False
        snapshots = [
            (s.as_pointer(), s.channel, s.frame_final_start, s.frame_final_end, s.select)
            for s in editor.strips
        ]
        added = self.video.add_to_sequencer(self.scene, str(self.path))
        self.assertEqual(added.channel, 2)
        self.assertEqual(editor.active_strip, third)
        self.assertEqual(
            [
                (s.as_pointer(), s.channel, s.frame_final_start, s.frame_final_end, s.select)
                for s in (first, third)
            ],
            snapshots,
        )

    def test_wholly_used_locked_and_muted_channels_are_skipped(self):
        self.color(4, 100, 110)
        editor = self.scene.sequence_editor
        editor.channels[1].lock = True
        editor.channels[2].mute = True
        strip = self.video.add_to_sequencer(self.scene, str(self.path))
        self.assertEqual(strip.channel, 3)

    def test_full_channels_fail_without_moving_existing_strips(self):
        for channel in range(1, 129):
            self.color(channel)
        editor = self.scene.sequence_editor
        before = {s.as_pointer(): s.channel for s in editor.strips}
        with self.assertRaisesRegex(ValueError, "No unused"):
            self.video.add_to_sequencer(self.scene, str(self.path))
        self.assertEqual({s.as_pointer(): s.channel for s in editor.strips}, before)

    def test_missing_unsupported_and_invalid_media_do_not_leave_an_editor(self):
        with tempfile.TemporaryDirectory() as directory:
            bad = Path(directory) / "invalid.mp4"
            bad.write_bytes(b"not a movie")
            for path in (str(bad), str(bad.with_suffix(".png")), str(bad.with_name("missing.mp4"))):
                with self.subTest(path=Path(path).name):
                    with self.assertRaises((ValueError, RuntimeError)):
                        self.video.add_to_sequencer(self.scene, path)
                    self.assertIsNone(self.scene.sequence_editor)

    def test_partial_decoder_failure_removes_only_the_new_strip(self):
        existing = self.color()
        editor = self.scene.sequence_editor
        original = self.video._load_movie

        def fail(*args):
            original(*args)
            raise RuntimeError("fixture failure after creation")

        with patch.object(self.video, "_load_movie", side_effect=fail):
            with self.assertRaisesRegex(RuntimeError, "fixture failure"):
                self.video.add_to_sequencer(self.scene, str(self.path))
        self.assertEqual(list(editor.strips), [existing])

    def test_registered_operator_uses_the_explicit_scene_and_selected_file(self):
        original_scene = bpy.context.scene
        with bpy.context.temp_override(scene=self.scene):
            self.assertEqual(
                bpy.ops.scenario.video_to_sequencer(local_id=self.record.local_id), {"FINISHED"}
            )
        self.assertIs(bpy.context.scene, original_scene)
        self.assertEqual(len(self.scene.sequence_editor.strips), 1)
        self.assertIn("Video strip added", self.runtime.state.last_message)
        self.assertEqual(self.record.files, [str(self.path)])

    def test_operator_rejects_stale_records_and_indices_without_scene_mutation(self):
        with bpy.context.temp_override(scene=self.scene):
            for local_id, index in (("missing", 0), (self.record.local_id, 8)):
                with self.assertRaisesRegex(RuntimeError, "available downloaded"):
                    bpy.ops.scenario.video_to_sequencer(local_id=local_id, file_index=index)
            self.record.status = "running"
            with self.assertRaisesRegex(RuntimeError, "available downloaded"):
                bpy.ops.scenario.video_to_sequencer(local_id=self.record.local_id)
        self.assertIsNone(self.scene.sequence_editor)

    def test_worker_cannot_access_blender_for_insertion(self):
        with ThreadPoolExecutor(max_workers=1) as worker:
            with self.assertRaisesRegex(RuntimeError, "main thread"):
                worker.submit(self.video.add_to_sequencer, self.scene, str(self.path)).result(2)
        self.assertIsNone(self.scene.sequence_editor)
