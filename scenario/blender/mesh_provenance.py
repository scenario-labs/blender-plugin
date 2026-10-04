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
from .job_session import OriginUnavailable, _main_thread
from .mesh_application import MeshApplicationError, capture_target, validate_target


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


def _capture(obj, geometry):
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


def _capture_sources(scene, objects, session):
    if scene != bpy.context.scene or any(obj.type != "MESH" for obj in objects):
        raise ScenarioError(0, "Choose live meshes in the selected scene")
    try:
        if not session.active:
            raise OriginUnavailable("This job context is inactive")
        # Snapshot rejection must not enroll targets in scene invalidation.
        hashes = mesh_export_fingerprint.fingerprints(obj.data for obj in objects)
        snapshots = tuple(
            _capture(obj, digest) for obj, digest in zip(objects, hashes, strict=True)
        )
        identities = session.capture_many(scene, objects)
    except OriginUnavailable:
        raise ScenarioError(
            0, "Source context is unavailable; select live meshes and capture again"
        ) from None
    return snapshots, identities


def export_with_source(context, objects, path, session):
    """Return immutable provenance; it does not authorize automatic application."""
    _main_thread()
    objects = tuple(objects)
    if not 1 <= len(objects) <= 64 or len(set(objects)) != len(objects):
        raise ScenarioError(0, "Choose between one and 64 distinct source meshes")
    scene = context.scene
    context.view_layer.update()
    before, identities = _capture_sources(scene, objects, session)
    # A live application guard is stricter than upload provenance: unsupported
    # rigs/modifiers remain uploadable, but never become an in-place edit target.
    target = None
    if len(objects) == 1:
        try:
            target = capture_target(scene, objects[0])
        except MeshApplicationError:
            pass
    mesh_export.export_glb(context, objects, path=str(path))
    context.view_layer.update()
    after, current = _capture_sources(scene, objects, session)
    if after != before:
        raise ScenarioError(0, "Source mesh changed during export; inspect it before uploading")
    # Export temporarily changes selection and can evaluate the graph. Freeze the
    # upload revision after restoration, retaining the exact pre-export identities.
    if target is not None:
        validate_target(target)
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
    if target is not None:
        session.retain_mesh_source(origin, source, target)
    return origin, source
