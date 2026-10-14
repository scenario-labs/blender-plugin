# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Synchronous skin attachment to a captured source; staged-import ownership.

A rigged source's single Armature skin is replaced, never retargeted: its old rig
object is left unchanged, and Keep original retains a copy still bound to it.
"""

from dataclasses import dataclass

import bpy
from mathutils import Matrix

from ..core.scene import mesh_correspondence
from . import mesh_application as mesh


def _weights(obj):
    if sum(len(vertex.groups) for vertex in obj.data.vertices) > mesh.MAX_COMPONENTS:
        raise mesh.MeshApplicationError("Skin weights exceed the synchronous component limit")
    return (
        tuple(group.name for group in obj.vertex_groups),
        tuple(tuple((group.group, group.weight) for group in v.groups) for v in obj.data.vertices),
    )


def _skin_checks(primary, rig):
    # Every returned mesh but a bone custom shape is a result: never drop one.
    if not any(modifier.type == "ARMATURE" for modifier in primary.modifiers):
        raise mesh.MeshApplicationError(
            "RIG result has a mesh the returned rig does not skin; nothing is discarded"
        )
    if (
        primary.animation_data
        or primary.data.animation_data
        or primary.data.shape_keys
        or primary.constraints
        or primary.children
        or len(primary.modifiers) != 1
    ):
        raise mesh.MeshApplicationError(
            "Mesh animation, morphs or extra modifiers require another policy"
        )
    rig_ancestors = set()
    ancestor = rig
    while ancestor is not None:
        rig_ancestors.add(ancestor)
        ancestor = ancestor.parent
    ancestor = primary.parent
    while ancestor is not None:
        if ancestor.animation_data and ancestor not in rig_ancestors:
            raise mesh.MeshApplicationError(
                "Independent mesh-parent animation requires another policy"
            )
        ancestor = ancestor.parent
    modifier = primary.modifiers[0]
    if (
        modifier.type != "ARMATURE"
        or modifier.object != rig
        or not modifier.use_vertex_groups
        or modifier.use_bone_envelopes
        or modifier.vertex_group
    ):
        raise mesh.MeshApplicationError("Use a vertex-weight skin bound to the single returned rig")
    mesh._fingerprint(primary.data)
    return modifier


def validate_skin(target, skins, objects, mapping):
    """Require compatible skins forming the source surface; never retarget.

    Several skinned meshes are matched as one surface. `mapping` is a strict
    scene-to-source-local matrix or an approved `FitRequest`.
    """
    mesh.validate_target(target)
    rigs = [obj for obj in objects if obj.type == "ARMATURE"]
    if (
        len(rigs) != 1
        or not skins
        or any(obj.type not in {"MESH", "ARMATURE", "EMPTY"} for obj in objects)
    ):
        raise mesh.MeshApplicationError("Rig application requires one armature and skinned meshes")
    rig = rigs[0]
    modifiers = [_skin_checks(primary, rig) for primary in skins]
    if rig.constraints or rig.data.animation_data or any(b.constraints for b in rig.pose.bones):
        raise mesh.MeshApplicationError(
            "Rig constraints and armature-data animation are unsupported"
        )
    if any(obj.animation_data and obj.animation_data.drivers for obj in objects):
        raise mesh.MeshApplicationError("Rig application cannot adopt animation drivers")
    if sum(len(v.groups) for obj in skins for v in obj.data.vertices) > mesh.MAX_COMPONENTS:
        raise mesh.MeshApplicationError("Skin weights exceed the synchronous component limit")
    # One group list across every skin, in first-seen order.
    names, weights = [], []
    for primary in skins:
        local_names, local_weights = _weights(primary)
        index = []
        for name in local_names:
            if name not in names:
                names.append(name)
            index.append(names.index(name))
        weights.extend(
            tuple((index[group], weight) for group, weight in vertex) for vertex in local_weights
        )
    names, weights = tuple(names), tuple(weights)
    surface = mesh.match_surface(target.obj, tuple(skins), mapping, "RIG")
    if surface.match is not None:
        # Split copies of one source vertex must agree; each source vertex takes them.
        weights = mesh._transfer(
            "RIG",
            mesh_correspondence.vertex_weights,
            surface.match,
            surface.source.loop_vertices,
            surface.result.loop_vertices,
            len(target.mesh.vertices),
            weights,
        )
    if not names or len(rig.data.bones) > 1024 or any(name not in rig.data.bones for name in names):
        raise mesh.MeshApplicationError(
            "Use at most 1024 bones and only matching bone weight groups"
        )
    for vertex in weights:
        if not vertex or any(
            index >= len(names) or not 0 <= weight <= 1 for index, weight in vertex
        ):
            raise mesh.MeshApplicationError("Every source vertex needs valid bone weights")
        if abs(sum(weight for _, weight in vertex) - 1) > 0.001:
            raise mesh.MeshApplicationError("Bone weights must be normalized for every vertex")
    return rig, modifiers[0], names, weights, surface


def _stage_weights(target, names, weights):
    staged = target.mesh.copy()
    owner = bpy.data.objects.new("Scenario skin staging", staged)
    try:
        # A rigged source's copy carries its old groups; returned weights replace them.
        owner.vertex_groups.clear()
        for name in names:
            owner.vertex_groups.new(name=name)
        for index, vertex in enumerate(weights):
            for group, weight in vertex:
                owner.vertex_groups[group].add([index], weight, "REPLACE")
        return staged
    except BaseException:
        bpy.data.objects.remove(owner)
        bpy.data.meshes.remove(staged)
        raise
    finally:
        if mesh._present(bpy.data.objects, owner):
            bpy.data.objects.remove(owner)


def _restore_skin(source, previous):
    """Recreate a replaced Armature skin with every writable setting it had."""
    kind, settings = previous
    modifier = source.modifiers.new(dict(settings)["name"], kind)
    for identifier, value in settings:
        setattr(modifier, identifier, set(value) if isinstance(value, frozenset) else value)
    if tuple(source.modifiers) != (modifier,) or mesh.modifier_settings(modifier) != previous:
        raise mesh.MeshApplicationError("Could not restore the source Armature skin")


def _unwind(source, modifier, previous, rigged):
    """Leave the structure the receipt's rollback validates; it restores the mesh."""
    if modifier is not None:
        source.modifiers.remove(modifier)
    if previous is not None:
        _restore_skin(source, previous)
    elif not rigged:
        # Applied weights leave with the applied mesh; an unrigged source has none.
        source.vertex_groups.clear()


