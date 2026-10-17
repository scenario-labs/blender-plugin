# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""capture_views renders offscreen views onto one contact sheet and leaves the file as it was."""

import base64
import json
import math
import os
import struct
import sys
import tempfile
import unittest
import unittest.mock

import bpy
from helpers import assert_unmarked, reset_scene, submodule

GPU_RENDERS = sys.platform == "darwin"
GPU_REASON = "Workbench needs the GPU context of macOS background runs"


def targa(width, height, rgb=(200, 40, 40)):
    header = struct.pack("<BBBHHBHHHHBB", 0, 0, 2, 0, 0, 0, 0, 0, width, height, 24, 0)
    return header + bytes((rgb[2], rgb[1], rgb[0])) * (width * height)


def png_size(data):
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    return list(struct.unpack(">II", data[16:24]))


class CaptureViewsTests(unittest.TestCase):
    def setUp(self):
        reset_scene()
        self.tb = submodule("mcp.tools_blender")
        self.scene = bpy.context.scene
        bpy.ops.mesh.primitive_cube_add(location=(0, 0, 1))
        self.cube = bpy.context.active_object
        self.cube.name = "Crate"
        bpy.ops.mesh.primitive_uv_sphere_add(location=(4, 0, 1))
        bpy.context.active_object.name = "Ball"
        self.cube.select_set(False)
        bpy.context.active_object.select_set(False)
        camera = bpy.data.objects.new("Shot", bpy.data.cameras.new("Shot"))
        self.scene.collection.objects.link(camera)
        camera.location = (0, -12, 2)
        camera.rotation_euler = (math.radians(85), 0, 0)
        self.scene.camera = camera
        render = self.scene.render
        render.engine = "CYCLES"
        render.resolution_x, render.resolution_y, render.resolution_percentage = 1920, 1080, 50
        render.filepath = "//renders/shot_"
        self.scene.frame_start, self.scene.frame_end = 1, 48
        self.scene.frame_set(7)

    def state(self):
        render, scene = self.scene.render, self.scene
        settings = render.image_settings
        return {
            "render": (
                render.engine,
                render.resolution_x,
                render.resolution_y,
                render.resolution_percentage,
                render.filepath,
                render.use_compositing,
                render.film_transparent,
                render.pixel_aspect_x,
                render.pixel_aspect_y,
                settings.file_format,
                settings.color_mode,
                settings.color_depth,
                getattr(settings, "media_type", ""),
            ),
            "shading": (
                scene.display.shading.light,
                scene.display.shading.color_type,
                scene.display.shading.show_object_outline,
            ),
            "view": (scene.view_settings.view_transform, scene.view_settings.look),
            "camera": scene.camera,
            "frame": (scene.frame_current, scene.frame_subframe),
            "objects": sorted(obj.name for obj in bpy.data.objects),
            "cameras": len(bpy.data.cameras),
            "images": sorted(image.name for image in bpy.data.images),
            "selection": sorted(
                obj.name for obj in bpy.context.view_layer.objects if obj.select_get()
            ),
        }

    def capture(self, args):
        content = self.tb.capture_views(args)
        self.assertEqual([item["type"] for item in content], ["image", "text"])
        png = base64.b64decode(content[0]["data"])
        caption = json.loads(content[1]["text"])
        self.assertEqual(png_size(png), caption["size"])
        return png, caption

    def fake_tiles(self, fail_at=None):
        seen = []

        def render(scene, path):
            if fail_at is not None and len(seen) == fail_at:
                raise RuntimeError("synthetic render failure")
            camera = scene.camera
            seen.append(
                {
                    "engine": scene.render.engine,
                    "format": scene.render.image_settings.file_format,
                    "camera": camera.name,
                    "type": camera.data.type,
                    "location": tuple(round(v, 3) for v in camera.location),
                    "rotation": tuple(round(v, 3) for v in camera.rotation_euler),
                    "frame": scene.frame_current,
                }
            )
            return targa(scene.render.resolution_x, scene.render.resolution_y)

        return seen, unittest.mock.patch.object(self.tb, "_render_tile", render)

    def test_angles_frame_the_scene_from_a_temporary_camera_and_restore_everything(self):
        settings = self.scene.render.image_settings
        settings.file_format, settings.color_depth = "PNG", "16"  # Targa tiles force 8-bit
        before = self.state()
        seen, patch = self.fake_tiles()
        with patch:
            png, caption = self.capture({})
        self.assertEqual(self.state(), before)
        assert_unmarked(self)
        self.assertEqual(caption["tiles"], ["FRONT", "RIGHT", "TOP", "3/4"])
        self.assertEqual((caption["framed"], caption["object_count"]), ("scene", 2))
        self.assertEqual(caption["size"], [1280, 1280])
        self.assertEqual(caption["layout"], "2x2, reading order")
        self.assertEqual({tile["engine"] for tile in seen}, {"BLENDER_WORKBENCH"})
        self.assertEqual({tile["format"] for tile in seen}, {"TARGA_RAW"})
        self.assertEqual({tile["camera"] for tile in seen}, {"Scenario capture camera"})
        self.assertEqual([tile["type"] for tile in seen], ["ORTHO", "ORTHO", "ORTHO", "PERSP"])
        center = caption["center"]
        front, right, top = (tile["location"] for tile in seen[:3])
        self.assertLess(front[1], center[1])
        self.assertGreater(right[0], center[0])
        self.assertGreater(top[2], center[2])
        # Top looks straight down with +X right and +Y up, like Blender's Top view.
        self.assertEqual(seen[2]["rotation"], (0.0, 0.0, 0.0))

    def test_angles_frame_named_objects_or_the_selection(self):
        seen, patch = self.fake_tiles()
        with patch:
            _, named = self.capture({"objects": ["Ball"], "angles": ["top"], "max_size": 512})
            self.cube.select_set(True)
            _, selected = self.capture({"angles": ["front", "front", "left"]})
        self.assertEqual((named["framed"], named["objects"]), ("objects", ["Ball"]))
        self.assertEqual(named["center"][:2], [4.0, 0.0])
        self.assertEqual(named["size"], [512, 512])
        self.assertEqual((selected["framed"], selected["objects"]), ("selection", ["Crate"]))
        self.assertEqual(selected["tiles"], ["FRONT", "LEFT"])

    def test_a_selected_camera_is_not_framed_and_collection_instances_are(self):
        seen, patch = self.fake_tiles()
        self.scene.camera.select_set(True)
        with patch:
            _, camera_only = self.capture({"angles": ["front"]})
        self.assertEqual(camera_only["framed"], "scene")
        self.scene.camera.select_set(False)
        props = bpy.data.collections.new("Props")
        for obj in list(self.scene.collection.objects):
            if obj.type == "MESH":
                self.scene.collection.objects.unlink(obj)
                props.objects.link(obj)
        instance = bpy.data.objects.new("Props instance", None)
        instance.instance_type, instance.instance_collection = "COLLECTION", props
        instance.location = (100, 0, 0)
        self.scene.collection.objects.link(instance)
        with patch:
            _, whole = self.capture({"angles": ["front"]})
            instance.select_set(True)
            _, selected = self.capture({"angles": ["front"]})
        self.assertEqual((whole["framed"], whole["objects"]), ("scene", ["Props instance"]))
        self.assertEqual(selected["framed"], "selection")
        # Framed on the instanced cube and sphere, not on the empty's origin alone.
        self.assertAlmostEqual(selected["center"][0], 102.0, places=3)
        self.assertGreater(selected["radius"], 2.0)

    def test_pixel_aspect_is_square_while_rendering_and_restored(self):
        render = self.scene.render
        render.pixel_aspect_x = 2.0
        aspects = []

        def tile(scene, path):
            aspects.append((scene.render.pixel_aspect_x, scene.render.pixel_aspect_y))
            return targa(scene.render.resolution_x, scene.render.resolution_y)

        before = self.state()
        with unittest.mock.patch.object(self.tb, "_render_tile", tile):
            _, caption = self.capture({"mode": "frames", "frames": [1], "max_size": 512})
        self.assertEqual(aspects, [(1.0, 1.0)])
        self.assertEqual(self.state(), before)
        # 960x540 at pixel aspect 2:1 is a 32:9 picture.
        width, height = caption["size"]
        self.assertAlmostEqual((width - 8) / (height - 8), 32 / 9, delta=0.05)

    def test_frames_render_the_scene_camera_and_return_to_the_current_frame(self):
        before = self.state()
        seen, patch = self.fake_tiles()
        with patch:
            _, spread = self.capture({"mode": "frames", "frame_count": 3})
            _, chosen = self.capture({"mode": "frames", "frames": [10, 2, 10], "max_size": 640})
        self.assertEqual(self.state(), before)
        self.assertEqual(spread["frames"], [1, 24, 48])
        self.assertEqual(spread["tiles"], ["FRAME 1", "FRAME 24", "FRAME 48"])
        self.assertEqual(chosen["frames"], [10, 2])
        self.assertEqual([tile["frame"] for tile in seen], [1, 24, 48, 10, 2])
        self.assertEqual({tile["camera"] for tile in seen}, {"Shot"})
        # Tiles keep the scene camera's 16:9 shape.
        width, height = spread["size"]
        self.assertEqual(width, 1280)
        self.assertLess(height, width)

    def test_a_failed_render_restores_the_scene_and_removes_the_camera(self):
        before = self.state()
        _, patch = self.fake_tiles(fail_at=2)
        with patch, self.assertRaisesRegex(RuntimeError, "synthetic render failure"):
            self.tb.capture_views({})
        self.assertEqual(self.state(), before)

    def test_invalid_requests_are_refused_before_the_scene_changes(self):
        before = self.state()
        for args, message in (
            ({"mode": "orbit"}, "mode must be"),
            ({"angles": ["sideways"]}, "Unknown angles"),
            ({"angles": []}, "at least one view"),
            ({"objects": ["Missing"]}, "Not in this scene: Missing"),
            ({"max_size": 100}, "max_size must be"),
            ({"max_size": 4096}, "max_size must be"),
            ({"frames": [1]}, "mode frames only"),
            ({"mode": "frames", "angles": ["top"]}, "mode angles only"),
            ({"mode": "frames", "frames": [1], "frame_count": 2}, "not both"),
            ({"mode": "frames", "frames": list(range(13))}, "1 to 12"),
            ({"mode": "frames", "frame_count": 0}, "frame_count must be"),
        ):
            with self.subTest(args=args), self.assertRaisesRegex(ValueError, message):
                self.tb.capture_views(args)
        self.scene.camera = None
        with self.assertRaisesRegex(ValueError, "scene camera"):
            self.tb.capture_views({"mode": "frames"})
        self.scene.camera = before["camera"]
        self.assertEqual(self.state(), before)

    def test_an_empty_scene_has_nothing_to_frame(self):
        reset_scene()
        with self.assertRaisesRegex(ValueError, "no renderable object"):
            self.tb.capture_views({})

    @unittest.skipUnless(GPU_RENDERS, GPU_REASON)
    def test_real_workbench_sheet_shows_the_objects_and_restores_everything(self):
        before = self.state()
        png, caption = self.capture({"max_size": 512})
        self.assertEqual(self.state(), before)
        assert_unmarked(self)
        self.assertEqual(caption["size"], [512, 512])
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "sheet.png")
            with open(path, "wb") as handle:
                handle.write(png)
            image = bpy.data.images.load(path)
            try:
                width, height = image.size
                pixels = list(image.pixels)
            finally:
                bpy.data.images.remove(image)
        self.assertEqual([width, height], [512, 512])
        # Each tile holds more than its background colour: the objects were rendered.
        tile = (512 - 12) // 2
        for x0, y0 in ((4, 4), (tile + 8, 4), (4, tile + 8), (tile + 8, tile + 8)):
            colours = {
                tuple(round(c, 2) for c in pixels[((y0 + y) * width + x0 + x) * 4 :][:3])
                for y in range(0, tile, 8)
                for x in range(0, tile, 8)
            }
            self.assertGreater(len(colours), 3, (x0, y0))

    @unittest.skipUnless(GPU_RENDERS, GPU_REASON)
    def test_real_workbench_frames_follow_the_animated_camera(self):
        camera = self.scene.camera
        camera.location.x = -6
        camera.keyframe_insert("location", frame=1)
        camera.location.x = 6
        camera.keyframe_insert("location", frame=48)
        self.scene.frame_set(7)
        before = self.state()
        png, caption = self.capture({"mode": "frames", "frames": [1, 48], "max_size": 400})
        self.assertEqual(self.state(), before)
        self.assertEqual(caption["frames"], [1, 48])
        self.assertEqual(png_size(png)[0], 400)
