# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Synchronous, explicit-target mesh application; no import, jobs or selection lookup."""

import hashlib
import math
import threading
from array import array
from dataclasses import dataclass, field, replace

import bpy
from mathutils import Matrix, Vector

from ..core.scene import mesh_correspondence

# Fingerprints run synchronously. Bound both geometry and generic attribute work.
MAX_COMPONENTS = 2_000_000
_ATTRIBUTE_FIELDS = {
    "FLOAT": "value",
    "INT": "value",
    "BOOLEAN": "value",
    "INT8": "value",
    "INT32_2D": "value",
    # Custom split normals, as created by Blender's glTF importer.
    "INT16_2D": "value",
    "FLOAT_VECTOR": "vector",
    "FLOAT2": "vector",
    "FLOAT_COLOR": "color",
    "BYTE_COLOR": "color",
}


class MeshApplicationError(RuntimeError):
    """An unsupported or changed target requires explicit caller review."""


def _main_thread():
    if threading.current_thread() is not threading.main_thread():
        raise MeshApplicationError("Mesh application must run on Blender's main thread")


def _present(collection, value):
    return any(item is value for item in collection)


def _linked(obj):
    return obj.library or obj.override_library or obj.data.library or obj.data.override_library


def _skin_rig(scene, obj):
    """Return the one vertex-weight Armature skin a rigged source may carry."""
    if len(obj.modifiers) != 1 or obj.modifiers[0].type != "ARMATURE":
        raise MeshApplicationError("Modifiers other than one Armature skin require another policy")
    modifier = obj.modifiers[0]
    if (
        not modifier.use_vertex_groups
        or modifier.use_bone_envelopes
        or modifier.use_multi_modifier
        or modifier.vertex_group
        or not obj.vertex_groups
    ):
        raise MeshApplicationError("Use a vertex-group Armature skin without envelopes or a mask")
    rig = modifier.object
    if rig is None or rig.type != "ARMATURE" or not _present(scene.objects, rig) or _linked(rig):
        raise MeshApplicationError("Bind the Armature skin to a local armature in this scene")
    if rig.mode == "EDIT":
        raise MeshApplicationError("Leave Edit Mode on the source rig")
    return modifier, rig


def _validate_object(scene, obj, *, skin=False, read_only=False):
    """Check supported structure; skin admits only one vertex-weight Armature skin.

    read_only admits custom mesh properties on a result that is only read.
    """
    if not _present(bpy.data.scenes, scene) or not _present(scene.objects, obj):
        raise MeshApplicationError("Use a live object in the explicit originating scene")
    if obj.type != "MESH" or obj.mode != "OBJECT":
        raise MeshApplicationError("Only meshes in Object Mode are supported")
    if _linked(obj):
        raise MeshApplicationError("Linked and overridden objects or meshes are unsupported")
    if obj.constraints or (not skin and (obj.modifiers or obj.vertex_groups)):
        raise MeshApplicationError(
            "Modifiers, constraints and vertex groups require another policy"
        )
    if obj.animation_data or obj.data.animation_data or obj.data.shape_keys:
        raise MeshApplicationError("Animation and shape keys require another policy")
    if skin:
        _skin_rig(scene, obj)
    if obj.parent and obj.parent_type == "ARMATURE":
        raise MeshApplicationError(
            "Armature-deform parenting is unsupported; use Object parenting and a modifier"
        )
    # Object parenting to an armature only transforms. A skinned source keeps it,
    # also to the rig its skin replaced, which then no longer deforms it.
    if obj.parent and ((obj.parent.type == "ARMATURE" and not skin) or obj.parent_type != "OBJECT"):
        raise MeshApplicationError("Bone and vertex parenting require another policy")
    if any(child.parent_type != "OBJECT" for child in obj.children):
        raise MeshApplicationError("Vertex-parented children require another policy")
    if any(slot.link != "DATA" for slot in obj.material_slots):
        raise MeshApplicationError("Object material overrides require another policy")
    # A result that is only read (UV, retexture) never passes its properties on.
    if obj.data.keys() and not read_only:
        raise MeshApplicationError("Custom mesh properties require another policy")


def _plain(value):
    if isinstance(value, float) and not math.isfinite(value):
        raise MeshApplicationError("Nonfinite mesh values are unsupported")
    if isinstance(value, (bool, int, float, str)) or value is None:
        return value
    return tuple(_plain(component) for component in value)


