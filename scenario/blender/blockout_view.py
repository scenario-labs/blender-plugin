# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Make a built Blockout readable at once: a colour and a material per group, and a camera and sun when the
scene has none. The maths (palette, bounds, framing) is in `core.scene.blockout_view`; this applies it in Blender.

Everything runs inside the build operator's single undo step. `Staging` records the data a build creates so a
failure removes exactly that and restores the scene camera; data the user owns is never touched."""

import bpy

from ..core.scene import blockout_view as view
from .image_plane import ensure_nodes

GROUP_KEY = "scenario_blockout_group"  # custom property on a group material: the group it colours
DRESS_KEY = (
    "scenario_blockout_view"  # custom property on an added camera or light: "camera" or "sun"
)
CAMERA_NAME = "Blockout Camera"
SUN_NAME = "Blockout Sun"
_NAME_BYTES = 63  # Blender's limit for a data-block name


class Staging:
    """The data-blocks one build creates, so a failed build removes only them."""

    def __init__(self):
        self.objects, self.blocks, self.undo = [], [], []

    def discard(self):
        for obj in self.objects:
            bpy.data.objects.remove(obj, do_unlink=True)
        for collection, block in self.blocks:
            collection.remove(block)
        for restore in reversed(self.undo):
            restore()


def _material_name(group):
    name = f"Blockout {group}".encode()[:_NAME_BYTES]
    return name.decode(errors="ignore")


def _find_material(group):
    return next((m for m in bpy.data.materials if m.get(GROUP_KEY) == group), None)


def _new_material(group, colour, staging):
    material = bpy.data.materials.new(_material_name(group))
    staging.blocks.append((bpy.data.materials, material))
    material[GROUP_KEY] = group
    material.diffuse_color = colour  # the viewport colour in Material Preview and Solid by material
    tree = ensure_nodes(material)
    shader = tree.nodes.get("Principled BSDF") or tree.nodes.new("ShaderNodeBsdfPrincipled")
    shader.inputs["Base Color"].default_value = colour
    shader.inputs["Roughness"].default_value = 0.8
    return material


def group_materials(colours, staging):
    """{group: material}: the group's shared material from an earlier build, else a new one."""
    return {
        group: _find_material(group) or _new_material(group, colour, staging)
        for group, colour in colours.items()
    }


def assign_material(obj, material):
    """Show `material` on one object without touching the primitive mesh it shares with the others."""
    mesh = obj.data
    if not mesh.materials:
        mesh.materials.append(None)  # one empty slot on the shared mesh; each object fills its own
    slot = obj.material_slots[0]
    slot.link = "OBJECT"
    slot.material = material


def purge_unused_materials():
    """Remove group materials no object uses any more (a group the plan dropped, a cleared blockout)."""
    for material in tuple(bpy.data.materials):
        if GROUP_KEY in material and material.users == 0 and not material.use_fake_user:
            bpy.data.materials.remove(material)


def lacks_camera(scene):
    return scene.camera is None and not any(obj.type == "CAMERA" for obj in scene.objects)


def lacks_light(scene):
    return not any(obj.type == "LIGHT" for obj in scene.objects)


def _link(scene, obj, kind, staging):
    obj[DRESS_KEY] = kind
    scene.collection.objects.link(obj)
    staging.objects.append(obj)


def add_camera(scene, low, high, staging):
    """A camera framing low..high for the scene's render aspect, set as the scene camera."""
    render = scene.render
    aspect = view.render_aspect(
        render.resolution_x, render.resolution_y, render.pixel_aspect_x, render.pixel_aspect_y
    )
    data = bpy.data.cameras.new(CAMERA_NAME)
    staging.blocks.append((bpy.data.cameras, data))
    data.sensor_fit = "AUTO"
    data.sensor_width = view.SENSOR
    frame = view.frame_camera(low, high, aspect, lens=view.LENS, sensor=view.SENSOR)
    data.lens = frame["lens"]
    data.shift_x, data.shift_y = frame["shift"]
    data.clip_start, data.clip_end = frame["clip_start"], frame["clip_end"]
    camera = bpy.data.objects.new(CAMERA_NAME, data)
    camera.location = frame["location"]
    camera.rotation_euler = frame["rotation"]
    _link(scene, camera, "camera", staging)
    previous = scene.camera
    scene.camera = camera
    staging.undo.append(lambda: setattr(scene, "camera", previous))
    return camera


def add_sun(scene, low, high, staging):
    """One sun above low..high, lighting the faces the camera sees."""
    data = bpy.data.lights.new(SUN_NAME, "SUN")
    staging.blocks.append((bpy.data.lights, data))
    data.energy = view.SUN_STRENGTH
    placed = view.frame_sun(low, high)
    sun = bpy.data.objects.new(SUN_NAME, data)
    sun.location = placed["location"]
    sun.rotation_euler = placed["rotation"]
    _link(scene, sun, "sun", staging)
    return sun
