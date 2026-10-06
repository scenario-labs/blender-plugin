# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Capture local mesh identities with the exact exported GLB before upload."""

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

import bpy

from ..core.api.errors import ScenarioError
from ..core.jobs.mesh_source import MeshSource, MeshSourceObject
from . import mesh_export, mesh_export_fingerprint


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


def _capture(scene, obj, geometry):
    if scene != bpy.context.scene or obj not in tuple(scene.objects) or obj.type != "MESH":
        raise ScenarioError(0, "Choose live meshes in the selected scene")
    return _Source(
        obj,
        obj.data,
        obj.name,
        obj.data.name,
        geometry,
        tuple(tuple(row) for row in obj.matrix_world),
        obj.parent,
        frozenset(obj.users_collection),
    )


def _capture_sources(scene, objects):
    if scene != bpy.context.scene or any(
        obj not in tuple(scene.objects) or obj.type != "MESH" for obj in objects
    ):
        raise ScenarioError(0, "Choose live meshes in the selected scene")
    hashes = mesh_export_fingerprint.fingerprints(obj.data for obj in objects)
    return tuple(_capture(scene, obj, digest) for obj, digest in zip(objects, hashes, strict=True))


def export_with_source(context, objects, path, session):
    """Return immutable provenance; it does not authorize automatic application."""
    objects = tuple(objects)
    if not 1 <= len(objects) <= 64 or len(set(objects)) != len(objects):
        raise ScenarioError(0, "Choose between one and 64 distinct source meshes")
    scene = context.scene
    context.view_layer.update()
    before = _capture_sources(scene, objects)
    identities = tuple(session.capture(scene, obj) for obj in objects)
    mesh_export.export_glb(context, objects, path=str(path))
    context.view_layer.update()
    if _capture_sources(scene, objects) != before:
        raise ScenarioError(0, "Source mesh changed during export; inspect it before uploading")
    # Export temporarily changes selection and can evaluate the graph. Freeze the
    # upload revision after restoration, retaining the exact pre-export identities.
    current = tuple(session.capture(scene, obj) for obj in objects)
    if any(
        (old.file_id, old.scene_id, old.target_id) != (new.file_id, new.scene_id, new.target_id)
        for old, new in zip(identities, current, strict=True)
    ):
        raise ScenarioError(
            0, "The source context changed during export; select it and capture again"
        )
    path = Path(path)
    if path.is_symlink() or not path.is_file() or not 1 <= path.stat().st_size <= 256 * 1024 * 1024:
        raise ScenarioError(
            0, "Mesh snapshot must be nonempty and at most 256 MiB; simplify it and capture again"
        )
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        total = 0
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            total += len(chunk)
            if total > 256 * 1024 * 1024:
                raise ScenarioError(
                    0, "Mesh snapshot exceeded 256 MiB; simplify it and capture again"
                )
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
