# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Import receipt-bound saved models into a new group at an approved cursor.

`apply_model` keeps the single embedded-GLB contract that Film shots use. A
saved job's classified import unit (GLB, JSON glTF, FBX, OBJ with its MTL and
maps, or mesh PLY) takes two main-thread steps instead: `prepare_snapshot`
rehashes every member into a private snapshot with rewritten references before
any application claim, so a changed or unsupported package leaves the saved job
unchanged; `import_snapshot` then imports that snapshot in a disposable scene,
keeps only images packed from it and publishes new data. Saved mesh edits stage
the same snapshot with `staged_snapshot` and apply it to their source instead.
SPZ, .splat and PLY units are first read on a worker: splats are decoded there
and shown by `splat_application`, and a mesh PLY returns here. While the
local-operation slot is busy, a PLY is only verified and imports here if it is
a mesh.
"""

import hashlib
import io
import json
import logging
import math
import os
import stat
import tempfile
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from functools import partial
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

from ..core.scene import placement, splat_ply, splats
from ..core.scene.glb import MAX_GLB_BYTES, GLBError, inspect_glb
from ..core.scene.model_formats import (
    FORMAT_MEDIA_TYPES,
    MAX_GLTF_JSON_BYTES,
    MAX_MEMBER_BYTES,
    MAX_MTL_BYTES,
    MAX_PACKAGE_BYTES,
    MAX_PLY_HEADER_BYTES,
    NON_COLOR_TEXTURE_ROLES,
    ModelFormat,
    ModelPackageError,
    PackageMember,
    UnitKind,
    check_signature,
    classify_packages,
    members_from_results,
)
from ..core.scene.model_references import inspect_gltf_json, rewrite_mtl, rewrite_obj

MODEL_MEDIA_TYPE = "model/gltf-binary"
_DATA = (
    "objects",
    "collections",
    "meshes",
    "materials",
    "node_groups",
    "images",
    "cameras",
    "lights",
    "armatures",
    "actions",
    "scenes",
)
_TRACKED_DATA = (*_DATA, "shape_keys")
# OBJ curves and legacy FBX textures, besides the GLB datablocks.
_PACKAGE_DATA = (*_DATA, "curves", "textures")
_PACKAGE_TRACKED = (*_PACKAGE_DATA, "shape_keys")
# Saved formats imported from a main-thread snapshot as a new group of meshes.
MESH_FORMATS = frozenset(
    {ModelFormat.GLB, ModelFormat.GLTF, ModelFormat.FBX, ModelFormat.OBJ, ModelFormat.PLY}
)
# Formats a worker reads before import: SPZ and .splat splats, and PLY, whose
# verified header decides between a mesh and Gaussian splats.
WORKER_FORMATS = frozenset({ModelFormat.PLY, ModelFormat.SPZ, ModelFormat.SPLAT})
IMPORT_FORMATS = MESH_FORMATS | WORKER_FORMATS
GLB_MEDIA_TYPES = FORMAT_MEDIA_TYPES[ModelFormat.GLB]
_IMAGE_SIGNATURES = {
    "png": (b"\x89PNG\r\n\x1a\n",),
    "jpg": (b"\xff\xd8\xff",),
}
_CHANGED = "The saved model changed; verify its receipt again"
_log = logging.getLogger("scenario.jobs")


class ModelApplicationError(RuntimeError):
    """The attempted import left no new model data or destination changes."""


class ModelPreflightError(ModelApplicationError):
    """The saved package was rejected before any application claim or scene change."""


@dataclass(frozen=True)
class ModelApplication:
    collection: object = field(repr=False)
    root: object = field(repr=False)
    objects: tuple = field(repr=False)
    format: str = "glb"
    members: tuple = ()
    dropped_references: int = 0
    frame_rate_mismatch: bool = False
    # Point counts, axes and SPZ flags of a splat import; None for meshes.
    splat: dict | None = None
    # The group's world-space mesh bounds measured after publication and any
    # requested scaling: (x, y, z) size and lowest height, empty/None if unmeasurable.
    dimensions: tuple = ()
    bottom: float | None = None
    # The uniform factor on the group root and the reviewed longest side, if any.
    scale: float = 1.0
    target_size: float | None = None


def _read(item, path, *, static_only=True):
    path, receipt = Path(path), item.receipt
    if (
        item.asset.media_type != MODEL_MEDIA_TYPE
        or receipt is None
        or not 0 < receipt.size <= MAX_GLB_BYTES
        or path.name != receipt.name
        or path.is_symlink()
    ):
        raise ModelApplicationError("Choose a supported saved GLB receipt")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    flags |= getattr(os, "O_BINARY", 0)
    with os.fdopen(os.open(path, flags), "rb") as source:
        if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
            raise ModelApplicationError("The saved model is not a regular file")
        data = source.read(receipt.size + 1)
    if len(data) != receipt.size or hashlib.sha256(data).hexdigest() != receipt.sha256:
        raise ModelApplicationError("The saved model changed; verify its receipt again")
    inspect_glb(data, static_only=static_only)
    return data


def _import(path):
    before = set(bpy.data.objects)
    result = bpy.ops.import_scene.gltf(
        filepath=str(path),
        import_pack_images=True,
        import_select_created_objects=False,
        import_scene_extras=False,
        import_scene_as_collection=False,
        bone_heuristic="BLENDER",
        disable_bone_shape=True,
    )
    if result != {"FINISHED"}:
        raise ModelApplicationError("Blender could not import the saved GLB")
    for obj in tuple(bpy.data.objects):
        if obj not in before and obj.type == "ARMATURE":
            _fit_bones(obj)


# Imported bone lengths, as fractions of the skeleton's size.
_LONGEST_BONE = 0.5
_SHORTEST_REACH = 0.005
_LONE_BONE = 0.1


def _skeleton_size(rig):
    """The longest side of the bone heads' and child meshes' bounds, in armature space."""
    points = [bone.head_local for bone in rig.data.bones]
    inverse = rig.matrix_world.inverted_safe()
    for obj in rig.children_recursive:
        if obj.type == "MESH":
            points.extend(inverse @ obj.matrix_world @ Vector(corner) for corner in obj.bound_box)
    if not points:
        return 0.0
    size = max(max(p[axis] for p in points) - min(p[axis] for p in points) for axis in range(3))
    return size if math.isfinite(size) else 0.0


def _fit_bones(rig):
    """Draw an imported armature's bones at the character's size, inside it.

    Blender's glTF importer (`bone_heuristic="BLENDER"`) divides each guessed
    bone length by the armature object's scale, so a centimetre skeleton under a
    0.01 scale draws bones a hundred times too long around the character, and In
    Front draws them over it. Only lengths change, not heads, directions or rolls,
    so every rest matrix, the skin and every pose stay as imported. A bone
    reaches its nearest child, a leaf takes its parent's length, and none passes
    half the skeleton. A bone with a connected child or B-Bone segments keeps its
    length, which would move that child or the skin. An object parented to a bone
    hangs from its tail, set back by the length guessed before that division: it
    lands where the file puts it.
    """
    layer = bpy.context.view_layer
    layer.update()
    size = _skeleton_size(rig)
    if size <= 0:
        return
    data = rig.data
    guessed = {bone.name: bone.length * max(rig.scale) for bone in data.bones}
    active = layer.objects.active
    layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    try:
        lengths = {}
        stack = [bone for bone in data.edit_bones if bone.parent is None]
        while stack:
            bone = stack.pop()
            stack.extend(bone.children)
            if bone.bbone_segments > 1 or any(child.use_connect for child in bone.children):
                lengths[bone.name] = bone.length
                continue
            reach = [(child.head - bone.head).length for child in bone.children]
            reach = [value for value in reach if value > size * _SHORTEST_REACH]
            if reach:
                length = min(reach)
            elif bone.parent is not None:
                length = lengths[bone.parent.name]
            else:
                length = size * _LONE_BONE
            bone.length = lengths[bone.name] = min(length, size * _LONGEST_BONE)
    finally:
        bpy.ops.object.mode_set(mode="OBJECT")
        layer.objects.active = active
    for child in rig.children:
        if child.parent_type == "BONE" and child.parent_bone in guessed:
            change = data.bones[child.parent_bone].length - guessed[child.parent_bone]
            if change:
                shift = Matrix.Translation((0.0, -change, 0.0))
                child.matrix_parent_inverse = shift @ child.matrix_parent_inverse
    rig.show_in_front = False


def _bounds(objects):
    """World-space low and high corners of the objects' mesh bounds, or None."""
    points = [
        obj.matrix_world @ Vector(corner)
        for obj in objects
        if obj.type == "MESH"
        for corner in obj.bound_box
    ]
    if not points or any(not math.isfinite(value) for point in points for value in point):
        return None
    low = [min(point[axis] for point in points) for axis in range(3)]
    high = [max(point[axis] for point in points) for axis in range(3)]
    return low, high