def _components(mesh):
    size = len(mesh.vertices) + len(mesh.edges) + len(mesh.loops) + len(mesh.polygons)
    return size + sum(len(attribute.data) for attribute in mesh.attributes)


def _fingerprint(mesh):
    """Guard geometry, generic attributes, UV roles and material slot bindings."""
    if _components(mesh) > MAX_COMPONENTS:
        raise MeshApplicationError("Mesh exceeds the synchronous application component limit")
    digest = hashlib.sha256()

    def add(value):
        digest.update(repr(_plain(value)).encode("utf-8"))
        digest.update(b"\0")

    add((len(mesh.vertices), len(mesh.edges), len(mesh.loops), len(mesh.polygons)))
    for vertex in mesh.vertices:
        add((vertex.co, vertex.select, vertex.hide))
    for edge in mesh.edges:
        add((edge.vertices, edge.use_seam, edge.use_edge_sharp, edge.select, edge.hide))
    for polygon in mesh.polygons:
        add(
            (
                polygon.vertices,
                polygon.material_index,
                polygon.use_smooth,
                polygon.select,
                polygon.hide,
            )
        )
    for loop in mesh.loops:
        add((loop.vertex_index, loop.edge_index))
    for attribute in mesh.attributes:
        name = _ATTRIBUTE_FIELDS.get(attribute.data_type)
        if name is None:
            raise MeshApplicationError("Unsupported mesh attribute type")
        add((attribute.name, attribute.data_type, attribute.domain))
        for item in attribute.data:
            add(getattr(item, name))
    add(
        tuple(
            (material.as_pointer(), material.name) if material else None
            for material in mesh.materials
        )
    )
    add(tuple((layer.name, layer.active_render, layer.active_clone) for layer in mesh.uv_layers))
    add(mesh.uv_layers.active_index)
    add((mesh.use_auto_texspace, mesh.texspace_location, mesh.texspace_size, mesh.use_fake_user))
    return digest.digest()


def _matrix(value):
    try:
        matrix = Matrix(value)
        if len(matrix) != 4 or any(len(row) != 4 for row in matrix):
            raise ValueError
        if any(not math.isfinite(component) for row in matrix for component in row):
            raise ValueError
        if tuple(matrix[3]) != (0.0, 0.0, 0.0, 1.0) or matrix.determinant() <= 0:
            raise ValueError
    except (TypeError, ValueError):
        raise MeshApplicationError(
            "Use an explicit finite orientation-preserving affine 4x4 mapping"
        ) from None
    return matrix


# Panel expansion and the active modifier are interface state, not skin binding.
_INTERFACE_STATE = frozenset({"show_expanded", "is_active"})


def modifier_settings(modifier, *, interface=True):
    """Writable modifier settings; object pointers stay live references for restoration."""
    settings = []
    for prop in modifier.bl_rna.properties:
        if prop.is_readonly or prop.type == "COLLECTION":
            continue
        if not interface and prop.identifier in _INTERFACE_STATE:
            continue
        value = getattr(modifier, prop.identifier)
        if isinstance(value, set):
            value = frozenset(value)
        elif prop.type != "POINTER":
            value = _plain(value)
        settings.append((prop.identifier, value))
    return (modifier.type, tuple(settings))


@dataclass(frozen=True)
class SourceSkin:
    """A rigged source's captured Armature skin; any change makes the target stale.

    The pose is excluded: glTF export sends the unposed mesh, and edits compare
    returned geometry with the source mesh data, never its evaluated pose.
    """

    rig: object = field(repr=False)
    armature: object = field(repr=False)
    rig_name: str
    armature_name: str
    modifier: tuple = field(repr=False)
    groups: tuple
    weights: bytes = field(repr=False)
    bones: bytes = field(repr=False)
    rig_world: tuple = field(repr=False)


def _digest(values):
    digest = hashlib.sha256()
    for value in values:
        digest.update(repr(_plain(value)).encode("utf-8"))
        digest.update(b"\0")
    return digest.digest()


