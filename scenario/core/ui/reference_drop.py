# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Which input of a lane form an image file dropped on the Scenario sidebar joins.

Only the lanes whose sidebar form lists its file inputs as they are take drops.
Render Image and Render Video share an input with their capture, Environment
checks a 2:1 panorama, Blockout keeps its own image and the 3D tab in Edit mode
edits a mesh; those keep their own controls.
"""

import os

DROP_LANES = frozenset({"image", "video", "3d", "material", "audio"})
# Image files the form's own File button offers that Scenario accepts as references.
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")


def is_image_file(path):
    """Whether `path` names an image the drop may add, judged by its extension."""
    return isinstance(path, str) and os.path.splitext(path)[1].lower() in IMAGE_EXTENSIONS


def has_room(spec, count):
    """A single-file input holds one reference; a list input up to its maximum, if any."""
    if spec.ptype == "file":
        return count < 1
    return not spec.max_length or count < spec.max_length


def image_input(lane, specs, counts):
    """The name of the lane's first image file input with room, or None.

    `lane` is the effective lane (the 3D tab in Edit mode is `edit3d`), `specs`
    the model's parameter specs and `counts` how many references each input
    holds, by input name. A file input without a declared kind is an image
    input, as the form draws it.
    """
    if lane not in DROP_LANES:
        return None
    for spec in specs:
        if (
            spec.is_file
            and (spec.kind or "image") == "image"
            and has_room(spec, counts.get(spec.name, 0))
        ):
            return spec.name
    return None
