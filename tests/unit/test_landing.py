# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Which saved results land as a camera background or an image plane, without Blender."""

from types import SimpleNamespace

import pytest

from scenario.core.scene import landing


def item(asset_id, media_type, *, role=None, downloaded=True):
    return SimpleNamespace(
        asset=SimpleNamespace(asset_id=asset_id, media_type=media_type, texture_role=role),
        receipt=SimpleNamespace() if downloaded else None,
    )


def record(*results, operation="model"):
    return SimpleNamespace(intent=SimpleNamespace(operation=operation), results=results)


SAVED = record(
    item("png", "image/png"),
    item("jpeg", "image/jpeg"),
    item("exr", "image/x-exr"),
    item("mp4", "video/mp4"),
    item("webm", "video/webm"),
    item("webp", "image/webp"),
    item("sound", "audio/wav"),
    item("glb", "model/gltf-binary"),
    item("normal", "image/png", role="normal"),
    item("base", "image/png", role="base"),
    item("missing", "image/png", downloaded=False),
)


def keys(items):
    return [value.asset.asset_id for value in items]


def test_backgrounds_take_downloaded_colour_stills_and_videos_in_result_order():
    found = landing.eligible_assets(SAVED, landing.CAMERA_BACKGROUND)
    assert keys(found) == ["png", "jpeg", "exr", "mp4", "webm", "base"]


def test_planes_take_downloaded_colour_stills_only():
    found = landing.eligible_assets(SAVED, landing.IMAGE_PLANE)
    assert keys(found) == ["png", "jpeg", "exr", "base"]


@pytest.mark.parametrize("operation", ["prompt", "translate"])
def test_text_jobs_and_unknown_purposes_offer_nothing(operation):
    assert landing.eligible_assets(record(*SAVED.results, operation=operation), "image_plane") == ()
    assert landing.eligible_assets(SAVED, "import") == ()


def test_kinds_name_what_each_media_type_lands_as():
    assert [landing.kind(media) for media in ("image/png", "video/webm", "audio/ogg")] == [
        "image",
        "video",
        None,
    ]
    assert landing.accepts("camera_background", "video/mp4")
    assert not landing.accepts("image_plane", "video/mp4")
    assert not landing.accepts("camera_background", "image/webp")