def _bottom_center(objects, bounds=None):
    bounds = bounds or _bounds(objects)
    if bounds is None:
        raise ModelApplicationError("GLB contains no supported finite mesh geometry")
    low, high = bounds
    return Vector(((low[0] + high[0]) / 2, (low[1] + high[1]) / 2, low[2]))


def source_fit(objects):
    """The bottom center and longest side of the meshes' world bounds, or None.

    An import that takes these meshes' place lands its own bottom center there,
    scaled to that longest side. None when they have no size an import can take.
    """
    bounds = _bounds(objects)
    if bounds is None:
        return None
    low, high = bounds
    try:
        size = placement.target_size(
            max(top - bottom for bottom, top in zip(low, high, strict=True))
        )
    except ValueError:
        return None
    return tuple(_bottom_center(objects, bounds)), size


def _fit(bounds, target_size):
    """The root scale for a reviewed longest side; 1.0 keeps the saved size."""
    try:
        return placement.fit_scale(*bounds, target_size)
    except ValueError as error:
        raise ModelApplicationError(str(error)) from None


def _publish(scene, objects, cursor, asset_id, anchor, members=(), scale=1.0):
    """Group new objects under a root that puts the scaled anchor at the cursor.

    A uniform root scale keeps the anchor (the bottom center) on the cursor. The
    returned application carries the group's measured world bounds.
    """
    collection = bpy.data.collections.new("Scenario Model")
    scene.collection.children.link(collection)
    root = bpy.data.objects.new("Scenario Model", None)
    collection.objects.link(root)
    for obj in objects:
        for owner in tuple(obj.users_collection):
            owner.objects.unlink(obj)
        collection.objects.link(obj)
        obj["scenario_asset"] = asset_id
        if obj.parent not in objects:
            obj.parent = root
    if scale != 1.0:
        root.scale = (scale, scale, scale)
    root.location = Vector(cursor) - anchor * scale
    root["scenario_asset"] = asset_id
    if members:
        # Every saved file the package import read, unit key first.
        root["scenario_assets"] = ",".join(members)
    bpy.context.view_layer.update()
    # Measured in the destination at its current frame, after any scaling.
    bounds = _bounds(objects)
    dimensions = (
        () if bounds is None else tuple(high - low for low, high in zip(*bounds, strict=True))
    )
    bottom = None if bounds is None else bounds[0][2]
    return ModelApplication(
        collection, root, tuple(objects), dimensions=dimensions, bottom=bottom, scale=scale
    )


