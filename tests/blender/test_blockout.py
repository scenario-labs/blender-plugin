# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
import math
import unittest
from unittest.mock import patch

import bpy
from bpy_extras.object_utils import world_to_camera_view
from helpers import reset_scene, submodule
from mathutils import Vector


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
        self.view = submodule("core.scene.blockout_view")

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
        # By default a group's colour, in group order: Ground, Center, Buildings.
        self.assertEqual(
            tuple(round(c, 3) for c in well.color),
            tuple(round(c, 3) for c in self.view.group_colour(1)),
        )

    def test_build_without_dressing_keeps_the_category_colours(self):
        els = [_el("Well", "water", "cylinder", group="Center")]
        well = self.blockout.build_blockout(bpy.context, els, dress=False)[0]
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


def _garden():
    """Four groups over a ground slab, one rotated and off-centre, so the bounds are not square."""
    return [
        _el("Ground", "floor", "plane", (0, 0, -0.05), (40, 24, 0.1), group="Ground"),
        _el("Pond", "water", "cylinder", (-9, 5, 0.1), (8, 6, 0.2), 20, group="Pond"),
        _el("Teahouse", "structure", "box", (8, -4, 2), (7, 5, 4), 30, group="Teahouse"),
        _el("Roof", "structure", "wedge", (8, -4, 4.75), (8, 6, 1.5), 30, group="Teahouse"),
        _el("Pine", "vegetation", "cone", (-12, -8, 3.5), (4, 4, 7), group="Trees"),
        _el("Lantern", "light", "sphere", (2, 9, 0.5), (0.6, 0.6, 1), group="Trees"),
    ]


def _of_type(kind):
    return [obj for obj in bpy.data.objects if obj.type == kind]


def _blocks():
    return {
        name: set(getattr(bpy.data, name))
        for name in ("objects", "cameras", "lights", "materials", "collections")
    }


