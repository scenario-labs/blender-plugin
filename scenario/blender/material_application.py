# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Apply verified texture maps to one explicit mesh slot without editing old materials."""

import threading
from array import array
from dataclasses import dataclass, field, replace

import bpy

from ..core.jobs.results import VerifiedResults
from .image_application import apply_images

_IMAGE_TYPES = {"image/png", "image/exr", "image/x-exr"}
_MAX_MAP_BYTES = 256 * 1024 * 1024
_MAX_POLYGONS = 1_000_000


class MaterialApplicationError(RuntimeError):
    """Material application was rejected or its scene changes were fully rolled back."""


def _main_thread():
    if threading.current_thread() is not threading.main_thread():
        raise MaterialApplicationError("Apply materials on Blender's main thread")


def selected_maps(record):
    """Require unambiguous saved roles; never choose a texture by name or array order."""
    result = {}
    for index, item in enumerate(record.results):
        role = item.asset.texture_role
        if role is None:
            continue
        if role in result or item.asset.media_type not in _IMAGE_TYPES or item.receipt is None:
            raise MaterialApplicationError("Choose one supported, unambiguous saved texture set")
        result[role] = index
    if ("base" in result) == ("albedo" in result):
        raise MaterialApplicationError("A material needs exactly one base-color or albedo map")
    if "roughness" in result and "smoothness" in result:
        raise MaterialApplicationError("Choose roughness or smoothness, not both")
    if sum(record.results[index].receipt.size for index in result.values()) > _MAX_MAP_BYTES:
        raise MaterialApplicationError("Saved material maps exceed the combined byte limit")
    return result


@dataclass(frozen=True)
class MaterialTarget:
    scene: object = field(repr=False)
    obj: object = field(repr=False)
    mesh: object = field(repr=False)
    slots: tuple = field(repr=False)
    active: int
    uv_name: str
    face_slots: bytes = field(repr=False)


def _face_slots(mesh):
    if len(mesh.polygons) > _MAX_POLYGONS:
        raise MaterialApplicationError("Mesh exceeds the material-assignment polygon limit")
    values = array("i", [0]) * len(mesh.polygons)
    mesh.polygons.foreach_get("material_index", values)
    return values.tobytes()


def capture_target(scene, obj):
    _main_thread()
    if (
        scene != bpy.context.scene
        or not scene.is_editable
        or obj is None
        or obj not in tuple(scene.objects)
        or obj.type != "MESH"
        or obj.mode != "OBJECT"
        or obj.library
        or obj.override_library
        or obj.data.library
        or obj.data.override_library
        or obj.data.users != 1
        or len(obj.users_scene) != 1
        or not obj.data.uv_layers.active
        or len(obj.material_slots) > 128
    ):
        raise MaterialApplicationError("Choose one local, single-user mesh with UVs in Object Mode")
    return MaterialTarget(
        scene,
        obj,
        obj.data,
        tuple((slot.link, slot.material) for slot in obj.material_slots),
        obj.active_material_index,
        obj.data.uv_layers.active.name,
        _face_slots(obj.data),
    )


def validate_target(target):
    if capture_target(target.scene, target.obj) != target:
        raise MaterialApplicationError("The mesh or material destination changed; review it again")