def validate_destination(scene, cursor):
    """Check non-mutating native preconditions before consuming an application claim."""
    if threading.current_thread() is not threading.main_thread():
        raise ModelApplicationError("Import models on Blender's main thread")
    if (
        scene != bpy.context.scene
        or scene.library
        or scene.override_library
        or bpy.context.mode != "OBJECT"
        or len(cursor) != 3
        or any(not math.isfinite(value) for value in cursor)
    ):
        raise ModelApplicationError("Choose a local scene in Object Mode and a finite cursor")


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
        raise RuntimeError("Blender could not record the undo state")


def _begin_history(history):
    """Record the checkpoint before a standalone import; return whether one was recorded.

    The checkpoint captures the latest state, including edits no operator
    recorded, so one Undo removes only this import. Without it nothing is staged.
    """
    if not (history and _undo_enabled()):
        return False
    try:
        _undo_push("Before Scenario model import")
    except Exception:
        raise ModelApplicationError(
            "Could not prepare Blender undo; nothing was imported"
        ) from None
    return True


def _end_history(undo):
    if not undo:
        return
    try:
        # The history state must contain no staging scene.
        _undo_push("Scenario model import")
    except Exception:
        # The import is complete. A missing history entry is not a failed
        # application and must never authorize another import.
        _log.warning("Model imported, but Blender undo could not be recorded")


def _snapshot(names=_TRACKED_DATA):
    return {name: set(getattr(bpy.data, name)) for name in names}


def _remove_new_data(previous, names=_DATA):
    for name in names:
        collection = getattr(bpy.data, name)
        for value in set(collection) - previous[name]:
            try:
                collection.remove(value, do_unlink=True)
            except Exception:
                # Continue independent cleanup, then verify the actual outcome.
                pass


@contextmanager
def _preserve_animation_ui(scenes):
    """glTF's optional animation UI writes to scenes[0], outside its import context."""
    saved = [
        (
            scene,
            tuple(track.name for track in scene.gltf2_animation_tracks),
            scene.gltf2_animation_active,
            scene.gltf2_animation_applied,
        )
        for scene in scenes
        if hasattr(scene, "gltf2_animation_tracks")
    ]
    try:
        yield
    finally:
        for scene, tracks, active, applied in saved:
            if tuple(track.name for track in scene.gltf2_animation_tracks) != tracks:
                scene.gltf2_animation_tracks.clear()
                for name in tracks:
                    scene.gltf2_animation_tracks.add().name = name
            scene.gltf2_animation_active = active
            scene.gltf2_animation_applied = applied


