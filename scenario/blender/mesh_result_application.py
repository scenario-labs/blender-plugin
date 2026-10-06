# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Replace one captured mesh from a verified single-mesh static GLB."""

import logging
from dataclasses import dataclass, field

import bpy

from . import mesh_application, model_application

_log = logging.getLogger("scenario.jobs")


class MeshResultApplicationError(RuntimeError):
    """Rejected before mutation, or all scene changes were verifiably rolled back."""


@dataclass(frozen=True)
class MeshEditApplication:
    source: object = field(repr=False)
    original: object = field(repr=False)
    policy: str
    undo_available: bool = False


def validate_request(target, *, policy, result_to_source, keep_original):
    """Validate the captured source and explicit policy without decoding files."""
    mesh_application.validate_target(target)
    if policy not in {"REMESH", "UV", "RETEXTURE"} or type(keep_original) is not bool:
        raise MeshResultApplicationError(
            "Choose REMESH, UV or RETEXTURE and an explicit Keep original value"
        )
    return mesh_application._matrix(result_to_source)


def _undo_enabled():
    """Respect native history settings; background sessions have no desktop history."""
    preferences = bpy.context.preferences.edit
    return (
        not bpy.app.background
        and preferences.use_global_undo
        and preferences.undo_steps > 1
        and bpy.context.window is not None
    )


def _undo_push(message):
    if bpy.ops.ed.undo_push(message=message) != {"FINISHED"}:
        raise RuntimeError("Blender could not record the mesh undo state")


def _release_import(imported, objects, staging):
    # Remove only imported objects, never the source or its Keep original copy.
    for obj in objects:
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.scenes.remove(staging)
    # The replacement mesh retains any material/image dependencies it needs.
    for name in model_application._DATA:
        if name in {"objects", "scenes"}:
            continue
        values = getattr(bpy.data, name)
        for value in imported[name]:
            if not value.users and not value.use_fake_user:
                values.remove(value)


def apply_saved_mesh(target, item, path, *, policy, result_to_source, keep_original):
    """Use an explicit GLB-scene-to-source-local mapping; never fit/guess alignment."""
    mapping = validate_request(
        target, policy=policy, result_to_source=result_to_source, keep_original=keep_original
    )
    undo = _undo_enabled()
    if undo:
        # Capture the latest user state before importing temporary datablocks.
        # A missing pre-state must stop replacement while the source is intact.
        try:
            _undo_push("Before Scenario mesh edit")
        except Exception:
            raise MeshResultApplicationError(
                "Could not prepare Blender undo; source is unchanged"
            ) from None
    before = model_application._snapshot()
    receipt = None
    try:
        with model_application.staged_model(item, path, before) as (staging, objects):
            meshes = [obj for obj in objects if obj.type == "MESH"]
            if len(meshes) != 1 or any(obj.type not in {"MESH", "EMPTY"} for obj in objects):
                raise MeshResultApplicationError("Choose one static primary mesh without variants")
            primary = meshes[0]
            # Blender has already converted GLB axes. Preserve imported node transforms,
            # but do not move the user's source or infer an alignment from selection.
            local_mapping = mapping @ primary.matrix_world
            imported = {
                name: set(getattr(bpy.data, name)) - previous for name, previous in before.items()
            }
            target.scene.collection.objects.link(primary)
            mesh_application.validate_target(target)
            receipt = mesh_application.apply_mesh(
                target.scene,
                target.obj,
                primary,
                policy=policy,
                result_to_source=local_mapping,
                keep_original=keep_original,
            )
            if receipt.original is not None:
                receipt.original.select_set(False)
            _release_import(imported, objects, staging)
            receipt.accept()
            if undo:
                try:
                    # The history state must contain no staging scene/private holder.
                    _undo_push("Scenario mesh edit")
                except Exception:
                    # The edit is complete. A missing history entry is not a failed
                    # application and must never authorize another replacement.
                    undo = False
                    _log.warning("Mesh applied, but Blender undo could not be recorded")
            return MeshEditApplication(target.obj, receipt.original, policy, undo)
    except Exception:
        if receipt is not None:
            try:
                receipt.rollback()
            except Exception:
                raise RuntimeError("Mesh replacement is uncertain; inspect the source") from None
        # Never remove new data while the source may still point at it.
        try:
            mesh_application.validate_target(target)
        except Exception:
            raise RuntimeError("Mesh source changed during application; inspect it") from None
        model_application._remove_new_data(before)
        if model_application._snapshot() != before:
            raise RuntimeError("Mesh cleanup is incomplete; do not apply again") from None
        raise MeshResultApplicationError(
            "Could not apply the verified mesh; source and saved files remain"
        ) from None
