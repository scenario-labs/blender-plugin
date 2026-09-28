# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Import one static receipt-bound GLB into a new group at an approved cursor."""

import hashlib
import logging
import math
import os
import stat
import tempfile
import threading
from dataclasses import dataclass, field
from pathlib import Path

import bpy
from mathutils import Vector

from ..core.scene.glb import MAX_GLB_BYTES, inspect_glb

MODEL_MEDIA_TYPE = "model/gltf-binary"
_DATA = (
    "objects",
    "collections",
    "meshes",
    "materials",
    "images",
    "node_groups",
    "cameras",
    "lights",
    "armatures",
    "actions",
    "scenes",
)
_TRACKED_DATA = (*_DATA, "shape_keys")
_log = logging.getLogger("scenario.jobs")


class ModelApplicationError(RuntimeError):
    """The attempted import left no new model data or destination changes."""


@dataclass(frozen=True)
class ModelApplication:
    collection: object = field(repr=False)
    root: object = field(repr=False)
    objects: tuple = field(repr=False)


def _read(item, path):
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
    inspect_glb(data)
    return data


def _import(path):
    result = bpy.ops.import_scene.gltf(
        filepath=str(path),
        import_pack_images=True,
        import_select_created_objects=False,
        import_scene_extras=False,
        import_scene_as_collection=False,
    )
    if result != {"FINISHED"}:
        raise ModelApplicationError("Blender could not import the saved GLB")


def _publish(scene, objects, cursor, asset_id):
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
    bpy.context.view_layer.update()
    points = [
        obj.matrix_world @ Vector(corner)
        for obj in objects
        if obj.type == "MESH"
        for corner in obj.bound_box
    ]
    if not points or any(not math.isfinite(value) for point in points for value in point):
        raise ModelApplicationError("GLB contains no supported finite mesh geometry")
    low = [min(point[axis] for point in points) for axis in range(3)]
    high = [max(point[axis] for point in points) for axis in range(3)]
    root.location = Vector(cursor) - Vector(
        ((low[0] + high[0]) / 2, (low[1] + high[1]) / 2, low[2])
    )
    root["scenario_asset"] = asset_id
    bpy.context.view_layer.update()
    return ModelApplication(collection, root, tuple(objects))


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


def _snapshot():
    return {name: set(getattr(bpy.data, name)) for name in _TRACKED_DATA}


def _remove_new_data(previous):
    for name in _DATA:
        collection = getattr(bpy.data, name)
        for value in set(collection) - previous[name]:
            try:
                collection.remove(value, do_unlink=True)
            except Exception:
                # Continue independent cleanup, then verify the actual outcome.
                pass


def apply_model(scene, item, path, *, cursor):
    """Stage in a disposable scene, then publish only newly imported model data."""
    validate_destination(scene, cursor)
    previous = _snapshot()
    temporary = None
    try:
        data = _read(item, path)
        package = __package__.rsplit(".", 1)[0]
        root = bpy.utils.extension_path_user(package, path="model-import", create=True)
        temporary = tempfile.TemporaryDirectory(prefix="result-", dir=root)
        snapshot = Path(temporary.name) / "model.glb"
        snapshot.write_bytes(data)
        staging = bpy.data.scenes.new("Scenario import staging")
        layer = staging.view_layers[0]
        with bpy.context.temp_override(
            scene=staging,
            view_layer=layer,
            collection=staging.collection,
            layer_collection=layer.layer_collection,
        ):
            _import(snapshot)
        objects = tuple(obj for obj in bpy.data.objects if obj not in previous["objects"])
        if any(obj not in tuple(staging.objects) for obj in objects):
            raise ModelApplicationError("Imported objects escaped the staging scene")
        for image in set(bpy.data.images) - previous["images"]:
            if image.packed_file is None:
                image.pack()
            if image.packed_file is None:
                raise ModelApplicationError("The model texture could not be packed")
            image.filepath = ""
        application = _publish(scene, objects, cursor, item.asset.asset_id)
        bpy.data.scenes.remove(staging)
        return application
    except Exception:
        _remove_new_data(previous)
        if _snapshot() != previous:
            # This is deliberately not ModelApplicationError: the session must
            # keep the durable claim uncertain and prevent duplicate imports.
            raise RuntimeError("Model cleanup is incomplete; do not import again") from None
        raise ModelApplicationError(
            "Could not import the verified model; saved files remain"
        ) from None
    finally:
        if temporary is not None:
            try:
                temporary.cleanup()
            except Exception:
                # Packed images have no dependency on this snapshot. A disk
                # cleanup failure must not undo a completed scene application.
                _log.warning("Model snapshot cleanup failed; temporary files may remain")
