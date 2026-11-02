# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""A music model's length starts at the scene's frame range and follows it until edited."""

import unittest

import bpy
from helpers import reset_scene, submodule

PROMPT = {"name": "prompt", "type": "string", "prompt": True, "required": {"always": True}}


def record(model_id, name, inputs):
    catalog = submodule("core.api.catalog")
    return catalog.ModelRecord.from_api(
        {
            "id": model_id,
            "name": name,
            "capabilities": ["txt2audio"],
            "status": "trained",
            "inputs": [PROMPT, *inputs],
        }
    )


# The length inputs of the live descriptions, as REST sends them.
MUSIC = record(
    "model_elevenlabs-music-v2-5",
    "ElevenLabs Music v2.5",
    [
        {
            "name": "durationSeconds",
            "type": "number",
            "default": 30,
            "min": 3,
            "max": 600,
            "step": 1,
            "costImpact": True,
        },
        {"name": "forceInstrumental", "type": "boolean", "default": False},
    ],
)
ACE = record(
    "model_ace-step-1-5-quality-text-to-music",
    "ACE-Step 1.5 Text to Music - Quality",
    [{"name": "duration", "type": "number", "min": 10, "max": 600, "step": 1, "costImpact": True}],
)
SFX = record(
    "model_elevenlabs-sound-effects-v2",
    "ElevenLabs Sound Effects 2",
    [{"name": "durationSeconds", "type": "number", "default": 5, "min": 0.5, "max": 30}],
)
LYRIA = record("model_lyria-3-5", "Google Lyria 3.5", [])


class MusicLengthTests(unittest.TestCase):
    def setUp(self):
        reset_scene()
        self.runtime = submodule("blender.runtime")
        self.generation = submodule("blender.generation")
        self.handlers = submodule("blender.handlers")
        self.scene = bpy.context.scene
        self.scene.render.fps, self.scene.render.fps_base = 24, 1.0
        self.scene.frame_start, self.scene.frame_end = 1, 360  # 15 s
        self.scene.scenario.lane = "audio"

    def load(self, *records):
        self.runtime.state.reset()
        self.handlers.dispatch(
            ("catalog", {"privacy": "public", "records": list(records), "detailed": list(records)})
        )
        lane = self.scene.scenario.lane_state("audio")
        lane.model_id = records[0].id
        lane.prompt = "a slow march"
        self.generation.on_model_changed(bpy.context, lane)
        return lane

    def length(self, lane, name="durationSeconds"):
        return lane.params[name].int_value

    def test_a_music_form_starts_at_the_scene_length_and_prices_it(self):
        lane = self.load(MUSIC, ACE, SFX)
        item = lane.params["durationSeconds"]
        self.assertEqual(item.int_value, 15)
        self.assertTrue(item.enabled and item.follows_scene)
        body = self.generation.build_request(self.scene, "audio", for_estimate=True).body
        self.assertEqual(body["durationSeconds"], 15)

    def test_the_scene_length_is_frames_over_fps_within_the_inputs_range(self):
        lane = self.load(MUSIC)
        cases = (
            ((1, 360, 24, 1.0), 15),  # 15 s
            ((1, 450, 30, 1.0), 15),  # the same length at another frame rate
            ((1, 24 * 5 + 6, 24, 1.0), 6),  # 5.25 s: whole seconds, rounded up
            ((1, 24, 24, 1.0), 3),  # 1 s, below the input's minimum
            ((1, 24 * 900, 24, 1.0), 600),  # 15 min, above its maximum
            ((1, 25, 25, 1.0), 3),  # fps 25 over a 1 s range, still the minimum
        )
        for (start, end, fps, base), expected in cases:
            with self.subTest(range=(start, end), fps=fps):
                self.scene.frame_start, self.scene.frame_end = start, end
                self.scene.render.fps, self.scene.render.fps_base = fps, base
                self.generation.sync_shown_forms()
                self.assertEqual(self.length(lane), expected)

    def test_the_preview_range_sets_the_length_when_it_is_on(self):
        lane = self.load(MUSIC)
        self.scene.use_preview_range = True
        self.scene.frame_preview_start, self.scene.frame_preview_end = 1, 120  # 5 s
        self.generation.sync_shown_forms()
        self.assertEqual(self.length(lane), 5)

    def test_it_follows_the_scene_until_the_user_edits_it(self):
        lane = self.load(MUSIC)
        self.scene.frame_end = 720  # 30 s
        self.assertTrue(self.generation.sync_shown_forms())  # the pump moves the shown form
        self.assertEqual(self.length(lane), 30)
        self.assertFalse(self.generation.sync_shown_forms())  # nothing more to move
        lane.params["durationSeconds"].int_value = 12  # the user's own length
        self.assertFalse(lane.params["durationSeconds"].follows_scene)
        self.scene.frame_end = 1440
        self.assertFalse(self.generation.sync_shown_forms())
        self.assertEqual(self.length(lane), 12)
        # Nor does a catalog refresh or a price request.
        self.handlers.dispatch(
            ("catalog", {"privacy": "public", "records": [MUSIC], "detailed": [MUSIC]})
        )
        self.assertEqual(self.length(lane), 12)
        request = self.generation.build_request(self.scene, "audio", for_estimate=True)
        self.assertEqual(request.body["durationSeconds"], 12)

    def test_a_price_request_after_a_range_change_prices_the_new_length(self):
        lane = self.load(MUSIC)
        self.scene.frame_end = 720
        body = self.generation.build_request(self.scene, "audio", for_estimate=True).body
        self.assertEqual(body["durationSeconds"], 30)
        self.assertEqual(self.length(lane), 30)

    def test_an_input_that_has_no_default_is_switched_on_at_the_scene_length(self):
        lane = self.load(ACE)
        item = lane.params["duration"]
        self.assertEqual(item.int_value, 15)
        self.assertTrue(item.enabled)
        self.scene.frame_end = 120  # 5 s, below the input's minimum of 10
        self.generation.sync_shown_forms()
        self.assertEqual(item.int_value, 10)

    def test_sound_effects_and_models_without_a_length_are_left_alone(self):
        lane = self.load(SFX)
        item = lane.params["durationSeconds"]
        self.assertEqual(item.float_value, 5.0)
        self.assertFalse(item.follows_scene)
        self.scene.frame_end = 720
        self.assertFalse(self.generation.sync_shown_forms())
        self.assertEqual(item.float_value, 5.0)
        lane = self.load(LYRIA)
        self.assertNotIn("durationSeconds", [p.name for p in lane.params])
        self.assertNotIn("duration", [p.name for p in lane.params])
        self.assertFalse(self.generation.sync_shown_forms())

    def test_a_reloaded_job_keeps_its_own_length(self):
        lane = self.load(MUSIC)
        item = lane.params["durationSeconds"]
        item.int_value = 45  # as reload_generation restores a job's settings
        self.assertFalse(item.follows_scene)
        self.scene.frame_end = 720
        self.generation.sync_shown_forms()
        self.assertEqual(item.int_value, 45)
