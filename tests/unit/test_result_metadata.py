# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Texture metadata is allowlisted independently from file-format selection."""

import pytest

from scenario.core.jobs.result_metadata import texture_role
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
