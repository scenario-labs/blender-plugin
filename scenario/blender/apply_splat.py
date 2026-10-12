# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Prototype Gaussian splat imports from local files (.spz from Marble and HY World, .ply).

Saved shared jobs import splats through `splat_application` after worker
decoding and an approved destination. This prototype entry decodes a local SPZ
file on the main thread and delegates the point cloud to the same builder, so it
creates its own mesh, Geometry Nodes group and material and never reuses an
existing material. Blender has no Gaussian splat renderer: the result is a
coloured point-cloud approximation in the viewport, EEVEE and Cycles.
"""

import logging
import os

import bpy

from ..core.scene import splats
from .splat_application import DEFAULT_POINTS, build_points

log = logging.getLogger("scenario.splat")
DEFAULT_MAX_POINTS = DEFAULT_POINTS
_DATA = ("objects", "meshes", "materials", "node_groups")


def import_spz(context, path, max_points=DEFAULT_MAX_POINTS, name=None, collection=None):
    """Decode an .spz file and add a point-cloud object at the origin (Y-up converted to Z-up).

    Returns the object. A rejected file raises `SplatError` before any data is created.
    """
    limit = min(max_points or DEFAULT_MAX_POINTS, splats.MAX_KEPT_POINTS)
    with open(str(path), "rb") as handle:
        data = splats.decode(
            handle,
            "model/spz",
            options=splats.SplatOptions(limit, "OPENGL"),
            size=os.fstat(handle.fileno()).st_size,
        )
    previous = {key: set(getattr(bpy.data, key)) for key in _DATA}
    try:
        obj = build_points(data, name or "Scenario Splat")
        (collection or context.scene.collection).objects.link(obj)
    except Exception:
        for key in _DATA:
            values = getattr(bpy.data, key)
            for value in set(values) - previous[key]:
                values.remove(value, do_unlink=True)
        raise
    log.info("splat %s: %d of %d points", path, data.kept, data.count)
    return obj


def import_ply(context, path):
    """PLY through Blender's importer (Gaussian splat PLYs come in as vertices with colour attributes)."""
    before = set(bpy.data.objects.keys())
    bpy.ops.wm.ply_import(filepath=str(path))
    return [o for o in bpy.data.objects if o.name not in before]
