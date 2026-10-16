# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Show decoded Gaussian splats as a coloured point cloud on Blender's main thread.

Blender has no Gaussian splat renderer. A worker decodes a saved SPZ, Gaussian
PLY or .splat file into a bounded `SplatData` snapshot; this module turns it
into a mesh of vertices whose Geometry Nodes modifier makes one point per vertex,
sized by the splat's median scale, with an unlit material that shows its colour
and opacity. Rotations, anisotropic scales, view-dependent colour and true alpha
blending are not reproduced: this is a point-cloud approximation, not a splat
renderer. Mesh plus Geometry Nodes is used instead of the PointCloud API,
because `PointCloud.resize` is missing in Blender 5.0.

Every datablock is created new: an existing material or node group named like
ours is never reused or changed.
"""

import math
from dataclasses import replace

import bpy

from ..core.scene.splats import FORMAT_AXES
from .model_application import (
    ModelApplicationError,
    _begin_history,
    _end_history,
    _fit,
    _publish,
    _remove_new_data,
    _snapshot,
    _target_size,
    validate_destination,
)

# Reviewed point limits; the decoder keeps every ceil(count / limit)-th point.
POINT_CHOICES = (250_000, 500_000, 1_000_000, 2_000_000)
DEFAULT_POINTS = 1_000_000
AXES = ("OPENGL", "OPENCV")
# Presentation defaults kept on the modifier, where users can change them.
POINT_SCALE = 1.0
RADIUS_SAMPLE = 10_000
RADIUS_PERCENTILE = 0.99
GAMMA = 2.2
_DATA = ("objects", "collections", "meshes", "materials", "node_groups")
_ATTRIBUTES = (
    ("splat_color", "FLOAT_COLOR", "color", "colors"),
    ("splat_opacity", "FLOAT", "value", "opacities"),
    ("splat_radius", "FLOAT", "value", "radii"),
)


def default_axes(fmt):
    """The saved format's documented storage axes; live evidence may differ."""
    return FORMAT_AXES[fmt]


