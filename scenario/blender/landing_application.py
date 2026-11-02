# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Land one receipt-bound saved image or video as a camera background or an image plane.

Both add data and keep everything that was there: a camera background is one
more entry in the camera's background list, an image plane one new object.
A failure removes only what this call added.
"""

import math
import shutil
import tempfile
import threading
from dataclasses import dataclass, field
from pathlib import Path

import bpy

from ..core.scene import landing
from . import image_plane
from .image_application import apply_image
from .media_application import snapshot

# Blender's own defaults for a new background: half opacity, behind objects,
# fitted inside the camera frame.
BACKGROUND_ALPHA = 0.5
BACKGROUND_DEPTH = "BACK"
BACKGROUND_FIT = "FIT"


class LandingApplicationError(RuntimeError):
    """Nothing this landing added remains in the file."""


@dataclass(frozen=True)
class LandingApplication:
    purpose: str
    kind: str
    # The camera given a background, or the new plane object.
    target: object = field(repr=False)
    image: object = field(default=None, repr=False)
    clip: object = field(default=None, repr=False)
    material: object = field(default=None, repr=False)
    path: Path | None = field(default=None, repr=False)
    alpha: bool = False
    backgrounds: int = 0


def _main_thread():
    if threading.current_thread() is not threading.main_thread():
        raise LandingApplicationError("Apply saved results on Blender's main thread")


def _local(data):
    return data is not None and data.library is None and data.override_library is None


def scene_camera(scene):
    """The local camera this scene renders through; refuse clearly when there is none."""
    camera = scene.camera
    if camera is None or camera.type != "CAMERA":
        raise LandingApplicationError("This scene has no camera; add one or set the scene camera")
    if not (_local(scene) and _local(camera) and _local(camera.data)):
        raise LandingApplicationError("Use a local scene camera; linked cameras cannot change")
    if scene.objects.get(camera.name) != camera:
        raise LandingApplicationError("Link the scene camera to this scene first")
    return camera


def validate_plane_destination(scene, cursor):
    """Check a plane's scene and cursor before any claim; never changes data."""
    _main_thread()
    if (
        scene != bpy.context.scene
        or not _local(scene)
        or bpy.context.mode != "OBJECT"
        or len(cursor) != 3
        or any(not math.isfinite(value) for value in cursor)
    ):
        raise LandingApplicationError("Choose a local scene in Object Mode and a finite cursor")


def _remove_new(before):
    """Remove data this landing added, then verify it is gone; raise if not."""
    for name, previous in before.items():
        collection = getattr(bpy.data, name)
        for value in set(collection) - previous:
            collection.remove(value, do_unlink=True)
    if any(set(getattr(bpy.data, name)) - previous for name, previous in before.items()):
        raise RuntimeError("Landing rollback needs inspection")


def apply_camera_background(scene, camera, item, path, *, frame=None):
    """Add one background showing the verified image or video to `camera`.

    Existing backgrounds stay. A video plays from a persistent private copy as
    a movie clip starting at `frame`; an image is packed. The camera shows its
    backgrounds afterwards, in camera view.
    """
    _main_thread()
    if scene.camera != camera:
        raise LandingApplicationError("The scene camera changed; review it again")
    scene_camera(scene)
    kind = landing.kind(item.asset.media_type)
    if kind is None or (kind == "video" and type(frame) is not int):
        raise LandingApplicationError("Choose a saved image, or a video and its start frame")
    data = camera.data
    before = len(data.background_images)
    shown = data.show_background_images
    added = {name: set(getattr(bpy.data, name)) for name in ("movieclips", "images")}
    directory = image = clip = copy = None
    try:
        if kind == "video":
            package = __package__.rsplit(".", 1)[0]
            root = bpy.utils.extension_path_user(package, path="media-import", create=True)
            directory = Path(tempfile.mkdtemp(prefix="result-", dir=root))
            copy = snapshot(item, path, directory, landing.VIDEO_TYPES[item.asset.media_type])
            clip = bpy.data.movieclips.load(str(copy), check_existing=False)
            if min(clip.size) <= 0 or clip.frame_duration <= 0:
                raise LandingApplicationError("Blender could not decode the video")
            clip.name = "Scenario Video"
            clip.frame_start = frame
            clip["scenario_asset"] = item.asset.asset_id
        else:
            image, _ = apply_image(item, path)
        background = data.background_images.new()
        if clip is not None:
            background.source = "MOVIE_CLIP"
            background.use_camera_clip = False
            background.clip = clip
        else:
            background.source = "IMAGE"
            background.image = image
        background.alpha = BACKGROUND_ALPHA
        background.display_depth = BACKGROUND_DEPTH
        background.frame_method = BACKGROUND_FIT
        background.show_background_image = True
        data.show_background_images = True
        return LandingApplication(
            landing.CAMERA_BACKGROUND,
            kind,
            camera,
            image=image,
            clip=clip,
            path=copy,
            backgrounds=len(data.background_images),
        )
    except Exception:
        # A rollback failure escapes as uncertainty before the private copy is
        # deleted: data that was not removed may still reference it.
        for index in reversed(range(before, len(data.background_images))):
            data.background_images.remove(data.background_images[index])
        data.show_background_images = shown
        _remove_new(added)
        if directory is not None:
            shutil.rmtree(directory)
        raise LandingApplicationError(
            "Could not add the verified result; saved downloads are preserved"
        ) from None


def apply_image_plane(scene, item, path, *, cursor, unlit=False):
    """Add one upright plane showing the verified image, its bottom center at `cursor`.

    The image is packed, its alpha (when the header declares one) makes the
    plane transparent, and `unlit` shows its colours without scene lighting.
    """
    validate_plane_destination(scene, cursor)
    if landing.kind(item.asset.media_type) != "image" or type(unlit) is not bool:
        raise LandingApplicationError("Choose a saved PNG, JPEG or OpenEXR image")
    added = {
        name: set(getattr(bpy.data, name)) for name in ("objects", "meshes", "materials", "images")
    }
    try:
        image, alpha = apply_image(item, path)
        obj = image_plane.add_image_plane(scene, image, cursor=cursor, alpha=alpha, unlit=unlit)
        obj["scenario_asset"] = item.asset.asset_id
        return LandingApplication(
            landing.IMAGE_PLANE,
            "image",
            obj,
            image=image,
            material=obj.data.materials[0],
            alpha=alpha,
        )
    except Exception:
        _remove_new(added)
        raise LandingApplicationError(
            "Could not add the verified image; saved downloads are preserved"
        ) from None
