# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
import math
import unittest
from unittest.mock import patch

import bpy
from helpers import reset_scene, submodule


def _el(
    name,
    category="other",
    primitive="box",
    position=(0, 0, 0.5),
    size=(1, 1, 1),
    rotation=0.0,
    group="Blockout",
):
    return {
        "name": name,
        "category": category,
        "primitive": primitive,
        "position": list(position),
        "size": list(size),
        "rotation": rotation,
        "group": group,
    }


class BlockoutTests(unittest.TestCase):
    def setUp(self):
        reset_scene()
        self.blockout = submodule("blender.blockout")
        self.core = submodule("core.scene.blockout")

    def test_build_places_primitives_grouped_and_coloured(self):
        els = [
            _el("Ground", "floor", "plane", (0, 0, -0.05), (12, 12, 0.1), group="Ground"),
            _el(
                "Well",
                "water",
                "cylinder",
                (0, 0, 0.6),
                (1.6, 1.6, 1.2),
                rotation=30,
                group="Center",
            ),
            _el("Roof", "structure", "wedge", (4, 0, 3), (3, 3, 1.5), group="Buildings"),
        ]
        created = self.blockout.build_blockout(bpy.context, els)
        self.assertEqual([o.name for o in created], ["Ground", "Well", "Roof"])
        root = bpy.data.collections[self.blockout.COLLECTION]
        self.assertEqual(sorted(c.name for c in root.children), ["Buildings", "Center", "Ground"])
        well = bpy.data.objects["Well"]
        self.assertGreater(len(well.data.vertices), 8)  # a cylinder, not a cube
        self.assertAlmostEqual(well.rotation_euler.z, math.radians(30), places=4)
        self.assertEqual(well[self.blockout.MARK], "water")
        self.assertEqual(
            tuple(round(c, 3) for c in well.color),
            tuple(round(c, 3) for c in self.core.CATEGORIES["water"][1]) + (1.0,),
        )

    def test_rebuild_clears_the_previous_blockout(self):
        self.blockout.build_blockout(bpy.context, [_el("A", group="G")])
        self.blockout.build_blockout(bpy.context, [_el("B", group="G")])
        names = [
            o.name for o in bpy.data.collections[self.blockout.COLLECTION].children["G"].objects
        ]
        self.assertEqual(names, ["B"])  # A was cleared

    def test_retired_plan_event_does_not_mutate_current_scene(self):
        self.blockout.on_blockout_plan({"elements": [_el("Late result")]})
        self.assertNotIn("Late result", bpy.data.objects)
        self.assertEqual(self.blockout.stored_plan(bpy.context.scene), [])

    def test_clear_removes_collection_and_plan(self):
        scene = bpy.context.scene
        self.blockout._store(scene, [_el("X")])
        self.blockout.build_blockout(bpy.context, [_el("X")])
        self.assertTrue(scene.scenario_blockout.plan_json)
        bpy.ops.scenario.blockout_clear()
        self.assertNotIn(self.blockout.COLLECTION, bpy.data.collections)
        self.assertEqual(scene.scenario_blockout.plan_json, "")

    def test_blockout_is_a_lane_tab_and_can_be_selected(self):
        props = submodule("blender.props")
        self.assertIn("blockout", [k for k, _l, _d in props.LANE_ITEMS])
        bpy.context.scene.scenario.lane = "blockout"  # selectable without error
        self.assertEqual(bpy.context.scene.scenario.lane, "blockout")

    def test_named_foreign_collection_and_other_scene_are_preserved(self):
        scene = bpy.context.scene
        foreign = bpy.data.collections.new("Blockout")
        scene.collection.children.link(foreign)
        foreign_group = bpy.data.collections.new("G")
        foreign.children.link(foreign_group)
        self.blockout.build_blockout(bpy.context, [_el("First", group="G")])
        first_root = scene.scenario_blockout.built_collection
        self.assertNotEqual(first_root, foreign)
        self.assertNotIn(foreign_group, tuple(first_root.children))
        other = bpy.data.scenes.new("Other blockout scene")
        bpy.context.window.scene = other
        self.blockout.build_blockout(bpy.context, [_el("Second", group="G")])
        second_root = other.scenario_blockout.built_collection
        self.assertNotEqual(first_root, second_root)
        self.blockout.clear_blockout(other)
        self.assertIn("First", bpy.data.objects)
        self.assertIn(foreign.name, bpy.data.collections)
        bpy.context.window.scene = scene

    def test_failed_staging_preserves_old_objects_and_collection(self):
        scene = bpy.context.scene
        old = self.blockout.build_blockout(bpy.context, [_el("Original")])[0]
        root = scene.scenario_blockout.built_collection
        before = set(bpy.data.collections)
        mesh_for = self.blockout._mesh_for
        count = 0

        def fail_second(primitive):
            nonlocal count
            count += 1
            if count == 2:
                raise RuntimeError("synthetic staging failure")
            return mesh_for(primitive)

        with patch.object(self.blockout, "_mesh_for", side_effect=fail_second):
            with self.assertRaises(RuntimeError):
                self.blockout.build_blockout(bpy.context, [_el("Staged"), _el("Failure")])
        self.assertEqual(scene.scenario_blockout.built_collection, root)
        self.assertEqual(bpy.data.objects.get("Original"), old)
        self.assertNotIn("Staged", bpy.data.objects)
        self.assertEqual(set(bpy.data.collections), before)

    def test_shared_generated_tree_cannot_be_cleared_or_rebuilt(self):
        scene = bpy.context.scene
        self.blockout.build_blockout(bpy.context, [_el("Shared")])
        root = scene.scenario_blockout.built_collection
        other = bpy.data.scenes.new("Shared scene")
        other.collection.children.link(root)
        with self.assertRaises(ValueError):
            self.blockout.clear_blockout(scene)
        with self.assertRaises(ValueError):
            self.blockout.build_blockout(bpy.context, [_el("Replacement")])
        self.assertIn("Shared", bpy.data.objects)

    def test_unrelated_objects_in_generated_tree_are_preserved(self):
        scene = bpy.context.scene
        self.blockout.build_blockout(bpy.context, [_el("Generated")])
        root = scene.scenario_blockout.built_collection
        foreign = bpy.data.objects.new("User object", None)
        root.objects.link(foreign)
        with self.assertRaises(ValueError):
            self.blockout.clear_blockout(scene)
        self.assertIn(foreign.name, bpy.data.objects)
        self.assertIn("Generated", bpy.data.objects)
