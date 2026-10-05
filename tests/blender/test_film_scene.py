# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Native Film shot geometry, choreography, receipt import and rollback."""

import copy
import hashlib
import json
import math
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import bpy
from helpers import FIXTURES, animated_glb, submodule
from mathutils import Vector


class FilmSceneTests(unittest.TestCase):
    def setUp(self):
        self.builder = submodule("blender.film_scene")
        self.old_scene, self.old_layer = bpy.context.window.scene, bpy.context.window.view_layer
        self.before = self.builder._snapshot()
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.enterContext(
            patch.object(bpy.utils, "extension_path_user", return_value=str(self.root))
        )
        scene = submodule("core.scene.film_scene_plan").local_plan("studio", "", 4)
        self.raw = {
            "title": "Shot fixture",
            "fps": 30,
            "shots": [{"id": "shot", "title": "Shot", "duration": 4, "scene": scene}],
        }
        self.selected = tuple(bpy.context.selected_objects)
        self.active = bpy.context.view_layer.objects.active
        self.frame = self.old_scene.frame_current

    def tearDown(self):
        bpy.context.window.scene, bpy.context.window.view_layer = self.old_scene, self.old_layer
        self.builder._rollback(self.before)

    def build(self, **options):
        return self.builder.build_shot(
            self.raw, production_id="production", shot_id="shot", **options
        )

    def unchanged_context(self):
        self.assertEqual(bpy.context.window.scene, self.old_scene)
        self.assertEqual(bpy.context.window.view_layer, self.old_layer)
        self.assertEqual(tuple(bpy.context.selected_objects), self.selected)
        self.assertEqual(bpy.context.view_layer.objects.active, self.active)
        self.assertEqual(self.old_scene.frame_current, self.frame)

    def source(self, data=None):
        if data is None:
            data = (FIXTURES / "synthetic/static-triangle.glb").read_bytes()
        storage = submodule("core.jobs.store")
        receipt = submodule("core.jobs.transfers").DownloadedResult
        path = self.root / "hero.glb"
        path.write_bytes(data)
        item = storage.StoredResult(
            storage.ResultAsset("hero-asset", path.name, "model/gltf-binary", len(data)),
            receipt(path.name, len(data), hashlib.sha256(data).hexdigest()),
        )
        return self.builder.HeroSource(item, path)

    def actors(self, count=1, **hero):
        self.raw["heroes"] = {
            "hero": dict(
                name="Actor",
                description="Synthetic fixture",
                mesh="hero-mesh",
                reference="hero-reference",
                **hero,
            )
        }
        self.raw["shots"][0]["actors"] = [
            dict(hero="hero", name=f"Actor {i}", location=[i * 3, 0, 0]) for i in range(count)
        ]

    def test_all_primitive_types_have_real_geometry_in_an_independent_scene(self):
        shot = self.raw["shots"][0]
        template = copy.deepcopy(shot["scene"]["objects"][0])
        shot["scene"]["objects"] = [
            dict(template, name=kind, type=kind, location=[i * 3, 0, 0], scale=[1, 2, 3])
            for i, kind in enumerate(("box", "sphere", "cylinder", "cone", "torus", "plane"))
        ]
        result = self.build()
        self.unchanged_context()
        self.assertNotEqual(result.scene, self.old_scene)
        self.assertEqual(
            (result.scene.frame_start, result.scene.frame_end, result.scene.render.fps),
            (1, 120, 30),
        )
        self.assertEqual(len(result.placeholders), 6)
        for obj in result.placeholders.values():
            self.assertGreater(len(obj.data.polygons), 0)
            self.assertEqual(obj["scenario_asset_policy"], "interpret_placeholder")
            self.assertTrue(obj.data.materials[0].use_nodes)
        box = result.placeholders["box"]
        self.assertEqual(tuple(box.dimensions), (2, 4, 6))
        self.assertTrue(result.scene.world.use_nodes)
        self.assertEqual(len([o for o in result.scene.objects if o.type == "LIGHT"]), 3)
        self.assertEqual(result.scene["scenario_film_production_id"], "production")
        self.assertEqual(result.scene["scenario_film_shot_id"], "shot")
        self.assertEqual(len(result.scene["scenario_film_recipe_sha256"]), 64)

    def test_camera_styles_move_and_track_the_authored_target(self):
        for style in ("orbit", "dolly", "crane", "path"):
            with self.subTest(style=style):
                spec = self.raw["shots"][0]["scene"]["camera"]
                spec["style"] = style
                spec["points"] = [[0, -8, 3], [2, -4, 5], [4, -2, 3]]
                result = self.build()
                bpy.context.window.scene = result.scene
                try:
                    positions = []
                    for frame in (1, 60, 120):
                        result.scene.frame_set(frame)
                        bpy.context.view_layer.update()
                        evaluated = result.camera.evaluated_get(
                            bpy.context.evaluated_depsgraph_get()
                        )
                        matrix = evaluated.matrix_world
                        positions.append(matrix.translation.copy())
                        direction = (
                            result.target.matrix_world.translation - matrix.translation
                        ).normalized()
                        forward = (matrix.to_quaternion() @ Vector((0, 0, -1))).normalized()
                        self.assertGreater(forward.dot(direction), 0.999)
                    self.assertGreater((positions[1] - positions[0]).length, 0.1)
                finally:
                    bpy.context.window.scene = self.old_scene
                self.assertEqual(
                    [c.type for c in result.camera.constraints], ["FOLLOW_PATH", "TRACK_TO"]
                )

    def test_camera_and_motion_use_recipe_frame_rate_and_exact_endpoints(self):
        for fps in (24, 30, 60):
            with self.subTest(fps=fps):
                self.raw["fps"] = fps
                shot = self.raw["shots"][0]
                name = shot["scene"]["objects"][0]["name"]
                shot["scene"]["objects"][0]["scale"] = [2, 3, 4]
                shot["motion"] = [
                    {
                        "object": name,
                        "keyframes": [
                            {"time": 0, "location": [1, 2, 3], "scale": [2, 3, 4]},
                            {
                                "time": 4,
                                "location": [5, 6, 7],
                                "scale": [4, 6, 8],
                                "rotation": [0, 0, 90],
                            },
                        ],
                    }
                ]
                shot["target_keyframes"] = [
                    {"time": 0, "location": [0, 0, 0]},
                    {"time": 4, "location": [0, 0, 2]},
                ]
                result = self.build()
                obj = result.placeholders[name]
                bpy.context.window.scene = result.scene
                try:
                    result.scene.frame_set(result.scene.frame_end)
                    self.assertEqual(tuple(obj.location), (5, 6, 7))
                    self.assertEqual(tuple(obj.scale), (2, 2, 2))
                    self.assertAlmostEqual(obj.rotation_euler.z, math.pi / 2)
                    self.assertEqual(tuple(result.target.location), (0, 0, 2))
                finally:
                    bpy.context.window.scene = self.old_scene
                keys = [
                    key.co.x
                    for curve in submodule("blender.shot_planner").fcurves_of(obj)
                    for key in curve.keyframe_points
                ]
                self.assertEqual((min(keys), max(keys)), (1, fps * 4))
                self.assertEqual(result.scene.render.fps_base, 1)

    def test_subframe_motion_keys_remain_distinct_near_the_end(self):
        name = self.raw["shots"][0]["scene"]["objects"][0]["name"]
        self.raw["shots"][0]["motion"] = [
            {
                "object": name,
                "keyframes": [
                    {"time": 3.99, "location": [1, 0, 0]},
                    {"time": 4, "location": [2, 0, 0]},
                ],
            }
        ]
        result = self.build()
        curves = submodule("blender.shot_planner").fcurves_of(result.placeholders[name])
        self.assertTrue(all(len(curve.keyframe_points) == 2 for curve in curves))
        self.assertTrue(
            all(curve.keyframe_points[0].co.x < curve.keyframe_points[1].co.x for curve in curves)
        )

    def test_hero_models_are_receipt_checked_packed_and_independent(self):
        self.actors(2, width=2, rotation=[0, 0, 90])
        first, second = self.raw["shots"][0]["actors"]
        first.update(action="hold", phase=0.5)
        second.update(action="loop", action_speed=2, action_until=2)
        result = self.build(heroes={"hero": self.source(animated_glb(clips=1))})
        self.unchanged_context()
        self.assertEqual(len(result.actors), 2)
        a, b = [entry[0] for entry in result.actors]
        self.assertTrue(set(a.objects).isdisjoint(b.objects))
        a_mesh = next(o for o in a.objects if o.type == "MESH")
        b_mesh = next(o for o in b.objects if o.type == "MESH")
        self.assertIsNot(a_mesh.data, b_mesh.data)
        self.assertIsNot(a_mesh.data.shape_keys, b_mesh.data.shape_keys)
        self.assertEqual(tuple(result.actors[1][1].location), (3, 0, 0))
        for application, pivot in result.actors:
            rigs = {o for o in application.objects if o.type == "ARMATURE"}
            self.assertTrue(rigs)
            for obj in application.objects:
                self.assertEqual(obj["scenario_hero_id"], "hero")
                for modifier in obj.modifiers:
                    if modifier.type == "ARMATURE":
                        self.assertIn(modifier.object, rigs)
            self.assertEqual(pivot["scenario_reference_task"], "hero-reference")
        images = set(bpy.data.images) - self.before["images"]
        self.assertTrue(images)
        self.assertTrue(all(image.packed_file and not image.filepath for image in images))
        bpy.context.window.scene = result.scene
        try:
            bpy.context.view_layer.update()
            graph = bpy.context.evaluated_depsgraph_get()
            for application, pivot in result.actors:
                bounds = [
                    evaluated.matrix_world @ Vector(corner)
                    for obj in application.objects
                    if obj.type == "MESH"
                    for evaluated in (obj.evaluated_get(graph),)
                    for corner in evaluated.bound_box
                ]
                for axis in (0, 1):
                    center = (min(p[axis] for p in bounds) + max(p[axis] for p in bounds)) / 2
                    self.assertAlmostEqual(center, pivot.location[axis], places=4)
                self.assertAlmostEqual(min(p.z for p in bounds), pivot.location.z, places=4)
                # The asset's 90-degree Z orientation moves its normalized X width onto Y.
                self.assertAlmostEqual(
                    max(p.y for p in bounds) - min(p.y for p in bounds), 2, places=4
                )
        finally:
            bpy.context.window.scene = self.old_scene

    def test_static_flat_hero_without_size_override_is_supported(self):
        self.actors()
        result = self.build(heroes={"hero": self.source()})
        self.assertEqual(len(result.actors), 1)
        self.unchanged_context()

    def test_imported_morph_hold_loop_speed_and_stop_evaluate_independently(self):
        self.actors(2)
        first, second = self.raw["shots"][0]["actors"]
        first.update(action="hold", phase=0.5)
        second.update(action="loop", action_speed=2, action_until=2)
        result = self.build(heroes={"hero": self.source(animated_glb(clips=1))})
        shapes = [
            next(o.data.shape_keys for o in application.objects if o.type == "MESH")
            for application, _pivot in result.actors
        ]
        bpy.context.window.scene = result.scene
        try:
            values = []
            for frame in (1, 8.5, 16, 60.5, 120):
                result.scene.frame_set(int(frame), subframe=frame % 1)
                bpy.context.view_layer.update()
                values.append(tuple(shape.key_blocks[1].value for shape in shapes))
            self.assertTrue(all(abs(pair[0] - 0.5) < 0.001 for pair in values))
            self.assertAlmostEqual(values[0][1], 0, places=3)
            self.assertAlmostEqual(values[1][1], 0.5, places=3)
            self.assertAlmostEqual(values[2][1], 0, places=3)
            self.assertAlmostEqual(values[3][1], values[4][1], places=3)
        finally:
            bpy.context.window.scene = self.old_scene

    def test_animation_stop_matches_motion_at_the_same_editorial_time(self):
        self.actors()
        actor = self.raw["shots"][0]["actors"][0]
        actor.update(
            action="loop", action_until=1.25, keyframes=[{"time": 1.25, "location": [1, 0, 0]}]
        )
        for fps in (24, 30, 60):
            self.raw["fps"] = fps
            result = self.build(heroes={"hero": self.source(animated_glb(clips=1))})
            application, pivot = result.actors[0]
            frame = submodule("blender.shot_planner").fcurves_of(pivot)[0].keyframe_points[0].co.x
            for obj in application.objects:
                owners = [obj]
                if obj.type == "MESH" and obj.data.shape_keys:
                    owners.append(obj.data.shape_keys)
                for owner in owners:
                    if owner.animation_data:
                        strips = [
                            strip
                            for track in owner.animation_data.nla_tracks
                            if not track.mute
                            for strip in track.strips
                        ]
                        for strip in strips:
                            self.assertAlmostEqual(strip.frame_end, frame, places=4)

    def test_tampered_hero_fails_before_creating_data(self):
        self.actors()
        source = self.source()
        source.path.write_bytes(b"changed")
        with self.assertRaisesRegex(RuntimeError, "changed"):
            self.build(heroes={"hero": source})
        self.assertEqual(self.builder._snapshot(), self.before)
        self.unchanged_context()

    def test_zero_action_stop_holds_the_initial_imported_pose(self):
        self.actors()
        self.raw["shots"][0]["actors"][0].update(action="loop", action_until=0)
        result = self.build(heroes={"hero": self.source(animated_glb(clips=1))})
        application = result.actors[0][0]
        shape = next(o.data.shape_keys for o in application.objects if o.type == "MESH")
        bpy.context.window.scene = result.scene
        try:
            for frame in (1, 15, 60, 120):
                result.scene.frame_set(frame)
                self.assertAlmostEqual(shape.key_blocks[1].value, 0, places=3)
        finally:
            bpy.context.window.scene = self.old_scene

    def test_missing_hero_and_duplicate_placeholder_names_do_not_mutate(self):
        self.actors()
        with self.assertRaisesRegex(ValueError, "every shot hero"):
            self.build()
        self.raw.pop("heroes")
        self.raw["shots"][0].pop("actors")
        objects = self.raw["shots"][0]["scene"]["objects"]
        objects.append(copy.deepcopy(objects[0]))
        with self.assertRaisesRegex(ValueError, "unique"):
            self.build()
        self.assertEqual(self.builder._snapshot(), self.before)

    def test_failed_second_hero_removes_first_hero_scene_and_resources(self):
        self.actors(2)
        source = self.source(animated_glb())
        original = self.builder._hero
        calls = []

        def fail(*args, **kwargs):
            calls.append(True)
            if len(calls) == 2:
                raise RuntimeError("Synthetic second hero failure")
            return original(*args, **kwargs)

        with patch.object(self.builder, "_hero", side_effect=fail):
            with self.assertRaisesRegex(RuntimeError, "second hero"):
                self.build(heroes={"hero": source})
        self.assertEqual(self.builder._snapshot(), self.before)
        self.unchanged_context()

    def test_receipt_is_rechecked_after_local_preflight(self):
        self.actors()
        source = self.source()
        original = self.builder._lighting

        def replace_file(*args):
            original(*args)
            source.path.write_bytes(b"changed after preflight")

        with patch.object(self.builder, "_lighting", side_effect=replace_file):
            with self.assertRaises(RuntimeError):
                self.build(heroes={"hero": source})
        self.assertEqual(self.builder._snapshot(), self.before)
        self.unchanged_context()

    def test_failure_during_native_geometry_build_rolls_back_world_and_curves(self):
        original = self.builder._lighting

        def fail(*args):
            original(*args)
            raise RuntimeError("Synthetic lighting failure")

        with patch.object(self.builder, "_lighting", side_effect=fail):
            with self.assertRaisesRegex(RuntimeError, "lighting"):
                self.build()
        self.assertEqual(self.builder._snapshot(), self.before)
        self.unchanged_context()

    def test_repeated_shot_builds_preserve_prior_take(self):
        first = self.build()
        before = [(obj, tuple(obj.matrix_world)) for obj in first.scene.objects]
        second = self.build()
        self.assertNotEqual(first.scene, second.scene)
        self.assertEqual(
            first.scene["scenario_film_shot_id"], second.scene["scenario_film_shot_id"]
        )
        self.assertTrue(set(first.scene.objects).isdisjoint(second.scene.objects))
        self.assertEqual(before, [(obj, tuple(obj.matrix_world)) for obj in first.scene.objects])
        self.unchanged_context()

    def test_saving_new_scene_retains_metadata_camera_and_packed_hero(self):
        self.actors()
        result = self.build(heroes={"hero": self.source()})
        path = self.root / "shot.blend"
        bpy.data.libraries.write(str(path), {result.scene})
        with bpy.data.libraries.load(str(path), link=False) as (source, target):
            target.scenes = source.scenes
        loaded = target.scenes[0]
        self.assertEqual(
            loaded["scenario_film_recipe_sha256"], result.scene["scenario_film_recipe_sha256"]
        )
        self.assertIsNotNone(loaded.camera)
        self.assertEqual(json.loads(loaded["scenario_film_shot"])["id"], "shot")
        self.assertTrue(
            any(o.get("scenario_asset_policy") == "preserve_hero" for o in loaded.objects)
        )
        self.unchanged_context()

    def test_worker_cannot_build_shot(self):
        with ThreadPoolExecutor(max_workers=1) as pool:
            with self.assertRaisesRegex(RuntimeError, "main thread"):
                pool.submit(self.build).result()
        self.assertEqual(self.builder._snapshot(), self.before)

    def test_unknown_shot_and_invalid_recipe_leave_existing_data(self):
        with self.assertRaisesRegex(ValueError, "Select a shot"):
            self.builder.build_shot(self.raw, production_id="production", shot_id="absent")
        self.raw["shots"][0]["scene"]["objects"][0]["type"] = "script"
        with self.assertRaises(ValueError):
            self.build()
        self.assertEqual(self.builder._snapshot(), self.before)

    def test_timeline_preserves_shots_and_uses_exact_editorial_order(self):
        second = copy.deepcopy(self.raw["shots"][0])
        second.update(id="second", title="Second shot", duration=2)
        self.raw["shots"].append(second)
        first = self.build()
        other = self.builder.build_shot(self.raw, production_id="production", shot_id="second")
        before = tuple(
            (scene, scene.frame_start, scene.frame_end, scene.camera)
            for scene in (first.scene, other.scene)
        )
        timeline = self.builder.build_timeline(
            self.raw, production_id="production", shots={"shot": first, "second": other}
        )
        strips = tuple(timeline.sequence_editor.strips)
        self.assertEqual([s.scene for s in strips], [first.scene, other.scene])
        self.assertTrue(all(s.scene_input == "CAMERA" for s in strips))
        self.assertEqual(
            [(s.frame_final_start, s.frame_final_end) for s in strips], [(1, 121), (121, 181)]
        )
        self.assertEqual(
            (timeline.frame_start, timeline.frame_end, timeline.render.fps), (1, 180, 30)
        )
        self.assertTrue(timeline.render.use_sequencer)
        self.assertEqual([m.frame for m in timeline.timeline_markers], [1, 121])
        self.assertEqual(
            before,
            tuple(
                (scene, scene.frame_start, scene.frame_end, scene.camera)
                for scene in (first.scene, other.scene)
            ),
        )
        self.unchanged_context()

    def test_timeline_rejects_foreign_recipe_identity_timing_and_removed_shot(self):
        result = self.build()
        before = self.builder._snapshot()
        for key, value in (
            ("scenario_film_production_id", "other"),
            ("scenario_film_recipe_sha256", "a" * 64),
        ):
            previous = result.scene[key]
            result.scene[key] = value
            with self.assertRaisesRegex(ValueError, "matching"):
                self.builder.build_timeline(
                    self.raw, production_id="production", shots={"shot": result}
                )
            result.scene[key] = previous
            self.assertEqual(self.builder._snapshot(), before)
        result.scene.frame_end += 1
        with self.assertRaisesRegex(ValueError, "timing"):
            self.builder.build_timeline(
                self.raw, production_id="production", shots={"shot": result}
            )
        bpy.data.scenes.remove(result.scene)
        remaining = self.builder._snapshot()
        with self.assertRaisesRegex(ValueError, "matching"):
            self.builder.build_timeline(
                self.raw, production_id="production", shots={"shot": result}
            )
        self.assertEqual(self.builder._snapshot(), remaining)

    def test_timeline_requires_complete_shot_selection_before_mutation(self):
        with self.assertRaisesRegex(ValueError, "every shot"):
            self.builder.build_timeline(self.raw, production_id="production", shots={})
        self.assertEqual(self.builder._snapshot(), self.before)
        self.unchanged_context()