def _capture_skin(scene, obj):
    modifier, rig = _skin_rig(scene, obj)
    bones = rig.data.bones
    entries = sum(len(vertex.groups) for vertex in obj.data.vertices)
    if entries + len(bones) > MAX_COMPONENTS:
        raise MeshApplicationError("Skin weights exceed the synchronous component limit")
    return SourceSkin(
        rig,
        rig.data,
        rig.name,
        rig.data.name,
        modifier_settings(modifier, interface=False),
        tuple((group.name, group.lock_weight) for group in obj.vertex_groups),
        _digest(
            tuple((group.group, group.weight) for group in vertex.groups)
            for vertex in obj.data.vertices
        ),
        _digest(
            (
                bone.name,
                bone.parent.name if bone.parent else None,
                bone.matrix_local,
                bone.length,
                bone.use_deform,
            )
            for bone in bones
        ),
        tuple(tuple(row) for row in rig.matrix_world),
    )


@dataclass(frozen=True)
class MeshTarget:
    scene: object = field(repr=False)
    obj: object = field(repr=False)
    mesh: object = field(repr=False)
    name: str
    mesh_name: str
    geometry: bytes = field(repr=False)
    context: tuple = field(repr=False)
    # Set only for a source skinned to an armature: RIG alone may replace it.
    skin: SourceSkin | None = field(default=None, repr=False)


def capture_target(scene, obj):
    """Freeze an explicit source before asynchronous work; never infer selection."""
    _main_thread()
    try:
        # A modifier or vertex group can only be a captured Armature skin.
        skin = bool(obj.modifiers or obj.vertex_groups)
        _validate_object(scene, obj, skin=skin)
        if (
            scene != bpy.context.scene
            or not scene.is_editable
            or scene.library
            or scene.override_library
            or len(obj.users_scene) != 1
        ):
            raise MeshApplicationError("Choose a source in only the current local scene")
        # Parent edits can leave matrix_world stale until dependency evaluation.
        bpy.context.view_layer.update()
        matrices = tuple(
            tuple(tuple(row) for row in matrix)
            for matrix in (
                obj.matrix_basis,
                obj.matrix_local,
                obj.matrix_world,
                obj.matrix_parent_inverse,
            )
        )
        context = (
            matrices,
            obj.parent,
            obj.parent_type,
            frozenset((collection, collection.name) for collection in obj.users_collection),
            obj.active_material_index,
        )
        return MeshTarget(
            scene,
            obj,
            obj.data,
            obj.name,
            obj.data.name,
            _fingerprint(obj.data),
            context,
            _capture_skin(scene, obj) if skin else None,
        )
    except (ReferenceError, AttributeError):
        raise MeshApplicationError("The source mesh was removed or replaced") from None


def validate_target(target):
    """Reject changed identity, geometry, transforms, parenting or memberships."""
    if not isinstance(target, MeshTarget) or capture_target(target.scene, target.obj) != target:
        raise MeshApplicationError("The source mesh changed; review it again")


def _same_topology(source, result, mapping):
    if (len(source.vertices), len(source.edges), len(source.polygons), len(source.loops)) != (
        len(result.vertices),
        len(result.edges),
        len(result.polygons),
        len(result.loops),
    ):
        return False
    return (
        all(
            tuple(a.co) == tuple(mapping @ b.co)
            for a, b in zip(source.vertices, result.vertices, strict=True)
        )
        and all(
            tuple(a.vertices) == tuple(b.vertices)
            for a, b in zip(source.edges, result.edges, strict=True)
        )
        and all(
            tuple(a.vertices) == tuple(b.vertices)
            for a, b in zip(source.polygons, result.polygons, strict=True)
        )
        and all(
            (a.vertex_index, a.edge_index) == (b.vertex_index, b.edge_index)
            for a, b in zip(source.loops, result.loops, strict=True)
        )
    )


def _buffer(data, name, code, width, count):
    values = array(code, [0]) * (count * width)
    data.foreach_get(name, values)
    return values


def _arrays(mesh):
    return mesh_correspondence.MeshArrays(
        _buffer(mesh.vertices, "co", "f", 3, len(mesh.vertices)),
        _buffer(mesh.loops, "vertex_index", "i", 1, len(mesh.loops)),
        _buffer(mesh.polygons, "loop_start", "i", 1, len(mesh.polygons)),
        _buffer(mesh.polygons, "loop_total", "i", 1, len(mesh.polygons)),
        _buffer(mesh.loops, "edge_index", "i", 1, len(mesh.loops)),
        len(mesh.edges),
    )


def _transfer(policy, call, *args):
    """Run one correspondence step, reporting its counted reason under the policy."""
    try:
        return call(*args)
    except mesh_correspondence.CorrespondenceError as exc:
        raise MeshApplicationError(
            f"{policy} result does not match the source mesh: {exc}"
        ) from None


