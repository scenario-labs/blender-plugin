# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Texture and projection metadata are allowlisted independently from file selection."""

import pytest

from scenario.core.jobs.result_metadata import (
    original_media_type,
    panorama_projection,
    texture_role,
)
from scenario.core.jobs.store import ResultAsset


@pytest.mark.parametrize(
    "source,expected",
    [
        ("texture", "base"),
        ("inference-txt2img-texture", "base"),
        ("inference-img2img-texture", "base"),
        ("inference-reference-texture", "base"),
        ("inference-controlnet-texture", "base"),
        ("upscale-texture", "base"),
        ("texture-albedo", "albedo"),
        ("texture-normal", "normal"),
        ("texture-smoothness", "smoothness"),
        ("texture-metallic", "metallic"),
        ("texture-height", "height"),
        ("texture-ao", "ao"),
        ("texture-edge", "edge"),
        ("3d-texture-albedo", "albedo"),
        ("3d-texture-normal", "normal"),
        ("3d-texture-roughness", "roughness"),
        ("3d-texture-metallic", "metallic"),
    ],
)
def test_documented_image_semantics(source, expected):
    assert texture_role({"mimeType": "image/png", "metadata": {"type": source}}) == expected


@pytest.mark.parametrize(
    "metadata",
    [None, [], {}, {"type": []}, {"type": "normal"}, {"type": "texture:new-private-value"}],
)
def test_missing_unknown_or_malformed_semantics_stay_unknown(metadata):
    assert texture_role({"mimeType": "image/png", "metadata": metadata}) is None


@pytest.mark.parametrize("mime", [None, [], "application/zip", "video/mp4", "model/gltf-binary"])
def test_generation_metadata_cannot_reclassify_a_nonimage_file(mime):
    assert texture_role({"mimeType": mime, "metadata": {"type": "texture-normal"}}) is None


@pytest.mark.parametrize("role", [[], "normal.png", "texture-normal", "unknown", True])
def test_store_refuses_unbounded_or_unsupported_role_values(role):
    with pytest.raises(ValueError, match="texture role"):
        ResultAsset("fixture-asset", "normal.png", "image/png", texture_role=role)


def test_store_does_not_allow_a_role_to_override_file_media_type():
    with pytest.raises(ValueError, match="texture role"):
        ResultAsset("fixture-asset", "model.glb", "model/gltf-binary", texture_role="normal")


@pytest.mark.parametrize("kind", ["skybox-base-360", "upscale-skybox", "skybox-hdri"])
@pytest.mark.parametrize("mime", ["image/jpeg", "image/png", "image/webp"])
def test_server_declared_skybox_images_are_equirectangular(kind, mime):
    record = {"mimeType": mime, "metadata": {"type": kind}}
    assert panorama_projection(record) == "equirectangular"
    assert texture_role(record) is None


@pytest.mark.parametrize(
    "record",
    [
        {"mimeType": "image/jpeg", "metadata": {"type": "skybox-3d"}},
        {"mimeType": "image/jpeg", "metadata": {"type": "texture"}},
        {"mimeType": "image/jpeg", "metadata": {"type": ["skybox-hdri"]}},
        {"mimeType": "image/jpeg", "metadata": None},
        {"mimeType": "image/jpeg"},
        {"mimeType": "model/gltf-binary", "metadata": {"type": "skybox-base-360"}},
        {"mimeType": None, "metadata": {"type": "skybox-hdri"}},
        {"mimeType": "image/jpeg", "name": "panorama-360.jpg", "metadata": {"type": "texture"}},
    ],
)
def test_projection_is_never_inferred_from_other_metadata_or_names(record):
    assert panorama_projection(record) is None


@pytest.mark.parametrize("original", ["image/x-exr", "image/aces"])
def test_exr_originals_replace_only_image_previews(original):
    record = {"mimeType": "image/jpeg", "originalMimeType": original}
    assert original_media_type(record) == original
    for mime in ("model/gltf-binary", "video/mp4", "audio/mpeg", None):
        assert original_media_type({**record, "mimeType": mime}) is None


@pytest.mark.parametrize(
    "original", [None, "image/vnd.radiance", "image/png", "model/ply", "model/spz", ["image/aces"]]
)
def test_other_originals_keep_the_asset_file(original):
    assert original_media_type({"mimeType": "image/jpeg", "originalMimeType": original}) is None
