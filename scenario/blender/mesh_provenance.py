# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Capture local mesh identities with the exact exported GLB before upload."""

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

import bpy

from ..core.jobs.mesh_source import MeshSource, MeshSourceObject
from . import mesh_export
from .mesh_application import _fingerprint


@dataclass(frozen=True)
class _Source:
    obj: object = field(repr=False)
    mesh: object = field(repr=False)
    name: str
    mesh_name: str
    geometry: bytes = field(repr=False)
    world: tuple
    parent: object = field(repr=False)
    collections: frozenset


def _capture(scene, obj):
    if scene != bpy.context.scene or obj not in tuple(scene.objects) or obj.type != "MESH":
        raise ValueError("Choose live meshes in the selected scene")
    return _Source(
        obj,
        obj.data,
        obj.name,
        obj.data.name,
        _fingerprint(obj.data),
        tuple(tuple(row) for row in obj.matrix_world),
        obj.parent,
        frozenset(obj.users_collection),
    )


def export_with_source(context, objects, path, session):
    """Return immutable provenance; it does not authorize automatic application."""
    objects = tuple(objects)
    if not 1 <= len(objects) <= 64 or len(set(objects)) != len(objects):
        raise ValueError("Choose between one and 64 distinct source meshes")
    scene = context.scene
    context.view_layer.update()
    before = tuple(_capture(scene, obj) for obj in objects)
    identities = tuple(session.capture(scene, obj) for obj in objects)
    mesh_export.export_glb(context, objects, path=str(path))
    context.view_layer.update()
    if tuple(_capture(scene, obj) for obj in objects) != before:
        raise ValueError("Source mesh changed during export; inspect it before uploading")
    # Export temporarily changes selection and can evaluate the graph. Freeze the
    # upload revision after restoration, retaining the exact pre-export identities.
    current = tuple(session.capture(scene, obj) for obj in objects)
    if any(
        (old.file_id, old.scene_id, old.target_id) != (new.file_id, new.scene_id, new.target_id)
        for old, new in zip(identities, current, strict=True)
    ):
        raise ValueError("The source context changed during export")
    path = Path(path)
    if path.is_symlink() or not path.is_file() or not 1 <= path.stat().st_size <= 256 * 1024 * 1024:
        raise ValueError("Use a bounded private GLB export")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        total = 0
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            total += len(chunk)
            if total > 256 * 1024 * 1024:
                raise ValueError("The exported source exceeded its capture limit")
            digest.update(chunk)
    source = MeshSource(
        digest.hexdigest(),
        tuple(
            MeshSourceObject(identity.target_id, snapshot.geometry.hex(), snapshot.world)
            for identity, snapshot in zip(current, before, strict=True)
        ),
    )
    origin = current[0] if len(current) == 1 else session.capture(scene)
    return origin, source