FIT_POLICIES = frozenset({"UV", "RETEXTURE", "RIG"})


@dataclass(frozen=True)
class FitRequest:
    """Approved FIT coordinates: verify a uniform scale and offset from each base.

    Each base is a (label, 4x4 rows) scene-to-source-local hypothesis, normally
    `WORLD` (inverse source world) and `LOCAL` (identity). A base is used only if
    the fitted mapping verifies; two bases must agree on every transferred index.
    """

    bases: tuple


@dataclass(frozen=True)
class Surface:
    """A verified result surface and the exact mapping that verified it.

    `match` is None when one result mesh has identical indexed topology. Otherwise
    its indices address the joined `result` buffers, whose `offsets` attribute
    each joined vertex, loop and face back to its mesh in `meshes`.
    """

    meshes: tuple
    mapping: object
    fitted_from: str | None
    scale: float
    source: object = field(repr=False)
    result: object = field(repr=False)
    match: object = field(repr=False)
    offsets: tuple = field(repr=False)

    def loops(self):
        """Joined result loop -> source loop indices (identity for exact topology)."""
        count = sum(len(mesh.loops) for mesh in self.meshes)
        return self.match.loops if self.match else array("i", range(count))

    def polygons(self):
        """Joined result face -> source polygon indices (identity for exact topology)."""
        count = sum(len(mesh.polygons) for mesh in self.meshes)
        return self.match.polygons if self.match else array("i", range(count))


def _hypothesis(source, src, results, base, policy, *, fit, scene, label):
    """Verify one base mapping, optionally with a uniform scale/offset fit."""
    pieces = [(obj.data, base @ obj.matrix_world if scene else base) for obj in results]
    if not fit and len(pieces) == 1 and _same_topology(source.data, *pieces[0]):
        return Surface((pieces[0][0],), base, None, 1.0, None, None, None, ((0, 0, 0),))
    parts = []
    for mesh, local in pieces:
        part = _arrays(mesh)
        rows = tuple(tuple(row) for row in local)
        parts.append(replace(part, co=mesh_correspondence.transformed(part.co, rows)))
    result, offsets = mesh_correspondence.concatenate(parts)
    mapping, scale, fitted = base, 1.0, None
    if fit:
        scale, offset = _transfer(policy, mesh_correspondence.similarity_fit, src, result)
        result = replace(result, co=mesh_correspondence.scaled(result.co, scale, offset))
        mapping = Matrix.Translation(offset) @ Matrix.Scale(scale, 4) @ base
        fitted = label
    # Far from the scene origin, float32 file transforms round more coarsely.
    inverse = source.matrix_world.inverted(None)
    origin = (inverse @ Vector((0.0, 0.0, 0.0))).length if inverse is not None else 0.0
    tolerance = _transfer(policy, mesh_correspondence.position_tolerance, src.co, origin)
    match = _transfer(policy, mesh_correspondence.match, src, result, tolerance)
    return Surface(
        tuple(mesh for mesh, _ in pieces), mapping, fitted, scale, src, result, match, offsets
    )


def match_surface(source, results, result_to_source, policy, *, scene=True):
    """Prove one or more result meshes are the source object's surface.

    With `scene`, each result object's world matrix is composed before the
    mapping (saved-GLB scene coordinates); otherwise mesh coordinates are mapped
    directly. Identical indexed topology is the cheap path. Otherwise a verified
    correspondence accepts triangulated, seam-split or reordered results within
    the documented tolerance. A `FitRequest` adds a verified uniform scale/offset
    fit; strict mappings never fit. Nothing is guessed: ambiguity fails closed.
    """
    # Split results share one synchronous bound, like parts.
    if sum(_components(obj.data) for obj in results) > MAX_COMPONENTS:
        raise MeshApplicationError("Result meshes exceed the synchronous component limit")
    src = _arrays(source.data)
    if not isinstance(result_to_source, FitRequest):
        return _hypothesis(
            source, src, results, result_to_source, policy, fit=False, scene=scene, label=None
        )
    if policy not in FIT_POLICIES:
        raise MeshApplicationError("Fitted coordinates apply to UV, retexture and rig only")
    verified, reasons = [], []
    for label, rows in result_to_source.bases:
        try:
            verified.append(
                _hypothesis(
                    source, src, results, _matrix(rows), policy, fit=True, scene=scene, label=label
                )
            )
        except MeshApplicationError as exc:
            reasons.append(f"{label}: {str(exc).split(': ', 1)[-1]}")
    if not verified:
        raise MeshApplicationError(
            f"{policy} result does not match the source mesh after fitting ({'; '.join(reasons)})"
        )
    first = verified[0]
    for other in verified[1:]:
        if first.loops() != other.loops() or first.polygons() != other.polygons():
            raise MeshApplicationError(
                f"{policy} result fits the source in several ways; choose scene or "
                "object local coordinates"
            )
    return first


