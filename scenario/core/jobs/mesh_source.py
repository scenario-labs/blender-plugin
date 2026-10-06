# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Immutable local provenance for a Blender mesh export, never an API parameter."""

import math
import re
from dataclasses import dataclass

from .store import _identity


def _sha(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError("Use a SHA256 mesh source identity")


def _finite(value):
    try:
        return type(value) in {int, float} and math.isfinite(value)
    except OverflowError:
        return False


@dataclass(frozen=True)
class MeshSourceObject:
    target_id: str
    geometry_sha256: str
    matrix_world: tuple[tuple[float, ...], ...]

    def __post_init__(self):
        _identity(self.target_id)
        _sha(self.geometry_sha256)
        matrix = self.matrix_world
        if (
            not isinstance(matrix, tuple)
            or len(matrix) != 4
            or any(not isinstance(row, tuple) or len(row) != 4 for row in matrix)
            or any(not _finite(v) for row in matrix for v in row)
            or matrix[3] != (0, 0, 0, 1)
        ):
            raise ValueError("Use a finite affine world matrix")


@dataclass(frozen=True)
class MeshSource:
    file_sha256: str
    objects: tuple[MeshSourceObject, ...]
    convention: str = "blender-world-gltf-y-up"
    evaluated_modifiers: bool = True
    animations: bool = False

    def __post_init__(self):
        _sha(self.file_sha256)
        if (
            not isinstance(self.objects, tuple)
            or not 1 <= len(self.objects) <= 64
            or any(not isinstance(obj, MeshSourceObject) for obj in self.objects)
            or len({obj.target_id for obj in self.objects}) != len(self.objects)
            or self.convention != "blender-world-gltf-y-up"
            or self.evaluated_modifiers is not True
            or self.animations is not False
        ):
            raise ValueError(
                "Use a bounded unique mesh source and the explicit exporter convention"
            )


def decode_mesh_source(value):
    if value is None:
        return None
    if not isinstance(value, dict) or set(value) != set(MeshSource.__dataclass_fields__):
        raise ValueError("Invalid mesh source record")
    value = dict(value)
    objects = value.pop("objects")
    if not isinstance(objects, list) or not 1 <= len(objects) <= 64:
        raise ValueError("Invalid mesh source objects")
    decoded = []
    for obj in objects:
        if not isinstance(obj, dict) or set(obj) != set(MeshSourceObject.__dataclass_fields__):
            raise ValueError("Invalid mesh source object")
        obj = dict(obj)
        matrix = obj.pop("matrix_world")
        if not isinstance(matrix, list) or any(not isinstance(row, list) for row in matrix):
            raise ValueError("Invalid mesh source transform")
        decoded.append(MeshSourceObject(**obj, matrix_world=tuple(tuple(row) for row in matrix)))
    return MeshSource(**value, objects=tuple(decoded))
