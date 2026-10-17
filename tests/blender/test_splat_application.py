# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Decoded Gaussian splats become a fresh point cloud at the approved cursor.

Decoding runs on a worker thread; the build, its Geometry Nodes group and material
run on Blender's main thread and never reuse existing data. Renders check that
the points evaluate in Cycles and, where the harness has a GPU context, EEVEE.
"""

import io
import math
import os
import sys
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import bpy
from helpers import reset_scene, splat_ply_bytes, splat_records, spz_bytes, submodule


def set_modifier_input(modifier, identifier, value):
    """Blender 5.2 moved Geometry Nodes modifier inputs from ID properties to `properties`."""
    if hasattr(modifier, "properties"):
        getattr(modifier.properties.inputs, identifier).value = value
    else:
        modifier[identifier] = value


class SplatApplicationTests(unittest.TestCase):
    def setUp(self):
        reset_scene()
        self.module = submodule("blender.splat_application")
        self.model = submodule("blender.model_application")
        self.splats = submodule("core.scene.splats")
        self.scene = bpy.context.scene
        self.existing = bpy.data.objects.new("Keep selection", None)
        self.scene.collection.objects.link(self.existing)
        self.existing.select_set(True)
        bpy.context.view_layer.objects.active = self.existing
        self.before = self.data()

    def data(self):
        return {name: set(getattr(bpy.data, name)) for name in self.module._DATA}

    def decode(self, data, media_type, *, max_points=100, axes="OPENGL"):
        """Decode off the main thread, as worker preparation does."""
        outcome = {}

        def run():
            outcome["worker"] = threading.current_thread() is not threading.main_thread()
            outcome["data"] = self.splats.decode(
                io.BytesIO(data),
                media_type,
                options=self.splats.SplatOptions(max_points, axes),
                size=len(data),
            )

        with ThreadPoolExecutor(max_workers=1) as pool:
            pool.submit(run).result(30)
        self.assertTrue(outcome["worker"])
        return outcome["data"]

    def apply(self, splat, cursor=(4.0, 5.0, 6.0), fmt="spz"):
        return self.module.import_splat(
            self.scene, splat, cursor=cursor, unit_key="splat-key", members=("splat-key",), fmt=fmt
        )

    def world_points(self, application):
        (obj,) = application.objects
        return [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]

    def assert_bottom_center(self, application, cursor):
        points = self.world_points(application)
        low = [min(point[i] for point in points) for i in range(3)]
        high = [max(point[i] for point in points) for i in range(3)]
        center = ((low[0] + high[0]) / 2, (low[1] + high[1]) / 2, low[2])
        for actual, expected in zip(center, cursor, strict=True):
            self.assertAlmostEqual(actual, expected, places=4)

    def evaluated_points(self, obj):
        """Read the evaluated point cloud while its geometry set is alive."""
        evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        geometry = evaluated.evaluated_geometry()
        cloud = geometry.pointcloud
        return SimpleNamespace(
            count=len(cloud.points),
            radii=[value.value for value in cloud.attributes["radius"].data],
            materials=[material.original for material in cloud.materials],
        )

    def test_spz_versions_import_thinned_points_at_the_cursor(self):
        points = [(index, 1, -index) for index in range(10)]
        for version in (2, 3):
            with self.subTest(version=version):
                splat = self.decode(spz_bytes(points, version=version), "model/spz", max_points=4)
                self.assertEqual((splat.count, splat.kept, splat.step), (10, 4, 3))
                application = self.apply(splat)
                (obj,) = application.objects
                self.assertEqual(len(obj.data.vertices), 4)
                self.assertEqual(self.evaluated_points(obj).count, 4)
                self.assert_bottom_center(application, (4.0, 5.0, 6.0))
                self.assertIn(application.collection, tuple(self.scene.collection.children))
                self.assertEqual(obj.parent, application.root)
                self.assertEqual(application.root["scenario_asset"], "splat-key")
                self.assertEqual(application.root["scenario_assets"], "splat-key")
                self.assertEqual(
                    (obj["scenario_splat_points"], obj["scenario_splat_kept"]), (10, 4)
                )
                self.assertEqual(
                    application.splat,
                    {
                        "points_total": 10,
                        "points_kept": 4,
                        "step": 3,
                        "axes": "OPENGL",
                        "spz_extensions": False,
                    },
                )
                self.assertEqual(application.format, "spz")
                self.assertEqual(set(bpy.context.selected_objects), {self.existing})
                self.assertEqual(bpy.context.view_layer.objects.active, self.existing)

    def test_target_size_scales_the_splat_centres_with_the_bottom_center_at_the_cursor(self):
        # OPENGL centres span 9 m along x and z: the longest side becomes 3 m.
        splat = self.decode(spz_bytes([(index, 1, -index) for index in range(10)]), "model/spz")
        application = self.module.import_splat(
            self.scene,
            splat,
            cursor=(4.0, 5.0, 6.0),
            unit_key="splat-key",
            members=("splat-key",),
            fmt="spz",
            target_size=3.0,
        )
        self.assertEqual(application.target_size, 3.0)
        self.assertAlmostEqual(application.scale, 1 / 3)
        for value in application.root.scale:
            self.assertAlmostEqual(value, 1 / 3, places=6)
        points = self.world_points(application)
        low = [min(point[i] for point in points) for i in range(3)]
        high = [max(point[i] for point in points) for i in range(3)]
        self.assertAlmostEqual(
            max(hi - lo for lo, hi in zip(low, high, strict=True)), 3.0, places=4
        )
        self.assert_bottom_center(application, (4.0, 5.0, 6.0))
        # The reported size is the displayed points, which extend past their centres.
        self.assertEqual(len(application.dimensions), 3)
        centres = [hi - lo for lo, hi in zip(low, high, strict=True)]
        for reported, extent in zip(application.dimensions, centres, strict=True):
            self.assertGreater(reported, extent)
        self.assertLess(application.bottom, 6.0)
        self.assertEqual(set(bpy.context.selected_objects), {self.existing})

    def test_unmeasurable_splats_refuse_a_target_size_before_building(self):
        splat = self.decode(spz_bytes([(1, 1, 1)]), "model/spz")
        with self.assertRaisesRegex(self.model.ModelApplicationError, "no measurable size"):
            self.module.import_splat(
                self.scene,
                splat,
                cursor=(0.0, 0.0, 0.0),
                unit_key="splat-key",
                members=("splat-key",),
                fmt="spz",
                target_size=1.0,
            )
        self.assertEqual(self.data(), self.before)

    def test_saved_axes_choose_which_way_is_up(self):
        # Saved +y is up in OPENGL (right/up/back) and down in OPENCV (right/down/forward).
        data = splat_records([(0.0, 0.0, 0.0), (0.0, 2.0, 0.0), (0.0, 0.0, 3.0)])
        for axes, expected in (
            ("OPENGL", [(0, 0, 0), (0, 0, 2), (0, -3, 0)]),
            ("OPENCV", [(0, 0, 0), (0, 0, -2), (0, 3, 0)]),
        ):
            with self.subTest(axes=axes):
                splat = self.decode(data, "model/splat", axes=axes)
                application = self.apply(splat, cursor=(0.0, 0.0, 0.0), fmt="splat")
                (obj,) = application.objects
                local = [tuple(round(value, 4) for value in v.co) for v in obj.data.vertices]
                self.assertEqual(local, [tuple(float(v) for v in row) for row in expected])
                self.assertEqual(obj["scenario_splat_axes"], axes)
                self.assert_bottom_center(application, (0.0, 0.0, 0.0))

    def test_gaussian_ply_points_carry_activated_colour_opacity_and_radius(self):
        rows = [
            (float(index), 0.0, 0.0, 1.0, -1.0, 0.0, 0.0, *(math.log(0.05),) * 3)
            for index in range(3)
        ]
        splat = self.decode(splat_ply_bytes(rows), "model/ply", axes="OPENCV")
        application = self.apply(splat, fmt="ply")
        (obj,) = application.objects
        attributes = obj.data.attributes
        color = attributes["splat_color"].data[0].color
        self.assertAlmostEqual(color[0], 0.5 + 0.28209479177387814, places=5)
        self.assertAlmostEqual(color[1], 0.5 - 0.28209479177387814, places=5)
        self.assertAlmostEqual(attributes["splat_opacity"].data[0].value, 0.5, places=5)
        self.assertAlmostEqual(attributes["splat_radius"].data[0].value, 0.05, places=5)
        cloud = self.evaluated_points(obj)
        self.assertEqual(cloud.count, 3)
        (material,) = self.data()["materials"] - self.before["materials"]
        self.assertEqual(cloud.materials, [material])
        self.assertEqual(material.node_tree.nodes["Splat colour"].attribute_name, "splat_color")

    def test_new_node_group_and_material_never_reuse_existing_data(self):
        material = bpy.data.materials.new("Scenario Splat")
        material.diffuse_color = (0.1, 0.2, 0.3, 1.0)
        color = tuple(material.diffuse_color)
        group = bpy.data.node_groups.new("Scenario Splat Points", "GeometryNodeTree")
        self.before = self.data()
        splat = self.decode(splat_records([(0.0, 0.0, 0.0), (1.0, 0.0, 0.0)]), "model/splat")
        (obj,) = self.apply(splat, fmt="splat").objects
        modifier = obj.modifiers["Scenario Splat Points"]
        self.assertEqual(modifier.type, "NODES")
        self.assertIsNot(modifier.node_group, group)
        self.assertIn(modifier.node_group, self.data()["node_groups"] - self.before["node_groups"])
        used = modifier.node_group.nodes["Set Material"].inputs["Material"].default_value
        self.assertIsNot(used, material)
        self.assertIn(used, self.data()["materials"] - self.before["materials"])
        self.assertEqual(tuple(material.diffuse_color), color)
        self.assertEqual(len(group.nodes), 0)
        self.assertEqual(material.users, 0)

    def test_radius_follows_point_scale_and_a_percentile_cap(self):
        points = [(float(index), 0.0, 0.0) for index in range(200)]
        data = splat_records(points[:199], scale=0.01) + splat_records(points[199:], scale=500.0)
        splat = self.decode(data, "model/splat", max_points=1000)
        (obj,) = self.apply(splat, fmt="splat").objects
        modifier = obj.modifiers["Scenario Splat Points"]
        tree = modifier.node_group
        cap = tree.interface.items_tree["Max radius"].default_value
        self.assertAlmostEqual(cap, self.module.max_radius(splat), places=6)
        self.assertAlmostEqual(cap, 0.01, places=6)
        radii = self.evaluated_points(obj).radii
        self.assertAlmostEqual(max(radii), cap, places=6)
        self.assertAlmostEqual(min(radii), 0.01, places=6)
        set_modifier_input(modifier, tree.interface.items_tree["Point scale"].identifier, 0.5)
        obj.update_tag()
        radii = self.evaluated_points(obj).radii
        self.assertAlmostEqual(min(radii), 0.005, places=6)

    def render_center(self, engine):
        points = [(x, 0.0, y) for x in (-1.0, 0.0, 1.0) for y in (-1.0, 0.0, 1.0)]
        splat = self.decode(splat_records(points), "model/splat", axes="OPENCV")
        self.apply(splat, cursor=(0.0, 0.0, 0.0), fmt="splat")
        camera = bpy.data.objects.new("Splat camera", bpy.data.cameras.new("Splat camera"))
        camera.data.type, camera.data.ortho_scale = "ORTHO", 4.0
        camera.location = (0.0, 0.0, 10.0)
        self.scene.collection.objects.link(camera)
        self.scene.camera, self.scene.world = camera, None
        self.scene.view_settings.view_transform = "Standard"
        render = self.scene.render
        render.engine, render.resolution_x, render.resolution_y = engine, 16, 16
        render.resolution_percentage = 100
        if engine == "CYCLES":
            self.scene.cycles.device, self.scene.cycles.samples = "CPU", 4
        with tempfile.TemporaryDirectory() as directory:
            render.filepath = os.path.join(directory, "splats.png")
            bpy.ops.render.render(write_still=True)
            image = bpy.data.images.load(render.filepath)
            try:
                pixels = list(image.pixels)
            finally:
                bpy.data.images.remove(image)
        bpy.data.objects.remove(camera)
        index = (8 * 16 + 8) * 4
        return pixels[index : index + 3], pixels[:3]

    def test_points_render_their_colour_in_cycles(self):
        center, corner = self.render_center("CYCLES")
        self.assertGreater(center[0], 0.9)
        self.assertLess(max(center[1:]), 0.05)
        self.assertEqual(corner, [0.0, 0.0, 0.0])

    @unittest.skipUnless(sys.platform == "darwin", "EEVEE needs the GPU context of macOS runs")
    def test_points_render_their_colour_in_eevee(self):
        center, corner = self.render_center("BLENDER_EEVEE")
        self.assertGreater(center[0], 0.9)
        self.assertLess(max(center[1:]), 0.05)
        self.assertEqual(corner, [0.0, 0.0, 0.0])

    def test_failed_publication_restores_every_datablock(self):
        splat = self.decode(spz_bytes([(0, 0, 0), (1, 1, 1)]), "model/spz")
        original = self.module._publish

        def fail(*args):
            original(*args)
            raise RuntimeError("synthetic publication failure")

        with patch.object(self.module, "_publish", side_effect=fail):
            with self.assertRaises(self.model.ModelApplicationError):
                self.apply(splat)
        self.assertEqual(self.data(), self.before)
        with (
            patch.object(self.module, "_publish", side_effect=fail),
            patch.object(self.module, "_remove_new_data"),
            self.assertRaisesRegex(RuntimeError, "cleanup is incomplete"),
        ):
            self.apply(splat)
        self.assertEqual(set(bpy.context.selected_objects), {self.existing})

    def test_build_refuses_worker_threads_and_unprepared_payloads(self):
        splat = self.decode(spz_bytes([(0, 0, 0)]), "model/spz")
        with ThreadPoolExecutor(max_workers=1) as pool:
            with self.assertRaisesRegex(self.model.ModelApplicationError, "main thread"):
                pool.submit(self.apply, splat).result(10)
        with self.assertRaises(self.model.ModelApplicationError):
            self.apply(None)
        self.assertEqual(self.data(), self.before)

    def test_prototype_spz_import_delegates_to_the_fresh_builder(self):
        material = bpy.data.materials.new("Scenario Splat")
        material.diffuse_color = (0.1, 0.2, 0.3, 1.0)
        color = tuple(material.diffuse_color)
        path = Path(tempfile.mkdtemp(prefix="scenario-spz-")) / "world.spz"
        path.write_bytes(spz_bytes([(index, 1, 0) for index in range(6)]))
        obj = submodule("blender.apply_splat").import_spz(bpy.context, path, max_points=3)
        self.assertEqual(len(obj.data.vertices), 3)
        self.assertIn("splat_color", obj.data.attributes)
        used = obj.modifiers[0].node_group.nodes["Set Material"].inputs["Material"].default_value
        self.assertIsNot(used, material)
        self.assertEqual(tuple(material.diffuse_color), color)


if __name__ == "__main__":
    unittest.main()
