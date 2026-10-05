# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Transactional native Film shot construction from validated data and GLB receipts.

This is a local application primitive. Its caller owns credential/task selection,
application claims and user approval; a filesystem path alone never supplies a hero.
Motion/NLA choreography adapts the selected Studio film_scene.py; see
docs/STUDIO_ADOPTION.md for source provenance and integration differences.
"""

import hashlib
import json
import math
import threading
from dataclasses import dataclass, field
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

from ..core.jobs.store import StoredResult, _identity
from ..core.scene.film_plan import validate_film_plan
from . import model_application
from .shot_planner import fcurves_of

_DATA = (*model_application._TRACKED_DATA, "worlds", "curves")


@dataclass(frozen=True)
class HeroSource:
    result: StoredResult
    path: Path

    def __post_init__(self):
        if not isinstance(self.result, StoredResult) or not isinstance(self.path, Path):
            raise TypeError("Choose a saved model result and its receipt path")


@dataclass(frozen=True)
class ShotScene:
    scene: object = field(repr=False)
    camera: object = field(repr=False)
    target: object = field(repr=False)
    placeholders: dict = field(repr=False)
    actors: tuple = field(repr=False)


def _snapshot():
    return {name: set(getattr(bpy.data, name)) for name in _DATA}


def _rollback(previous):
    added = {value for name in _DATA for value in set(getattr(bpy.data, name)) - previous[name]}
    if added:
        bpy.data.batch_remove(ids=added)
    if _snapshot() != previous:
        raise RuntimeError("Film cleanup is incomplete; inspect Blender data before continuing")


def _main_thread():
    if threading.current_thread() is not threading.main_thread():
        raise RuntimeError("Build Film scenes on Blender's main thread")
    if bpy.context.window is None or bpy.context.mode != "OBJECT":
        raise ValueError("Build Film scenes in a Blender window in Object Mode")


def _collection(scene, name):
    result = bpy.data.collections.new(name)
    scene.collection.children.link(result)
    return result


def _object(collection, name, data=None):
    obj = bpy.data.objects.new(name, data)
    collection.objects.link(obj)
    return obj


def _rgba(value):
    return (*value[:3], value[3] if len(value) == 4 else 1)


def _material(name, color):
    value = bpy.data.materials.new(name)
    value.use_nodes = True
    value.diffuse_color = _rgba(color)
    surface = value.node_tree.nodes.get("Principled BSDF")
    surface.inputs["Base Color"].default_value = _rgba(color)
    surface.inputs["Alpha"].default_value = value.diffuse_color[3]
    surface.inputs["Roughness"].default_value = 0.5
    if value.diffuse_color[3] < 1:
        value.surface_render_method = "DITHERED"
    return value


def _mesh(kind, name):
    mesh = bpy.data.meshes.new(name)
    if kind == "torus":
        rings, sides = 48, 16
        vertices = []
        for ring in range(rings):
            u = ring * math.tau / rings
            for side in range(sides):
                v = side * math.tau / sides
                radius = 1 + 0.2 * math.cos(v)
                vertices.append((radius * math.cos(u), radius * math.sin(u), 0.2 * math.sin(v)))
        faces = []
        for ring in range(rings):
            for side in range(sides):
                faces.append(
                    tuple(
                        r * sides + s
                        for r, s in (
                            (ring, side),
                            ((ring + 1) % rings, side),
                            ((ring + 1) % rings, (side + 1) % sides),
                            (ring, (side + 1) % sides),
                        )
                    )
                )
        mesh.from_pydata(vertices, [], faces)
    else:
        bm = bmesh.new()
        try:
            if kind == "box":
                bmesh.ops.create_cube(bm, size=2)
            elif kind == "plane":
                bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=1)
            elif kind == "sphere":
                bmesh.ops.create_uvsphere(bm, u_segments=40, v_segments=24, radius=1)
            elif kind in {"cylinder", "cone"}:
                bmesh.ops.create_cone(
                    bm,
                    cap_ends=True,
                    cap_tris=False,
                    segments=48,
                    radius1=1,
                    radius2=1 if kind == "cylinder" else 0,
                    depth=2,
                )
            else:
                raise ValueError("Choose a supported Film primitive")
            bm.to_mesh(mesh)
        finally:
            bm.free()
    mesh.update()
    return mesh


def _primitive(collection, spec, material):
    mesh = _mesh(spec["type"], spec["name"])
    for vertex in mesh.vertices:
        vertex.co = tuple(vertex.co[i] * spec["scale"][i] for i in range(3))
    mesh.update()
    obj = _object(collection, spec["name"], mesh)
    obj.location = spec["location"]
    obj.rotation_euler = tuple(map(math.radians, spec["rotation"]))
    obj.color = _rgba(spec["color"])
    mesh.materials.append(material)
    obj["scenario_role"] = spec["role"]
    obj["scenario_primitive"] = spec["type"]
    obj["scenario_asset_policy"] = "interpret_placeholder"
    if spec["bevel"] and spec["type"] in {"box", "cylinder", "cone"}:
        bevel = obj.modifiers.new("Film edge softness", "BEVEL")
        bevel.width, bevel.segments = spec["bevel"], 3
    return obj


def _linear(obj):
    for curve in fcurves_of(obj):
        for key in curve.keyframe_points:
            key.interpolation = "LINEAR"


def _motion(obj, keys, fps, frames, *, baked_scale=None):
    # Preserve subframe timing instead of collapsing distinct authored keys by rounding.
    for key in keys:
        frame = 1 + key["time"] * fps * (frames - 1) / frames
        for name in ("location", "rotation", "scale"):
            if name not in key:
                continue
            attr = "rotation_euler" if name == "rotation" else name
            value = key[name]
            if name == "rotation":
                value = tuple(map(math.radians, value))
            elif name == "scale" and baked_scale is not None:
                value = tuple(v / base for v, base in zip(value, baked_scale, strict=True))
            setattr(obj, attr, value)
            obj.keyframe_insert(data_path=attr, frame=frame)
    _linear(obj)


def _camera_points(spec):
    if spec["style"] == "path":
        return spec["points"], False
    target, distance, height = Vector(spec["target"]), spec["distance"], spec["height"]
    if spec["style"] == "orbit":
        return [
            (
                target.x + distance * math.sin(i * math.tau / 12),
                target.y - distance * math.cos(i * math.tau / 12),
                height,
            )
            for i in range(12)
        ], True
    if spec["style"] == "dolly":
        return [
            (target.x - distance / 4, target.y - distance, height),
            (target.x + distance / 5, target.y - distance / 2, height * 0.8),
        ], False
    return [
        (target.x - distance / 3, target.y - distance, max(0.5, height / 3)),
        (target.x, target.y - distance * 0.8, height),
        (target.x + distance / 3, target.y - distance * 0.65, min(50, height * 1.7)),
    ], False


def _camera(scene, collection, spec, shot, fps):
    camera_data = bpy.data.cameras.new("Film Camera")
    camera_data.lens = spec["lens"]
    camera = _object(collection, "Film Camera", camera_data)
    target = _object(collection, "Film Camera Target")
    target.location = spec["target"]
    target.empty_display_type = "SPHERE"
    target.empty_display_size = 0.15
    points, cyclic = _camera_points(spec)
    data = bpy.data.curves.new("Film Camera Path", "CURVE")
    data.dimensions, data.resolution_u, data.use_path = "3D", 32, True
    data.path_duration = max(1, shot["frames"] - 1)
    spline = data.splines.new("BEZIER")
    spline.bezier_points.add(len(points) - 1)
    for point, position in zip(spline.bezier_points, points, strict=True):
        point.co = position
        point.handle_left_type = point.handle_right_type = "AUTO"
    spline.use_cyclic_u = cyclic
    path = _object(collection, "Film Camera Path", data)
    path.hide_render = True
    path["scenario_camera_path"] = True
    follow = camera.constraints.new("FOLLOW_PATH")
    follow.target, follow.use_fixed_location = path, True
    follow.use_curve_follow = False
    for frame, offset in ((1, 0), (shot["frames"], 1)):
        follow.offset_factor = offset
        follow.keyframe_insert("offset_factor", frame=frame)
    track = camera.constraints.new("TRACK_TO")
    track.target, track.track_axis, track.up_axis = target, "TRACK_NEGATIVE_Z", "UP_Y"
    _linear(camera)
    _motion(target, shot["target_keyframes"], fps, shot["frames"])
    scene.camera = camera
    return camera, target


def _lighting(scene, collection, spec):
    world = bpy.data.worlds.new("Film World")
    world.use_nodes = True
    settings = spec.get("world", {"color": [0.04, 0.05, 0.08], "strength": 0.35})
    background = world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = _rgba(settings["color"])
    background.inputs["Strength"].default_value = settings["strength"]
    scene.world = world
    target = Vector(spec["camera"]["target"])
    size = max(1, spec["camera"]["distance"] / 8)
    for name, offset, power, color in (
        ("Key", (-4, -4, 6), 1800, (1, 0.87, 0.73)),
        ("Rim", (4, 3, 4), 2400, (0.36, 0.64, 1)),
        ("Fill", (1, -2, 5), 900, (1, 1, 1)),
    ):
        light = bpy.data.lights.new("Film " + name, "AREA")
        light.energy, light.size, light.color = power * size**2, 4 * size, color
        obj = _object(collection, light.name, light)
        obj.location = target + Vector(offset) * size
        obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def _clip(obj, actor, frames, fps):
    animation = obj.animation_data
    if animation is None:
        return
    action = animation.action
    slot = getattr(animation, "action_slot", None)
    if action is None:
        strips = [s for track in animation.nla_tracks for s in track.strips if s.action]
        if not strips:
            return
        action, slot = strips[0].action, getattr(strips[0], "action_slot", None)
    animation.action = None
    for track in animation.nla_tracks:
        track.mute = True
    track = animation.nla_tracks.new()
    track.name = "Film " + actor["action"]
    strip = track.strips.new(action.name, 1, action)
    if slot is not None and hasattr(strip, "action_slot"):
        strip.action_slot = slot
    if actor["action"] == "loop" and actor["action_until"] > 0:
        end = min(frames, max(1, round(actor["action_until"] * fps)))
        strip.scale = 1 / actor["action_speed"]
        span = max(1, (action.frame_range[1] - action.frame_range[0]) * strip.scale)
        strip.repeat = max(1, math.ceil(end / span))
        strip.frame_end = end
    else:
        strip.use_animated_time = True
        phase = actor["phase"] if actor["action"] == "hold" else 0
        strip.strip_time = action.frame_range[0] + phase * (
            action.frame_range[1] - action.frame_range[0]
        )
        strip.frame_end = frames
    strip.blend_type, strip.extrapolation = "REPLACE", "HOLD"


def _hero(scene, actor, spec, source, shot, fps):
    application = model_application.apply_model(scene, source.result, source.path, cursor=(0, 0, 0))
    root, objects = application.root, application.objects
    root.name = "Film / " + actor["name"]
    application.collection.name = "Film Hero / " + actor["name"]
    # Geometry/rigs are imported independently for every actor. No cached source
    # or existing scene can receive a changed pose, morph animation or transform.
    for obj in objects:
        _clip(obj, actor, shot["frames"], fps)
        if obj.type == "MESH" and obj.data.shape_keys:
            _clip(obj.data.shape_keys, actor, shot["frames"], fps)
        obj["scenario_asset_policy"] = "preserve_hero"
        obj["scenario_hero_id"] = actor["hero"]
    scene.frame_set(1)
    bpy.context.view_layer.update()
    points = [
        obj.matrix_world @ Vector(corner)
        for obj in objects
        if obj.type == "MESH"
        for corner in obj.bound_box
    ]
    low = Vector(tuple(min(p[i] for p in points) for i in range(3)))
    high = Vector(tuple(max(p[i] for p in points) for i in range(3)))
    extent = high - low
    axis = 0 if "width" in spec else 2
    dimension = "width" if "width" in spec else "height"
    factor = 1
    if dimension in spec:
        if not math.isfinite(extent[axis]) or extent[axis] <= 0:
            raise ValueError("The selected hero has no measurable size in the requested dimension")
        factor = spec[dimension] / extent[axis]
    # The selected held pose can move the imported bounds away from the
    # importer's initial placement. Center and ground that pose before rotating.
    root.location -= Vector(((low.x + high.x) / 2, (low.y + high.y) / 2, low.z))
    root.scale = (factor,) * 3
    root.location *= factor
    orientation = _object(application.collection, "Film Orientation / " + actor["name"])
    root.parent = orientation
    orientation.rotation_euler = tuple(map(math.radians, spec["rotation"]))
    pivot = _object(application.collection, "Film Trajectory / " + actor["name"])
    orientation.parent = pivot
    pivot.location = actor["location"]
    pivot.rotation_euler = tuple(map(math.radians, actor["rotation"]))
    pivot.scale = (actor["scale"],) * 3
    pivot["scenario_hero_id"] = actor["hero"]
    pivot["scenario_reference_task"] = spec["reference"]
    _motion(pivot, actor["keyframes"], fps, shot["frames"])
    return application, pivot


def build_shot(raw_recipe, *, production_id, shot_id, heroes=None):
    """Create one complete new scene or remove all new data on failure.

    This does not activate a new scene, spend, save a file or change job state.
    The command layer must bind and claim every hero result before calling it.
    """
    _main_thread()
    _identity(production_id)
    plan = validate_film_plan(raw_recipe)
    shot = next((item for item in plan["shots"] if item["id"] == shot_id), None)
    if shot is None:
        raise ValueError("Select a shot from the validated Film recipe")
    names = [item["name"] for item in shot["scene"]["objects"]]
    if len(set(names)) != len(names):
        raise ValueError("Shot placeholder names must be unique for unambiguous motion")
    sources = dict(heroes or {})
    needed = {actor["hero"] for actor in shot["actors"]}
    if set(sources) != needed or any(not isinstance(v, HeroSource) for v in sources.values()):
        raise ValueError("Select exactly one receipt-bound saved model for every shot hero")
    # Fail before any Blender mutation for missing/tampered/unsupported files.
    # Import rechecks the receipt again at use; preflight is not a TOCTOU exemption.
    for source in sources.values():
        model_application._read(source.result, source.path, static_only=False)
    previous = _snapshot()
    window = bpy.context.window
    original, layer = window.scene, window.view_layer
    result = None
    try:
        scene = bpy.data.scenes.new(f"Film / {shot['id']} / {shot['title']}")
        scene.render.fps, scene.render.fps_base = plan["fps"], 1
        scene.frame_start, scene.frame_end = 1, shot["frames"]
        scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
        scene.render.resolution_percentage = 100
        scene.render.use_sequencer = False
        scene["scenario_film_production_id"] = production_id
        scene["scenario_film_shot_id"] = shot_id
        scene["scenario_film_recipe_sha256"] = hashlib.sha256(
            json.dumps(plan, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        ).hexdigest()
        scene["scenario_film_shot"] = json.dumps(shot, allow_nan=False)
        window.scene = scene
        collection = _collection(scene, "Film Placeholders")
        placeholders, materials = {}, {}
        for spec in shot["scene"]["objects"]:
            key = tuple(_rgba(spec["color"]))
            if key not in materials:
                materials[key] = _material("Film Proxy", spec["color"])
            placeholders[spec["name"]] = _primitive(collection, spec, materials[key])
        if not any(
            s["type"] == "plane" and s["role"] == "environment" for s in shot["scene"]["objects"]
        ):
            ground = dict(
                name="Film Ground",
                type="plane",
                location=[0, 0, -0.08],
                rotation=[0, 0, 0],
                scale=[100, 100, 1],
                color=[0.045, 0.055, 0.075],
                role="environment",
                bevel=0,
            )
            _primitive(collection, ground, _material("Film Ground", ground["color"]))
        for moving in shot["motion"]:
            scale = next(
                s["scale"] for s in shot["scene"]["objects"] if s["name"] == moving["object"]
            )
            _motion(
                placeholders[moving["object"]],
                moving["keyframes"],
                plan["fps"],
                shot["frames"],
                baked_scale=scale,
            )
        rig = _collection(scene, "Film Camera and Lighting")
        camera, target = _camera(scene, rig, shot["scene"]["camera"], shot, plan["fps"])
        _lighting(scene, rig, shot["scene"])
        actors = tuple(
            _hero(
                scene,
                actor,
                plan["heroes"][actor["hero"]],
                sources[actor["hero"]],
                shot,
                plan["fps"],
            )
            for actor in shot["actors"]
        )
        scene.frame_set(1)
        bpy.context.view_layer.update()
        result = ShotScene(scene, camera, target, placeholders, actors)
    finally:
        window.scene, window.view_layer = original, layer
        if result is None:
            _rollback(previous)
    return result


def build_timeline(raw_recipe, *, production_id, shots):
    """Compose explicit matching shot scenes into a new editable scene-strip timeline."""
    _main_thread()
    _identity(production_id)
    plan = validate_film_plan(raw_recipe)
    digest = hashlib.sha256(
        json.dumps(plan, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()
    if not isinstance(shots, dict) or set(shots) != {shot["id"] for shot in plan["shots"]}:
        raise ValueError("Build and select every shot in this Film recipe")
    for shot in plan["shots"]:
        item = shots[shot["id"]]
        try:
            valid = (
                isinstance(item, ShotScene)
                and item.scene in tuple(bpy.data.scenes)
                and not item.scene.library
                and not item.scene.override_library
                and item.scene.get("scenario_film_production_id") == production_id
                and item.scene.get("scenario_film_shot_id") == shot["id"]
                and item.scene.get("scenario_film_recipe_sha256") == digest
                and item.scene.camera is not None
                and item.scene.render.fps == plan["fps"]
                and item.scene.render.fps_base == 1
                and (item.scene.frame_start, item.scene.frame_end) == (1, shot["frames"])
            )
        except ReferenceError:
            valid = False
        if not valid:
            raise ValueError("Choose matching live Film shot scenes with unchanged timing")
    previous = _snapshot()
    complete = False
    try:
        master = bpy.data.scenes.new("Film Timeline / " + plan["title"])
        master.render.fps, master.render.fps_base = plan["fps"], 1
        master.frame_start, master.frame_end = 1, plan["total_frames"]
        master.render.resolution_x, master.render.resolution_y = 1920, 1080
        master.render.resolution_percentage = 100
        master.render.use_sequencer = True
        master["scenario_film_production_id"] = production_id
        master["scenario_film_recipe_sha256"] = digest
        master["scenario_film_sequence_kind"] = "editable_shot_plan"
        editor = master.sequence_editor_create()
        for shot in plan["shots"]:
            strip = editor.strips.new_scene(
                shot["title"], shots[shot["id"]].scene, 1, shot["start_frame"]
            )
            strip.scene_input = "CAMERA"
            strip.frame_final_duration = shot["frames"]
            master.timeline_markers.new(shot["title"], frame=shot["start_frame"])
        complete = True
        return master
    finally:
        if not complete:
            _rollback(previous)
