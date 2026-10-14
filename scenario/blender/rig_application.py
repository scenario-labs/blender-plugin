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


def _targets(target):
    return target if isinstance(target, tuple) else (target,)


def validate_skin(target, skins, objects, mapping):
    """Require compatible skins forming the source surface; never retarget.

    Several skinned meshes are matched as one surface. `mapping` is a strict
    scene-to-source-local matrix or an approved `FitRequest`. A tuple of targets
    is matched as one surface in scene coordinates (`mesh.match_sources`), and
    the returned weights then cover every target's vertices in order.
    """
    targets = _targets(target)
    for item in targets:
        mesh.validate_target(item)
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
    if len(targets) == 1:
        surface = mesh.match_surface(targets[0].obj, tuple(skins), mapping, "RIG")
    else:
        surface = mesh.match_sources(
            tuple(item.obj for item in targets), tuple(skins), mapping, "RIG"
        )
    if surface.match is not None:
        # Split copies of one source vertex must agree; each source vertex takes them.
        weights = mesh._transfer(
            "RIG",
            mesh_correspondence.vertex_weights,
            surface.match,
            surface.source.loop_vertices,
            surface.result.loop_vertices,
            sum(len(item.mesh.vertices) for item in targets),
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
class SkinnedSource:
    """One source's published skin: its mesh receipt and new Armature modifier."""

    receipt: mesh.MeshApplication
    modifier: object = None
    signature: tuple = ()
    modifier_state: tuple = ()
    # The replaced Armature skin of a rigged source, restored by rollback.
    previous: tuple | None = None

    def check(self):
        """Raise if the published skin changed; the mesh receipt checks the rest."""
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

    def unwind(self):
        """Remove the new skin, then let the mesh receipt check and restore the source."""
        _unwind(self.receipt.source, self.modifier, self.previous, self.receipt._skin)
        self.receipt.rollback()


@dataclass
class RigApplication:
    """Internal synchronous rollback handle; finalized by the saved-result command.

    `skins` has one entry per source, in target order; all share one rig group.
    """

    skins: tuple
    objects: tuple
    rig: object
    surface: object = None

    @property
    def original(self):
        return self.skins[0].receipt.original if len(self.skins) == 1 else None

    @property
    def originals(self):
        return tuple(skin.receipt.original for skin in self.skins)

    def accept(self):
        for skin in self.skins:
            skin.receipt.accept()

    def rollback(self):
        for skin in self.skins:
            skin.check()
        for skin in reversed(self.skins):
            skin.unwind()


def _bind(target, bound, rig, names, weights, imported_modifier):
    """Bind one published source to `rig`, recording each step on `bound` for unwinding."""
    # Blender owns vertex-group names on the mesh; the staged copy already
    # carries the matching names and deform weights when assigned to source.
    if _weights(target.obj) != (names, weights):
        raise mesh.MeshApplicationError("Blender did not retain the staged skin weights")
    if target.skin is not None:
        # Keep original copied the old skin before publication. The source now
        # deforms only with the returned rig; the old rig object is untouched.
        old = target.obj.modifiers[0]
        settings = mesh.modifier_settings(old)
        target.obj.modifiers.remove(old)
        bound.previous = settings
    modifier = bound.modifier = target.obj.modifiers.new("Scenario Rig", "ARMATURE")
    modifier.object = rig
    modifier.use_vertex_groups = True
    modifier.use_bone_envelopes = False
    modifier.use_deform_preserve_volume = imported_modifier.use_deform_preserve_volume


def apply_skin(target, skins, objects, mapping, *, keep_original):
    """Retain imported rig hierarchy; keep source geometry, materials and object context.

    The skinned result meshes are matched, then removed with the import. With a
    tuple of targets, one returned rig skins them all: every source is staged
    before any is published, and each gets its own weights and modifier.
    """
    targets = _targets(target)
    rig, imported_modifier, names, weights, surface = validate_skin(target, skins, objects, mapping)
    parts = tuple(
        weights[start : start + len(item.mesh.vertices)]
        for (start, _, _), item in zip(surface.source_offsets, targets, strict=True)
    )
    staged = []
    try:
        for item, part in zip(targets, parts, strict=True):
            staged.append(_stage_weights(item, names, part))
    except BaseException:
        for data in staged:
            bpy.data.meshes.remove(data)
        raise
    bound = []
    try:
        for item, data in zip(targets, staged, strict=True):
            receipt = mesh._replace_mesh(
                item.scene, item.obj, data, keep_original=keep_original, skin=item.skin is not None
            )
            bound.append(SkinnedSource(receipt))
        for item, skin, part in zip(targets, bound, parts, strict=True):
            _bind(item, skin, rig, names, part, imported_modifier)
        first = targets[0]
        retained = tuple(obj for obj in objects if obj.type != "MESH")
        root = bpy.data.objects.new(f"{first.name} Rig", None)
        # One source's rig group follows its parent. Several sources share one
        # group placed in scene coordinates, in the first source's collections.
        single = len(targets) == 1
        root.parent = first.obj.parent if single else None
        root.matrix_parent_inverse = Matrix.Identity(4)
        for collection in first.obj.users_collection:
            collection.objects.link(root)
        # The verified mapping, including any approved fit, places the rig group.
        root.matrix_world = (first.obj.matrix_world if single else Matrix.Identity(4)) @ (
            surface.mapping
        )
        for obj in retained:
            if obj.parent is None:
                obj.parent = root
                obj.matrix_parent_inverse = Matrix.Identity(4)
            for collection in tuple(obj.users_collection):
                collection.objects.unlink(obj)
            for collection in first.obj.users_collection:
                collection.objects.link(obj)
            obj.select_set(False)
        bpy.context.view_layer.update()
        for skin in bound:
            skin.signature = _weights(skin.receipt.source)
            skin.modifier_state = mesh._holder_signature(skin.modifier)
        return RigApplication(tuple(bound), (root, *retained), rig, surface)
    except BaseException:
        # A failed publication removed its own staged copy; later ones were never used.
        for data in staged[len(bound) + 1 :]:
            if not data.users:
                bpy.data.meshes.remove(data)
        # Each unwinding leaves the structure its mesh receipt's rollback validates.
        for skin in reversed(bound):
            skin.unwind()
        raise
