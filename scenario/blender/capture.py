# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Viewport and camera captures (stills and playblasts). Main thread only; the real runner needs the GUI."""

import logging
import time
from dataclasses import dataclass

import bpy

from ..core.scene import capture_plan
from . import runtime

log = logging.getLogger("scenario.capture")
_view_context = {"value": True}


def capture_dir():
    path = runtime.paths().cache_dir / "captures"
    path.mkdir(parents=True, exist_ok=True)
    return path


def new_capture_path(prefix, ext):
    return str(capture_dir() / f"{prefix}_{int(time.time() * 1000)}.{ext}")


@dataclass
class RenderSettings:
    resolution_x: int
    resolution_y: int
    resolution_percentage: int
    file_format: str
    color_mode: str
    filepath: str
    use_stamp: bool
    frame_start: int
    frame_end: int
    use_preview_range: bool
    ffmpeg_format: str
    ffmpeg_codec: str
    ffmpeg_audio: str
    film_transparent: bool
    camera_name: str
    media_type: str = ""
    frame_current: int = 1
    color_depth: str = ""
    pixel_aspect_x: float = 1.0
    pixel_aspect_y: float = 1.0
    ffmpeg_crf: str = ""
    ffmpeg_gop: int = 0
    ffmpeg_lossless: bool = False
    ffmpeg_split: bool = False

    @classmethod
    def snapshot(cls, scene):
        r = scene.render
        return cls(
            r.resolution_x,
            r.resolution_y,
            r.resolution_percentage,
            r.image_settings.file_format,
            r.image_settings.color_mode,
            r.filepath,
            r.use_stamp,
            scene.frame_start,
            scene.frame_end,
            scene.use_preview_range,
            r.ffmpeg.format,
            r.ffmpeg.codec,
            r.ffmpeg.audio_codec,
            r.film_transparent,
            scene.camera.name if scene.camera else "",
            getattr(r.image_settings, "media_type", ""),
            scene.frame_current,
            r.image_settings.color_depth,
            r.pixel_aspect_x,
            r.pixel_aspect_y,
            r.ffmpeg.constant_rate_factor,
            r.ffmpeg.gopsize,
            r.ffmpeg.use_lossless_output,
            r.ffmpeg.use_autosplit,
        )

    def restore(self, scene):
        r = scene.render
        r.resolution_x, r.resolution_y, r.resolution_percentage = (
            self.resolution_x,
            self.resolution_y,
            self.resolution_percentage,
        )
        r.pixel_aspect_x, r.pixel_aspect_y = self.pixel_aspect_x, self.pixel_aspect_y
        if self.media_type and hasattr(r.image_settings, "media_type"):
            r.image_settings.media_type = self.media_type
        if self.media_type != "VIDEO":
            r.image_settings.file_format = self.file_format
        try:
            r.image_settings.color_mode = self.color_mode
        except TypeError:
            pass
        # A capture format without the saved depth, such as PNG for 10-bit DPX, changes it.
        if self.color_depth and r.image_settings.color_depth != self.color_depth:
            try:
                r.image_settings.color_depth = self.color_depth
            except TypeError:
                pass  # The restored format offers no such depth; Blender kept a valid one.
        r.filepath, r.use_stamp = self.filepath, self.use_stamp
        scene.frame_start, scene.frame_end = self.frame_start, self.frame_end
        _set_preview_range(scene, self.use_preview_range)
        r.ffmpeg.format, r.ffmpeg.codec, r.ffmpeg.audio_codec = (
            self.ffmpeg_format,
            self.ffmpeg_codec,
            self.ffmpeg_audio,
        )
        _assign(r.ffmpeg, "constant_rate_factor", self.ffmpeg_crf)
        _assign(r.ffmpeg, "gopsize", self.ffmpeg_gop)
        _assign(r.ffmpeg, "use_lossless_output", self.ffmpeg_lossless)
        _assign(r.ffmpeg, "use_autosplit", self.ffmpeg_split)
        r.film_transparent = self.film_transparent
        if self.camera_name and bpy.data.objects.get(self.camera_name) is not None:
            scene.camera = bpy.data.objects[self.camera_name]
        elif not self.camera_name and scene.camera is not None:
            scene.camera = None  # A camera capture chose the first camera; the scene had none.
        if scene.frame_current != self.frame_current:
            scene.frame_set(self.frame_current)


def _assign(owner, name, value):
    """Write a property only when it differs, so restoring an unchanged setting notifies nothing.

    An enum whose stored value is outside its items reads as "" and cannot be written back by
    name; it keeps what the capture set."""
    if value != "" and getattr(owner, name) != value:
        setattr(owner, name, value)


def _set_preview_range(scene, enabled):
    """Write the preview-range toggle only when it changes.

    Its RNA update sends a frame notifier even for a same-value write. In the
    GUI, Blender answers after the capturing operator or timer returns with a
    same-frame update that runs frame_change_pre, which invalidates any origin
    captured in between, such as the upload origin of this very capture.
    """
    if scene.use_preview_range != enabled:
        scene.use_preview_range = enabled


