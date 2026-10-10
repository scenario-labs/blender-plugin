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
    mime = record.get("mimeType")
    metadata = record.get("metadata")
    if not isinstance(mime, str) or not mime.startswith("image/") or not isinstance(metadata, dict):
        return None
    kind = metadata.get("type")
    return _TEXTURE_ROLES.get(kind) if isinstance(kind, str) else None
