# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Texture metadata is allowlisted independently from file-format selection."""

import pytest

from scenario.core.jobs.result_metadata import (
    IMAGE_SIGNATURE_TYPES,
    image_signature_matches,
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


PNG = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01"
WEBP = b"RIFF\x24\x00\x00\x00WEBPVP8 "


@pytest.mark.parametrize(
    "head,media_type", [(PNG, "image/png"), (JPEG, "image/jpeg"), (WEBP, "image/webp")]
)
def test_still_image_signatures_match_their_saved_media_type(head, media_type):
    assert image_signature_matches(head, media_type)
    assert media_type in IMAGE_SIGNATURE_TYPES
    for other in IMAGE_SIGNATURE_TYPES - {media_type}:
        assert not image_signature_matches(head, other)


@pytest.mark.parametrize(
    "head,media_type",
    [
        (PNG[:11], "image/png"),  # truncated before a full container header
        (b"RIFF\x24\x00\x00\x00WAVEfmt ", "image/webp"),  # RIFF that is not WebP
        (b"\xff\xd8\x00\x00" + JPEG[4:], "image/jpeg"),  # SOI without a marker
        (PNG, "image/exr"),  # formats outside the still-image handoff
        (PNG, "image/gif"),
        (PNG, None),
        ("\x89PNG\r\n\x1a\n0000", "image/png"),  # text, not bytes
        (b"", "image/png"),
    ],
)
def test_mismatched_truncated_or_unsupported_images_are_refused(head, media_type):
    assert not image_signature_matches(head, media_type)
