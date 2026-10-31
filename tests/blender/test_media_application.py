# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Receipt-bound sequencer insertion and rollback with real offline media."""

import hashlib
import io
import tempfile
import unittest
import wave
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import bpy
from helpers import FIXTURES, submodule


def wav_bytes():
    stream = io.BytesIO()
    with wave.open(stream, "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(8000)
        output.writeframes(b"\0\0" * 8000)
    return stream.getvalue()


class MediaApplicationTests(unittest.TestCase):
    def setUp(self):
        self.media = submodule("blender.media_application")
        self.storage = submodule("core.jobs.store")
        self.transfers = submodule("core.jobs.transfers")
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.snapshots = self.root / "snapshots"
        self.snapshots.mkdir()
        self.enterContext(
            patch.object(bpy.utils, "extension_path_user", return_value=str(self.snapshots))
        )
        self.scene = bpy.data.scenes.new("Media application fixture")
        self.sounds = set(bpy.data.sounds)

    def tearDown(self):
        bpy.data.scenes.remove(self.scene)
        for sound in set(bpy.data.sounds) - self.sounds:
            bpy.data.sounds.remove(sound, do_unlink=True)

    def asset(self, video=False):
        data = (FIXTURES / "synthetic/video-six-frames.mp4").read_bytes() if video else wav_bytes()
        mime, suffix = ("video/mp4", ".mp4") if video else ("audio/wav", ".wav")
        path = self.root / ("saved" + suffix)
        path.write_bytes(data)
        receipt = self.transfers.DownloadedResult(
            path.name, len(data), hashlib.sha256(data).hexdigest()
        )
        return self.storage.StoredResult(
            self.storage.ResultAsset("asset", path.name, mime, len(data)), receipt
        ), path

    def test_video_and_audio_use_independent_exact_files_and_preserve_timing(self):
        for video in (False, True):
            with self.subTest(video=video):
                item, path = self.asset(video)
                before = (
                    self.scene.frame_current,
                    self.scene.frame_start,
                    self.scene.frame_end,
                    self.scene.render.fps,
                )
                result = self.media.apply_media(self.scene, item, path, frame=17)
                self.assertEqual(result.strip.type, "MOVIE" if video else "SOUND")
                self.assertEqual(result.strip.frame_final_start, 17)
                self.assertGreater(result.strip.frame_duration, 0)
                self.assertEqual(result.path.read_bytes(), path.read_bytes())
                self.assertNotEqual(result.path, path)
                path.unlink()
                self.assertTrue(result.path.is_file())
                self.assertEqual(
                    (
                        self.scene.frame_current,
                        self.scene.frame_start,
                        self.scene.frame_end,
                        self.scene.render.fps,
                    ),
                    before,
                )
        self.assertEqual(len(self.scene.sequence_editor.strips), 2)

    def test_existing_channels_selection_and_active_strip_are_preserved(self):
        editor = self.scene.sequence_editor_create()
        first = editor.strips.new_effect("existing", "COLOR", 1, 1, length=10)
        editor.active_strip, first.select = first, True
        editor.channels[2].lock = True
        editor.channels[3].mute = True
        item, path = self.asset()
        result = self.media.apply_media(self.scene, item, path, frame=1)
        self.assertEqual(result.strip.channel, 4)
        self.assertEqual(editor.active_strip, first)
        self.assertTrue(first.select)

    def test_sequencer_without_a_scene_shows_the_strip_and_a_chosen_one_is_kept(self):
        # Blender 5's Sequencer shows its workspace's sequencer scene, not the window's.
        workspace = bpy.context.workspace
        self.addCleanup(setattr, workspace, "sequencer_scene", workspace.sequencer_scene)
        workspace.sequencer_scene = None
        item, path = self.asset()
        with patch.object(self.media, "_insert", side_effect=RuntimeError("synthetic")):
            with self.assertRaises(self.media.MediaApplicationError):
                self.media.apply_media(self.scene, item, path, frame=1)
        self.assertIsNone(workspace.sequencer_scene)
        result = self.media.apply_media(self.scene, item, path, frame=1)
        self.assertEqual(workspace.sequencer_scene, self.scene)
        self.assertIn(result.strip, list(workspace.sequencer_scene.sequence_editor.strips))
        chosen = bpy.data.scenes.new("Chosen sequencer scene")
        self.addCleanup(bpy.data.scenes.remove, chosen)
        workspace.sequencer_scene = chosen
        self.media.apply_media(self.scene, item, path, frame=40)
        self.assertEqual(workspace.sequencer_scene, chosen)
        self.assertEqual(len(self.scene.sequence_editor.strips), 2)

    def test_saved_wav_original_inserts_a_strip_as_long_as_the_wav(self):
        # Scenario keeps a model's WAV as the original behind its MP3 re-encode; the
        # saved original has no expected size and must keep its exact 2.5 s length.
        stream = io.BytesIO()
        with wave.open(stream, "wb") as output:
            output.setnchannels(2)
            output.setsampwidth(2)
            output.setframerate(48000)
            output.writeframes(b"\0\0\0\0" * 120000)
        data = stream.getvalue()
        path = self.root / "000-sound.wav"
        path.write_bytes(data)
        asset = self.storage.ResultAsset("asset", path.name, "audio/wav", source="original")
        receipt = self.transfers.DownloadedResult(
            path.name, len(data), hashlib.sha256(data).hexdigest()
        )
        self.scene.render.fps, self.scene.render.fps_base = 24, 1.0
        result = self.media.apply_media(
            self.scene, self.storage.StoredResult(asset, receipt), path, frame=1
        )
        self.assertIsNone(asset.expected_size)
        self.assertEqual(result.strip.type, "SOUND")
        self.assertEqual(result.strip.frame_duration, 60)
        self.assertEqual(result.path.read_bytes(), data)

    def test_compressed_audio_and_webm_decode_into_real_strips(self):
        for name, mime, kind in (
            ("audio-silence.mp3", "audio/mpeg", "SOUND"),
            ("audio-silence.ogg", "audio/ogg", "SOUND"),
            ("video-six-frames.webm", "video/webm", "MOVIE"),
        ):
            with self.subTest(mime=mime):
                path = FIXTURES / "synthetic" / name
                data = path.read_bytes()
                receipt = self.transfers.DownloadedResult(
                    name, len(data), hashlib.sha256(data).hexdigest()
                )
                item = self.storage.StoredResult(
                    self.storage.ResultAsset("asset", name, mime, len(data)), receipt
                )
                result = self.media.apply_media(self.scene, item, path, frame=31)
                self.assertEqual(result.strip.type, kind)
                self.assertEqual(result.strip.frame_final_start, 31)
                self.assertGreater(result.strip.frame_duration, 0)
                self.assertEqual(result.path.read_bytes(), data)

    def test_changed_bytes_or_wrong_container_leave_no_strip_or_snapshot(self):
        for corrupt in (False, True):
            with self.subTest(corrupt=corrupt):
                item, path = self.asset()
                if corrupt:
                    path.write_bytes(path.read_bytes() + b"changed")
                else:
                    item = replace(item, asset=replace(item.asset, media_type="video/mp4"))
                with self.assertRaises(self.media.MediaApplicationError):
                    self.media.apply_media(self.scene, item, path, frame=1)
                self.assertIsNone(self.scene.sequence_editor)
                self.assertEqual(list(self.snapshots.iterdir()), [])

    def test_failure_after_sound_insertion_rolls_back_only_created_data(self):
        item, path = self.asset()
        original = self.media._insert

        def fail(*args):
            original(*args)
            raise RuntimeError("synthetic post-insert failure")

        with patch.object(self.media, "_insert", side_effect=fail):
            with self.assertRaises(self.media.MediaApplicationError):
                self.media.apply_media(self.scene, item, path, frame=1)
        self.assertIsNone(self.scene.sequence_editor)
        self.assertEqual(set(bpy.data.sounds), self.sounds)
        self.assertEqual(list(self.snapshots.iterdir()), [])
        self.assertTrue(path.exists())

    def test_full_channels_fail_without_removing_existing_strips(self):
        editor = self.scene.sequence_editor_create()
        for channel in range(1, 129):
            editor.strips.new_effect(str(channel), "COLOR", channel, 1, length=2)
        item, path = self.asset()
        with self.assertRaises(self.media.MediaApplicationError):
            self.media.apply_media(self.scene, item, path, frame=1)
        self.assertEqual(len(editor.strips), 128)
        self.assertEqual(list(self.snapshots.iterdir()), [])

    def test_worker_call_cannot_mutate_blender(self):
        item, path = self.asset()
        with ThreadPoolExecutor(max_workers=1) as pool:
            with self.assertRaises(self.media.MediaApplicationError):
                pool.submit(self.media.apply_media, self.scene, item, path, frame=1).result(5)
        self.assertIsNone(self.scene.sequence_editor)
