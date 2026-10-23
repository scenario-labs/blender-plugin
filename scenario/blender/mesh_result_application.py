# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Apply an explicitly chosen mesh, skin, clips or parts policy to a captured source.

The result is one classified import unit of the saved job: a GLB, JSON glTF,
FBX, or OBJ with its MTL and maps. It is rehashed into the same private snapshot
as a package import before any claim, then staged in a disposable scene.
"""

import logging
from array import array
from dataclasses import dataclass, field

import bmesh
import bpy
from mathutils import Matrix

from ..core.scene import mesh_correspondence
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
    # ANIMATE's largest rest correction in degrees; None for the other policies.
    rest_correction_deg: float | None = None
    # The verified scene-to-source-local mapping, and the FIT base it came from;
    # empty for ANIMATE, which uses no mapping. For several sources the mapping
    # takes result scene coordinates to scene coordinates.
    mapping: tuple = ()
    fitted_from: str | None = None
    # RIG or ANIMATE clips keyed at an FBX file's other frame rate; never retimed.
    frame_rate_mismatch: bool = False
    # Every edited source and its Keep original copy (or None), in capture order.
    sources: tuple = field(default=(), repr=False)
    originals: tuple = field(default=(), repr=False)
    # PARTS: "source_faces" when the source was split along the result's parts,
    # "result_meshes" when the result's own meshes were copied.
    parts_from: str | None = None
    # REMESH: how many result meshes were joined into the one remesh.
    joined_meshes: int | None = None
    # A bounds fit's (worst distance, fraction beyond tolerance) of the source size.
    fit_residual: tuple = ()


POLICIES = frozenset({"REMESH", "UV", "RETEXTURE", "PARTS", "RIG", "ANIMATE"})
# Policies that import a returned rig and its clips; the others require a static result.
_RIGGED = frozenset({"RIG", "ANIMATE"})
# Import formats a mesh edit can stage. A PLY's bytes decide between a mesh and
# splats, which only the worker import path reads, and splats never edit a mesh.
FORMATS = frozenset({ModelFormat.GLB, ModelFormat.GLTF, ModelFormat.FBX, ModelFormat.OBJ})


def applicable(unit):
    """Whether a classified import unit can be applied to a source in place."""
    return unit.kind is UnitKind.MESH and unit.format in FORMATS


# Several captured sources keep their geometry: one surface, one mapping, one rig.
SEVERAL_SOURCE_POLICIES = frozenset({"UV", "RETEXTURE", "RIG"})


def targets(target):
    """The captured targets of a request: one `MeshTarget`, or a tuple of several."""
    return target if isinstance(target, tuple) else (target,)


def _validate_sources(sources, policy, result_to_source):
    """Several captured sources: one scene, a surface policy and scene coordinates."""
    if not 2 <= len(sources) <= 64 or len({item.obj for item in sources}) != len(sources):
        raise MeshResultApplicationError("Choose between two and 64 distinct captured sources")
    if len({item.scene for item in sources}) != 1:
        raise MeshResultApplicationError("Use captured sources in one scene")
    if policy not in SEVERAL_SOURCE_POLICIES:
        raise MeshResultApplicationError(
            "Several captured objects accept only UV, RETEXTURE or RIG; replacing geometry, "
            "parts or animation needs one object"
        )
    bases = (
        result_to_source.bases
        if isinstance(result_to_source, mesh_application.FitRequest)
        else (("WORLD", result_to_source),)
    )
    # Every source is placed by its own transform: only scene coordinates are shared.
    if [label for label, _ in bases] != ["WORLD"] or any(
        mesh_application._matrix(rows) != Matrix.Identity(4) for _, rows in bases
    ):
        raise MeshResultApplicationError(
            "Several captured objects use scene coordinates or Fit and verify"
        )


def validate_request(target, *, policy, result_to_source, keep_original):
    """Validate the captured source(s) and explicit policy without decoding files.

    A tuple of targets is several captured sources edited together: UV,
    RETEXTURE or RIG, with result scene coordinates (identity) or its FIT.
    """
    sources = targets(target)
    for item in sources:
        mesh_application.validate_target(item)
    if policy not in POLICIES or type(keep_original) is not bool:
        raise MeshResultApplicationError(
            "Choose REMESH, UV, RETEXTURE, PARTS, RIG or ANIMATE and an explicit Keep original value"
        )
    if isinstance(target, tuple):
        _validate_sources(sources, policy, result_to_source)
    if any(item.skin is not None for item in sources) and policy not in _RIGGED:
        # Static policies would silently drop the source's skin and rig binding.
        raise MeshResultApplicationError(
            "This source is skinned to an armature; choose RIG to replace its skin "
            "or ANIMATE to apply returned clips to its rig"
        )
    if sources[0].skin is None and policy == "ANIMATE":
        raise MeshResultApplicationError(
            "ANIMATE needs a mesh skinned to an armature; choose RIG to attach the returned rig"
        )
    if policy == "PARTS" and (not sources[0].mesh.vertices or not sources[0].mesh.polygons):
        raise MeshResultApplicationError(
            "Choose a source with surface geometry, not a parts anchor"
        )
    if isinstance(result_to_source, mesh_application.FitRequest):
        if policy not in mesh_application.FIT_POLICIES or not result_to_source.bases:
            raise MeshResultApplicationError("Fitted coordinates do not apply to animation")
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


def _part_name(target, index, obj):
    return f"{target.name} Part {index:03d} {obj.name}"


def _part_textures(surface, meshes, source, owner):
    """The UVs and materials the result parts carry, resolved per split part, or None.

    Parts that all carry them are retextured through the verified correspondence,
    like RETEXTURE; when only some do, this fails, so the parts are copied.
    """
    carried = [
        bool(obj.data.uv_layers) or any(material is not None for material in obj.data.materials)
        for obj in meshes
    ]
    if not any(carried):
        return None
    if not all(carried):
        raise mesh_application.MeshApplicationError("only some result parts carry UVs or materials")
    materials, layers, indices, active = mesh_application._retexture_values(surface, (source,))
    starts, totals = surface.source.polygon_starts, surface.source.polygon_totals
    corners = [[array("f") for _ in layers] for _ in meshes]
    faces = [array("i") for _ in meshes]
    for polygon, part in enumerate(owner):
        faces[part].append(indices[polygon])
        start, end = 2 * starts[polygon], 2 * (starts[polygon] + totals[polygon])
        for values, (_, coordinates) in zip(corners[part], layers, strict=True):
            values.extend(coordinates[start:end])
    return [
        (
            materials,
            [(layer, values) for (layer, _), values in zip(layers, corners[part], strict=True)],
            faces[part],
            active,
        )
        for part in range(len(meshes))
    ]


def _source_parts(target, meshes, surface, owner, textures=None):
    """Split the source mesh along the part boundaries of a verified result surface.

    `owner` gives each source polygon's part. Each part keeps the source's own
    positions, attributes and edge and face flags, and its UVs and materials
    unless `textures` (`_part_textures`) replaces them. A smooth-shaded or
    custom-normal source's corner normals are set on each part as custom
    normals, since splitting changes the corner fans they are computed over. The source is read once and halved by part until
    each piece holds one part, so the work grows with the source size times the
    logarithm of the part count; deleting faces keeps the rest in source order.
    """
    source = target.mesh
    normals = None
    smooth = [False] * len(source.polygons)
    source.polygons.foreach_get("use_smooth", smooth)
    # A part's own faces would otherwise shade its boundary differently.
    if source.has_custom_normals or any(smooth):
        values = array("f", [0.0]) * (3 * len(source.loops))
        source.corner_normals.foreach_get("vector", values)
        normals = [[] for _ in meshes]
        starts, totals = surface.source.polygon_starts, surface.source.polygon_totals
        for polygon, part in enumerate(owner):
            start = starts[polygon]
            normals[part].extend(
                values[3 * loop : 3 * loop + 3] for loop in range(start, start + totals[polygon])
            )
    geometry = bmesh.new()
    pending = [(geometry, list(owner), 0, len(meshes))]
    split = {}
    try:
        geometry.from_mesh(source)
        while pending:
            # Every bmesh stays pending until it is freed, so a failure frees it.
            geometry, owners, low, high = pending[-1]
            if high - low == 1:
                mesh = source.copy()
                mesh.use_fake_user = False
                geometry.to_mesh(mesh)
                pending.pop()[0].free()
                split[low] = mesh
                continue
            middle = (low + high) // 2
            upper = geometry.copy()
            pending[-1] = (geometry, [part for part in owners if part < middle], low, middle)
            pending.append((upper, [part for part in owners if part >= middle], middle, high))
            # Removing faces also removes the edges and vertices only they used.
            for piece, keep in ((geometry, range(low, middle)), (upper, range(middle, high))):
                others = [
                    face for face, part in zip(piece.faces, owners, strict=True) if part not in keep
                ]
                bmesh.ops.delete(piece, geom=others, context="FACES")
    finally:
        for geometry, *_ in pending:
            geometry.free()
    parts = []
    for index, obj in enumerate(meshes):
        mesh = split[index]
        if textures is not None:
            # Each part keeps only the materials its faces use.
            mesh_application._retexture(mesh, textures[index], 0, 0, several=True)
        if normals is not None:
            mesh.normals_split_custom_set(normals[index])
        mesh.update()
        mesh_application._fingerprint(mesh)
        parts.append(bpy.data.objects.new(_part_name(target, index + 1, obj), mesh))
    return tuple(parts)


def _copied_parts(target, meshes, mapping):
    """Copy result part meshes into source-local coordinates."""
    for obj in meshes:
        mesh_application._validate_object(obj.users_scene[0], obj)
        mesh_application._matrix(mapping @ obj.matrix_world)
    parts = []
    for index, obj in enumerate(meshes, 1):
        mesh = obj.data.copy()
        mesh.use_fake_user = False
        # Like parts split from the source's faces, each keeps the source's properties.
        mesh_application._carry_properties(target.mesh, mesh)
        mesh.transform(mapping @ obj.matrix_world)
        mesh.update()
        mesh_application._fingerprint(mesh)
        parts.append(bpy.data.objects.new(_part_name(target, index, obj), mesh))
    return tuple(parts)


def _stage_parts(target, meshes, mapping):
    """Stage parts before replacement, from the source's faces when possible.

    When the result meshes together are the source surface, each source face in
    one part, the source is split along their boundaries, adopting the UVs and
    materials the parts carry, if every part carries them. Otherwise, such as for
    remeshed parts, the result meshes are copied, under a verified bounds fit for
    FIT coordinates, or the face match's mapping when only the split failed.
    """
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
    try:
        surface = mesh_application.match_surface(target.obj, tuple(meshes), mapping, "PARTS")
    except mesh_application.MeshApplicationError as exc:
        # Not the source's own faces: copy the result meshes instead.
        _log.info("Parts are copied from the result meshes: %s", exc)
        fit = mesh_application.fit_bounds(target.obj, tuple(meshes), mapping, "PARTS")
        parts, origin = _copied_parts(target, meshes, fit.mapping), "result_meshes"
    else:
        fit = mesh_application.BoundsFit(surface.mapping, surface.fitted_from)
        try:
            owner = mesh_application._transfer(
                "PARTS",
                mesh_correspondence.owners,
                surface.source,
                surface.polygons(),
                surface.offsets,
            )
            textures = _part_textures(surface, meshes, target.mesh, owner)
        except mesh_application.MeshApplicationError as exc:
            # The source's surface, but not split along whole source faces or not
            # consistently textured: copy the result meshes under the mapping the
            # face match verified.
            _log.info("Parts are copied from the result meshes: %s", exc)
            parts, origin = _copied_parts(target, meshes, fit.mapping), "result_meshes"
        else:
            parts = _source_parts(target, meshes, surface, owner, textures)
            origin = "source_faces"
    # Reuse the guarded mesh-swap primitive with an empty result. The original
    # object becomes the group anchor; existing children/context are unchanged.
    blank = bpy.data.objects.new("Scenario parts staging", bpy.data.meshes.new("Scenario parts"))
    target.scene.collection.objects.link(blank)
    return parts, blank, origin, fit


def _join(target, meshes):
    """Join several REMESH result meshes into one, in imported scene coordinates.

    Meshes that cover one surface between them, such as variants, are refused.
    Each mesh's world matrix is applied and its material slots are merged once
    per material, so the joined mesh keeps every face's material.
    """
    if (
        sum(mesh_application._components(obj.data) for obj in meshes)
        > mesh_application.MAX_COMPONENTS
    ):
        raise MeshResultApplicationError("Result meshes exceed the synchronous component limit")
    for obj in meshes:
        mesh_application._validate_object(obj.users_scene[0], obj)
        mesh_application._fingerprint(obj.data)
    mesh_application.separate_pieces(meshes)
    materials, slots = [], {}
    geometry = bmesh.new()
    try:
        for obj in meshes:
            matrix = mesh_application._matrix(obj.matrix_world)
            copy = obj.data.copy()
            try:
                remap = []
                for material in tuple(copy.materials) or (None,):
                    key = material.as_pointer() if material is not None else None
                    if key not in slots:
                        slots[key] = len(materials)
                        materials.append(material)
                    remap.append(slots[key])
                indices = [0] * len(copy.polygons)
                copy.polygons.foreach_get("material_index", indices)
                copy.polygons.foreach_set(
                    "material_index", [remap[min(index, len(remap) - 1)] for index in indices]
                )
                copy.transform(matrix)
                geometry.from_mesh(copy)
            finally:
                bpy.data.meshes.remove(copy)
        joined = bpy.data.meshes.new("Scenario remesh")
        geometry.to_mesh(joined)
    finally:
        geometry.free()
    for material in materials:
        joined.materials.append(material)
    joined.update()
    obj = bpy.data.objects.new("Scenario remesh", joined)
    target.scene.collection.objects.link(obj)
    return obj


def _publish_parts(target, parts):
    for part in parts:
        part.parent = target.obj
        part.matrix_parent_inverse = Matrix.Identity(4)
        part.matrix_basis = Matrix.Identity(4)
        for collection in target.obj.users_collection:
            collection.objects.link(part)
        part.select_set(False)
    bpy.context.view_layer.update()


def _validate_targets(target):
    for item in targets(target):
        mesh_application.validate_target(item)


def apply_saved_mesh(target, snapshot, *, policy, result_to_source, keep_original):
    """Use an explicit imported-scene-to-source-local mapping or an approved verified fit.

    `snapshot` comes from `prepare_saved_mesh` and is consumed here. UV,
    RETEXTURE, RIG and PARTS treat every returned result mesh as one surface, and
    REMESH joins them; display helpers (`_helpers`) are never result meshes.
    Alignment is never guessed: a `FitRequest` is used only when the full
    correspondence, or for REMESH and copied parts the surface distance, verifies
    it. A tuple of targets applies UV, RETEXTURE or RIG to all of them at once, or
    to none.
    """
    mapping = validate_request(
        target, policy=policy, result_to_source=result_to_source, keep_original=keep_original
    )
    model_application.use_snapshot(snapshot)
    several = isinstance(target, tuple)
    first = targets(target)[0]
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
            mismatch = policy in _RIGGED and model_application.frame_rate_mismatch(
                snapshot, staging, before, first.scene
            )
            # Display helpers are not results; they go with the other imported data.
            helpers = _helpers(objects)
            meshes = [obj for obj in objects if obj.type == "MESH" and obj not in helpers]
            if policy not in _RIGGED and any(obj.type not in {"MESH", "EMPTY"} for obj in objects):
                raise MeshResultApplicationError("Choose static meshes with optional Empty parents")
            parts = clips = ()
            rig = correction = fit = parts_from = joined = None
            if policy == "PARTS":
                parts, primary, parts_from, fit = _stage_parts(first, meshes, mapping)
                objects = (*objects, primary)
                local_mapping = Matrix.Identity(4)
            elif policy != "ANIMATE":
                if not meshes:
                    raise MeshResultApplicationError("Choose a result with a mesh")
                for obj in meshes:
                    first.scene.collection.objects.link(obj)
                if policy == "REMESH":
                    # One remesh may arrive in several meshes; join them first.
                    joined = len(meshes)
                    primary = meshes[0]
                    if joined > 1:
                        if not isinstance(mapping, mesh_application.FitRequest):
                            # Only a verified fit checks the joined meshes are the surface.
                            raise mesh_application.MeshApplicationError(
                                f"{joined} result meshes are joined into one remesh only "
                                "under Fit and verify"
                            )
                        primary = _join(first, meshes)
                        objects = (*objects, primary)
                    fit = mesh_application.fit_bounds(first.obj, (primary,), mapping, policy)
                    # Blender has already converted the file's axes and units. Preserve
                    # imported node transforms; never infer alignment or move the source.
                    local_mapping = fit.mapping @ primary.matrix_world
            imported = {
                name: set(getattr(bpy.data, name)) - previous for name, previous in before.items()
            }
            _validate_targets(target)
            if policy == "ANIMATE":
                # Clips are pose data on the source's own rig: no mapping and no
                # returned object is kept.
                receipt = animation_application.apply_clips(
                    target, tuple(obj for obj in objects if obj not in helpers)
                )
                rig, clips = receipt.rig, receipt.actions
                correction = receipt.rest_correction_deg
            elif policy == "RIG":
                skin = tuple(obj for obj in objects if obj not in helpers)
                receipt = rig_application.apply_skin(
                    target, tuple(meshes), skin, mapping, keep_original=keep_original
                )
                rig = receipt.rig
                objects = tuple(obj for obj in objects if obj not in receipt.objects)
            elif policy in {"UV", "RETEXTURE"} and several:
                receipt = mesh_application.apply_surfaces(
                    first.scene,
                    tuple(source.obj for source in target),
                    tuple(meshes),
                    policy=policy,
                    result_to_source=mapping,
                    keep_original=keep_original,
                )
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
            # ANIMATE makes no copy; every other receipt lists one entry per source.
            originals = receipt.originals or (None,) * len(targets(target))
            for original in originals:
                if original is not None:
                    original.select_set(False)
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
            fit = fit or getattr(receipt, "surface", None)
            used = () if policy == "ANIMATE" else (fit.mapping if fit else mapping)
            return MeshEditApplication(
                first.obj,
                receipt.original,
                policy,
                undo,
                parts,
                rig,
                clips,
                correction,
                tuple(tuple(row) for row in used),
                fit.fitted_from if fit else None,
                mismatch,
                tuple(source.obj for source in targets(target)),
                originals,
                parts_from,
                joined,
                getattr(fit, "residual", ()),
            )
    except Exception as error:
        if receipt is not None:
            try:
                receipt.rollback()
            except Exception:
                raise RuntimeError("Mesh replacement is uncertain; inspect the source") from None
        # Never remove new data while a source may still point at it.
        try:
            _validate_targets(target)
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
