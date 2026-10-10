# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Decode a local image into a bounded preview outside the open blend file.

Blender decodes the image inside ``bpy.data.temp_data()``, a separate data
block freed when the decode returns, so the open file's data, undo history
and dependency graph never see it. Loading an image into ``bpy.data`` and
removing it again is not equivalent: the removal makes the next dependency
graph evaluation report updates for the scene and its objects, and the job
session's dependency handler then invalidates every origin captured in that
scene. In the temporary block, loading, scaling, reading pixels and writing a
PNG through a temporary scene report no ID updates.

The helper reads only the file it is given. Callers check its format and
declared dimensions beforehand: ``limit`` sees the dimensions only after
Blender has loaded the whole image. It runs on Blender's main thread only,
never while drawing.
"""

import array
import math
import threading
from pathlib import Path

import bpy

from ..core.jobs.local_render import LocalRenderError, blender_path


class PreviewDecodeError(RuntimeError):
    """Blender could not decode a preview image; the message is sanitized."""


def _main_thread():
    if threading.current_thread() is not threading.main_thread():
        raise RuntimeError("Preview decoding belongs to Blender's main thread")


def fit(width, height, edge):
    """Fit ``width`` by ``height`` within ``edge`` pixels per side, never upscaling."""
    scale = min(1.0, edge / max(width, height))
    return max(1, round(width * scale)), max(1, round(height * scale))


def _encode(value):
    """Linear scene value to an sRGB display value, clamped to [0, 1]."""
    if not value > 0.0:  # Also NaN.
        return 0.0
    if value >= 1.0:
        return 1.0
    if value <= 0.0031308:
        return value * 12.92
    return 1.055 * math.pow(value, 1 / 2.4) - 0.055


def _png_scene(data):
    """A temporary scene that writes 8-bit RGBA PNG display values.

    Its render settings stay in this frame, which ends before the block does.
    """
    scene = data.scenes.new("Scenario preview")
    settings = scene.render.image_settings
    settings.file_format = "PNG"
    settings.color_mode = "RGBA"
    settings.color_depth = "8"
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    return scene


def _scaled(data, path, edge, limit, output, scene):
    """Decode one file in a temporary block; every reference stays in this frame."""
    image = data.images.load(path, check_existing=False)
    try:
        width, height = image.size
        if not image.has_data or not limit(width, height):
            return None
        size = fit(width, height, edge)
        if size != (width, height):
            image.scale(*size)
        if output is not None:
            image.save_render(output, scene=scene)
            return size, None
        pixels = array.array("f", bytes(4 * size[0] * size[1] * 4))
        image.pixels.foreach_get(pixels)
        if image.is_float:
            # High bit-depth files load as linear, premultiplied floats; previews
            # hold straight display values, like 8-bit files and the PNG output.
            for index in range(0, len(pixels), 4):
                alpha = pixels[index + 3]
                scale = 1.0 / alpha if 0.0 < alpha < 1.0 else 1.0
                for channel in range(index, index + 3):
                    pixels[channel] = _encode(pixels[channel] * scale)
        return size, pixels
    finally:
        data.images.remove(image)
        del image


def decode(path, edge, limit, *, output=None):
    """Decode ``path`` fitted to ``edge`` without touching the open file's data.

    ``limit(width, height)`` receives the loaded image's dimensions and returns
    whether to continue; a false or raising ``limit`` refuses the image. Without
    ``output``, returns ``((width, height), pixels)``: RGBA floats, row by row
    from the bottom, holding sRGB display values with straight alpha (high
    bit-depth and float files are unpremultiplied and converted from linear).
    With ``output``, the fitted image is written there as an 8-bit RGBA PNG
    through the Standard view transform and ``((width, height), None)`` is
    returned.

    ``bpy.data.temp_data()`` is a separate block freed on exit. A Python object
    that still refers to it afterwards reads freed memory, which can crash
    Blender or reach whatever data reuses it. So the image, scene and render
    setting references live in ``_png_scene`` and ``_scaled`` frames that end
    inside the block, this frame drops its own ``data`` and ``scene`` before
    the block closes, and a failure is recorded without keeping the exception
    and raised only after the block is gone. Neither the error's context nor
    the locals of the frames on its traceback refer into the block. Every
    failure raises ``PreviewDecodeError`` with a message that names neither
    the path nor Blender's own error, and with no original error as its cause
    or context.
    """
    _main_thread()
    # Raising inside an except suite would keep the original error, which holds
    # the path, as the new error's context, even with ``from None``.
    refused = None
    try:
        # A path object applies the Windows path check to strings as well.
        source = blender_path(Path(path))
        output = None if output is None else blender_path(Path(output))
    except LocalRenderError:
        refused = "Preview paths are too long for Blender on this system"
    except ValueError:
        # On Windows the check encodes paths as UTF-16, which rejects a lone
        # surrogate with UnicodeEncodeError.
        refused = "Blender cannot use these preview paths on this system"
    if refused is not None:
        raise PreviewDecodeError(refused)
    result, failed, scene = None, False, None
    with bpy.data.temp_data() as data:
        try:
            if output is not None:
                scene = _png_scene(data)
            result = _scaled(data, source, edge, limit, output, scene)
        except Exception:
            failed = True
        del data, scene
    if failed or result is None:
        raise PreviewDecodeError("Blender could not decode this preview")
    return result