def _model_root():
    package = __package__.rsplit(".", 1)[0]
    return bpy.utils.extension_path_user(package, path="model-import", create=True)


def _stage(previous, run, *, gltf_timing=True, deselect=False):
    """Run one importer in a new disposable scene; return it and the new objects.

    The caller owns removing the staging scene and every new datablock.
    """
    staging = bpy.data.scenes.new("Scenario import staging")
    destination = bpy.context.scene
    staging.render.fps = destination.render.fps
    # Supported Blender importers multiply by fps_base when converting glTF
    # seconds. Use a reciprocal only in staging to retain destination timing.
    staging.render.fps_base = (
        1.0 / destination.render.fps_base if gltf_timing else destination.render.fps_base
    )
    staging.frame_set(destination.frame_current, subframe=destination.frame_subframe)
    layer = staging.view_layers[0]
    window = bpy.context.window
    # Background CLI sessions normally retain an off-screen window. Static
    # imports also work with only an explicit scene/view-layer context.
    if window is not None:
        previous_scene, previous_layer = window.scene, window.view_layer
    try:
        # Armature construction uses operators and context.object; a scene
        # override alone still exposes the destination's active object.
        if window is not None:
            window.scene = staging
            window.view_layer = layer
        with bpy.context.temp_override(
            scene=staging,
            view_layer=layer,
            collection=staging.collection,
            layer_collection=layer.layer_collection,
        ):
            with _preserve_animation_ui(previous["scenes"]):
                run()
            if deselect:
                # FBX, OBJ and PLY importers select what they create. Clear that
                # in staging so publication cannot carry it to the destination.
                for obj in staging.objects:
                    obj.select_set(False, view_layer=layer)
                layer.objects.active = None
            layer.update()
    finally:
        if window is not None:
            try:
                if bpy.context.mode != "OBJECT":
                    bpy.ops.object.mode_set(mode="OBJECT")
            finally:
                window.scene = previous_scene
                window.view_layer = previous_layer
    objects = tuple(obj for obj in bpy.data.objects if obj not in previous["objects"])
    if any(obj not in tuple(staging.objects) for obj in objects):
        raise ModelApplicationError("Imported objects escaped the staging scene")
    return staging, objects


@contextmanager
def staged_model(item, path, previous, *, static_only=True):
    """Decode a receipt-bound snapshot in isolation; caller owns all Blender cleanup."""
    temporary = None
    try:
        data = _read(item, path, static_only=static_only)
        window = bpy.context.window
        if window is None and not static_only and inspect_glb(data, static_only=False).get("skins"):
            raise ModelApplicationError("Rigged model import requires a Blender window context")
        temporary = tempfile.TemporaryDirectory(prefix="result-", dir=_model_root())
        snapshot = Path(temporary.name) / "model.glb"
        snapshot.write_bytes(data)
        staging, objects = _stage(previous, lambda: _import(snapshot))
        for image in set(bpy.data.images) - previous["images"]:
            if image.packed_file is None:
                image.pack()
            if image.packed_file is None:
                raise ModelApplicationError("The model texture could not be packed")
            image.filepath = ""
        yield staging, objects
    finally:
        if temporary is not None:
            try:
                temporary.cleanup()
            except Exception:
                _log.warning("Model snapshot cleanup failed; temporary files may remain")


def apply_model(scene, item, path, *, cursor):
    """Stage in a disposable scene, then publish only newly imported model data."""
    validate_destination(scene, cursor)
    previous = _snapshot()
    try:
        with staged_model(item, path, previous, static_only=False) as (staging, objects):
            # Measure the first clip at time zero in isolation. Measuring after
            # publication would bake the destination's current animated offset
            # into the parent group, moving the starting pose away from the cursor.
            layer = staging.view_layers[0]
            with bpy.context.temp_override(scene=staging, view_layer=layer):
                staging.frame_set(0)
                layer.update()
                anchor = _bottom_center(objects)
            application = _publish(scene, objects, cursor, item.asset.asset_id, anchor)
            bpy.data.scenes.remove(staging)
            return application
    except Exception:
        _remove_new_data(previous)
        if _snapshot() != previous:
            raise RuntimeError("Model cleanup is incomplete; do not import again") from None
        raise ModelApplicationError(
            "Could not import the verified model; saved files remain"
        ) from None


def import_plan(record):
    """Classify one saved job's results into ordered import units; reads no files."""
    return classify_packages(members_from_results(record.results))


def importable(unit):
    """Whether this release imports the unit as a new group (meshes or splat points)."""
    return unit.format in IMPORT_FORMATS


def worker_prepared(unit):
    """Whether a worker decodes or classifies the unit before its import."""
    return unit.format in WORKER_FORMATS


