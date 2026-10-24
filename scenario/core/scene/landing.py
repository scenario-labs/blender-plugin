# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Saved results that can land as a camera background or an image plane. No bpy.

Both are saved-job applications: `ModelJobs.actions()` offers them, the review
binds the scene and its camera or cursor, and application rehashes the saved
file against its receipt first. This module only classifies saved metadata.
"""

CAMERA_BACKGROUND = "camera_background"
IMAGE_PLANE = "image_plane"
PURPOSES = (CAMERA_BACKGROUND, IMAGE_PLANE)

# Still images Blender loads and packs after the bounded header preflight.
IMAGE_TYPES = frozenset({"image/png", "image/jpeg", "image/exr", "image/x-exr"})
# Videos a camera background plays as a movie clip, with their snapshot suffix.
VIDEO_TYPES = {"video/mp4": ".mp4", "video/webm": ".webm"}
# A server-declared texture role other than base colour marks a material map.
_COLOUR_ROLES = (None, "base")
# Saved jobs whose results are text, never pictures.
_TEXT_OPERATIONS = frozenset({"prompt", "translate"})


def kind(media_type):
    """'image' or 'video' for a saved media type a landing accepts, else None."""
    if media_type in IMAGE_TYPES:
        return "image"
    if media_type in VIDEO_TYPES:
        return "video"
    return None


def accepts(purpose, media_type):
    """Whether `purpose` lands a result of this media type: planes take stills only."""
    found = kind(media_type)
    return found == "image" or (found == "video" and purpose == CAMERA_BACKGROUND)


def eligible_assets(record, purpose):
    """Downloaded colour results `purpose` can land, in result order; reads no file."""
    if purpose not in PURPOSES or record.intent.operation in _TEXT_OPERATIONS:
        return ()
    return tuple(
        item
        for item in record.results
        if item.receipt is not None
        and item.asset.texture_role in _COLOUR_ROLES
        and accepts(purpose, item.asset.media_type)
    )
