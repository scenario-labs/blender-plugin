# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Real-world tiling of a saved material: tile size, box scale and UV measurement. No bpy."""

import math
from dataclasses import dataclass

# One texture repeat every this many Blender units (metres at the default unit scale).
DEFAULT_TILE_SIZE_M = 2.0
MIN_TILE_SIZE_M = 0.01
MAX_TILE_SIZE_M = 1000.0
# Image Texture box projection blends its three projections over this fraction of the face
# angle; small enough to keep the texture sharp, enough to hide the seam on a rounded mesh.
BOX_BLEND = 0.1
# Floor for an object scale axis, so a flattened axis keeps a Mapping scale above zero.
_MIN_AXIS_SCALE = 1e-6
# Areas at or below this are degenerate for the UV measurement.
_MIN_AREA = 1e-12

BOX = "BOX"
UV = "UV"


def tile_size(value):
    """Validate an optional tile size in Blender units; None gives the default."""
    if value is None:
        return DEFAULT_TILE_SIZE_M
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        # Also refuses NaN, infinities and integers too large for a float.
        or not MIN_TILE_SIZE_M <= value <= MAX_TILE_SIZE_M
    ):
        raise ValueError(
            f"tile_size_m must be a length in Blender units from {MIN_TILE_SIZE_M:g} "
            f"to {MAX_TILE_SIZE_M:g}"
        )
    return float(value)


def box_scale(size, object_scale):
    """The Mapping scale of object-space coordinates that repeats once per `size` metres.

    One object-space unit is as long in the world as the object's scale on that axis, so a
    scaled plane keeps the tile size it was given in world metres.
    """
    size = tile_size(size)
    axes = tuple(abs(float(axis)) for axis in object_scale)
    if len(axes) != 3 or not all(math.isfinite(axis) for axis in axes):
        raise ValueError("The object's scale is not three finite numbers")
    return tuple(max(axis, _MIN_AXIS_SCALE) / size for axis in axes)


def polygon_area(points):
    """Area of one planar polygon from its corners, given as 2D or 3D coordinates.

    Newell's method: half the length of the summed cross products of consecutive corners.
    """
    total = [0.0, 0.0, 0.0]
    corners = [(*point, 0.0)[:3] for point in points]
    for (ax, ay, az), (bx, by, bz) in zip(corners, corners[1:] + corners[:1], strict=True):
        total[0] += ay * bz - az * by
        total[1] += az * bx - ax * bz
        total[2] += ax * by - ay * bx
    return math.sqrt(sum(axis * axis for axis in total)) / 2.0


def uv_metres_per_unit(samples):
    """Metres one UV unit spans, from (world area, UV area) pairs of sampled faces.

    The median of the per-face ratios ignores degenerate faces and outliers such as atlas
    islands. None when no face has both areas, so the UV layout cannot be measured.
    """
    ratios = sorted(
        math.sqrt(world / uv)
        for world, uv in samples
        if math.isfinite(world) and math.isfinite(uv) and world > _MIN_AREA and uv > _MIN_AREA
    )
    if not ratios:
        return None
    middle = len(ratios) // 2
    return ratios[middle] if len(ratios) % 2 else (ratios[middle - 1] + ratios[middle]) / 2.0


@dataclass(frozen=True)
class MaterialMapping:
    """How the shared Mapping node of a new material places every map.

    `projection` is "BOX" for a mesh without UVs (object-space box projection) or "UV";
    `scale` is the Mapping node's scale; `measured` is False when a UV mesh's size in
    metres could not be read and its tiling stays at 1.
    """

    projection: str
    tile_size: float
    scale: tuple
    measured: bool = True


def plan_mapping(size, *, uv, object_scale, metres_per_uv=None):
    """Choose the projection and Mapping scale for one mesh.

    A mesh without UVs uses box projection scaled by its object scale. A UV mesh scales
    its layout by the measured metres per UV unit, or keeps tiling 1 without one.
    """
    size = tile_size(size)
    if not uv:
        return MaterialMapping(BOX, size, box_scale(size, object_scale))
    if metres_per_uv is None or not math.isfinite(metres_per_uv) or metres_per_uv <= 0:
        return MaterialMapping(UV, size, (1.0, 1.0, 1.0), measured=False)
    scale = metres_per_uv / size
    return MaterialMapping(UV, size, (scale, scale, scale))