class BlockoutViewTests(unittest.TestCase):
    """A built blockout reads at once: a colour and material per group, a camera and a sun."""

    def setUp(self):
        reset_scene()
        self.blockout = submodule("blender.blockout")
        self.bview = submodule("blender.blockout_view")
        self.view = submodule("core.scene.blockout_view")
        self.scene = bpy.context.scene

    def build(self, elements=None, **options):
        return self.blockout.build_blockout(bpy.context, elements or _garden(), **options)

    def corners(self, obj):
        return [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]

    def assert_framed(self, created):
        bpy.context.view_layer.update()
        camera = self.scene.camera
        self.assertIsNotNone(camera)
        for obj in created:
            for corner in self.corners(obj):
                x, y, depth = world_to_camera_view(self.scene, camera, corner)
                self.assertGreater(depth, camera.data.clip_start, obj.name)
                self.assertLess(depth, camera.data.clip_end, obj.name)
                for axis in (x, y):
                    self.assertGreaterEqual(axis, 0.0, obj.name)
                    self.assertLessEqual(axis, 1.0, obj.name)

    def test_each_group_gets_its_own_palette_colour_in_group_order(self):
        created = self.build()
        by_group = {}
        for obj, element in zip(created, _garden(), strict=True):
            by_group.setdefault(element["group"], set()).add(tuple(round(c, 4) for c in obj.color))
        self.assertEqual(list(by_group), ["Ground", "Pond", "Teahouse", "Trees"])
        for index, colours in enumerate(by_group.values()):
            expected = tuple(round(c, 4) for c in self.view.group_colour(index))
            self.assertEqual(colours, {expected})
        self.assertEqual(len({next(iter(c)) for c in by_group.values()}), 4)  # all distinct

    def test_each_group_shares_one_material_that_renders_in_its_colour(self):
        created = self.build()
        materials = {}
        for obj, element in zip(created, _garden(), strict=True):
            slot = obj.material_slots[0]
            self.assertEqual(slot.link, "OBJECT")
            materials.setdefault(element["group"], set()).add(slot.material)
        self.assertEqual({len(group) for group in materials.values()}, {1})
        self.assertEqual(len({next(iter(group)) for group in materials.values()}), 4)
        for index, group in enumerate(materials.values()):
            material = next(iter(group))
            expected = self.view.group_colour(index)
            self.assertEqual(
                tuple(round(c, 4) for c in material.diffuse_color),
                tuple(round(c, 4) for c in expected),
            )
            base = material.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value
            self.assertEqual(tuple(round(c, 4) for c in base), tuple(round(c, 4) for c in expected))
        # The unit meshes stay shared: a material on the object, not on the primitive's mesh.
        meshes = {obj.data for obj in created}
        self.assertEqual(
            len(meshes), 6
        )  # one per primitive: box, plane, cylinder, wedge, cone, sphere
        self.assertTrue(all(mesh.materials[0] is None for mesh in meshes))

    def test_a_follow_up_reuses_the_materials_and_drops_the_unused_ones(self):
        self.build()
        first = {m.name: m for m in bpy.data.materials if self.bview.GROUP_KEY in m}
        self.assertEqual(len(first), 4)
        followup = _garden() + [_el("Bridge", "structure", "box", (0, 5, 0.3), group="Bridge")]
        self.build(followup)
        second = {m.name: m for m in bpy.data.materials if self.bview.GROUP_KEY in m}
        self.assertEqual(len(second), 5)
        for name, material in first.items():
            self.assertIs(second[name], material)  # the same data-block, not "Name.001"
        self.assertFalse(any("." in name.rpartition(" ")[2] for name in second))
        # Dropping a group removes its material, which nothing uses any more.
        self.build([el for el in followup if el["group"] != "Trees"])
        left = {m[self.bview.GROUP_KEY] for m in bpy.data.materials if self.bview.GROUP_KEY in m}
        self.assertEqual(left, {"Ground", "Pond", "Teahouse", "Bridge"})

    def test_a_rebuild_keeps_each_group_colour_in_solid_and_material_views(self):
        def looks():
            seen = {}
            for obj in bpy.data.objects:
                if obj.type != "MESH" or not obj.material_slots:
                    continue
                material = obj.material_slots[0].material
                group = material[self.bview.GROUP_KEY]
                colour = tuple(round(c, 3) for c in obj.color)
                self.assertEqual(colour, tuple(round(c, 3) for c in material.diffuse_color))
                seen.setdefault(group, colour)
            return seen

        self.build()
        first = looks()
        # Trees first, Pond gone, a new Bridge group: kept groups keep their colour.
        garden = [el for el in _garden() if el["group"] != "Pond"]
        trees = [el for el in garden if el["group"] == "Trees"]
        bridge = _el("Bridge", "structure", "box", (0, 5, 0.3), group="Bridge")
        self.build(trees + [bridge] + garden[:3])
        second = looks()
        for group in ("Ground", "Teahouse", "Trees"):
            self.assertEqual(second[group], first[group])
        self.assertEqual(len(set(second.values())), len(second))

    def test_user_objects_and_materials_are_never_recoloured_or_reused(self):
        mine = bpy.data.objects.new("Mine", bpy.data.meshes.new("Mine"))
        mine.color = (0.1, 0.2, 0.3, 1.0)
        self.scene.collection.objects.link(mine)
        user_material = bpy.data.materials.new("Blockout Ground")
        user_material.diffuse_color = (0.9, 0.9, 0.1, 1.0)
        self.build()
        self.assertEqual(tuple(round(c, 4) for c in mine.color), (0.1, 0.2, 0.3, 1.0))
        self.assertEqual(
            tuple(round(c, 3) for c in user_material.diffuse_color), (0.9, 0.9, 0.1, 1.0)
        )
        ground = bpy.data.objects["Ground"].material_slots[0].material
        self.assertIsNot(ground, user_material)
        self.blockout.clear_blockout(self.scene)
        # Clearing purges only the group materials this build made.
        self.assertIn(user_material.name, bpy.data.materials)

    def test_an_empty_scene_gets_a_camera_that_frames_every_object_and_one_sun(self):
        created = self.build()
        self.assertEqual(len(_of_type("CAMERA")), 1)
        self.assertEqual(len(_of_type("LIGHT")), 1)
        camera, sun = self.scene.camera, _of_type("LIGHT")[0]
        self.assertEqual(camera.type, "CAMERA")
        self.assertEqual(sun.data.type, "SUN")
        self.assertIn(camera.name, self.scene.collection.objects)  # outside the Blockout tree
        self.assertIn(sun.name, self.scene.collection.objects)
        self.assert_framed(created)
        # Three-quarter and a little above: off both axes, looking down at the middle.
        centre = sum((Vector(c) for obj in created for c in self.corners(obj)), Vector()) / (
            8 * len(created)
        )
        self.assertGreater(camera.location.z, centre.z)
        self.assertGreater(camera.location.x, centre.x)
        self.assertLess(camera.location.y, centre.y)
        self.assertLess(
            math.degrees(
                math.atan2(camera.location.z - centre.z, (camera.location.xy - centre.xy).length)
            ),
            45.0,
        )

    def test_the_camera_frames_every_object_for_any_render_aspect(self):
        for width, height in ((1920, 1080), (1080, 1920), (1000, 1000), (2048, 858)):
            with self.subTest(size=(width, height)):
                reset_scene()
                scene = bpy.context.scene
                scene.render.resolution_x, scene.render.resolution_y = width, height
                self.scene = scene
                self.assert_framed(self.build())

    def test_a_follow_up_adds_no_second_camera_or_light(self):
        self.build()
        camera, sun = self.scene.camera, _of_type("LIGHT")[0]
        placed = camera.matrix_world.copy(), sun.matrix_world.copy()
        self.build(_garden() + [_el("Bridge", "structure", "box", (30, 5, 0.3), (12, 2, 0.6))])
        self.assertEqual(len(_of_type("CAMERA")), 1)
        self.assertEqual(len(_of_type("LIGHT")), 1)
        self.assertIs(self.scene.camera, camera)
        self.assertEqual(len(bpy.data.cameras), 1)
        self.assertEqual(len(bpy.data.lights), 1)
        self.assertEqual((camera.matrix_world, sun.matrix_world), placed)

    def test_a_users_camera_and_light_are_left_alone(self):
        data = bpy.data.cameras.new("My camera")
        mine = bpy.data.objects.new("My camera", data)
        mine.location, mine.rotation_euler = (3, -2, 5), (1.0, 0.0, 0.2)
        light = bpy.data.objects.new("My light", bpy.data.lights.new("My light", "POINT"))
        light.location = (1, 1, 6)
        for obj in (mine, light):
            self.scene.collection.objects.link(obj)
        self.scene.camera = mine
        before = mine.matrix_world.copy(), light.matrix_world.copy(), data.lens
        created = self.build()
        self.assertEqual(_of_type("CAMERA"), [mine])
        self.assertEqual(_of_type("LIGHT"), [light])
        self.assertIs(self.scene.camera, mine)
        self.assertEqual((mine.matrix_world, light.matrix_world, data.lens), before)
        self.assertEqual(created.added, ())

    def test_only_the_missing_one_is_added(self):
        light = bpy.data.objects.new("My light", bpy.data.lights.new("My light", "AREA"))
        self.scene.collection.objects.link(light)
        created = self.build()
        self.assertEqual(created.added, ("camera",))
        self.assertEqual(_of_type("LIGHT"), [light])
        self.assert_framed(created)

    def test_a_camera_that_is_not_the_scene_camera_still_counts(self):
        spare = bpy.data.objects.new("Spare", bpy.data.cameras.new("Spare"))
        self.scene.collection.objects.link(spare)
        self.assertIsNone(self.scene.camera)
        self.build()
        self.assertEqual(_of_type("CAMERA"), [spare])
        self.assertIsNone(self.scene.camera)

    def test_a_failure_while_dressing_leaves_nothing_behind(self):
        self.build([_el("Original", group="Old")], dress=False)
        kept = _blocks()
        with patch.object(self.bview, "add_sun", side_effect=RuntimeError("synthetic sun failure")):
            with self.assertRaises(RuntimeError):
                self.build()
        # The materials and camera staged before the failure are gone, the old blockout intact.
        self.assertEqual(_blocks(), kept)
        self.assertIsNone(self.scene.camera)
        self.assertIn("Original", bpy.data.objects)

    def test_a_failure_while_placing_objects_removes_the_new_materials_and_camera(self):
        kept = _blocks()
        mesh_for = self.blockout._mesh_for
        calls = 0

        def fail_fourth(primitive):
            nonlocal calls
            calls += 1
            if calls == 4:
                raise RuntimeError("synthetic placement failure")
            return mesh_for(primitive)

        with patch.object(self.blockout, "_mesh_for", side_effect=fail_fourth):
            with self.assertRaises(RuntimeError):
                self.build()
        self.assertEqual(_blocks(), kept)
        self.assertIsNone(self.scene.camera)

    def test_the_option_off_adds_no_material_camera_or_light(self):
        kept = _blocks()
        created = self.build(dress=False)
        after = _blocks()
        self.assertEqual(after["materials"], kept["materials"])
        self.assertEqual(after["cameras"], kept["cameras"])
        self.assertEqual(after["lights"], kept["lights"])
        self.assertIsNone(self.scene.camera)
        self.assertEqual(created.added, ())
        self.assertTrue(
            all(
                len(obj.material_slots) == 0 or obj.material_slots[0].material is None
                for obj in created
            )
        )

    def test_the_build_operator_follows_the_scene_option(self):
        self.assertTrue(self.scene.scenario_blockout.dress_scene)  # on by default
        self.blockout._store(self.scene, _garden())
        self.scene.scenario_blockout.dress_scene = False
        self.assertEqual(bpy.ops.scenario.blockout_build(), {"FINISHED"})
        self.assertEqual((len(_of_type("CAMERA")), len(_of_type("LIGHT"))), (0, 0))
        self.scene.scenario_blockout.dress_scene = True
        self.assertEqual(bpy.ops.scenario.blockout_build(), {"FINISHED"})
        self.assertEqual((len(_of_type("CAMERA")), len(_of_type("LIGHT"))), (1, 1))

    def test_one_undo_removes_the_blockout_with_its_camera_light_and_materials(self):
        self.assertIn("UNDO", self.blockout.SCENARIO_OT_blockout_build.bl_options)
        self.blockout._store(self.scene, _garden())
        bpy.ops.ed.undo_push(message="Before blockout")
        self.assertEqual(bpy.ops.scenario.blockout_build(), {"FINISHED"})
        # Python operator calls skip undo pushes; record the step the operator adds.
        bpy.ops.ed.undo_push(message="Build blockout")
        self.assertEqual(len(_of_type("CAMERA")), 1)
        self.assertEqual(bpy.ops.ed.undo(), {"FINISHED"})
        self.assertEqual(
            (len(_of_type("CAMERA")), len(_of_type("LIGHT")), len(bpy.data.objects)), (0, 0, 0)
        )
        self.assertEqual([m for m in bpy.data.materials if self.bview.GROUP_KEY in m], [])
        self.assertEqual(bpy.ops.ed.redo(), {"FINISHED"})
        self.assertEqual((len(_of_type("CAMERA")), len(_of_type("LIGHT"))), (1, 1))
        self.assertIsNotNone(bpy.context.scene.camera)

    def test_a_refinement_and_its_rebuild_each_undo_in_one_step(self):
        first = _garden()
        moved = {**first[-1], "position": [-5.0, 5.0, 0.5]}  # the lantern moves beside the pond
        bench = _el("Bench", "furniture", "box", (-4, 2, 0.25), (1.8, 0.5, 0.5), group="Pond")
        refined = [*first[:-1], moved, bench]
        self.blockout._store(self.scene, first)
        bpy.ops.ed.undo_push(message="Before blockout")
        self.assertEqual(bpy.ops.scenario.blockout_build(), {"FINISHED"})
        bpy.ops.ed.undo_push(message="Build blockout")
        # A refined plan lands through maintenance, which records its own step.
        self.blockout._store(self.scene, refined)
        bpy.ops.ed.undo_push(message="Scenario Blockout plan")
        self.assertEqual(bpy.ops.scenario.blockout_build(), {"FINISHED"})
        bpy.ops.ed.undo_push(message="Build blockout")
        props = self.scene.scenario_blockout
        self.assertEqual(
            {obj.name for obj in props.built_collection.all_objects},
            {element["name"] for element in refined},
        )
        self.assertEqual((len(_of_type("CAMERA")), len(_of_type("LIGHT"))), (1, 1))

        self.assertEqual(bpy.ops.ed.undo(), {"FINISHED"})
        props = bpy.context.scene.scenario_blockout
        built = {obj.name: list(obj.location) for obj in props.built_collection.all_objects}
        self.assertEqual(set(built), {element["name"] for element in first})
        self.assertEqual(built["Lantern"], first[-1]["position"])
        self.assertEqual(self.blockout.stored_plan(bpy.context.scene), refined)
        self.assertEqual(bpy.ops.ed.undo(), {"FINISHED"})
        self.assertEqual(self.blockout.stored_plan(bpy.context.scene), first)
        # Undo past the first build frees the shared primitive meshes; a new build remakes them.
        self.assertEqual(bpy.ops.ed.undo(), {"FINISHED"})
        self.assertEqual(len(bpy.data.objects), 0)
        self.assertEqual(bpy.ops.scenario.blockout_build(), {"FINISHED"})
        self.assertEqual(len(_of_type("MESH")), len(first))
