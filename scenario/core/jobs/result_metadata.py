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
# exposes a JPEG preview as `url` and its EXR as `originalFileUrl`. Only these
# OpenEXR labels replace an image preview; Radiance, mesh, splat, audio and video
# originals keep the asset's own file until a decoder accepts them.
ORIGINAL_MEDIA_TYPES = frozenset({"image/x-exr", "image/aces"})

# SDK 2.2.0 AssetMetadata.type values that describe a 2:1 360 environment.
# "skybox-3d" is a separate 3D world output, not an equirectangular image.
_PANORAMA_TYPES = frozenset({"skybox-base-360", "upscale-skybox", "skybox-hdri"})
PROJECTIONS = frozenset({"equirectangular"})


def _image(record):
    mime = record.get("mimeType")
    return isinstance(mime, str) and mime.startswith("image/")


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
    """Return the declared OpenEXR original that replaces an image preview, if any.

    The caller must still require `originalFileUrl`; a declared original without a
    destination fails closed rather than silently saving the preview instead.
    """
    original = record.get("originalMimeType")
    if not _image(record) or not isinstance(original, str):
        return None
    return original if original in ORIGINAL_MEDIA_TYPES else None