def set_video_output(render):
    """Blender 4.x uses file_format FFMPEG; 4.5+/5.x use image_settings.media_type VIDEO."""
    settings = render.image_settings
    if hasattr(settings, "media_type"):
        settings.media_type = "VIDEO"
    else:
        settings.file_format = "FFMPEG"


# Playblast encoding: H.264 at Blender's Medium quality, whatever the scene's own output uses.
# A scene set to lossless or a high bitrate would upload a clip tens of times larger for the same
# frames (a 1280x720 clip of 120 frames: about 0.5 MB at Medium, 30 MB lossless). The encoder
# preset stays the scene's: it moves the size by a factor of two at most.
PLAYBLAST_CRF = "MEDIUM"
PLAYBLAST_GOP = 18


def set_playblast_encoding(ffmpeg):
    """Encode a playblast as a small H.264 MP4 without audio; the caller restores the scene's settings."""
    ffmpeg.format, ffmpeg.codec, ffmpeg.audio_codec = "MPEG4", "H264", "NONE"
    ffmpeg.constant_rate_factor = PLAYBLAST_CRF
    ffmpeg.gopsize = PLAYBLAST_GOP
    ffmpeg.use_lossless_output = False
    ffmpeg.use_autosplit = False


def set_image_output(render, file_format):
    settings = render.image_settings
    if hasattr(settings, "media_type"):
        settings.media_type = "IMAGE"
    settings.file_format = file_format


def _view3d(context):
    area = getattr(context, "area", None)
    if area is not None and area.type == "VIEW_3D" and getattr(context, "window", None) is not None:
        region = getattr(context, "region", None)
        if region is None or region.type != "WINDOW":
            region = next((r for r in area.regions if r.type == "WINDOW"), None)
        return context.window, area, region
    for window in context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == "VIEW_3D":
                region = next((r for r in area.regions if r.type == "WINDOW"), None)
                return window, area, region
    return None, None, None


class _CameraView:
    """Look through the scene camera in the active viewport for the duration of a capture, then restore the view.

    `render.opengl(view_context=False)` renders with the scene's Workbench settings: flat grey whatever the viewport
    shows, which is why "Camera clip" came out as clay even with Grey clay capture off. Capturing the viewport in
    camera view keeps its shading (Material Preview, Rendered) and still frames exactly what the camera sees."""

    def __init__(self, area):
        self.space = area.spaces.active if area is not None else None
        self.saved = None

    def __enter__(self):
        r3d = getattr(self.space, "region_3d", None)
        if r3d is not None:
            self.saved = (
                r3d.view_perspective,
                r3d.view_matrix.copy(),
                r3d.view_distance,
                r3d.view_location.copy(),
                r3d.view_rotation.copy(),
                getattr(r3d, "view_camera_zoom", 0.0),
                getattr(r3d, "view_camera_offset", (0.0, 0.0))[:],
            )
            r3d.view_perspective = "CAMERA"
            try:
                r3d.view_camera_zoom = 29.0  # the camera frame fills the region; render.opengl crops to the camera anyway
                r3d.view_camera_offset = (0.0, 0.0)
            except (AttributeError, TypeError):
                pass
        return self

    def __exit__(self, *exc):
        r3d = getattr(self.space, "region_3d", None)
        if r3d is not None and self.saved is not None:
            perspective, matrix, distance, location, rotation, zoom, offset = self.saved
            r3d.view_perspective = perspective
            if perspective != "CAMERA":
                r3d.view_location = location
                r3d.view_rotation = rotation
                r3d.view_distance = distance
            try:
                r3d.view_camera_zoom = zoom
                r3d.view_camera_offset = offset
            except (AttributeError, TypeError):
                pass
        return False


def _default_runner(kind, context, scene):
    window, area, region = _view3d(context)
    if window is None:
        raise RuntimeError("No 3D viewport available for the capture")
    with context.temp_override(window=window, area=area, region=region, scene=scene):
        if _view_context["value"]:
            bpy.ops.render.opengl(
                animation=(kind == "animation"), view_context=True, write_still=(kind == "still")
            )
        else:
            # camera source: capture through the viewport in camera view so materials and lighting come along
            with _CameraView(area):
                bpy.ops.render.opengl(
                    animation=(kind == "animation"),
                    view_context=True,
                    write_still=(kind == "still"),
                )


class _Overlays:
    """Hide overlays and gizmos (and optionally force solid shading) while a capture runs."""

    def __init__(self, context, force_solid):
        self.spaces = []
        for window in context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == "VIEW_3D":
                    self.spaces.append(area.spaces.active)
        self.force_solid = force_solid
        self.saved = []

    def __enter__(self):
        for space in self.spaces:
            self.saved.append(
                (
                    space.overlay.show_overlays,
                    space.show_gizmo,
                    space.shading.type,
                    space.shading.color_type,
                )
            )
            space.overlay.show_overlays = False
            space.show_gizmo = False
            if self.force_solid:
                space.shading.type = "SOLID"
                space.shading.color_type = "SINGLE"
        return self

    def __exit__(self, *exc):
        for space, (overlays, gizmo, shading, color) in zip(self.spaces, self.saved, strict=False):
            space.overlay.show_overlays = overlays
            space.show_gizmo = gizmo
            space.shading.type = shading
            space.shading.color_type = color
        return False


