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

from ..core.scene.panorama import MAX_FILE_BYTES, inspect_image


class ImageApplicationError(RuntimeError):
    """Image decode or rollback failed; no generation retry is implied."""


def apply_images(verified, *, pixel_budget=None):
    if threading.current_thread() is not threading.main_thread():
        raise ImageApplicationError("Apply images on Blender's main thread")
    if pixel_budget is not None and (type(pixel_budget) is not int or pixel_budget < 1):
        raise ImageApplicationError("Use a positive combined image pixel budget")
    total_pixels = 0
    images = []
    package = __package__.rsplit(".", 1)[0]
    root = bpy.utils.extension_path_user(package, path="image-import", create=True)
    try:
        for item, path in zip(verified.record.results, verified.paths, strict=True):
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
            info = inspect_image(data)
            total_pixels += info.width * info.height
            if pixel_budget is not None and total_pixels > pixel_budget:
                raise ImageApplicationError(
                    "Combined image dimensions exceed the application limit"
                )
            expected = {"PNG": {"image/png"}, "OPEN_EXR": {"image/exr", "image/x-exr"}}
            if item.asset.media_type not in expected[info.file_format]:
                raise ImageApplicationError("Image contents do not match the saved media type")
            with tempfile.TemporaryDirectory(prefix="result-", dir=root) as directory:
                snapshot = Path(directory) / (
                    "image.png" if info.file_format == "PNG" else "image.exr"
                )
                snapshot.write_bytes(data)
                image = bpy.data.images.load(str(snapshot), check_existing=False)
                images.append(image)
                if (
                    tuple(image.size) != (info.width, info.height)
                    or image.file_format != info.file_format
                    or (info.hdr_capable and not image.is_float)
                ):
                    raise ImageApplicationError(
                        "Decoded image does not match its verified container"
                    )
                image.pack()
                if image.packed_file is None:
                    raise ImageApplicationError("Image could not be packed into the blend file")
                image.name = "Scenario Image"
                image.filepath = ""
                image.use_fake_user = True
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