def max_radius(splat):
    """The 99th percentile of an even sample of at most 10,000 kept radii.

    A presentation cap, so that rare huge splats cannot hide the cloud; users can
    change it on the modifier. Sampling keeps the main-thread cost bounded.
    """
    radii = splat.floats("radii")
    step = max(1, -(-len(radii) // RADIUS_SAMPLE))
    sample = sorted(radii[::step])
    return float(sample[min(len(sample) - 1, int(len(sample) * RADIUS_PERCENTILE))])


def _mesh(splat, name):
    mesh = bpy.data.meshes.new(name)
    mesh.vertices.add(splat.kept)
    mesh.vertices.foreach_set("co", splat.floats("positions"))
    for attribute, kind, _, _ in _ATTRIBUTES:
        mesh.attributes.new(attribute, kind, "POINT")
    # On Blender 5.0.1 a reference taken before adding another attribute stops
    # receiving writes, so look each one up by name after adding them all.
    for attribute, _, key, values in _ATTRIBUTES:
        mesh.attributes[attribute].data.foreach_set(key, splat.floats(values))
    mesh.update()
    return mesh


def _material(name):
    """A new unlit material: colour as emission, mixed with transparency by opacity.

    Decoded colours are display-referred; a gamma of 2.2 approximates the sRGB
    to linear conversion Blender's scene-linear shading expects.
    """
    material = bpy.data.materials.new(name)
    if material.node_tree is None:
        material.use_nodes = True
    nodes, links = material.node_tree.nodes, material.node_tree.links
    nodes.clear()
    color = nodes.new("ShaderNodeAttribute")
    color.name, color.attribute_type, color.attribute_name = (
        "Splat colour",
        "GEOMETRY",
        "splat_color",
    )
    opacity = nodes.new("ShaderNodeAttribute")
    opacity.name, opacity.attribute_type, opacity.attribute_name = (
        "Splat opacity",
        "GEOMETRY",
        "splat_opacity",
    )
    gamma = nodes.new("ShaderNodeGamma")
    gamma.inputs["Gamma"].default_value = GAMMA
    emission = nodes.new("ShaderNodeEmission")
    emission.inputs["Strength"].default_value = 1.0
    transparent = nodes.new("ShaderNodeBsdfTransparent")
    mix = nodes.new("ShaderNodeMixShader")
    output = nodes.new("ShaderNodeOutputMaterial")
    links.new(color.outputs["Color"], gamma.inputs["Color"])
    links.new(gamma.outputs["Color"], emission.inputs["Color"])
    links.new(opacity.outputs["Fac"], mix.inputs["Fac"])
    links.new(transparent.outputs["BSDF"], mix.inputs[1])
    links.new(emission.outputs["Emission"], mix.inputs[2])
    links.new(mix.outputs["Shader"], output.inputs["Surface"])
    layout = (color, opacity, gamma, transparent, emission, mix, output)
    for index, node in enumerate(layout):
        node.location = (-900 + 150 * index, 0 if index % 2 else -200)
    return material


def _points(name, material, radius_cap):
    """A new Geometry Nodes group: Mesh to Points, radius from the splat scale."""
    tree = bpy.data.node_groups.new(name, "GeometryNodeTree")
    interface = tree.interface
    interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    scale = interface.new_socket("Point scale", in_out="INPUT", socket_type="NodeSocketFloat")
    scale.default_value, scale.min_value = POINT_SCALE, 0.0
    cap = interface.new_socket("Max radius", in_out="INPUT", socket_type="NodeSocketFloat")
    cap.default_value, cap.min_value = radius_cap, 0.0
    interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    nodes, links = tree.nodes, tree.links
    group_in = nodes.new("NodeGroupInput")
    radius = nodes.new("GeometryNodeInputNamedAttribute")
    radius.data_type = "FLOAT"
    radius.inputs["Name"].default_value = "splat_radius"
    scaled = nodes.new("ShaderNodeMath")
    scaled.operation = "MULTIPLY"
    capped = nodes.new("ShaderNodeMath")
    capped.operation = "MINIMUM"
    to_points = nodes.new("GeometryNodeMeshToPoints")
    set_material = nodes.new("GeometryNodeSetMaterial")
    set_material.name = "Set Material"
    set_material.inputs["Material"].default_value = material
    group_out = nodes.new("NodeGroupOutput")
    links.new(radius.outputs["Attribute"], scaled.inputs[0])
    links.new(group_in.outputs["Point scale"], scaled.inputs[1])
    links.new(scaled.outputs["Value"], capped.inputs[0])
    links.new(group_in.outputs["Max radius"], capped.inputs[1])
    links.new(group_in.outputs["Geometry"], to_points.inputs["Mesh"])
    links.new(capped.outputs["Value"], to_points.inputs["Radius"])
    links.new(to_points.outputs["Points"], set_material.inputs["Geometry"])
    links.new(set_material.outputs["Geometry"], group_out.inputs["Geometry"])
    layout = (group_in, radius, scaled, capped, to_points, set_material, group_out)
    for index, node in enumerate(layout):
        node.location = (-900 + 200 * index, 0)
    return tree


def build_points(splat, name="Scenario Splats"):
    """Create an unlinked point-cloud object and its own mesh, node group and material.

    The caller links the object and owns removing every new datablock on failure.
    """
    mesh = _mesh(splat, name)
    obj = bpy.data.objects.new(name, mesh)
    material = _material("Scenario Splat")
    tree = _points("Scenario Splat Points", material, max_radius(splat))
    modifier = obj.modifiers.new("Scenario Splat Points", "NODES")
    modifier.node_group = tree
    obj["scenario_splat_points"] = splat.count
    obj["scenario_splat_kept"] = splat.kept
    obj["scenario_splat_axes"] = splat.axes
    return obj


def _anchor(splat):
    (low_x, low_y, low_z), (high_x, high_y, _) = splat.bounds
    return ((low_x + high_x) / 2, (low_y + high_y) / 2, low_z)


def import_splat(scene, splat, *, cursor, unit_key, members, fmt, history=False, target_size=None):
    """Publish one decoded snapshot as a new group with its bottom center at the cursor.

    Nothing existing is reused, selected or changed. On failure every new
    datablock is removed; an incomplete cleanup is reported as uncertain.
    ``history`` records the same desktop Undo checkpoints as a saved model
    import, before building and after publication. ``target_size`` scales the
    group so the longest side of the decoded splat centres has that length.
    """
    from mathutils import Vector

    validate_destination(scene, cursor)
    target_size = _target_size(target_size)
    if splat is None or not math.isfinite(sum(_anchor(splat))):
        raise ModelApplicationError("Prepare the saved splats again")
    scale = _fit(splat.bounds, target_size)
    undo = _begin_history(history)
    previous = _snapshot(_DATA)
    try:
        obj = build_points(splat)
        application = _publish(
            scene, (obj,), cursor, unit_key, Vector(_anchor(splat)), members, scale
        )
        application.root["scenario_splat_points"] = splat.count
        application.root["scenario_splat_kept"] = splat.kept
    except Exception:
        _remove_new_data(previous, _DATA)
        if _snapshot(_DATA) != previous:
            raise RuntimeError("Splat cleanup is incomplete; do not import again") from None
        raise ModelApplicationError(
            "Could not show the verified splats; saved files remain"
        ) from None
    _end_history(undo)
    return replace(
        application,
        format=fmt,
        members=tuple(members),
        splat=splat_summary(splat),
        target_size=target_size,
    )


def splat_summary(splat):
    """The session status fields of one splat import."""
    return {
        "points_total": splat.count,
        "points_kept": splat.kept,
        "step": splat.step,
        "axes": splat.axes,
        "spz_extensions": splat.extensions,
    }
