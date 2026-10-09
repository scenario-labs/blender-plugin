# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Allowlisted texture semantics, independent of the delivered file's MIME type."""

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


def texture_role(record):
    """Use documented semantic metadata only for delivered image files."""
    mime = record.get("mimeType")
    metadata = record.get("metadata")
    if not isinstance(mime, str) or not mime.startswith("image/") or not isinstance(metadata, dict):
        return None
    kind = metadata.get("type")
    return _TEXTURE_ROLES.get(kind) if isinstance(kind, str) else None
