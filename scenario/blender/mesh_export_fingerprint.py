# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Bounded, bulk base-mesh snapshots for export, independent of edit policies."""

import hashlib
import struct
import sys
from array import array

from ..core.api.errors import ScenarioError

# Per pass, across all distinct datablocks in the selection. Buffers are read and
# released one field at a time; the export file has its own independent byte cap.
MAX_SNAPSHOT_BYTES = 256 * 1024 * 1024
_STRING_BYTES = 256
_TYPES = {"FLOAT": "f", "INT": "i", "BOOLEAN": "b", "STRING": None}


def _plan(mesh):
    fields = []

    def field(collection, name, code, width=1):
        fields.append((collection, name, code, width))

    field(mesh.vertices, "co", "f", 3)
    field(mesh.edges, "vertices", "i", 2)
    field(mesh.loops, "vertex_index", "i")
    field(mesh.loops, "edge_index", "i")
    field(mesh.polygons, "loop_start", "i")
    field(mesh.polygons, "loop_total", "i")
    field(mesh.polygons, "material_index", "i")
    field(mesh.polygons, "use_smooth", "b")
    attributes = []
    for attribute in mesh.attributes:
        properties = attribute.bl_rna.properties["data"].fixed_type.properties
        name = next((key for key in ("value", "vector", "color") if key in properties), None)
        if name is None or properties[name].type not in _TYPES:
            raise ScenarioError(0, "This mesh attribute cannot be captured for export")
        prop = properties[name]
        field(attribute.data, name, _TYPES[prop.type], max(1, getattr(prop, "array_length", 1)))
        attributes.append((attribute.name, attribute.data_type, attribute.domain))
    metadata = repr(
        (
            "mesh-export-v1",
            attributes,
            [(name, code, width, len(data)) for data, name, code, width in fields],
            [(item.as_pointer(), item.name) if item else None for item in mesh.materials],
            [(layer.name, layer.active_render, layer.active_clone) for layer in mesh.uv_layers],
            mesh.uv_layers.active_index,
        )
    ).encode("utf-8")
    size = len(metadata) + sum(
        len(data) * width * (array(code).itemsize if code else _STRING_BYTES + 4)
        for data, _, code, width in fields
    )
    return fields, metadata, size


def _hash(plan):
    fields, metadata, _ = plan
    digest = hashlib.sha256(metadata)
    for data, name, code, width in fields:
        if code is None:
            # Blender exposes string attribute values as bounded byte strings;
            # foreach_get supports only numeric fields. Charge their maximum
            # storage up front, including empty strings, to bound Python work.
            for item in data:
                value = getattr(item, name)
                if not isinstance(value, bytes) or len(value) > _STRING_BYTES:
                    raise ScenarioError(0, "This mesh string attribute exceeds the capture limit")
                digest.update(struct.pack("<I", len(value)))
                digest.update(value)
        else:
            values = array(code, [0]) * (len(data) * width)
            data.foreach_get(name, values)
            if sys.byteorder != "little":
                values.byteswap()
            digest.update(values)
            del values
    return digest.digest()


def fingerprints(meshes):
    """Preflight the whole selection before hashing any buffers on the main thread."""
    meshes = tuple(meshes)
    plans = {}
    size = 0
    for mesh in meshes:
        if mesh in plans:
            continue
        plan = _plan(mesh)
        size += plan[2]
        if size > MAX_SNAPSHOT_BYTES:
            raise ScenarioError(
                0,
                "Selected meshes exceed the export snapshot budget; select fewer or simpler meshes",
            )
        plans[mesh] = plan
    hashes = {mesh: _hash(plan) for mesh, plan in plans.items()}
    return tuple(hashes[mesh] for mesh in meshes)