def _corner_values(surface, layers, width, count, policy, label):
    """Join one per-loop buffer per result mesh and resolve it per source loop."""
    values = array("f")
    for mesh, layer in zip(surface.meshes, layers, strict=True):
        values.extend(_buffer(layer.data, "uv", "f", width, len(mesh.loops)))
    if surface.match is None:
        return values
    return _transfer(
        policy, mesh_correspondence.corners, surface.match, values, width, count, label
    )


def _retexture(staged, surface):
    """Adopt result UV/material bindings without mutating shared shader graphs."""
    meshes = surface.meshes
    if any(not mesh.materials or any(m is None for m in mesh.materials) for mesh in meshes):
        raise MeshApplicationError("Retexture requires nonempty result material slots")
    if any(face.material_index >= len(mesh.materials) for mesh in meshes for face in mesh.polygons):
        raise MeshApplicationError("Retexture requires valid result face material assignments")
    if not all(mesh.uv_layers for mesh in meshes):
        raise MeshApplicationError(
            "Retexture requires result UV layers; color-only results are unsupported"
        )
    first = meshes[0]
    names = [layer.name for layer in first.uv_layers]
    if any([layer.name for layer in mesh.uv_layers] != names for mesh in meshes):
        raise MeshApplicationError("Retexture requires the same UV layers on every result mesh")
    source_uv_names = {layer.name for layer in staged.uv_layers}
    other_names = {attribute.name for attribute in staged.attributes} - source_uv_names
    if any(name in other_names for name in names):
        raise MeshApplicationError("Result UV names conflict with preserved source attributes")
    # Merge every result mesh's slots (once per material) and remap its faces.
    materials, slots, indices = [], {}, array("i")
    for mesh in meshes:
        remap = []
        for material in mesh.materials:
            if material.as_pointer() not in slots:
                slots[material.as_pointer()] = len(materials)
                materials.append(material)
            remap.append(slots[material.as_pointer()])
        local = _buffer(mesh.polygons, "material_index", "i", 1, len(mesh.polygons))
        indices.extend(array("i", (remap[index] for index in local)))
    # Resolve every transferred value before the staged copy changes.
    layers = [
        (
            layer,
            _corner_values(
                surface,
                [mesh.uv_layers[index] for mesh in meshes],
                2,
                len(staged.loops),
                "RETEXTURE",
                "UV coordinates",
            ),
        )
        for index, layer in enumerate(first.uv_layers)
    ]
    if surface.match is not None:
        indices = _transfer(
            "RETEXTURE",
            mesh_correspondence.faces,
            surface.match,
            indices,
            len(staged.polygons),
            "materials",
        )
    for layer in tuple(staged.uv_layers):
        staged.uv_layers.remove(layer)
    for layer, values in layers:
        destination = staged.uv_layers.new(name=layer.name, do_init=False)
        if destination.name != layer.name:
            raise MeshApplicationError("Cannot preserve result UV names")
        destination.data.foreach_set("uv", values)
        destination.active_render = layer.active_render
        destination.active_clone = layer.active_clone
    staged.uv_layers.active_index = first.uv_layers.active_index
    staged.materials.clear()
    for material in materials:
        staged.materials.append(material)
    staged.polygons.foreach_set("material_index", indices)


def _stage(source, result, policy, mapping):
    """Copy a remesh result into source-local coordinates."""
    staged = result.copy()
    try:
        staged.transform(mapping)
        staged.update()
        return staged
    except BaseException:
        bpy.data.meshes.remove(staged)
        raise