_FLAGS = (
    os.O_RDONLY
    | getattr(os, "O_NOFOLLOW", 0)
    | getattr(os, "O_NONBLOCK", 0)
    | getattr(os, "O_BINARY", 0)
)


class _Receipt:
    """Read one saved member once; its bytes must equal the verified receipt."""

    def __init__(self, item, path, limit):
        path, receipt = Path(path), item.receipt
        if (
            receipt is None
            or not 0 < receipt.size <= limit
            or path.name != receipt.name
            or path.is_symlink()
        ):
            raise ModelPreflightError("Choose a supported saved model receipt")
        self._receipt, self._digest, self._size = receipt, hashlib.sha256(), 0
        try:
            self._file = os.fdopen(os.open(path, _FLAGS), "rb")
        except OSError:
            raise ModelPreflightError("The saved model could not be read") from None
        if not stat.S_ISREG(os.fstat(self._file.fileno()).st_mode):
            self._file.close()
            raise ModelPreflightError("The saved model is not a regular file")

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self._file.close()

    def _count(self, data):
        self._size += len(data)
        if self._size > self._receipt.size:
            raise ModelPreflightError(_CHANGED)
        self._digest.update(data)
        return data

    def read(self, size=-1):
        if size is None or size < 0:
            size = self._receipt.size - self._size + 1
        return self._count(self._file.read(size))

    def readline(self, size=-1):
        return self._count(self._file.readline(size))

    def finish(self):
        """Hash the unread remainder; the member must equal its saved receipt."""
        while self.read(1 << 20):
            pass
        if self._size != self._receipt.size or self._digest.hexdigest() != self._receipt.sha256:
            raise ModelPreflightError(_CHANGED)


def _package_error(source, error):
    """Report a changed member before a message about its bytes."""
    source.finish()
    return ModelPreflightError(str(error))


def _image_head(name, head):
    """A packed texture must at least start like its declared image type."""
    extension = name.rsplit(".", 1)[-1]
    if extension == "webp":
        valid = head[:4] == b"RIFF" and head[8:12] == b"WEBP"
    else:
        valid = head.startswith(_IMAGE_SIGNATURES.get(extension, (b"",)))
    if not valid:
        raise ModelPreflightError("A saved model texture is not a supported image")


def _copy(item, path, target, *, limit=MAX_MEMBER_BYTES, keep=64):
    """Copy one member into the snapshot; return its first `keep` bytes."""
    head = b""
    with _Receipt(item, path, limit) as source, open(target, "xb") as output:
        while chunk := source.read(1 << 20):
            if len(head) < keep:
                head += chunk[: keep - len(head)]
            output.write(chunk)
        source.finish()
    return head


@dataclass(eq=False)
class ModelSnapshot:
    """A private, rewritten copy of one import unit; imported at most once."""

    unit: object = field(repr=False)
    members: tuple
    entry: Path
    dropped_references: int = 0
    requires_window: bool = False
    _temporary: object = field(default=None, repr=False)
    used: bool = False

    @property
    def directory(self):
        return self.entry.parent

    def cleanup(self):
        if self._temporary is None:
            return
        temporary, self._temporary = self._temporary, None
        try:
            temporary.cleanup()
        except Exception:
            _log.warning("Model snapshot cleanup failed; temporary files may remain")


def _members(files, asset_ids):
    selected = []
    for asset_id in asset_ids:
        if asset_id not in files:
            raise ModelPreflightError("The saved model package is incomplete")
        selected.append(files[asset_id])
    return selected


def _snapshot_glb(unit, files, directory, *, static_only=False):
    item, path = _members(files, (unit.key,))[0]
    if item.asset.media_type not in GLB_MEDIA_TYPES:
        raise ModelPreflightError("Choose a supported saved GLB receipt")
    with _Receipt(item, path, MAX_GLB_BYTES) as source:
        data = source.read()
        source.finish()
    try:
        document = inspect_glb(data, static_only=static_only)
    except GLBError as error:
        raise ModelPreflightError(str(error)) from None
    entry = directory / "model.glb"
    entry.write_bytes(data)
    return entry, unit.members, 0, bool(document.get("skins"))


def _snapshot_gltf(unit, files, directory, *, static_only=False):
    item, path = _members(files, (unit.key,))[0]
    with _Receipt(item, path, MAX_GLTF_JSON_BYTES) as source:
        data = source.read()
        source.finish()
    resources = []
    for candidate, _ in _members(files, unit.resources):
        resources.append(
            PackageMember(
                candidate.asset.asset_id,
                candidate.asset.media_type,
                candidate.receipt.size if candidate.receipt is not None else None,
            )
        )
    try:
        package = inspect_gltf_json(data, resources=resources, static_only=static_only)
        rigged = bool(json.loads(package.document).get("skins"))
    except (ModelPackageError, ValueError) as error:
        raise ModelPreflightError(str(error)) from None
    entry = directory / "model.gltf"
    entry.write_bytes(package.document)
    for name, asset_id in package.files:
        resource, resource_path = files[asset_id]
        head = _copy(resource, resource_path, directory / name)
        if not name.endswith(".bin"):
            _image_head(name, head)
    members = tuple(dict.fromkeys((*unit.members, *(asset for _, asset in package.files))))
    return entry, members, 0, rigged


