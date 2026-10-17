# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Placement math, importer selection and primary-mesh choice for 3D results. No bpy."""

import json
import math
import pathlib
import struct

# Accepted longest side of a saved model import, in Blender units (metres at the
# default unit scale, as every MCP length): a small prop up to a large building.
MIN_TARGET_SIZE_M = 0.01
MAX_TARGET_SIZE_M = 1000.0

_IMPORTERS = {
    ".glb": "gltf",
    ".gltf": "gltf",
    ".fbx": "fbx",
    ".obj": "obj",
    ".spz": "spz",
    ".ply": "ply",
}
_FORMAT_RANK = {
    "gltf": 0,
    "fbx": 1,
    "obj": 2,
    "ply": 3,
    "spz": 4,
}  # splats come last: they are worlds, not meshes


def importer_for(path):
    suffix = pathlib.Path(str(path)).suffix.lower()
    kind = _IMPORTERS.get(suffix)
    if kind is None and suffix in (".bin", ""):
        # splats downloaded before 0.8.1 kept a generic extension (mime model/spz was unknown): recognise them by content
        from . import spz

        if spz.sniff_spz(path):
            return "spz"
    return kind


def bottom_center_offset(bbox_min, bbox_max, target):
    cx = (bbox_min[0] + bbox_max[0]) / 2.0
    cy = (bbox_min[1] + bbox_max[1]) / 2.0
    return (float(target[0] - cx), float(target[1] - cy), float(target[2] - bbox_min[2]))


def target_size(value):
    """Validate an optional requested longest side in Blender units; None keeps the saved size.

    The longest side does not depend on how a provider oriented the model, and
    it is the size usually quoted for an object.
    """
    if value is None:
        return None
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        # Also refuses NaN, infinities and integers too large for a float.
        or not MIN_TARGET_SIZE_M <= value <= MAX_TARGET_SIZE_M
    ):
        raise ValueError(
            f"target_size_m must be a length in Blender units from {MIN_TARGET_SIZE_M:g} "
            f"to {MAX_TARGET_SIZE_M:g}"
        )
    return float(value)


def fit_scale(bbox_min, bbox_max, size):
    """The uniform factor that gives the box's longest side `size`; 1.0 when size is None."""
    if size is None:
        return 1.0
    longest = max(float(high) - float(low) for low, high in zip(bbox_min, bbox_max, strict=True))
    factor = size / longest if longest > 0 else math.inf
    if not math.isfinite(factor) or factor <= 0:
        raise ValueError("The model has no measurable size to scale")
    return factor


def glb_summary(path):
    """Read the JSON chunk of a binary glTF: image count and whether the first material has PBR textures."""
    try:
        with open(path, "rb") as fh:
            magic, _version, _length = struct.unpack("<4sII", fh.read(12))
            if magic != b"glTF":
                return {"images": 0, "pbr_textures": 0, "materials": 0}
            chunk_len, _chunk_type = struct.unpack("<II", fh.read(8))
            js = json.loads(fh.read(chunk_len))
    except (OSError, ValueError, struct.error):
        return {"images": 0, "pbr_textures": 0, "materials": 0}
    materials = js.get("materials") or []
    pbr = 0
    for mat in materials:
        pbr += sum(1 for key in (mat.get("pbrMetallicRoughness") or {}) if key.endswith("Texture"))
        pbr += sum(1 for key in ("normalTexture", "occlusionTexture") if key in mat)
    return {"images": len(js.get("images") or []), "pbr_textures": pbr, "materials": len(materials)}


def rank_mesh_files(paths):
    """Order mesh files from the one to import first to the least useful.

    Providers ship several variants of one result (Meshy: GLB + OBJ + textures, Rodin with material=All: a shaded GLB
    and a PBR GLB). Prefer glTF, then the file with the most PBR textures, then the most images, then the larger file.
    """
    ranked = []
    for path in paths:
        kind = importer_for(path)
        if kind is None:
            continue
        info = (
            glb_summary(path)
            if kind == "gltf"
            else {"images": 0, "pbr_textures": 0, "materials": 0}
        )
        try:
            size = pathlib.Path(path).stat().st_size
        except OSError:
            size = 0
        ranked.append(
            (_FORMAT_RANK[kind], -info["pbr_textures"], -info["images"], -size, str(path), info)
        )
    ranked.sort()
    return [(entry[4], entry[5]) for entry in ranked]


def pick_primary_mesh(paths):
    """Return (primary_path, alternates) or (None, [])."""
    ranked = rank_mesh_files(paths)
    if not ranked:
        return None, []
    return ranked[0][0], [path for path, _ in ranked[1:]]