def _stage_surface(source, surface, policy):
    """Copy the source mesh with UVs or textures transferred from a verified surface."""
    values = None
    if policy == "UV":
        if any(len(mesh.uv_layers) != 1 for mesh in surface.meshes):
            raise MeshApplicationError("UV application requires exactly one result UV layer")
        values = _corner_values(
            surface,
            [mesh.uv_layers[0] for mesh in surface.meshes],
            2,
            len(source.loops),
            policy,
            "UV coordinates",
        )
    staged = source.copy()
    try:
        if policy == "RETEXTURE":
            _retexture(staged, surface)
        else:
            destination = staged.uv_layers.active or staged.uv_layers.new(
                name=surface.meshes[0].uv_layers[0].name
            )
            destination.data.foreach_set("uv", values)
        staged.update()
        return staged
    except BaseException:
        bpy.data.meshes.remove(staged)
        raise


def _holder_signature(holder):
    """Snapshot writable object settings; deletion is reserved for our pristine holder."""
    settings = []
    for prop in holder.bl_rna.properties:
        if prop.is_readonly or prop.type == "COLLECTION":
            continue
        value = getattr(holder, prop.identifier)
        if prop.type == "POINTER":
            value = value.as_pointer() if value is not None else None
        elif isinstance(value, set):
            value = tuple(sorted(value))
        settings.append((prop.identifier, _plain(value)))
    return tuple(settings)


def _holder_state(holder):
    # Vertex group names belong to the held mesh; new ones are user changes.
    return _holder_signature(holder), tuple(group.name for group in holder.vertex_groups)


def _publish(source, staged):
    source.data = staged


@dataclass(eq=False)
class MeshApplication:
    """Caller-owned rollback boundary. Call accept() or rollback() on the main thread.

    A visible Keep original object is user-owned once returned and survives both
    methods. Without Keep original, an unlinked holder retains the original mesh
    until this receipt is finalized. No destructor touches Blender data.
    """

    source: object
    original: object | None
    _scene: object = field(repr=False)
    _before: object = field(repr=False)
    _applied: object = field(repr=False)
    _holder: object = field(repr=False)
    _holder_state: tuple = field(repr=False)
    _before_active: int = field(repr=False)
    _applied_active: int = field(repr=False)
    _before_name: str = field(repr=False)
    _before_hash: bytes = field(repr=False)
    _applied_hash: bytes = field(repr=False)
    _closed: bool = field(default=False, repr=False)
    _skin: bool = field(default=False, repr=False)
    surface: object = field(default=None, repr=False)

    def _release_holder(self):
        if self.original is not None or not _present(bpy.data.objects, self._holder):
            return False
        holder = self._holder
        # Any new ownership or settings retain the object for user review.
        if (
            not holder.users
            and not holder.users_collection
            and not holder.keys()
            and not holder.modifiers
            and not holder.constraints
            and not holder.animation_data
            and not holder.children
            and not holder.rigid_body
            and not holder.rigid_body_constraint
            and all(slot.link == "DATA" for slot in holder.material_slots)
            and _holder_state(holder) == self._holder_state
        ):
            bpy.data.objects.remove(holder)
            return True
        return False

    def _discard_unused_original(self):
        """Discard only the unchanged original after releasing our private holder."""
        mesh = self._before
        if not _present(bpy.data.meshes, mesh) or mesh.users:
            return
        if (
            mesh.name != self._before_name
            or mesh.keys()
            or mesh.animation_data
            or mesh.shape_keys
            or mesh.asset_data
        ):
            return
        try:
            unchanged = _fingerprint(mesh) == self._before_hash
        except MeshApplicationError:
            # New unsupported data or an exceeded work cap needs user review.
            return
        if unchanged:
            bpy.data.meshes.remove(mesh)

    def accept(self):
        """Release private rollback data; retain originals with user edits or owners."""
        _main_thread()
        if self._closed:
            raise MeshApplicationError("This application receipt is already finalized")
        if self._release_holder():
            self._discard_unused_original()
        self._closed = True

    def rollback(self):
        """Restore only if both mesh snapshots and the explicit target remain valid."""
        _main_thread()
        if self._closed:
            raise MeshApplicationError("This application receipt is already finalized")
        try:
            try:
                _validate_object(self._scene, self.source, skin=self._skin)
            except MeshApplicationError as exc:
                raise MeshApplicationError(
                    f"Target structure changed; rollback requires explicit review: {exc}"
                ) from exc
            if self.source.active_material_index != self._applied_active:
                raise MeshApplicationError("Active material selection changed after application")
            if self.source.data is not self._applied:
                raise MeshApplicationError("The target mesh was replaced after application")
            if (
                _fingerprint(self._applied) != self._applied_hash
                or _fingerprint(self._before) != self._before_hash
            ):
                raise MeshApplicationError("Mesh data changed; rollback requires explicit review")
        except ReferenceError:
            raise MeshApplicationError(
                "Application data was removed; rollback is unavailable"
            ) from None
        self.source.data = self._before
        self.source.active_material_index = self._before_active
        self._release_holder()
        # This is our staged copy only; never remove the imported result or a
        # mesh that another object/user has adopted since application.
        if not self._applied.users:
            bpy.data.meshes.remove(self._applied)
        self._closed = True


