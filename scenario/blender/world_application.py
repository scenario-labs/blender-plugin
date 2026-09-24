# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Explicit synchronous World replacement with guarded, session-local restoration."""

import hashlib
import os
import stat
import tempfile
import threading
from dataclasses import dataclass, field
from pathlib import Path

import bpy

from ..core.jobs.transfers import DownloadedResult
from ..core.scene.panorama import MAX_FILE_BYTES, PanoramaError, PanoramaInfo, inspect_panorama


class WorldApplicationError(RuntimeError):
    """A local panorama could not be applied or safely restored."""


def _main_thread():
    if threading.current_thread() is not threading.main_thread():
        raise WorldApplicationError("World application requires Blender's main thread")


def _present(value, collection):
    try:
        return value is not None and value in tuple(collection)
    except ReferenceError:
        return False


def _scene(scene):
    if not _present(scene, bpy.data.scenes) or not scene.is_editable:
        raise WorldApplicationError("The explicitly selected scene is unavailable or read-only")


def _value(value):
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if hasattr(value, "as_pointer"):
        return value.as_pointer()
    if hasattr(value, "to_dict"):
        return _value(value.to_dict())
    if isinstance(value, dict):
        return tuple(sorted((key, _value(item)) for key, item in value.items()))
    if isinstance(value, set):
        return tuple(sorted(value))
    return tuple(_value(item) for item in value)


def _settings(value, *, exclude=()):
    if value is None:
        return None
    values = []
    for prop in value.bl_rna.properties:
        if (
            prop.identifier not in exclude
            and not prop.is_readonly
            and prop.type
            in {
                "BOOLEAN",
                "INT",
                "FLOAT",
                "STRING",
                "ENUM",
                "POINTER",
            }
        ):
            values.append((prop.identifier, _value(getattr(value, prop.identifier))))
    if hasattr(value, "keys"):
        try:
            keys = value.keys()
        except TypeError:
            # Some RNA settings expose keys() but do not support IDProperties.
            keys = ()
        values.append(("custom", tuple(sorted((key, _value(value[key])) for key in keys))))
    return tuple(values)


def _packed_digest(image):
    packed = image.packed_file
    if packed is None or packed.size > MAX_FILE_BYTES:
        raise WorldApplicationError("The packed panorama changed; preserve or restore it manually")
    return hashlib.sha256(packed.data).digest()


def _ramp(node):
    mapping = getattr(node, "color_mapping", None)
    if mapping is None:
        return None
    ramp = mapping.color_ramp
    return _settings(ramp), tuple(_settings(element) for element in ramp.elements)


def _fingerprint(world, image):
    if not world.use_nodes or world.node_tree is None:
        raise WorldApplicationError("The applied World was edited; preserve or restore it manually")
    tree = world.node_tree
    # Accessing extension PropertyGroups can initialize custom IDProperties.
    # Capture them before taking the parent ID snapshot so the first is stable.
    world_options = tuple(
        _settings(getattr(world, name, None))
        for name in ("cycles", "cycles_visibility", "mist_settings")
    )
    return (
        _settings(world),
        world_options,
        bool(world.animation_data),
        bool(world.asset_data),
        _settings(tree),
        bool(tree.animation_data),
        tuple(
            (
                node.as_pointer(),
                _settings(node),
                tuple(
                    _settings(getattr(node, name, None))
                    for name in ("texture_mapping", "color_mapping", "image_user")
                ),
                _ramp(node),
                tuple(_settings(socket) for socket in node.inputs),
            )
            for node in tree.nodes
        ),
        tuple(
            (
                link.from_node.as_pointer(),
                link.from_socket.identifier,
                link.to_node.as_pointer(),
                link.to_socket.identifier,
            )
            for link in tree.links
        ),
        # Pixels are a potentially huge writable FLOAT array, not a setting.
        # Dirty state and packed-byte digest guard edits without boxing pixels.
        _settings(image, exclude={"pixels"}),
        _settings(image.colorspace_settings),
        tuple(image.size),
        bool(image.is_dirty),
        _packed_digest(image),
    )


def _discard_unused(world, image):
    # Cleanup is best effort; failure cannot reverse an already completed scene
    # assignment. Never unlink an ID retained by another scene/material/user.
    for value, collection in ((world, bpy.data.worlds), (image, bpy.data.images)):
        try:
            if _present(value, collection) and value.users == 0:
                collection.remove(value)
        except Exception:
            # Best-effort orphan cleanup must not undo a completed restoration.
            continue