def _snapshot_obj(unit, files, directory):
    names = dict(unit.files)
    item, path = _members(files, (unit.key,))[0]
    entry = directory / "model.obj"
    material = names.get(unit.material) if unit.material else None
    with _Receipt(item, path, MAX_MEMBER_BYTES) as source, open(entry, "xb") as output:
        try:
            obj = rewrite_obj(source, output, material_name=material)
        except ModelPackageError as error:
            raise _package_error(source, error) from None
        source.finish()
    dropped = obj.report.dropped_total
    if unit.material is not None:
        material_item, material_path = _members(files, (unit.material,))[0]
        with _Receipt(material_item, material_path, MAX_MTL_BYTES) as source:
            data = source.read()
            source.finish()
        textures = {slot: names[asset_id] for slot, asset_id in unit.textures}
        try:
            mtl = rewrite_mtl(data, textures=textures)
        except ModelPackageError as error:
            raise ModelPreflightError(str(error)) from None
        (directory / material).write_bytes(mtl.data)
        dropped += mtl.report.dropped_total
        # Every canonical name the material may reference must exist in the snapshot.
        for _, asset_id in unit.textures:
            texture, texture_path = files[asset_id]
            _image_head(names[asset_id], _copy(texture, texture_path, directory / names[asset_id]))
    return entry, unit.members, dropped, True


def _snapshot_fbx(unit, files, directory):
    if not hasattr(bpy.types, "IMPORT_SCENE_OT_fbx"):
        raise ModelPreflightError("Enable Blender's bundled FBX add-on to import FBX models")
    item, path = _members(files, (unit.key,))[0]
    entry = directory / "model.fbx"
    head = _copy(item, path, entry)
    try:
        check_signature(ModelFormat.FBX, head, item.receipt.size)
    except ModelPackageError as error:
        raise ModelPreflightError(str(error)) from None
    return entry, unit.members, 0, True


def _snapshot_ply(unit, files, directory):
    item, path = _members(files, (unit.key,))[0]
    entry = directory / "model.ply"
    head = _copy(item, path, entry, keep=MAX_PLY_HEADER_BYTES)
    try:
        check_signature(ModelFormat.PLY, head, item.receipt.size)
        # The same rule as worker splat preparation: only a mesh PLY imports here.
        kind = splat_ply.read_header(splats.Reader(io.BytesIO(head))).classify()
    except (ModelPackageError, splats.SplatError) as error:
        raise ModelPreflightError(str(error)) from None
    if kind != "mesh":
        # Worker preparation routes a Gaussian splat PLY to the point-cloud builder;
        # a PLY reaches here unprepared only while the local-operation slot is busy.
        raise ModelPreflightError(
            "This PLY holds Gaussian splat data; wait for the current local media "
            "operation to finish, then review the import again"
        )
    return entry, unit.members, 0, True


_SNAPSHOTS = {
    ModelFormat.GLB: _snapshot_glb,
    ModelFormat.GLTF: _snapshot_gltf,
    ModelFormat.FBX: _snapshot_fbx,
    ModelFormat.OBJ: _snapshot_obj,
    ModelFormat.PLY: _snapshot_ply,
}


