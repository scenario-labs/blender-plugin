# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Allowlisted result semantics and file selection, independent of local filenames."""

# SDK 2.2.0 AssetMetadata.type and the public assets.retrieve contract.
# These labels describe map roles, never a format or a decoder guarantee.
_TEXTURE_ROLES = {
    "texture": "base",
    "inference-txt2img-texture": "base",
    "inference-img2img-texture": "base",
    "inference-reference-texture": "base",
    "inference-controlnet-texture": "base",
    "upscale-texture": "base",
    "texture-albedo": "albedo",
    "texture-normal": "normal",
    "texture-smoothness": "smoothness",
    "texture-metallic": "metallic",
    "texture-height": "height",
    "texture-ao": "ao",
    "texture-edge": "edge",
    "3d-texture-albedo": "albedo",
    "3d-texture-normal": "normal",
    "3d-texture-roughness": "roughness",
    "3d-texture-metallic": "metallic",
}
TEXTURE_ROLES = frozenset(_TEXTURE_ROLES.values())

# Filename rewriting during ingestion left legacy OBJ/MTL byte counts stale.
REWRITTEN_MESH_TYPES = frozenset({"model/obj", "model/mtl"})

# SDK 2.2.0 AssetRetrieveResponse.original_mime_type documents that an HDRi skybox
# exposes a JPEG preview as `url` and its `.exr` or `.hdr` file as `originalFileUrl`.
# Only these OpenEXR labels replace an image preview.
EXR_ORIGINAL_TYPES = frozenset({"image/x-exr", "image/aces"})
# Scenario re-encodes non-MP3 audio to a 128 kb/s MP3 asset file and keeps the
# model's file as the original (SDK 2.2.0 `original_file_url` lists audio). A WAV
# original replaces that lossy, padded MP3; the extension already decodes WAV.
# Radiance, mesh, splat, video and other audio originals keep the asset's own file
# until a decoder accepts them.
WAV_ORIGINAL_TYPES = frozenset({"audio/wav", "audio/x-wav"})
ORIGINAL_MEDIA_TYPES = EXR_ORIGINAL_TYPES | WAV_ORIGINAL_TYPES

# SDK 2.2.0 AssetMetadata.type values that describe a 2:1 360 environment.
# "skybox-3d" is a separate 3D world output, not an equirectangular image.
_PANORAMA_TYPES = frozenset({"skybox-base-360", "upscale-skybox", "skybox-hdri"})
PROJECTIONS = frozenset({"equirectangular"})


def _image(record):
    mime = record.get("mimeType")
    return isinstance(mime, str) and mime.startswith("image/")


# Container signatures of still images a saved result can hand to another model
# input. A match proves only the container, never that a decoder accepts it.
_IMAGE_SIGNATURES = {
    "image/png": lambda head: head.startswith(b"\x89PNG\r\n\x1a\n"),
    "image/jpeg": lambda head: head.startswith(b"\xff\xd8\xff"),
    "image/webp": lambda head: head[:4] == b"RIFF" and head[8:12] == b"WEBP",
}
IMAGE_SIGNATURE_TYPES = frozenset(_IMAGE_SIGNATURES)


def image_signature_matches(head, media_type):
    """Whether the first bytes of a file carry the container of its saved media type."""
    check = _IMAGE_SIGNATURES.get(media_type)
    return check is not None and isinstance(head, bytes) and len(head) >= 12 and check(head)


def texture_role(record):
    """Use documented semantic metadata only for delivered image files."""
    metadata = record.get("metadata")
    if not _image(record) or not isinstance(metadata, dict):
        return None
    kind = metadata.get("type")
    return _TEXTURE_ROLES.get(kind) if isinstance(kind, str) else None


def panorama_projection(record):
    """Report the server-declared 360 projection of an image asset, never a guess."""
    metadata = record.get("metadata")
    if not _image(record) or not isinstance(metadata, dict):
        return None
    kind = metadata.get("type")
    return "equirectangular" if isinstance(kind, str) and kind in _PANORAMA_TYPES else None


def original_media_type(record):
    """Return the declared original that replaces the asset's own file, if any.

    An OpenEXR original replaces an image preview and a WAV original replaces an
    audio file. The caller must still require `originalFileUrl`; a declared original
    without a destination fails closed rather than silently saving the asset file.
    """
    original = record.get("originalMimeType")
    mime = record.get("mimeType")
    if not isinstance(original, str) or not isinstance(mime, str):
        return None
    if mime.startswith("image/"):
        return original if original in EXR_ORIGINAL_TYPES else None
    if mime.startswith("audio/"):
        return original if original in WAV_ORIGINAL_TYPES else None
    return None
