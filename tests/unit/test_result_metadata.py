# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Texture and projection metadata are allowlisted independently from file selection."""

import pytest

from scenario.core.jobs.result_metadata import (
    IMAGE_SIGNATURE_TYPES,
    image_signature_matches,
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


@pytest.mark.parametrize("original", ["audio/wav", "audio/x-wav"])
def test_wav_originals_replace_only_audio_files(original):
    # Scenario re-encodes a model's WAV to an MP3 asset file and keeps the WAV as original.
    record = {"mimeType": "audio/mpeg", "originalMimeType": original}
    assert original_media_type(record) == original
    for mime in ("image/jpeg", "video/mp4", "model/gltf-binary", None):
        assert original_media_type({**record, "mimeType": mime}) is None


@pytest.mark.parametrize(
    "original", ["audio/mpeg", "audio/ogg", "audio/flac", "image/x-exr", ["audio/wav"]]
)
def test_other_audio_originals_keep_the_asset_file(original):
    assert original_media_type({"mimeType": "audio/mpeg", "originalMimeType": original}) is None


def test_panorama_hdr_types_never_include_audio_originals():
    from scenario.core.jobs.result_metadata import (
        EXR_ORIGINAL_TYPES,
        ORIGINAL_MEDIA_TYPES,
        WAV_ORIGINAL_TYPES,
    )
    from scenario.core.scene.panorama_contract import HDR_MEDIA_TYPES

    assert HDR_MEDIA_TYPES == EXR_ORIGINAL_TYPES | {"image/exr"}
    assert not WAV_ORIGINAL_TYPES & HDR_MEDIA_TYPES
    assert ORIGINAL_MEDIA_TYPES == EXR_ORIGINAL_TYPES | WAV_ORIGINAL_TYPES


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