def prepare_snapshot(unit, files, *, static_only=False):
    """Rehash one unit's members into a private snapshot before any claim.

    `files` maps every saved asset ID of the verified job to its (StoredResult,
    path). Members are opened without following links, must match their
    receipts byte for byte and are written under canonical names after OBJ, MTL
    and glTF references are rewritten. Nothing touches the scene. Any failure
    raises ModelPreflightError and removes the snapshot. `static_only` also
    refuses a GLB or glTF with skins or animations, as static mesh edits require.
    """
    if threading.current_thread() is not threading.main_thread():
        raise ModelPreflightError("Import models on Blender's main thread")
    if unit.format not in MESH_FORMATS or unit.kind is UnitKind.SPLAT:
        raise ModelPreflightError("Saved splats are decoded on a worker; review the import again")
    selected = _members(files, (*unit.members, *unit.resources))
    sizes = [item.receipt.size for item, _ in selected if item.receipt is not None]
    if len(sizes) != len(selected) or sum(sizes[: len(unit.members)]) > MAX_PACKAGE_BYTES:
        raise ModelPreflightError("The saved model package exceeds the supported import limit")
    temporary = tempfile.TemporaryDirectory(prefix="package-", dir=_model_root())
    try:
        # The fourth value is whether the importer needs a window: Blender's FBX,
        # OBJ and PLY operators require one, and glTF needs it only for armatures.
        snapshot = _SNAPSHOTS[unit.format]
        if unit.format in (ModelFormat.GLB, ModelFormat.GLTF):
            snapshot = partial(snapshot, static_only=static_only)
        entry, members, dropped, windowed = snapshot(unit, files, Path(temporary.name))
        if windowed and bpy.context.window is None:
            raise ModelPreflightError(
                "Rigged model import requires a Blender window context"
                if unit.format in (ModelFormat.GLB, ModelFormat.GLTF)
                else f"{unit.format.value.upper()} import requires a Blender window context"
            )
    except ModelPreflightError:
        _discard(temporary)
        raise
    except OSError:
        _discard(temporary)
        raise ModelPreflightError("The saved model snapshot could not be written") from None
    return ModelSnapshot(unit, members, entry, dropped, windowed, temporary)


def _discard(temporary):
    try:
        temporary.cleanup()
    except Exception:
        _log.warning("Model snapshot cleanup failed; temporary files may remain")


def _run_importer(fmt, entry, *, animation=True):
    if fmt in (ModelFormat.GLB, ModelFormat.GLTF):
        _import(entry)
        return
    if fmt is ModelFormat.FBX:
        # The file's own axes and units apply; its unit scale stays on the
        # imported objects, so world transforms keep their size.
        result = bpy.ops.import_scene.fbx(
            filepath=str(entry),
            use_image_search=False,
            use_anim=animation,
            mtl_name_collision_mode="MAKE_UNIQUE",
        )
    elif fmt is ModelFormat.OBJ:
        # Y-up, -Z forward: the glTF convention, so an OBJ and a GLB of the same
        # coordinates land in the same Blender positions.
        result = bpy.ops.wm.obj_import(
            filepath=str(entry),
            validate_meshes=True,
            mtl_name_collision_mode="MAKE_UNIQUE",
            forward_axis="NEGATIVE_Z",
            up_axis="Y",
        )
    else:
        result = bpy.ops.wm.ply_import(filepath=str(entry))
    if result != {"FINISHED"}:
        raise ModelApplicationError(f"Blender could not import the saved {fmt.value.upper()}")


def _snapshot_image(image, root):
    """Resolve an unpacked image file inside the snapshot, else None."""
    if image.source != "FILE" or not image.filepath:
        return None
    try:
        path = Path(bpy.path.abspath(image.filepath, library=image.library)).resolve(strict=True)
    except (OSError, RuntimeError, ValueError):
        return None
    return path if path.parent == root and path.is_file() else None


def _route_normal_maps(tree, images):
    """Feed each normal map into the shader through one Normal Map node.

    Blender's OBJ importer adds the node for ``map_Bump``; a map linked straight
    into a Normal input, or left unlinked, gets one here.
    """
    for node in tuple(tree.nodes):
        if node.type != "TEX_IMAGE" or node.image not in images:
            continue
        color = node.outputs["Color"]
        if any(link.to_node.type == "NORMAL_MAP" for link in color.links):
            continue
        targets = [link.to_socket for link in color.links if link.to_socket.name == "Normal"]
        for link in tuple(color.links):
            if link.to_socket.name == "Normal":
                tree.links.remove(link)
        if not targets:
            targets = [
                shader.inputs["Normal"]
                for shader in tree.nodes
                if shader.type == "BSDF_PRINCIPLED" and not shader.inputs["Normal"].is_linked
            ]
        if not targets:
            continue
        normal = tree.nodes.new("ShaderNodeNormalMap")
        normal.location = node.location.x + 300.0, node.location.y
        tree.links.new(color, normal.inputs["Color"])
        for socket in targets:
            tree.links.new(normal.outputs["Normal"], socket)


def _apply_texture_roles(previous, directory, texture_files):
    """Read bound data maps as Non-Color and route normal maps through a Normal Map node.

    ``texture_files`` pairs each bound map's snapshot name with its slot. Blender's
    OBJ importer reads every MTL map as sRGB; base color maps keep that.
    """
    slots = dict(texture_files)
    if not slots:
        return
    root = directory.resolve()
    normals = set()
    for image in set(bpy.data.images) - previous["images"]:
        path = _snapshot_image(image, root)
        slot = slots.get(path.name) if path is not None else None
        if slot in NON_COLOR_TEXTURE_ROLES:
            image.colorspace_settings.is_data = True
        if slot == "normal":
            normals.add(image)
    if not normals:
        return
    for material in set(bpy.data.materials) - previous["materials"]:
        if material.node_tree is not None:
            _route_normal_maps(material.node_tree, normals)