@dataclass
class RigApplication:
    """Internal synchronous rollback handle; finalized by the saved-result command."""

    receipt: mesh.MeshApplication
    modifier: object
    signature: tuple
    modifier_state: tuple
    objects: tuple
    rig: object
    # The replaced Armature skin of a rigged source, restored by rollback.
    previous: tuple | None = None
    surface: object = None

    @property
    def original(self):
        return self.receipt.original

    def accept(self):
        self.receipt.accept()

    def rollback(self):
        source = self.receipt.source
        if (
            source.data is not self.receipt._applied
            or tuple(source.modifiers) != (self.modifier,)
            or _weights(source) != self.signature
            or mesh._holder_signature(self.modifier) != self.modifier_state
        ):
            raise mesh.MeshApplicationError(
                "Applied skin changed; inspect the source before recovery"
            )
        _unwind(source, self.modifier, self.previous, self.receipt._skin)
        self.receipt.rollback()


def apply_skin(target, skins, objects, mapping, *, keep_original):
    """Retain imported rig hierarchy; keep source geometry, materials and object context.

    The skinned result meshes are matched, then removed with the import.
    """
    rig, imported_modifier, names, weights, surface = validate_skin(target, skins, objects, mapping)
    staged = _stage_weights(target, names, weights)
    rigged = target.skin is not None
    receipt = mesh._replace_mesh(
        target.scene, target.obj, staged, keep_original=keep_original, skin=rigged
    )
    modifier = previous = None
    try:
        # Blender owns vertex-group names on the mesh; the staged copy already
        # carries the matching names and deform weights when assigned to source.
        if _weights(target.obj) != (names, weights):
            raise mesh.MeshApplicationError("Blender did not retain the staged skin weights")
        if rigged:
            # Keep original copied the old skin before publication. The source now
            # deforms only with the returned rig; the old rig object is untouched.
            old = target.obj.modifiers[0]
            settings = mesh.modifier_settings(old)
            target.obj.modifiers.remove(old)
            previous = settings
        modifier = target.obj.modifiers.new("Scenario Rig", "ARMATURE")
        modifier.object = rig
        modifier.use_vertex_groups = True
        modifier.use_bone_envelopes = False
        modifier.use_deform_preserve_volume = imported_modifier.use_deform_preserve_volume
        retained = tuple(obj for obj in objects if obj.type != "MESH")
        root = bpy.data.objects.new(f"{target.name} Rig", None)
        root.parent = target.obj.parent
        root.matrix_parent_inverse = Matrix.Identity(4)
        for collection in target.obj.users_collection:
            collection.objects.link(root)
        # The verified mapping, including any approved fit, places the rig group.
        root.matrix_world = target.obj.matrix_world @ surface.mapping
        for obj in retained:
            if obj.parent is None:
                obj.parent = root
                obj.matrix_parent_inverse = Matrix.Identity(4)
            for collection in tuple(obj.users_collection):
                collection.objects.unlink(obj)
            for collection in target.obj.users_collection:
                collection.objects.link(obj)
            obj.select_set(False)
        bpy.context.view_layer.update()
        return RigApplication(
            receipt,
            modifier,
            _weights(target.obj),
            mesh._holder_signature(modifier),
            (root, *retained),
            rig,
            previous,
            surface,
        )
    except BaseException:
        _unwind(target.obj, modifier, previous, rigged)
        receipt.rollback()
        raise
