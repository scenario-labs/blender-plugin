# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Load and pack exact receipt-bound image snapshots without changing scene targets."""

import hashlib
import os
import stat
import tempfile
import threading
from pathlib import Path

import bpy

from ..core.scene.panorama import MAX_FILE_BYTES, image_alpha, inspect_image


class ImageApplicationError(RuntimeError):
    """Image decode or rollback failed; no generation retry is implied."""


# The container each saved media type must use, and the snapshot name Blender loads.
_MEDIA_TYPES = {
    "PNG": {"image/png"},
    "JPEG": {"image/jpeg"},
    "OPEN_EXR": {"image/exr", "image/x-exr"},
}
_SNAPSHOTS = {"PNG": "image.png", "JPEG": "image.jpg", "OPEN_EXR": "image.exr"}


def _root():
    package = __package__.rsplit(".", 1)[0]
    return bpy.utils.extension_path_user(package, path="image-import", create=True)


def _read(item, path):
    """The saved file's bytes, exactly as its receipt recorded them."""
    receipt = item.receipt
    path = Path(path)
    if receipt is None or path.name != receipt.name or path.is_symlink():
        raise ImageApplicationError("Use the saved image download receipt")
    flags = (
        os.O_RDONLY
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
        | getattr(os, "O_BINARY", 0)
    )
    with os.fdopen(os.open(path, flags), "rb") as source:
        if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
            raise ImageApplicationError("The saved image is not a regular file")
        data = source.read(MAX_FILE_BYTES + 1)
    if (
        len(data) > MAX_FILE_BYTES
        or len(data) != receipt.size
        or hashlib.sha256(data).hexdigest() != receipt.sha256
    ):
        raise ImageApplicationError("The saved image no longer matches its receipt")
    return data


def _load(item, data, info, root):
    """Load and pack one checked snapshot; a failed check removes the new image."""
    if item.asset.media_type not in _MEDIA_TYPES[info.file_format]:
        raise ImageApplicationError("Image contents do not match the saved media type")
    with tempfile.TemporaryDirectory(prefix="result-", dir=root) as directory:
        snapshot = Path(directory) / _SNAPSHOTS[info.file_format]
        snapshot.write_bytes(data)
        image = bpy.data.images.load(str(snapshot), check_existing=False)
        try:
            if (
                tuple(image.size) != (info.width, info.height)
                or image.file_format != info.file_format
                or (info.hdr_capable and not image.is_float)
            ):
                raise ImageApplicationError("Decoded image does not match its verified container")
            image.pack()
            if image.packed_file is None:
                raise ImageApplicationError("Image could not be packed into the blend file")
            image.name = "Scenario Image"
            image.filepath = ""
            image.use_fake_user = True
        except BaseException:
            bpy.data.images.remove(image)
            raise
    return image


def apply_image(item, path):
    """Load and pack one verified saved PNG, color JPEG or OpenEXR result.

    Returns the packed image and whether its header declares alpha. The caller
    removes the image if its own later step fails.
    """
    if threading.current_thread() is not threading.main_thread():
        raise ImageApplicationError("Apply images on Blender's main thread")
    try:
        data = _read(item, path)
        info = inspect_image(data, jpeg=True)
        return _load(item, data, info, _root()), image_alpha(data)
    except Exception:
        raise ImageApplicationError(
            "Could not apply the verified image; saved downloads are preserved"
        ) from None


def apply_images(verified, *, pixel_budget=None, jpeg=False):
    """Load and pack each verified result; `jpeg` also accepts color JPEG (material maps)."""
    if threading.current_thread() is not threading.main_thread():
        raise ImageApplicationError("Apply images on Blender's main thread")
    if pixel_budget is not None and (type(pixel_budget) is not int or pixel_budget < 1):
        raise ImageApplicationError("Use a positive combined image pixel budget")
    total_pixels = 0
    images = []
    root = _root()
    try:
        for item, path in zip(verified.record.results, verified.paths, strict=True):
            data = _read(item, path)
            info = inspect_image(data, jpeg=jpeg)
            total_pixels += info.width * info.height
            if pixel_budget is not None and total_pixels > pixel_budget:
                raise ImageApplicationError(
                    "Combined image dimensions exceed the application limit"
                )
            images.append(_load(item, data, info, root))
        return tuple(images)
    except BaseException as error:
        for image in reversed(images):
            if image in tuple(bpy.data.images):
                bpy.data.images.remove(image)
        if isinstance(error, Exception):
            raise ImageApplicationError(
                "Could not apply verified images; saved downloads are preserved"
            ) from None
        raise
