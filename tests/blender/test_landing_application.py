# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Receipt-bound camera backgrounds and image planes, with rollback, on real data."""

import hashlib
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import bpy
from helpers import FIXTURES, reset_scene, submodule
from test_apply_image import linked, png


class LandingApplicationTests(unittest.TestCase):
    def setUp(self):
        reset_scene()
        self.landing = submodule("blender.landing_application")
        self.storage = submodule("core.jobs.store")
        self.transfers = submodule("core.jobs.transfers")
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.private = self.root / "private"
        self.private.mkdir()
        self.enterContext(
            patch.object(bpy.utils, "extension_path_user", return_value=str(self.private))
        )
        self.scene = bpy.context.scene
        camera = bpy.data.cameras.new("Camera")
        self.camera = bpy.data.objects.new("Camera", camera)
        self.scene.collection.objects.link(self.camera)
        self.scene.camera = self.camera

    def saved(self, data, media_type, name):
        path = self.root / name
        path.write_bytes(data)
        receipt = self.transfers.DownloadedResult(
            path.name, len(data), hashlib.sha256(data).hexdigest()
        )
        asset = self.storage.ResultAsset("asset", path.name, media_type, len(data))
        return self.storage.StoredResult(asset, receipt), path

    def image(self, *, alpha=True):
        return self.saved(png(alpha=alpha), "image/png", "saved.png")

    def video(self):
        data = (FIXTURES / "synthetic/video-six-frames.mp4").read_bytes()
        return self.saved(data, "video/mp4", "saved.mp4")

    def snapshot(self):
        return {key: set(getattr(bpy.data, key)) for key in ("images", "movieclips", "objects")}

    def test_image_background_adds_one_more_and_keeps_the_others(self):
        data = self.camera.data
        existing = data.background_images.new()
        existing.alpha, existing.display_depth = 0.9, "FRONT"
        kept = (existing.alpha, existing.display_depth)  # alpha reads back as a 32-bit float
        data.show_background_images = False
        item, path = self.image()
        result = self.landing.apply_camera_background(self.scene, self.camera, item, path)
        self.assertEqual(len(data.background_images), 2)
        self.assertEqual((existing.alpha, existing.display_depth), kept)
        added = data.background_images[1]
        self.assertEqual((added.source, added.image), ("IMAGE", result.image))
        self.assertAlmostEqual(added.alpha, 0.5)
        self.assertEqual((added.display_depth, added.frame_method), ("BACK", "FIT"))
        self.assertTrue(added.show_background_image and data.show_background_images)
        self.assertIsNotNone(result.image.packed_file)
        self.assertEqual((result.kind, result.backgrounds), ("image", 2))

    def test_video_background_plays_a_persistent_private_copy_from_the_frame(self):
        item, path = self.video()
        result = self.landing.apply_camera_background(self.scene, self.camera, item, path, frame=12)
        added = self.camera.data.background_images[0]
        self.assertEqual((added.source, added.clip), ("MOVIE_CLIP", result.clip))
        self.assertFalse(added.use_camera_clip)
        self.assertEqual(result.clip.frame_start, 12)
        self.assertEqual(result.path.read_bytes(), path.read_bytes())
        self.assertTrue(result.path.is_relative_to(self.private))
        path.unlink()
        self.assertTrue(result.path.is_file())

    def test_no_scene_camera_is_refused_clearly(self):
        self.scene.camera = None
        with self.assertRaisesRegex(self.landing.LandingApplicationError, "no camera"):
            self.landing.scene_camera(self.scene)
        item, path = self.image()
        with self.assertRaises(self.landing.LandingApplicationError):
            self.landing.apply_camera_background(self.scene, self.camera, item, path)
        self.assertEqual(len(self.camera.data.background_images), 0)

    def test_failed_background_removes_only_what_it_added(self):
        data = self.camera.data
        data.background_images.new()
        before = self.snapshot()
        # Changed bytes fail the receipt; undecodable video fails after its copy.
        corrupt, corrupt_path = self.image()
        corrupt_path.write_bytes(corrupt_path.read_bytes() + b"changed")
        sound, sound_path = self.saved(b"\0" * 64, "video/mp4", "saved-sound.mp4")
        for item, path, frame in ((corrupt, corrupt_path, None), (sound, sound_path, 1)):
            with self.subTest(media_type=item.asset.media_type):
                with self.assertRaises(self.landing.LandingApplicationError):
                    self.landing.apply_camera_background(
                        self.scene, self.camera, item, path, frame=frame
                    )
                self.assertEqual(len(data.background_images), 1)
                self.assertFalse(data.show_background_images)
                self.assertEqual(self.snapshot(), before)
                self.assertEqual(list(self.private.iterdir()), [])

    def test_failure_after_the_background_is_added_rolls_it_back(self):
        item, path = self.image()
        before = self.snapshot()
        with patch.object(
            self.landing, "LandingApplication", side_effect=RuntimeError("synthetic")
        ):
            with self.assertRaises(self.landing.LandingApplicationError):
                self.landing.apply_camera_background(self.scene, self.camera, item, path)
        self.assertEqual(len(self.camera.data.background_images), 0)
        self.assertEqual(self.snapshot(), before)

    def test_plane_uses_alpha_sits_on_the_cursor_and_keeps_the_selection(self):
        bpy.ops.mesh.primitive_cube_add()
        cube = bpy.context.active_object
        for alpha, unlit in ((True, False), (True, True), (False, False), (False, True)):
            with self.subTest(alpha=alpha, unlit=unlit):
                item, path = self.image(alpha=alpha)
                result = self.landing.apply_image_plane(
                    self.scene, item, path, cursor=(1.0, 2.0, 3.0), unlit=unlit
                )
                plane, tree = result.target, result.material.node_tree
                self.assertEqual(result.alpha, alpha)
                self.assertEqual(tuple(plane.location), (1.0, 2.0, 3.0))
                self.assertAlmostEqual(plane.dimensions.z, 1.0, places=5)
                self.assertAlmostEqual(plane.dimensions.x, 2.0, places=5)
                self.assertEqual(plane["scenario_asset"], "asset")
                self.assertIn(plane, tuple(self.scene.collection.objects))
                self.assertEqual(bpy.context.view_layer.objects.active, cube)
                self.assertFalse(plane.select_get())
                shader = "EMISSION" if unlit else "BSDF_PRINCIPLED"
                colour = "Color" if unlit else "Base Color"
                self.assertEqual(linked(tree, shader, colour).image, result.image)
                if alpha and unlit:
                    self.assertEqual(linked(tree, "MIX_SHADER", "Fac").type, "TEX_IMAGE")
                elif alpha:
                    self.assertEqual(linked(tree, shader, "Alpha").type, "TEX_IMAGE")
                else:
                    self.assertIsNone(linked(tree, shader, "Alpha"))
                    self.assertIsNone(linked(tree, "MIX_SHADER", "Fac"))
                expected = "BLENDED" if alpha else "DITHERED"
                self.assertEqual(result.material.surface_render_method, expected)

    def test_failed_plane_removes_only_what_it_added(self):
        item, path = self.image()
        before = {
            key: set(getattr(bpy.data, key)) for key in ("images", "objects", "meshes", "materials")
        }
        plane = submodule("blender.image_plane")
        original = plane.add_image_plane

        def fail(*args, **kwargs):
            original(*args, **kwargs)
            raise RuntimeError("synthetic post-link failure")

        with patch.object(plane, "add_image_plane", side_effect=fail):
            with self.assertRaises(self.landing.LandingApplicationError):
                self.landing.apply_image_plane(self.scene, item, path, cursor=(0.0, 0.0, 0.0))
        for key, previous in before.items():
            self.assertEqual(set(getattr(bpy.data, key)), previous, key)
        video, video_path = self.video()
        with self.assertRaises(self.landing.LandingApplicationError):
            self.landing.apply_image_plane(self.scene, video, video_path, cursor=(0.0, 0.0, 0.0))

    def test_worker_call_cannot_mutate_blender(self):
        item, path = self.image()
        with ThreadPoolExecutor(max_workers=1) as pool:
            for call in (
                lambda: self.landing.apply_camera_background(self.scene, self.camera, item, path),
                lambda: self.landing.apply_image_plane(
                    self.scene, item, path, cursor=(0.0, 0.0, 0.0)
                ),
            ):
                with self.assertRaises(self.landing.LandingApplicationError):
                    pool.submit(call).result(5)
        self.assertEqual(len(self.camera.data.background_images), 0)