def _build(images, uv_name):
    material = bpy.data.materials.new("Scenario Material")
    material.use_nodes = True
    tree = material.node_tree
    tree.nodes.clear()
    output = tree.nodes.new("ShaderNodeOutputMaterial")
    bsdf = tree.nodes.new("ShaderNodeBsdfPrincipled")
    tree.links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    output.location = (600, 0)
    uv = tree.nodes.new("ShaderNodeUVMap")
    uv.uv_map = uv_name
    uv.location = (-1000, 0)
    textures = {}
    for index, (role, image) in enumerate(images.items()):
        image.colorspace_settings.name = "sRGB" if role in {"base", "albedo"} else "Non-Color"
        image.name = f"Scenario {role}"
        image.use_fake_user = False
        texture = tree.nodes.new("ShaderNodeTexImage")
        texture.image, texture.label = image, role.title()
        texture.location = (-700, -index * 250)
        tree.links.new(uv.outputs["UV"], texture.inputs["Vector"])
        textures[role] = texture
    base = textures.get("albedo") or textures["base"]
    tree.links.new(base.outputs["Color"], bsdf.inputs["Base Color"])
    for role, socket in (("roughness", "Roughness"), ("metallic", "Metallic")):
        if role in textures:
            tree.links.new(textures[role].outputs["Color"], bsdf.inputs[socket])
    if "smoothness" in textures:
        invert = tree.nodes.new("ShaderNodeInvert")
        invert.label = "Smoothness to roughness"
        tree.links.new(textures["smoothness"].outputs["Color"], invert.inputs["Color"])
        tree.links.new(invert.outputs["Color"], bsdf.inputs["Roughness"])
    normal = None
    if "normal" in textures:
        normal = tree.nodes.new("ShaderNodeNormalMap")
        normal.uv_map = uv_name
        tree.links.new(textures["normal"].outputs["Color"], normal.inputs["Color"])
    if "height" in textures:
        bump = tree.nodes.new("ShaderNodeBump")
        bump.inputs["Distance"].default_value = 0.05
        tree.links.new(textures["height"].outputs["Color"], bump.inputs["Height"])
        if normal:
            tree.links.new(normal.outputs["Normal"], bump.inputs["Normal"])
        normal = bump
    if normal:
        tree.links.new(normal.outputs["Normal"], bsdf.inputs["Normal"])
    # AO and edge remain named, packed nodes for deliberate artist wiring.
    return material


def _assign(target, material):
    if target.slots:
        target.obj.material_slots[target.active].material = material
    else:
        target.mesh.materials.append(material)


def _restore_slots(target):
    if target.obj.data != target.mesh or target.mesh.users != 1:
        raise RuntimeError("The material target changed during application")
    if target.slots:
        for slot, (link, material) in zip(target.obj.material_slots, target.slots, strict=True):
            slot.link, slot.material = link, material
    else:
        target.mesh.materials.clear()
    if _face_slots(target.mesh) != target.face_slots:
        values = array("i")
        values.frombytes(target.face_slots)
        target.mesh.polygons.foreach_set("material_index", values)
    target.obj.active_material_index = target.active


@dataclass(frozen=True)
class MaterialApplication:
    material: object = field(repr=False)
    images: tuple = field(repr=False)
    target: MaterialTarget = field(repr=False)


def apply_material(verified, target):
    _main_thread()
    validate_target(target)
    roles = selected_maps(verified.record)
    before_images, before_materials = set(bpy.data.images), set(bpy.data.materials)
    try:
        chosen = VerifiedResults(
            replace(
                verified.record, results=tuple(verified.record.results[i] for i in roles.values())
            ),
            tuple(verified.paths[i] for i in roles.values()),
        )
        images = apply_images(chosen, pixel_budget=32_000_000)
        material = _build(dict(zip(roles, images, strict=True)), target.uv_name)
        _assign(target, material)
        return MaterialApplication(material, images, target)
    except Exception:
        # Verify cleanup's outcome before permitting the durable job to retry.
        try:
            _restore_slots(target)
            for value in set(bpy.data.materials) - before_materials:
                bpy.data.materials.remove(value)
            for value in set(bpy.data.images) - before_images:
                bpy.data.images.remove(value)
            restored = (
                capture_target(target.scene, target.obj) == target
                and set(bpy.data.images) == before_images
                and set(bpy.data.materials) == before_materials
            )
        except Exception:
            restored = False
        if not restored:
            raise RuntimeError("Material cleanup is incomplete; do not apply again") from None
        raise MaterialApplicationError("Could not apply the saved material; files remain") from None
