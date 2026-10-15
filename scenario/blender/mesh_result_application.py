# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Apply an explicitly chosen mesh, skin, clips or parts policy to a captured source.

The result is one classified import unit of the saved job: a GLB, JSON glTF,
FBX, or OBJ with its MTL and maps. It is rehashed into the same private snapshot
as a package import before any claim, then staged in a disposable scene.
"""

import logging
from dataclasses import dataclass, field

import bpy
from mathutils import Matrix

from ..core.scene.model_formats import ModelFormat, UnitKind
from . import animation_application, mesh_application, model_application, rig_application
from .model_application import _undo_enabled, _undo_push

_log = logging.getLogger("scenario.jobs")


class MeshResultApplicationError(RuntimeError):
    """Rejected before mutation, or all scene changes were verifiably rolled back.

    `reason` repeats a mesh policy's own fixed rejection text, such as which
    result geometry failed to match the source; it never carries file data.
    """

    def __init__(self, message, reason=None):
        super().__init__(message)
        self.reason = reason


@dataclass(frozen=True)
class MeshEditApplication:
    source: object = field(repr=False)
    original: object = field(repr=False)
    policy: str
    undo_available: bool = False
    parts: tuple = field(default=(), repr=False)
    rig: object = field(default=None, repr=False)
    # New actions ANIMATE assigned to the rig, the active one first.
    clips: tuple = field(default=(), repr=False)
    # The verified scene-to-source-local mapping, and the FIT base it came from;
    # empty for ANIMATE, which uses no mapping.
    mapping: tuple = ()
    fitted_from: str | None = None


POLICIES = frozenset({"REMESH", "UV", "RETEXTURE", "PARTS", "RIG", "ANIMATE"})
# Policies that import a returned rig and its clips; the others require a static result.
_RIGGED = frozenset({"RIG", "ANIMATE"})
# Import formats a mesh edit can stage. A PLY's bytes decide between a mesh and
# splats, which only the worker import path reads, and splats never edit a mesh.
FORMATS = frozenset({ModelFormat.GLB, ModelFormat.GLTF, ModelFormat.FBX, ModelFormat.OBJ})


def applicable(unit):
    """Whether a classified import unit can be applied to a source in place."""
    return unit.kind is UnitKind.MESH and unit.format in FORMATS


def validate_request(target, *, policy, result_to_source, keep_original):
    """Validate the captured source and explicit policy without decoding files."""
    mesh_application.validate_target(target)
    if policy not in POLICIES or type(keep_original) is not bool:
        raise MeshResultApplicationError(
            "Choose REMESH, UV, RETEXTURE, PARTS, RIG or ANIMATE and an explicit Keep original value"
        )
    if target.skin is not None and policy not in _RIGGED:
        # Static policies would silently drop the source's skin and rig binding.
        raise MeshResultApplicationError(
            "This source is skinned to an armature; choose RIG to replace its skin "
            "or ANIMATE to apply returned clips to its rig"
        )
    if target.skin is None and policy == "ANIMATE":
        raise MeshResultApplicationError(
            "ANIMATE needs a mesh skinned to an armature; choose RIG to attach the returned rig"
        )
    if policy == "PARTS" and (not target.mesh.vertices or not target.mesh.polygons):
        raise MeshResultApplicationError(
            "Choose a source with surface geometry, not a parts anchor"
        )
    if isinstance(result_to_source, mesh_application.FitRequest):
        if policy not in mesh_application.FIT_POLICIES or not result_to_source.bases:
            raise MeshResultApplicationError(
                "Fitted coordinates apply to UV, retexture and rig only"
            )
        for _, rows in result_to_source.bases:
            mesh_application._matrix(rows)
        return result_to_source
    return mesh_application._matrix(result_to_source)


def prepare_saved_mesh(target, unit, files, *, policy, result_to_source, keep_original):
    """Check the request, then rehash the unit into a private snapshot before any claim.

    `files` maps the verified job's asset IDs to (StoredResult, path). Static
    policies refuse a GLB or glTF with skins or animations here. Raises
    ModelPreflightError with the scene and saved job unchanged; the caller owns
    the returned snapshot's cleanup.
    """
    validate_request(
        target, policy=policy, result_to_source=result_to_source, keep_original=keep_original
    )
    if not applicable(unit):
        raise model_application.ModelPreflightError(
            "Choose a GLB, glTF, FBX or OBJ mesh result; splats and PLY files cannot "
            "edit a mesh in place"
        )
    return model_application.prepare_snapshot(unit, files, static_only=policy not in _RIGGED)


def _release_import(imported, objects, staging):
    # Remove only imported objects, never the source or its Keep original copy.
    for obj in objects:
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.scenes.remove(staging)
    # The replacement mesh retains any material/image dependencies it needs.
    for name in model_application._PACKAGE_DATA:
        if name in {"objects", "scenes"}:
            continue
        values = getattr(bpy.data, name)
        for value in imported[name]:
            if not value.users and not value.use_fake_user:
                values.remove(value)


def _helpers(objects):
    """Imported meshes that only display a returned rig: pose bones' custom shapes.

    Any other mesh, such as an unskinned accessory beside the skin, stays a
    result mesh, so the policy's mesh checks refuse it instead of discarding it.
    """
    helpers = set()
    for rig in (obj for obj in objects if obj.type == "ARMATURE"):
        for bone in rig.pose.bones:
            if bone.custom_shape is not None:
                helpers.add(bone.custom_shape)
                # A retained rig keeps no pointer to a helper removed with the import.
                bone.custom_shape = None
    return tuple(obj for obj in objects if obj in helpers)


def _stage_parts(target, meshes, mapping):
    """Copy static part geometry into source-local coordinates before replacement."""
    if not 2 <= len(meshes) <= 128:
        raise MeshResultApplicationError("Choose a static result containing 2 to 128 mesh parts")
    components = 0
    for obj in meshes:
        mesh_application._validate_object(obj.users_scene[0], obj)
        data = obj.data
        components += len(data.vertices) + len(data.edges) + len(data.loops) + len(data.polygons)
        components += sum(len(attribute.data) for attribute in data.attributes)
        if components > mesh_application.MAX_COMPONENTS:
            raise MeshResultApplicationError("Parts exceed the synchronous component limit")
        if not data.vertices or not data.polygons:
            raise MeshResultApplicationError("Each part must contain surface geometry")
        mesh_application._fingerprint(data)
        mesh_application._matrix(mapping @ obj.matrix_world)
    parts = []
    for index, obj in enumerate(meshes, 1):
        mesh = obj.data.copy()
        mesh.use_fake_user = False
        mesh.transform(mapping @ obj.matrix_world)
        mesh.update()
        mesh_application._fingerprint(mesh)
        name = f"{target.name} Part {index:03d} {obj.name}"
        part = bpy.data.objects.new(name, mesh)
        parts.append(part)
    # Reuse the guarded mesh-swap primitive with an empty result. The original
    # object becomes the group anchor; existing children/context are unchanged.
    blank = bpy.data.objects.new("Scenario parts staging", bpy.data.meshes.new("Scenario parts"))
    target.scene.collection.objects.link(blank)
    return tuple(parts), blank


def _publish_parts(target, parts):
    for part in parts:
        part.parent = target.obj
        part.matrix_parent_inverse = Matrix.Identity(4)
        part.matrix_basis = Matrix.Identity(4)
        for collection in target.obj.users_collection:
            collection.objects.link(part)
        part.select_set(False)
    bpy.context.view_layer.update()


def apply_saved_mesh(target, snapshot, *, policy, result_to_source, keep_original):
    """Use an explicit imported-scene-to-source-local mapping or an approved verified fit.

    `snapshot` comes from `prepare_saved_mesh` and is consumed here. UV,
    RETEXTURE and RIG treat every returned result mesh as one surface; display
    helpers (`_helpers`) are never result meshes. Alignment is never guessed: a
    `FitRequest` is used only when the full correspondence verifies it.
    """
    mapping = validate_request(
        target, policy=policy, result_to_source=result_to_source, keep_original=keep_original
    )
    model_application.use_snapshot(snapshot)
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
    # FBX and OBJ importers can also create curves and legacy textures.
    before = model_application._snapshot(model_application._PACKAGE_TRACKED)
    receipt = None
    try:
        # Static policies keep FBX clips out; GLB and glTF ones were refused unless static.
        with model_application.staged_snapshot(snapshot, before, animation=policy in _RIGGED) as (
            staging,
            objects,
        ):
            # Display helpers are not results; they go with the other imported data.
            helpers = _helpers(objects)
            meshes = [obj for obj in objects if obj.type == "MESH" and obj not in helpers]
            if policy not in _RIGGED and any(obj.type not in {"MESH", "EMPTY"} for obj in objects):
                raise MeshResultApplicationError("Choose static meshes with optional Empty parents")
            parts = clips = ()
            rig = None
            if policy == "PARTS":
                parts, primary = _stage_parts(target, meshes, mapping)
                objects = (*objects, primary)
                local_mapping = Matrix.Identity(4)
            elif policy != "ANIMATE":
                if not meshes or (policy == "REMESH" and len(meshes) != 1):
                    raise MeshResultApplicationError("Choose one primary mesh without variants")
                primary = meshes[0]
                # Blender has already converted the file's axes and units. Preserve
                # imported node transforms; never infer alignment or move the source.
                if policy == "REMESH":
                    local_mapping = mapping @ primary.matrix_world
                for obj in meshes:
                    target.scene.collection.objects.link(obj)
            imported = {
                name: set(getattr(bpy.data, name)) - previous for name, previous in before.items()
            }
            mesh_application.validate_target(target)
            if policy == "ANIMATE":
                # Clips are pose data on the source's own rig: no mapping and no
                # returned object is kept.
                receipt = animation_application.apply_clips(
                    target, tuple(obj for obj in objects if obj not in helpers)
                )
                rig, clips = receipt.rig, receipt.actions
            elif policy == "RIG":
                skin = tuple(obj for obj in objects if obj not in helpers)
                receipt = rig_application.apply_skin(
                    target, tuple(meshes), skin, mapping, keep_original=keep_original
                )
                rig = receipt.rig
                objects = tuple(obj for obj in objects if obj not in receipt.objects)
            elif policy in {"UV", "RETEXTURE"}:
                receipt = mesh_application.apply_surface(
                    target.scene,
                    target.obj,
                    tuple(meshes),
                    policy=policy,
                    result_to_source=mapping,
                    keep_original=keep_original,
                )
            else:
                receipt = mesh_application.apply_mesh(
                    target.scene,
                    target.obj,
                    primary,
                    policy="REMESH" if policy == "PARTS" else policy,
                    result_to_source=local_mapping,
                    keep_original=keep_original,
                )
            if parts:
                _publish_parts(target, parts)
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
            surface = getattr(receipt, "surface", None)
            used = () if policy == "ANIMATE" else (surface.mapping if surface else mapping)
            return MeshEditApplication(
                target.obj,
                receipt.original,
                policy,
                undo,
                parts,
                rig,
                clips,
                tuple(tuple(row) for row in used),
                surface.fitted_from if surface else None,
            )
    except Exception as error:
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
        model_application._remove_new_data(before, model_application._PACKAGE_DATA)
        if model_application._snapshot(model_application._PACKAGE_TRACKED) != before:
            raise RuntimeError("Mesh cleanup is incomplete; do not apply again") from None
        reason = str(error) if isinstance(error, mesh_application.MeshApplicationError) else None
        raise MeshResultApplicationError(
            "Could not apply the verified mesh; source and saved files remain"
            + (f": {reason}" if reason else ""),
            reason,
        ) from None
