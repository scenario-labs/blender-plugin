# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Image planes: a material showing one image, with its alpha, lit or unlit, and the plane."""

import bpy

from ..core.scene.panorama import image_alpha

# Header bytes read for alpha: PNG tRNS precedes the image data, EXR headers are small.
_HEADER_BYTES = 1024 * 1024
# The plane's height in Blender units; its width follows the image's aspect.
PLANE_HEIGHT = 1.0


def ensure_nodes(material):
    if bpy.app.version < (5, 0, 0):
        material.use_nodes = True
    if material.node_tree is None:  # very old files
        material.use_nodes = True
    return material.node_tree


def file_alpha(path):
    """Whether a local image file's header declares alpha; unreadable files read as opaque."""
    try:
        with open(path, "rb") as source:
            return image_alpha(source.read(_HEADER_BYTES))
    except OSError:
        return False


def plane_material(name, image, *, alpha=False, unlit=False):
    """A new material showing `image`.

    With `alpha`, the image's alpha drives transparency and the material blends.
    `unlit` emits the image colour instead of shading it with scene lights.
    """
    material = bpy.data.materials.new(name)
    tree = ensure_nodes(material)
    nodes, links = tree.nodes, tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (400, 0)
    texture = nodes.new("ShaderNodeTexImage")
    texture.image = image
    texture.location = (-500, 0)
    if unlit:
        shader = nodes.new("ShaderNodeEmission")
        links.new(texture.outputs["Color"], shader.inputs["Color"])
    else:
        shader = nodes.new("ShaderNodeBsdfPrincipled")
        links.new(texture.outputs["Color"], shader.inputs["Base Color"])
    shader.location = (-100, 0)
    surface = shader.outputs[0]
    if alpha:
        if unlit:
            transparent = nodes.new("ShaderNodeBsdfTransparent")
            transparent.location = (-100, 200)
            mix = nodes.new("ShaderNodeMixShader")
            mix.location = (200, 0)
            links.new(texture.outputs["Alpha"], mix.inputs["Fac"])
            links.new(transparent.outputs["BSDF"], mix.inputs[1])
            links.new(surface, mix.inputs[2])
            surface = mix.outputs["Shader"]
        else:
            links.new(texture.outputs["Alpha"], shader.inputs["Alpha"])
        material.surface_render_method = "BLENDED"
    links.new(surface, output.inputs["Surface"])
    return material


def add_image_plane(scene, image, *, cursor, alpha=False, unlit=False, name="Scenario Image Plane"):
    """Link a new upright plane showing `image` to the scene's own collection.

    The plane is PLANE_HEIGHT tall, as wide as the image's aspect, faces the
    Front view (-Y) and has its bottom center at `cursor`. Selection and the
    active object are unchanged.
    """
    width, height = image.size
    if width <= 0 or height <= 0:
        raise ValueError("The image has no size to show")
    half = PLANE_HEIGHT * width / height / 2
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(
        [
            (-half, 0.0, 0.0),
            (half, 0.0, 0.0),
            (half, 0.0, PLANE_HEIGHT),
            (-half, 0.0, PLANE_HEIGHT),
        ],
        [],
        [(0, 1, 2, 3)],
    )
    layer = mesh.uv_layers.new(name="UVMap")
    for loop, uv in zip(layer.data, ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)), strict=True):
        loop.uv = uv
    mesh.update()
    mesh.materials.append(plane_material(name, image, alpha=alpha, unlit=unlit))
    obj = bpy.data.objects.new(name, mesh)
    obj.location = cursor
    scene.collection.objects.link(obj)
    return obj