def apply_mesh(scene, source, result, *, policy, result_to_source, keep_original=False):
    """Apply one explicit imported mesh in source-local coordinates.

    REMESH adopts result geometry, materials and UVs. UV preserves source mesh
    attributes/materials and replaces only its active UV coordinates from one
    result UV layer. RETEXTURE preserves geometry/non-UV attributes and adopts
    result UV layers/material assignments. Both require the same surface: exact
    indexed topology/positions, or a verified triangulated, seam-split or
    reordered correspondence within tolerance. Selection is unused.
    The caller must validate captured job origin immediately before invoking this
    synchronous primitive; it does not prove cloud provenance or import safety.
    """
    _main_thread()
    if policy not in {"REMESH", "UV", "RETEXTURE"} or type(keep_original) is not bool:
        raise MeshApplicationError(
            "Use an explicit REMESH/UV/RETEXTURE policy and boolean Keep original"
        )
    if policy == "REMESH":
        _validate_results(scene, source, (result,), read_only=False)
        staged = _stage(source.data, result.data, policy, _matrix(result_to_source))
        return _replace_mesh(scene, source, staged, keep_original=keep_original)
    return apply_surface(
        scene,
        source,
        (result,),
        policy=policy,
        result_to_source=result_to_source,
        keep_original=keep_original,
        scene_coordinates=False,
    )


def _validate_results(scene, source, results, *, read_only=True):
    _validate_object(scene, source)
    for result in results:
        _validate_object(scene, result, read_only=read_only)
        if source is result or source.data is result.data:
            raise MeshApplicationError("Use a separate imported result mesh")
    _fingerprint(source.data)
    for result in results:
        _fingerprint(result.data)


def apply_surface(
    scene, source, results, *, policy, result_to_source, keep_original, scene_coordinates=True
):
    """Apply UVs or textures from one or more result meshes forming the source surface.

    `result_to_source` maps result scene coordinates (each object's world matrix
    composed) to source-local coordinates, or is an approved `FitRequest`. The
    returned receipt's `surface` records the verified mapping and any fit base.
    """
    _main_thread()
    if policy not in {"UV", "RETEXTURE"} or type(keep_original) is not bool or not results:
        raise MeshApplicationError("Use an explicit UV/RETEXTURE policy and boolean Keep original")
    _validate_results(scene, source, results)
    if not isinstance(result_to_source, FitRequest):
        result_to_source = _matrix(result_to_source)
    surface = match_surface(source, results, result_to_source, policy, scene=scene_coordinates)
    staged = _stage_surface(source.data, surface, policy)
    receipt = _replace_mesh(scene, source, staged, keep_original=keep_original)
    receipt.surface = surface
    return receipt


def _replace_mesh(scene, source, staged, *, keep_original, skin=False):
    """Publish an already validated private mesh; caller owns non-mesh changes.

    skin=True means rollback finds the source with its restored Armature skin.
    """
    before = source.data
    before_active = source.active_material_index
    before_hash = _fingerprint(before)
    holder = None
    try:
        staged.use_fake_user = False
        applied_hash = _fingerprint(staged)
        holder = (
            source.copy() if keep_original else bpy.data.objects.new("Scenario rollback", before)
        )
        holder.use_fake_user = False
        if keep_original:
            holder.name = f"{source.name} Original"
            for collection in source.users_collection:
                collection.objects.link(holder)
        holder_state = _holder_state(holder) if not keep_original else ()
        _publish(source, staged)
        return MeshApplication(
            source,
            holder if keep_original else None,
            scene,
            before,
            staged,
            holder,
            holder_state,
            before_active,
            source.active_material_index,
            before.name,
            before_hash,
            applied_hash,
            _skin=skin,
        )
    except BaseException:
        if staged is not None and source.data is staged:
            source.data = before
            source.active_material_index = before_active
        if holder is not None:
            bpy.data.objects.remove(holder, do_unlink=True)
        if staged is not None and not staged.users:
            bpy.data.meshes.remove(staged)
        raise