def _pack_snapshot_images(previous, directory):
    """Keep only images embedded in the model or read from the snapshot itself."""
    root = directory.resolve()
    for image in set(bpy.data.images) - previous["images"]:
        if image.packed_file is None:
            if _snapshot_image(image, root) is None:
                raise ModelApplicationError("A model texture is not part of the saved package")
            try:
                image.pack()
            except RuntimeError:
                raise ModelApplicationError("The model texture could not be packed") from None
            if image.packed_file is None:
                raise ModelApplicationError("The model texture could not be packed")
        image.filepath = ""


def _target_size(value):
    try:
        return placement.target_size(value)
    except ValueError as error:
        raise ModelApplicationError(str(error)) from None


def use_snapshot(snapshot):
    """Mark a prepared, unused snapshot as consumed; it imports at most once."""
    if not isinstance(snapshot, ModelSnapshot) or snapshot.used or snapshot._temporary is None:
        raise ModelApplicationError("Prepare the saved model again")
    snapshot.used = True


@contextmanager
def staged_snapshot(snapshot, previous, *, animation=True):
    """Import a consumed snapshot into a disposable scene; yield it and the new objects.

    Images get the unit's texture roles and must be packed from the model or the
    snapshot itself. `animation=False` keeps FBX clips out. The caller owns
    removing the staging scene and every datablock new since `previous`.
    """
    fmt = snapshot.unit.format
    gltf = fmt in (ModelFormat.GLB, ModelFormat.GLTF)
    staging, objects = _stage(
        previous,
        lambda: _run_importer(fmt, snapshot.entry, animation=animation),
        gltf_timing=gltf,
        deselect=not gltf,
    )
    _apply_texture_roles(previous, snapshot.directory, snapshot.unit.texture_files)
    _pack_snapshot_images(previous, snapshot.directory)
    yield staging, objects


def frame_rate_mismatch(snapshot, staging, previous, scene):
    """Whether staged clips play at another speed in `scene`; never retimes them.

    glTF converts seconds at the destination rate. FBX instead sets the file's
    frame rate on the staging scene; the destination keeps its own, so different
    rates play the imported clips at another speed.
    """
    return (
        snapshot.unit.format not in (ModelFormat.GLB, ModelFormat.GLTF)
        and bool(set(bpy.data.actions) - previous["actions"])
        and not math.isclose(
            staging.render.fps / staging.render.fps_base,
            scene.render.fps / scene.render.fps_base,
            rel_tol=1e-6,
        )
    )


def import_snapshot(scene, snapshot, *, cursor, history=False, target_size=None):
    """Import one prepared snapshot into a new group; only new data is published.

    ``history`` records desktop Undo checkpoints around a standalone import, which
    runs outside any native operator: one before staging and one after
    publication. Callers importing inside a larger build own their history and
    must not record its partial states. ``target_size`` is the reviewed longest
    side in Blender units: the group root is scaled uniformly to it, measured like the
    anchor, with the bottom center kept at the cursor. A model with no measurable
    size then fails and is rolled back like other import failures.
    """
    validate_destination(scene, cursor)
    target_size = _target_size(target_size)
    use_snapshot(snapshot)
    undo = _begin_history(history)
    fmt = snapshot.unit.format
    previous = _snapshot(_PACKAGE_TRACKED)
    try:
        with staged_snapshot(snapshot, previous) as (staging, objects):
            mismatch = frame_rate_mismatch(snapshot, staging, previous, scene)
            layer = staging.view_layers[0]
            with bpy.context.temp_override(scene=staging, view_layer=layer):
                staging.frame_set(0)
                layer.update()
                bounds = _bounds(objects)
                anchor = _bottom_center(objects, bounds)
                scale = _fit(bounds, target_size)
            application = _publish(
                scene, objects, cursor, snapshot.unit.key, anchor, snapshot.members, scale
            )
            bpy.data.scenes.remove(staging)
    except Exception:
        _remove_new_data(previous, _PACKAGE_DATA)
        if _snapshot(_PACKAGE_TRACKED) != previous:
            raise RuntimeError("Model cleanup is incomplete; do not import again") from None
        raise ModelApplicationError(
            "Could not import the verified model; saved files remain"
        ) from None
    _end_history(undo)
    return replace(
        application,
        format=fmt.value,
        members=snapshot.members,
        dropped_references=snapshot.dropped_references,
        frame_rate_mismatch=mismatch,
        target_size=target_size,
    )