@dataclass(eq=False)
class WorldApplication:
    """Keep this handle for explicit restore in the same live file session.

    No undo entry, persistent pointer, file/scene guess or job dispatch is created.
    File-load/undo-invalidated handles must be discarded by the application owner.
    """

    info: PanoramaInfo
    _scene: object = field(repr=False)
    _previous: object = field(repr=False)
    _world: object = field(repr=False)
    _image: object = field(repr=False)
    _snapshot: object = field(repr=False)
    _restored: bool = field(default=False, repr=False)

    def restore(self):
        _main_thread()
        if self._restored:
            return False
        _scene(self._scene)
        try:
            if self._scene.world != self._world or not _present(self._world, bpy.data.worlds):
                raise WorldApplicationError(
                    "The scene's World changed; restore requires explicit review"
                )
            if (
                not _present(self._image, bpy.data.images)
                or _fingerprint(self._world, self._image) != self._snapshot
            ):
                raise WorldApplicationError(
                    "The applied World was edited; preserve or restore it manually"
                )
            if self._previous is not None and not _present(self._previous, bpy.data.worlds):
                raise WorldApplicationError(
                    "The original World was removed; restore requires explicit review"
                )
            self._scene.world = self._previous
        except ReferenceError:
            raise WorldApplicationError(
                "The original file, scene or World is no longer available"
            ) from None
        self._restored = True
        _discard_unused(self._world, self._image)
        return True


def _load_image(data, info):
    package = __package__.rsplit(".", 1)[0]
    root = bpy.utils.extension_path_user(package, path="world-import", create=True)
    image = None
    try:
        # Decode stable private bytes, not a caller path that could change during
        # loading. Packing detaches the result from this temporary filename.
        with tempfile.TemporaryDirectory(prefix="panorama-", dir=root) as directory:
            path = Path(directory) / ("input.png" if info.file_format == "PNG" else "input.exr")
            path.write_bytes(data)
            image = bpy.data.images.load(str(path), check_existing=False)
            if (
                tuple(image.size) != (info.width, info.height)
                or image.file_format != info.file_format
                or image.type != "IMAGE"
            ):
                raise WorldApplicationError(
                    "Decoded panorama does not match its supported container"
                )
            if info.hdr_capable and not image.is_float:
                raise WorldApplicationError(
                    "OpenEXR panorama did not decode as floating-point data"
                )
            image.pack()
            if image.packed_file is None:
                raise WorldApplicationError("The panorama could not be retained in the blend file")
            image.name = "Scenario Panorama"
            image.filepath = ""
        return image
    except BaseException:
        _discard_unused(None, image)
        raise


def apply_world(scene, filepath, *, expected_receipt=None):
    """Apply a local supported 2:1 panorama to exactly this scene, on main thread.

    The caller explicitly selects an equirectangular panorama. Aspect ratio does
    not prove projection, seams, poles or high dynamic range. Async integrations
    must validate their captured file/scene/revision before calling this function
    and supply the saved download receipt to bind the decoded snapshot's bytes.
    """
    _main_thread()
    _scene(scene)
    if expected_receipt is not None and not isinstance(expected_receipt, DownloadedResult):
        raise WorldApplicationError("Use a downloaded-result receipt for panorama verification")
    previous, world, image = scene.world, None, None
    try:
        path = Path(filepath)
        if not stat.S_ISREG(path.stat().st_mode):
            raise WorldApplicationError("Select a regular local panorama file")
        flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_BINARY", 0)
        descriptor = os.open(path, flags)
        with os.fdopen(descriptor, "rb") as source:
            if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
                raise WorldApplicationError("Select a regular local panorama file")
            data = source.read(MAX_FILE_BYTES + 1)
        if expected_receipt is not None and (
            path.name != expected_receipt.name
            or len(data) != expected_receipt.size
            or hashlib.sha256(data).hexdigest() != expected_receipt.sha256
        ):
            raise WorldApplicationError("The panorama no longer matches its download receipt")
        info = inspect_panorama(data)
        image = _load_image(data, info)
        world = bpy.data.worlds.new("Scenario Panorama")
        world.use_nodes = True
        nodes, links = world.node_tree.nodes, world.node_tree.links
        nodes.clear()
        environment = nodes.new("ShaderNodeTexEnvironment")
        environment.image = image
        environment.projection = "EQUIRECTANGULAR"
        background = nodes.new("ShaderNodeBackground")
        background.inputs["Strength"].default_value = 1.0
        output = nodes.new("ShaderNodeOutputWorld")
        links.new(environment.outputs["Color"], background.inputs["Color"])
        links.new(background.outputs["Background"], output.inputs["Surface"])
        receipt = WorldApplication(info, scene, previous, world, image, _fingerprint(world, image))
        _scene(scene)
        if scene.world != previous:
            raise WorldApplicationError("The scene's World changed while preparing the panorama")
        scene.world = world
        return receipt
    except BaseException as exc:
        try:
            if world is not None and _present(scene, bpy.data.scenes) and scene.world == world:
                scene.world = previous
        finally:
            _discard_unused(world, image)
        if isinstance(exc, (WorldApplicationError, PanoramaError)):
            raise
        if isinstance(exc, Exception):
            raise WorldApplicationError(
                "Could not apply the local panorama; the original World is preserved"
            ) from None
        raise