def capture_size(context, source):
    """The (width, height) a still or clip from this source records, read without writing.

    Camera captures keep the scene's render frame, pixel aspect included. Viewport
    captures keep the shape of the 3D viewport they render, or the render frame
    when that viewport looks through the camera. The long side stays 1280 pixels.
    """
    render = context.scene.render
    if source.removesuffix("_CLIP") != "CAMERA":
        _, area, region = _view3d(context)
        r3d = getattr(area.spaces.active, "region_3d", None) if area is not None else None
        if region is not None and getattr(r3d, "view_perspective", "") != "CAMERA":
            return capture_plan.capture_size(region.width, region.height)
    return capture_plan.capture_size(
        render.resolution_x,
        render.resolution_y,
        pixel_aspect=(render.pixel_aspect_x, render.pixel_aspect_y),
    )


def unavailable_reason(context, source, camera=None):
    """Why this source cannot be captured now, in words for the user, else None; reads, never captures."""
    if bpy.app.background:
        return "Viewport and camera captures require the Blender GUI"
    if source.removesuffix("_CLIP") == "CAMERA":
        scene = context.scene
        if camera or scene.camera or any(o.type == "CAMERA" for o in scene.objects):
            return None
        return "Add a camera to capture the scene, or capture the viewport"
    if _view3d(context)[0] is None:
        return "Open a 3D viewport to capture the scene"
    return None


def _prepare_source(scene, source, camera):
    if source == "CAMERA":
        cam = camera or scene.camera or next((o for o in scene.objects if o.type == "CAMERA"), None)
        if cam is None:
            raise RuntimeError("Camera capture needs a camera in the scene")
        scene.camera = cam
    _view_context["value"] = source != "CAMERA"


def capture_still(
    context,
    path,
    source="VIEWPORT",
    camera=None,
    width=None,
    height=None,
    force_solid=False,
    runner=None,
):
    scene = context.scene
    saved = RenderSettings.snapshot(scene)
    runner = runner or _default_runner
    try:
        _prepare_source(scene, source, camera)
        r = scene.render
        if width and height:
            r.resolution_x, r.resolution_y = int(width), int(height)
            r.pixel_aspect_x = r.pixel_aspect_y = 1.0
        r.resolution_percentage = 100
        set_image_output(r, "PNG")
        r.image_settings.color_mode = "RGB"
        r.use_stamp = False
        r.filepath = str(path)
        with _Overlays(context, force_solid):
            runner("still", context, scene)
        return str(path)
    finally:
        saved.restore(scene)


def capture_playblast(
    context,
    path,
    source="VIEWPORT",
    camera=None,
    width=1280,
    height=720,
    frame_start=None,
    frame_end=None,
    force_solid=False,
    runner=None,
):
    scene = context.scene
    saved = RenderSettings.snapshot(scene)
    runner = runner or _default_runner
    fps = scene.render.fps / (scene.render.fps_base or 1.0)
    start, end, seconds = capture_plan.frame_span(
        frame_start if frame_start is not None else scene.frame_start,
        frame_end if frame_end is not None else scene.frame_end,
        fps,
        use_preview=(frame_start is None and scene.use_preview_range),
        preview_start=scene.frame_preview_start,
        preview_end=scene.frame_preview_end,
    )
    try:
        _prepare_source(scene, source, camera)
        r = scene.render
        r.resolution_x, r.resolution_y, r.resolution_percentage = int(width), int(height), 100
        r.pixel_aspect_x = r.pixel_aspect_y = 1.0
        set_video_output(r)
        set_playblast_encoding(r.ffmpeg)
        r.use_stamp = False
        # Blender renders an enabled preview range. Keep it when it is the span.
        if (start, end) != (scene.frame_preview_start, scene.frame_preview_end):
            _set_preview_range(scene, False)
        scene.frame_start, scene.frame_end = start, end
        r.filepath = str(path)
        with _Overlays(context, force_solid):
            runner("animation", context, scene)
        return {
            "path": str(path),
            "frame_start": start,
            "frame_end": end,
            "seconds": seconds,
            "fps": fps,
        }
    finally:
        saved.restore(scene)


def first_frame_still(
    context, path, source="VIEWPORT", camera=None, force_solid=False, runner=None
):
    scene = context.scene
    current = scene.frame_current
    start = scene.frame_preview_start if scene.use_preview_range else scene.frame_start
    try:
        scene.frame_set(start)
        return capture_still(
            context,
            path,
            source=source,
            camera=camera,
            width=1280,
            height=720,
            force_solid=force_solid,
            runner=runner,
        )
    finally:
        scene.frame_set(current)
