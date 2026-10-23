# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Helpers for tests that run inside `blender --background`."""

import importlib
import json
import pathlib
import struct
import sys
import tempfile
from contextlib import contextmanager
from unittest.mock import patch

import bpy
from mathutils import Matrix

ROOT = pathlib.Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures"
# OpenEXR chromaticities: red, green, blue and white CIE xy coordinates.
REC709 = (0.64, 0.33, 0.30, 0.60, 0.15, 0.06, 0.3127, 0.3290)
ACES_AP0 = (0.7347, 0.2653, 0.0, 1.0, 0.0001, -0.0770, 0.32168, 0.33767)
ACES_AP1 = (0.713, 0.293, 0.165, 0.830, 0.128, 0.044, 0.32168, 0.33767)


_PACKAGE = None
_INSTALLED = None


def configure(package, installed, profile):
    global _PACKAGE, _INSTALLED
    _PACKAGE, _INSTALLED = package, installed
    prefs = bpy.context.preferences.addons[package].preferences
    prefs.output_dir = str(profile / "output")
    prefs.api_key = prefs.api_secret = ""


def addon_name():
    if _PACKAGE is None:
        raise RuntimeError("Installed package not verified: use make test-blender")
    return _PACKAGE


def addon():
    return importlib.import_module(addon_name())


def submodule(path):
    module = importlib.import_module(f"{addon_name()}.{path}")
    if not pathlib.Path(module.__file__).resolve().is_relative_to(_INSTALLED):
        raise RuntimeError("Submodule is outside the verified installed package")
    return module


def reset_scene():
    bpy.ops.wm.read_homefile(use_empty=True)


# Blender 5.0 reports a background file as modified even right after reading it.
# From 5.1, a file read in the background starts unmarked, as on the desktop.
MARKS_OBSERVABLE = not bpy.app.background or bpy.app.version >= (5, 1, 0)


def assert_unmarked(test, message=None):
    """Check that the open file is not marked modified, where Blender can show it."""
    if MARKS_OBSERVABLE:
        test.assertFalse(bpy.data.is_dirty, message)


@contextmanager
def file_marks(test, *, clean=True):
    """Record the messages of the marks that flag the open file modified inside the block.

    Background Blender clears the modified flag only when it reads a file, so a
    test that checks a change marks the file must start unmarked (``clean``).
    The real mark still runs: callers also check ``bpy.data.is_dirty``.
    """
    if clean:
        assert_unmarked(test, "The fixture already marked the file modified")
    module = submodule("blender.file_state")
    marks = []
    mark = module.mark_modified

    def record(message):
        marks.append(message)
        return mark(message)

    with patch.object(module, "mark_modified", side_effect=record):
        yield marks


@contextmanager
def temp_credentials(key="fixture-key", secret="fixture-secret"):
    """Restore the exact incoming preference values, including on setup failure."""
    prefs = bpy.context.preferences.addons[addon_name()].preferences
    saved = prefs.api_key, prefs.api_secret
    try:
        prefs.api_key, prefs.api_secret = key, secret
        yield prefs
    finally:
        prefs.api_key, prefs.api_secret = saved


# Scene properties whose RNA update sends NC_SCENE | ND_FRAME (Blender 5.x
# rna_scene.cc). In the GUI, the window manager answers that notifier after the
# calling operator or timer returns with a frame update that runs
# frame_change_pre, even for a same-value write. Background mode never does.
FRAME_NOTIFYING = frozenset(
    {
        "frame_current",
        "frame_subframe",
        "frame_float",
        "frame_step",
        "use_preview_range",
        "frame_preview_start",
        "frame_preview_end",
        "lock_frame_selection_to_range",
        "show_subframe",
        "show_keys_from_selected_only",
        "render.frame_map_old",
        "render.frame_map_new",
    }
)


class RecordingStruct:
    """Forward to a real Blender struct and record attribute writes by dotted path.

    Nested non-ID structs are wrapped too; IDs, collections and methods are real.
    """

    def __init__(self, struct, writes, prefix=""):
        object.__setattr__(self, "_struct", struct)
        object.__setattr__(self, "_writes", writes)
        object.__setattr__(self, "_prefix", prefix)

    def __getattr__(self, name):
        value = getattr(self._struct, name)
        if isinstance(value, bpy.types.bpy_struct) and not isinstance(value, bpy.types.ID):
            return RecordingStruct(value, self._writes, f"{self._prefix}{name}.")
        return value

    def __setattr__(self, name, value):
        self._writes.append(f"{self._prefix}{name}")
        setattr(self._struct, name, value)


def recording_context(context, writes):
    """A capture context whose scene records writes; the window manager stays real."""
    from types import SimpleNamespace

    return SimpleNamespace(
        scene=RecordingStruct(context.scene, writes), window_manager=context.window_manager
    )


@contextmanager
def online_access(enabled):
    """Opt into a real Blender preference branch without leaving it enabled."""
    system = bpy.context.preferences.system
    saved = system.use_online_access
    try:
        system.use_online_access = enabled
        if bool(bpy.app.online_access) != enabled:
            raise RuntimeError("Blender command-line override prevents online-access testing")
        yield
    finally:
        system.use_online_access = saved


@contextmanager
def isolated_manager():
    """Use private job storage after state.reset(), restoring the previous manager.

    The runner starts offline, so tests must explicitly use online_access(True)
    for online branches and provide a synthetic service before starting workers.
    Keep runtime.paths patched too: ensure_manager refreshes an existing manager's
    paths and must never redirect the test back to the profile-wide registry.
    """
    runtime = submodule("blender.runtime")
    config = submodule("core.config")
    records = submodule("core.jobs.records")
    manager_module = submodule("core.jobs.manager")
    previous = runtime.state.manager
    with tempfile.TemporaryDirectory(prefix="scenario-test-jobs-") as directory:
        root = pathlib.Path(directory)
        paths = config.Paths(root / "state", root / "cache", root / "output")
        manager = manager_module.JobManager(records.JobRegistry(paths.registry_file).load(), paths)
        with patch.object(runtime, "paths", return_value=paths):
            runtime.state.manager = manager
            try:
                yield manager
            finally:
                manager.shutdown()
                manager.join(timeout=5)
                runtime.state.manager = previous
                if manager.has_active():
                    message = "Test job workers did not stop before storage cleanup"
                    original = sys.exception()
                    if original is None:
                        raise RuntimeError(message)
                    original.add_note(message)


def mcp_call(name, arguments, *, during=None):
    """Serve one installed tool call as local MCP does, without a socket.

    The request runs on a worker thread while this main thread pumps the server's
    queue, so deferred tools wait off the main thread as they do in Blender.
    `during(server, result)` runs after each pump. Returns the JSON-RPC response.
    """
    import time
    from concurrent.futures import ThreadPoolExecutor

    registry = submodule("blender.mcp_service").build_registry()
    server = submodule("mcp.server").McpServer("127.0.0.1", 0, registry, {}, timeout=5)
    message = {"id": 1, "method": "tools/call", "params": {"name": name, "arguments": arguments}}
    with ThreadPoolExecutor(max_workers=1) as worker:
        result = worker.submit(server.handle, message)
        deadline = time.monotonic() + 5
        while not result.done() and time.monotonic() < deadline:
            server.process_pending()
            if during is not None:
                during(server, result)
            time.sleep(0.001)
        return result.result(1)


def exr_attribute(name, kind, payload):
    return name + b"\0" + kind + b"\0" + struct.pack("<I", len(payload)) + payload


def scanline_exr(width=8, height=4, primaries=None, value=(4.0, 0.5, 0.25), extra=b""):
    """Uncompressed FLOAT B/G/R scanline OpenEXR, optionally declaring chromaticities.

    Written directly from the OpenEXR file layout so tests control every header
    attribute, unlike Blender's writer, which adds its own color metadata.
    ``extra`` adds encoded attributes such as other color declarations.
    """
    channels = b"".join(
        name + b"\0" + struct.pack("<iBBBBii", 2, 0, 0, 0, 0, 1, 1) for name in (b"B", b"G", b"R")
    )
    window = struct.pack("<iiii", 0, 0, width - 1, height - 1)
    declared = (
        b""
        if primaries is None
        else exr_attribute(b"chromaticities", b"chromaticities", struct.pack("<8f", *primaries))
    )
    header = (
        b"\x76\x2f\x31\x01"
        + struct.pack("<I", 2)
        + exr_attribute(b"channels", b"chlist", channels + b"\0")
        + declared
        + extra
        + exr_attribute(b"compression", b"compression", b"\0")
        + exr_attribute(b"dataWindow", b"box2i", window)
        + exr_attribute(b"displayWindow", b"box2i", window)
        + exr_attribute(b"lineOrder", b"lineOrder", b"\0")
        + exr_attribute(b"pixelAspectRatio", b"float", struct.pack("<f", 1.0))
        + exr_attribute(b"screenWindowCenter", b"v2f", bytes(8))
        + exr_attribute(b"screenWindowWidth", b"float", struct.pack("<f", 1.0))
        + b"\0"
    )
    red, green, blue = value
    line = b"".join(struct.pack("<f", channel) * width for channel in (blue, green, red))
    start = len(header) + height * 8
    table = b"".join(struct.pack("<Q", start + row * (len(line) + 8)) for row in range(height))
    blocks = b"".join(struct.pack("<ii", row, len(line)) + line for row in range(height))
    return header + table + blocks


def parts_glb(count=2):
    """First-party textured triangle instances with nested, named part transforms."""
    data = (FIXTURES / "synthetic/static-triangle.glb").read_bytes()
    length = struct.unpack_from("<I", data, 12)[0]
    document = json.loads(data[20 : 20 + length])
    document["nodes"] = [
        {
            "name": "Parts transform",
            "translation": [2, 0, 0],
            "children": list(range(1, count + 1)),
        },
        *[
            {"name": f"Panel {index + 1}", "mesh": 0, "translation": [index * 3, 0, 0]}
            for index in range(count)
        ],
    ]
    document["scenes"] = [{"nodes": [0]}]
    value = json.dumps(document).encode()
    value += b" " * (-len(value) % 4)
    tail = data[20 + length :]
    return (
        struct.pack("<4sIII4s", b"glTF", 2, 20 + len(value) + len(tail), len(value), b"JSON")
        + value
        + tail
    )


def cube_result_glb(*, parts=1, subdivide=0, scale=0.5, location=(0, 0, 3)):
    """A provider-style edit of a 2-unit cube, exported with the Edit 3D exporter.

    The cube's quads are split into `parts` meshes without UVs or materials, or
    subdivided as a remesh, then scaled and moved like a normalized result.
    """
    import bmesh

    objects = []
    for part in range(parts):
        mesh = bmesh.new()
        bmesh.ops.create_cube(mesh, size=2.0)
        if subdivide:
            bmesh.ops.subdivide_edges(mesh, edges=mesh.edges[:], cuts=subdivide, use_grid_fill=True)
        mesh.faces.ensure_lookup_table()
        others = [face for face in mesh.faces if face.index * parts // len(mesh.faces) != part]
        bmesh.ops.delete(mesh, geom=others, context="FACES")
        bmesh.ops.scale(mesh, vec=(scale, scale, scale), verts=mesh.verts)
        data = bpy.data.meshes.new("Cube result")
        mesh.to_mesh(data)
        mesh.free()
        obj = bpy.data.objects.new("Cube result", data)
        bpy.context.scene.collection.objects.link(obj)
        obj.location = location
        objects.append(obj)
    bpy.context.view_layer.update()
    with tempfile.TemporaryDirectory() as directory:
        path = pathlib.Path(directory) / "result.glb"
        submodule("blender.mesh_export").export_glb(bpy.context, objects, str(path))
        body = path.read_bytes()
    for obj in objects:
        data = obj.data
        bpy.data.objects.remove(obj)
        bpy.data.meshes.remove(data)
    return body


def centered_figure_glb(height=1.85, width=0.6, depth=0.4):
    """A box as tall as a person, centred on the origin as a provider delivers a real-size character.

    The feet are at -height / 2 in the file, so an import must still ground them.
    """
    import bmesh

    mesh = bmesh.new()
    bmesh.ops.create_cube(mesh, size=1.0)
    bmesh.ops.scale(mesh, vec=(width, depth, height), verts=mesh.verts)
    data = bpy.data.meshes.new("Figure")
    mesh.to_mesh(data)
    mesh.free()
    obj = bpy.data.objects.new("Figure", data)
    bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.update()
    with tempfile.TemporaryDirectory() as directory:
        path = pathlib.Path(directory) / "figure.glb"
        submodule("blender.mesh_export").export_glb(bpy.context, [obj], str(path))
        body = path.read_bytes()
    bpy.data.objects.remove(obj)
    bpy.data.meshes.remove(data)
    return body


def animated_glb(*, clips=2, morph=True, node_transform=False):
    """Add a two-bone skin, morph target and node clips to our first-party triangle."""
    original = (FIXTURES / "synthetic/static-triangle.glb").read_bytes()
    length = struct.unpack_from("<I", original, 12)[0]
    document = json.loads(original[20 : 20 + length])
    binary = bytearray(original[28 + length :])

    def accessor(values, fmt, kind, count, component=5126):
        binary.extend(b"\0" * (-len(binary) % 4))
        offset = len(binary)
        binary.extend(struct.pack("<" + fmt * len(values), *values))
        view = len(document["bufferViews"])
        document["bufferViews"].append(
            {"buffer": 0, "byteOffset": offset, "byteLength": len(binary) - offset}
        )
        index = len(document["accessors"])
        document["accessors"].append(
            {"bufferView": view, "componentType": component, "count": count, "type": kind}
        )
        return index

    primitive = document["meshes"][0]["primitives"][0]
    primitive["attributes"]["JOINTS_0"] = accessor([0, 0, 0, 0] * 3, "H", "VEC4", 3, 5123)
    primitive["attributes"]["WEIGHTS_0"] = accessor([1, 0, 0, 0] * 3, "f", "VEC4", 3)
    primitive["targets"] = [{"POSITION": accessor([0, 0, 1] * 3, "f", "VEC3", 3)}]
    document["meshes"][0]["weights"] = [0]
    document["nodes"] = [
        {"name": "Character", "children": [1, 2]},
        {"name": "Body", "mesh": 0, "skin": 0},
        {"name": "RootJoint", "children": [3]},
        {"name": "TipJoint", "translation": [0, 1, 0]},
    ]
    identity = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
    tip_inverse = identity.copy()
    tip_inverse[13] = -1
    document["skins"] = [
        {
            "joints": [2, 3],
            "skeleton": 2,
            "inverseBindMatrices": accessor(identity + tip_inverse, "f", "MAT4", 2),
        }
    ]
    times = accessor([0, 1], "f", "SCALAR", 2)
    document["accessors"][times].update(min=[0], max=[1])
    document["animations"] = []
    for index in range(clips):
        translations = accessor([0, 0, 0, (index + 1) * 2, 0, 0], "f", "VEC3", 2)
        weights = accessor([0, 1], "f", "SCALAR", 2)
        document["animations"].append(
            {
                "name": f"Move {index + 1}",
                "samplers": [
                    {"input": times, "output": translations},
                    {"input": times, "output": weights},
                ],
                "channels": [
                    {
                        "sampler": 0,
                        "target": {"node": 0 if node_transform else 2, "path": "translation"},
                    },
                    {"sampler": 1, "target": {"node": 1, "path": "weights"}},
                ],
            }
        )
    if not morph:
        primitive.pop("targets")
        document["meshes"][0].pop("weights")
        for clip in document["animations"]:
            clip["channels"] = clip["channels"][:1]
            clip["samplers"] = clip["samplers"][:1]
    document["buffers"][0]["byteLength"] = len(binary)
    binary.extend(b"\0" * (-len(binary) % 4))
    description = json.dumps(document).encode()
    description += b" " * (-len(description) % 4)
    return (
        struct.pack(
            "<4sIII4s", b"glTF", 2, 28 + len(description) + len(binary), len(description), b"JSON"
        )
        + description
        + struct.pack("<I4s", len(binary), b"BIN\0")
        + binary
    )


def skin_to_new_rig(scene, source, *, parent=True):
    """Skin every source vertex to a new one-bone rig, as Blender's Armature skin does."""
    rig = bpy.data.objects.new("Old rig", bpy.data.armatures.new("Old armature"))
    scene.collection.objects.link(rig)
    view_layer = bpy.context.view_layer
    active = view_layer.objects.active
    view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    try:
        bone = rig.data.edit_bones.new("Old bone")
        bone.head, bone.tail = (0, 0, 0), (0, 0, 1)
    finally:
        bpy.ops.object.mode_set(mode="OBJECT")
    view_layer.objects.active = active
    group = source.vertex_groups.new(name="Old bone")
    group.add(list(range(len(source.data.vertices))), 1.0, "REPLACE")
    modifier = source.modifiers.new("Old skin", "ARMATURE")
    modifier.object = rig
    modifier.use_deform_preserve_volume = True
    if parent:
        source.parent = rig
    view_layer.update()
    return rig


def several_sources(scene):
    """Three meshes for one export: different shapes, transforms, parents and collections.

    A cube with two materials under a rotated, scaled Empty; a quad strip with a
    pentagon in its own collection; an icosphere parented to the cube. Each has
    a "Source UV" layer. Returned in export order.
    """
    import math

    import bmesh

    def mesh(name, build):
        data = bpy.data.meshes.new(name)
        shape = bmesh.new()
        build(shape)
        shape.to_mesh(data)
        shape.free()
        layer = data.uv_layers.new(name="Source UV")
        for index, item in enumerate(layer.data):
            item.uv = (index / 100, 0.5)
        for suffix in ("A", "B"):
            data.materials.append(bpy.data.materials.new(f"{name} {suffix}"))
        for polygon in data.polygons:
            polygon.material_index = polygon.index % 2
        data.update()
        return data

    def strip(shape):
        row = [shape.verts.new((x, y, 0)) for y in (0, 1) for x in range(4)]
        for x in range(3):
            shape.faces.new((row[x], row[x + 1], row[x + 5], row[x + 4]))
        ring = [
            shape.verts.new((6 + math.cos(step * math.tau / 5), math.sin(step * math.tau / 5), 0))
            for step in range(5)
        ]
        shape.faces.new(ring)

    parent = bpy.data.objects.new("Several parent", None)
    scene.collection.objects.link(parent)
    parent.location, parent.rotation_euler, parent.scale = (40, -25, 12), (0.3, 0.1, 0.7), (2,) * 3
    cube = bpy.data.objects.new(
        "Several cube", mesh("Several cube", lambda shape: bmesh.ops.create_cube(shape, size=2))
    )
    scene.collection.objects.link(cube)
    cube.parent = parent
    cube.location, cube.rotation_euler, cube.scale = (2, 3, 4), (0.2, 0.3, 0.4), (1, 2, 3)
    collection = bpy.data.collections.new("Several collection")
    scene.collection.children.link(collection)
    flat = bpy.data.objects.new("Several strip", mesh("Several strip", strip))
    collection.objects.link(flat)
    flat.location, flat.rotation_euler, flat.scale = (-30, 8, -6), (0, 0.8, 0.2), (1, 2, 0.5)
    sphere = bpy.data.objects.new(
        "Several sphere",
        mesh(
            "Several sphere",
            lambda shape: bmesh.ops.create_icosphere(shape, subdivisions=1, radius=1.5),
        ),
    )
    scene.collection.objects.link(sphere)
    sphere.parent = cube
    sphere.location = (0, 0, 6)
    bpy.context.view_layer.update()
    return cube, flat, sphere


def several_source_result(
    scene, sources, path, change, *, extra=(), merge=False, finish=None, fmt="glb"
):
    """Write edited copies of `sources` as one result file, a GLB by default.

    Each copy keeps its source's world placement without a parent; `change(index,
    copy)` edits it, and `extra` lists other objects to export, such as a rig. Copies
    are made in reverse order, so the result lists them shuffled. `merge` joins
    them into one mesh, as a provider may; `finish(objects)` then moves them all.
    A GLB uses the Edit 3D exporter; `fmt` "obj" or "fbx" uses Blender's own
    exporter, writing an OBJ's MTL beside it. Returns the main file's bytes.
    """
    export = submodule("blender.mesh_export")
    bpy.context.view_layer.update()
    copies = []
    for index in reversed(range(len(sources))):
        source = sources[index]
        copy = source.copy()
        copy.data = source.data.copy()
        copy.name = f"Result {len(sources) - index}"
        scene.collection.objects.link(copy)
        copy.parent = None
        copy.matrix_world = source.matrix_world.copy()
        change(index, copy)
        copies.append(copy)
    bpy.context.view_layer.update()
    if merge:
        bpy.context.view_layer.objects.active = copies[0]
        for copy in copies:
            copy.select_set(True)
        with bpy.context.temp_override(
            active_object=copies[0],
            object=copies[0],
            selected_objects=copies,
            selected_editable_objects=copies,
        ):
            bpy.ops.object.join()
        copies = copies[:1]
    objects = [*copies, *extra]
    if finish is not None:
        finish(objects)
    bpy.context.view_layer.update()
    if fmt == "glb":
        export.export_glb(bpy.context, objects, str(path))
    else:
        layer = bpy.context.view_layer
        selected, active = list(bpy.context.selected_objects), layer.objects.active
        for obj in scene.objects:
            obj.select_set(obj in objects)
        layer.objects.active = objects[0]
        if fmt == "obj":
            bpy.ops.wm.obj_export(filepath=str(path), export_selected_objects=True)
        else:
            bpy.ops.export_scene.fbx(
                filepath=str(path),
                use_selection=True,
                add_leaf_bones=False,
                path_mode="COPY",
                embed_textures=True,
                bake_anim=False,
            )
        for obj in scene.objects:
            obj.select_set(obj in selected)
        layer.objects.active = active
    for obj in objects:
        data, kind = obj.data, obj.type
        bpy.data.objects.remove(obj)
        (bpy.data.meshes if kind == "MESH" else bpy.data.armatures).remove(data)
    bpy.context.view_layer.update()
    return pathlib.Path(path).read_bytes()


def normalize_objects(objects, size=1.0):
    """Bake world positions into the meshes, then fit them all to `size`, centred at the origin."""
    from mathutils import Matrix, Vector

    for obj in objects:
        obj.data.transform(obj.matrix_world)
        obj.matrix_world = Matrix()
    points = [vertex.co for obj in objects for vertex in obj.data.vertices]
    low = Vector([min(point[axis] for point in points) for axis in range(3)])
    high = Vector([max(point[axis] for point in points) for axis in range(3)])
    scale = size / max(high - low)
    for obj in objects:
        obj.data.transform(Matrix.Scale(scale, 4) @ Matrix.Translation(-(low + high) / 2))


# A three-bone chain: (name, parent, head, tail) in armature units, with an
# optional roll in radians as a fifth item.
CHAIN = (
    ("Hips", None, (0, 0, 1), (0, 0, 1.2)),
    ("Spine", "Hips", (0, 0, 1.2), (0, 0, 1.6)),
    ("Head", "Spine", (0, 0, 1.6), (0, 0.1, 1.9)),
)


def chain_rig(scene, name, bones=CHAIN, *, unit=1.0):
    """A new armature in `scene`, the window's scene, with bones scaled by `unit`."""
    rig = bpy.data.objects.new(name, bpy.data.armatures.new(name))
    scene.collection.objects.link(rig)
    view_layer = bpy.context.view_layer
    active = view_layer.objects.active
    view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    try:
        for bone, parent, head, tail, *roll in bones:
            edit = rig.data.edit_bones.new(bone)
            edit.head = [value * unit for value in head]
            edit.tail = [value * unit for value in tail]
            edit.roll = roll[0] if roll else 0.0
            if parent:
                edit.parent = rig.data.edit_bones[parent]
    finally:
        bpy.ops.object.mode_set(mode="OBJECT")
    view_layer.objects.active = active
    return rig


def skin_to_chain_rig(scene, source):
    """Skin source vertex N to chain bone N (the last bone takes any others)."""
    rig = chain_rig(scene, "Chain rig")
    for index, (name, *_) in enumerate(CHAIN):
        group = source.vertex_groups.new(name=name)
        count = len(source.data.vertices)
        group.add([i for i in range(count) if min(i, len(CHAIN) - 1) == index], 1.0, "REPLACE")
    source.modifiers.new("Chain skin", "ARMATURE").object = rig
    bpy.context.view_layer.update()
    return rig


def humanoid_bones(names, *, prefix="", height=1.0, arms_down=0.0, roll=0.0):
    """A standing humanoid facing -Y with the 22 slot bones of `names`, in slot order.

    Bones follow `scenario.core.scene.humanoid`: (name, parent, head, tail, roll)
    as `chain_rig` and `clip_glb` take them, at `height` times a 1.8 m figure,
    the arms lowered by `arms_down` radians from a T-pose and every bone rolled
    by `roll` radians.
    """
    import math

    h = height
    sag = (math.cos(arms_down), 0, -math.sin(arms_down))
    joints = {
        "hips": ((0, 0, 1.0), (0, 0, 1.1)),
        "spine": ((0, 0, 1.1), (0, 0, 1.25)),
        "chest": ((0, 0, 1.25), (0, 0, 1.4)),
        "upper_chest": ((0, 0, 1.4), (0, 0, 1.5)),
        "neck": ((0, 0, 1.5), (0, 0, 1.6)),
        "head": ((0, 0, 1.6), (0, 0, 1.8)),
    }
    for side, sign in (("l", 1), ("r", -1)):
        start = (sign * 0.18, 0, 1.45)
        joints[f"{side}_shoulder"] = ((sign * 0.05, 0, 1.45), start)
        for slot, length in (("arm", 0.27), ("forearm", 0.25), ("hand", 0.08)):
            end = (start[0] + sign * sag[0] * length, 0, start[2] + sag[2] * length)
            joints[f"{side}_{slot}"] = (start, end)
            start = end
        x = sign * 0.1
        joints[f"{side}_upleg"] = ((x, 0, 1.0), (x, 0, 0.55))
        joints[f"{side}_leg"] = ((x, 0, 0.55), (x, 0, 0.1))
        joints[f"{side}_foot"] = ((x, 0, 0.1), (x, -0.12, 0.02))
        joints[f"{side}_toe"] = ((x, -0.12, 0.02), (x, -0.18, 0.02))
    humanoid = submodule("core.scene.humanoid")
    mapped = dict(zip(humanoid.SLOTS, names, strict=True))
    bones = []
    for slot in humanoid.SLOTS:
        head, tail = joints[slot]
        parent = humanoid.PARENTS.get(slot)
        bones.append(
            (
                prefix + mapped[slot],
                prefix + mapped[parent] if parent else None,
                tuple(value * h for value in head),
                tuple(value * h for value in tail),
                roll,
            )
        )
    return tuple(bones)


def clip_glb(
    bones=CHAIN,
    *,
    unit=100.0,
    scale=0.01,
    clips=(1.0, 2.0),
    location=True,
    stretch=False,
    rotation=None,
    turn_object=True,
    still=(),
    carry=False,
    prop=None,
):
    """Export a returned animated character with Blender's glTF exporter.

    The armature has `unit` armature-space units per world unit under object scale
    `scale`, like a centimetre rig at 0.01. A `rotation` Euler turns the armature
    object while its bones turn back, so they keep the same world rest; without
    `turn_object` only the bones turn back. Clip N (one NLA track, `Clip N`) turns
    every bone not named in `still` about its X axis by half its amount in radians
    and, with `location`, moves the first such bone along its Y axis by its amount
    in world units, over 24 frames; `stretch` also scales it along its Y axis, or by
    `1 + amount * rate` on each axis when it is a tuple of three rates. The
    `still` bones stay unkeyed in the export. With `carry`, Clip N also moves the
    armature object by its amount along world X and turns it by a quarter of it
    in radians about Z, as files whose skin leaves the moving scene root out of
    its joints do. A triangle skinned to the first bone is included, and with
    `prop` an Empty hangs from that bone's tail. All scratch data is removed.
    """
    import math

    names = ("objects", "meshes", "armatures", "scenes", "actions", "collections")
    before = {name: set(getattr(bpy.data, name)) for name in names}
    window = bpy.context.window
    previous = window.scene, window.view_layer
    scene = bpy.data.scenes.new("Clip export fixture")
    scene.render.fps, scene.render.fps_base = 24, 1.0
    directory = tempfile.TemporaryDirectory()
    try:
        window.scene, window.view_layer = scene, scene.view_layers[0]
        rig = chain_rig(scene, "Armature", bones, unit=unit)
        rig.scale = (scale,) * 3
        mesh = bpy.data.meshes.new("Body")
        root = [value * unit for value in bones[0][2]]
        mesh.from_pydata([root, (root[0] + unit, root[1], root[2]), (0, 0, 0)], [], [(0, 1, 2)])
        if rotation is not None:
            back = rotation.to_matrix().to_4x4().inverted()
            rig.data.transform(back)
            mesh.transform(back)
            if turn_object:
                rig.rotation_euler = rotation
        body = bpy.data.objects.new("Body", mesh)
        scene.collection.objects.link(body)
        body.parent = rig
        body.vertex_groups.new(name=bones[0][0]).add([0, 1, 2], 1.0, "REPLACE")
        body.modifiers.new("Armature", "ARMATURE").object = rig
        if prop is not None:
            held = bpy.data.objects.new("Prop", None)
            scene.collection.objects.link(held)
            held.parent, held.parent_type, held.parent_bone = rig, "BONE", prop
        data = rig.animation_data_create()
        for index, amount in enumerate(clips, 1):
            action = bpy.data.actions.new(f"Clip {index}")
            data.action = action
            for frame, factor in ((1, 0.0), (25, amount)):
                keyed = (bone for bone in bones if bone[0] not in still)
                for number, (name, *_) in enumerate(keyed):
                    pose = rig.pose.bones[name]
                    pose.rotation_quaternion = (math.cos(factor / 4), math.sin(factor / 4), 0, 0)
                    pose.keyframe_insert("rotation_quaternion", frame=frame)
                    if location and number == 0:
                        pose.location = (0, factor * unit, 0)
                        pose.keyframe_insert("location", frame=frame)
                    if stretch and number == 0:
                        rates = (0, 0.5, 0) if stretch is True else stretch
                        pose.scale = [1 + factor * rate for rate in rates]
                        pose.keyframe_insert("scale", frame=frame)
                if carry:
                    rig.location = (factor, 0, 0)
                    rig.rotation_euler = (0, 0, factor / 4)
                    rig.keyframe_insert("location", frame=frame)
                    rig.keyframe_insert("rotation_euler", frame=frame)
            data.action = None
            track = data.nla_tracks.new()
            track.name = action.name
            track.strips.new(action.name, 1, action)
        for pose in rig.pose.bones:
            pose.location, pose.rotation_quaternion = (0, 0, 0), (1, 0, 0, 0)
            pose.scale = (1, 1, 1)
        if carry:
            rig.location, rig.rotation_euler = (0, 0, 0), (0, 0, 0)
        path = pathlib.Path(directory.name) / "clip.glb"
        # As above, only the window shows the scratch scene during export.
        bpy.ops.export_scene.gltf(
            filepath=str(path),
            use_active_scene=True,
            export_animations=bool(clips),
            export_animation_mode="NLA_TRACKS",
            # Otherwise every bone keeps at least one key.
            export_optimize_animation_keep_anim_armature=not still,
        )
        return path.read_bytes()
    finally:
        window.scene, window.view_layer = previous
        bpy.data.scenes.remove(scene)
        directory.cleanup()
        for name in names:
            values = getattr(bpy.data, name)
            for value in set(values) - before[name]:
                values.remove(value, do_unlink=True)


def deform_matrices(scene, rig, frames, *, world=False):
    """Each bone's armature-space deform matrix, pose times inverted rest, at each frame.

    Skinning moves a vertex by this matrix, so equal matrices move a mesh equally
    whatever each rig's bone orientations. With `world`, the matrices are in world
    space, so rigs whose objects are turned or scaled differently compare too. The
    scene must be the window's scene.
    """
    current = scene.frame_current
    deforms = {}
    for frame in frames:
        scene.frame_set(frame)
        outer = rig.matrix_world if world else Matrix.Identity(4)
        deforms[frame] = {
            bone.name: outer
            @ rig.pose.bones[bone.name].matrix
            @ bone.matrix_local.inverted()
            @ outer.inverted()
            for bone in rig.data.bones
        }
    scene.frame_set(current)
    return deforms


def clip_deforms(body, clip, frames, *, fps=24, world=False):
    """`deform_matrices` of a returned GLB's rig playing clip `clip`, imported as staging does.

    The rig is imported into a scratch scene at `fps` with the staging import
    options and removed with everything else the import created.
    """
    with _played_clip(body, clip, fps) as (scene, rig):
        return deform_matrices(scene, rig, frames, world=world)


def clip_heads(body, clip, frames, *, fps=24):
    """World head positions of a returned GLB's bones playing clip `clip`, by frame and bone.

    Imported like `clip_deforms`, so a clip that also moves the armature object counts.
    """
    with _played_clip(body, clip, fps) as (scene, rig):
        heads = {}
        for frame in frames:
            scene.frame_set(frame)
            heads[frame] = {bone.name: rig.matrix_world @ bone.head for bone in rig.pose.bones}
        return heads


@contextmanager
def _played_clip(body, clip, fps):
    names = (
        "objects",
        "meshes",
        "armatures",
        "scenes",
        "actions",
        "collections",
        "materials",
        "images",
    )
    before = {name: set(getattr(bpy.data, name)) for name in names}
    window = bpy.context.window
    previous = window.scene, window.view_layer
    scene = bpy.data.scenes.new("Clip reference fixture")
    scene.render.fps, scene.render.fps_base = fps, 1.0
    directory = tempfile.TemporaryDirectory()
    try:
        window.scene, window.view_layer = scene, scene.view_layers[0]
        path = pathlib.Path(directory.name) / "clip.glb"
        path.write_bytes(body)
        bpy.ops.import_scene.gltf(
            filepath=str(path),
            import_pack_images=True,
            import_select_created_objects=False,
            import_scene_extras=False,
            import_scene_as_collection=False,
            disable_bone_shape=True,
        )
        (rig,) = (
            obj for obj in set(bpy.data.objects) - before["objects"] if obj.type == "ARMATURE"
        )
        data = rig.animation_data
        for track in data.nla_tracks:
            track.mute = True
        (action,) = (
            item for item in set(bpy.data.actions) - before["actions"] if item.name == clip
        )
        data.action = action
        data.action_slot = action.slots[0]
        yield scene, rig
    finally:
        window.scene, window.view_layer = previous
        bpy.data.scenes.remove(scene)
        directory.cleanup()
        for name in names:
            values = getattr(bpy.data, name)
            for value in set(values) - before[name]:
                values.remove(value, do_unlink=True)


def textured_model_exports(directory, *, fps=24):
    """Export one textured, animated cube with Blender's own exporters.

    Returns paths of a binary FBX with an embedded texture, an FBX that names
    the texture by absolute path, an OBJ with its MTL, a separate glTF with its
    buffer, a binary mesh PLY and the PNG texture. All scratch data is removed.
    """
    import bmesh

    directory = pathlib.Path(directory)
    names = ("objects", "meshes", "materials", "images", "scenes", "actions", "collections")
    before = {name: set(getattr(bpy.data, name)) for name in names}
    window = bpy.context.window
    previous = window.scene, window.view_layer
    scene = bpy.data.scenes.new("Export fixture")
    scene.render.fps, scene.render.fps_base = fps, 1.0
    layer = scene.view_layers[0]
    try:
        window.scene, window.view_layer = scene, layer
        mesh = bpy.data.meshes.new("Fixture cube")
        shape = bmesh.new()
        shape.loops.layers.uv.new()
        bmesh.ops.create_cube(shape, size=2.0, calc_uvs=True)
        shape.to_mesh(mesh)
        shape.free()
        image = bpy.data.images.new("tex", width=4, height=4)
        image.pixels[:] = [0.75, 0.25, 0.125, 1.0] * 16
        image.file_format = "PNG"
        image.filepath_raw = str(directory / "tex.png")
        image.save()
        material = bpy.data.materials.new("Fixture material")
        material.use_nodes = True
        node = material.node_tree.nodes.new("ShaderNodeTexImage")
        node.image = image
        principled = material.node_tree.nodes["Principled BSDF"]
        material.node_tree.links.new(node.outputs["Color"], principled.inputs["Base Color"])
        mesh.materials.append(material)
        obj = bpy.data.objects.new("Fixture cube", mesh)
        scene.collection.objects.link(obj)
        obj.location = (0.0, 0.0, 0.0)
        obj.keyframe_insert("location", frame=1)
        obj.location = (2.0, 0.0, 0.0)
        obj.keyframe_insert("location", frame=fps)
        obj.location = (0.0, 0.0, 0.0)
        obj.select_set(True, view_layer=layer)
        layer.objects.active = obj
        paths = {
            "fbx": directory / "cube.fbx",
            "external_fbx": directory / "external.fbx",
            "obj": directory / "cube.obj",
            "mtl": directory / "cube.mtl",
            "gltf": directory / "cube.gltf",
            "bin": directory / "cube.bin",
            "ply": directory / "cube.ply",
            "png": directory / "tex.png",
        }
        # The window already shows the scratch scene. A context override as well
        # crashes the glTF exporter's depsgraph evaluation on Blender 5.1.
        bpy.ops.export_scene.fbx(
            filepath=str(paths["fbx"]),
            use_selection=True,
            path_mode="COPY",
            embed_textures=True,
        )
        bpy.ops.export_scene.fbx(
            filepath=str(paths["external_fbx"]),
            use_selection=True,
            path_mode="ABSOLUTE",
            embed_textures=False,
            bake_anim=False,
        )
        bpy.ops.wm.obj_export(filepath=str(paths["obj"]), export_selected_objects=True)
        bpy.ops.export_scene.gltf(
            filepath=str(paths["gltf"]),
            export_format="GLTF_SEPARATE",
            use_selection=True,
            use_active_scene=True,
            export_animations=False,
        )
        bpy.ops.wm.ply_export(
            filepath=str(paths["ply"]), export_selected_objects=True, ascii_format=False
        )
        return paths
    finally:
        window.scene, window.view_layer = previous
        bpy.data.scenes.remove(scene)
        for name in names:
            values = getattr(bpy.data, name)
            for value in set(values) - before[name]:
                values.remove(value, do_unlink=True)


SPLAT_PLY_PROPERTIES = (
    "x",
    "y",
    "z",
    "f_dc_0",
    "f_dc_1",
    "f_dc_2",
    "opacity",
    "scale_0",
    "scale_1",
    "scale_2",
)


def spz_bytes(points, *, version=3, scale_byte=96, alpha=255, color=(128, 128, 128), flags=0):
    """Synthetic SPZ with integer saved positions, 12 fractional bits and identity rotations.

    `flags` sets the header's antialiasing (0x1) and extension (0x2) bits; no
    extension record is written.
    """
    import gzip

    count = len(points)
    header = struct.pack("<IIIBBBB", 0x5053474E, version, count, 0, 12, flags, 0)
    body = bytearray()
    for point in points:
        for value in point:
            raw = (int(value) << 12) & 0xFFFFFF
            body += bytes((raw & 0xFF, (raw >> 8) & 0xFF, raw >> 16))
    body += bytes([alpha] * count) + bytes(color) * count + bytes([scale_byte] * 3 * count)
    rotation = b"\x00\x00\x00\xc0" if version == 3 else b"\x00\x00\x00"
    return gzip.compress(bytes(header + body) + rotation * count)


def splat_records(points, scale=0.6, rgba=(255, 0, 0, 255)):
    """.splat records: float32 position and linear scale, RGBA and a byte quaternion."""
    return b"".join(
        struct.pack("<3f3f4B4B", *point, scale, scale, scale, *rgba, 128, 128, 128, 255)
        for point in points
    )


def splat_ply_bytes(rows):
    """A binary 3DGS PLY: one row of ten floats per splat, in SPLAT_PLY_PROPERTIES order."""
    header = "ply\nformat binary_little_endian 1.0\n"
    header += f"element vertex {len(rows)}\n"
    header += "".join(f"property float {name}\n" for name in SPLAT_PLY_PROPERTIES)
    return (header + "end_header\n").encode() + b"".join(struct.pack("<10f", *row) for row in rows)


def draw_job_panels():
    """Draw the real Jobs header, Jobs and Generations panels into recording layouts.

    Drawing must not read job storage, so a store read fails the caller. Returns
    the three layouts and the rows Generations listed through its real
    draw_result.
    """
    from types import SimpleNamespace
    from unittest.mock import MagicMock

    panels = submodule("blender.panels")
    store = submodule("blender.runtime").state.job_store
    header, jobs, generations = MagicMock(), MagicMock(), MagicMock()
    with (
        patch.object(store, "get", side_effect=AssertionError("Store read in draw")),
        patch.object(store, "records", side_effect=AssertionError("Store read in draw")),
        patch.object(panels, "draw_result", wraps=panels.draw_result) as draw_result,
    ):
        panels.SCENARIO_PT_jobs.draw_header(SimpleNamespace(layout=header), bpy.context)
        panels.SCENARIO_PT_jobs.draw(SimpleNamespace(layout=jobs), bpy.context)
        panels.SCENARIO_PT_generations.draw(SimpleNamespace(layout=generations), bpy.context)
    return header, jobs, generations, [call.args[1] for call in draw_result.call_args_list]


def draw_in_studio(draw, width):
    """Call `draw` where Studio's real Jobs page draws its panel, `width` interface units wide.

    Studio's `draw_view` runs around it as the popup operator's `draw` calls it,
    with the width the operator passes to `invoke_popup`; only the panel body is
    replaced by `draw`.
    """
    from unittest.mock import MagicMock

    studio = submodule("blender.studio")
    view = bpy.context.window_manager.scenario_studio_view
    page = view.page
    view.page = "JOBS"
    try:
        with patch.object(studio, "draw_panel", lambda _layout, _context, _panel: draw()):
            studio.draw_view(MagicMock(), bpy.context, width=width)
    finally:
        view.page = page


def drawn_texts(*layouts):
    """Every `text` drawn anywhere under recording layouts, nested rows and boxes included."""
    return [
        call.kwargs["text"]
        for layout in layouts
        for call in layout.mock_calls
        if "text" in call.kwargs
    ]


def assert_finished_without_download(test, request_id):
    """Check a finished job whose text is read without a download after Inspect saved jobs.

    Prompt Spark, Translate and Blockout jobs keep the saved state `succeeded`.
    With Online Access off, the real panels must list the job in Generations,
    neither count nor draw it in Jobs and draw no offline line, and MCP
    `job_status` must report no delivery or offline hold. Returns the view and
    that status.
    """
    runtime = submodule("blender.runtime")
    panels = submodule("blender.panels")
    tools = submodule("mcp.tools_scenario")
    with online_access(False):
        test.assertEqual(bpy.ops.scenario.inspect_saved_jobs(), {"FINISHED"})
        view = runtime.state.model_jobs.views[request_id]
        header, jobs, generations, listed = draw_job_panels()
        status = tools.job_status({"job_id": request_id})
        offline = set(panels.SHARED_OFFLINE_TEXT.values())
        header.label.assert_called_once()
        # One comparison, so a regression reports every visible symptom at once.
        test.assertEqual(
            {
                "view": (view.meta["saved_state"], view.status, view.is_terminal),
                "header": header.label.call_args.kwargs["text"],
                "jobs_rows": jobs.box.call_count,
                "in_generations": any(row is view for row in listed),
                "offline_lines": offline & set(drawn_texts(header, jobs, generations)),
                "mcp": (
                    status["status"],
                    status["delivery_paused"],
                    status["delivery_active"],
                    status["delivery_offline"],
                ),
            },
            {
                "view": ("succeeded", "succeeded", True),
                "header": "Jobs",
                "jobs_rows": 0,
                "in_generations": True,
                "offline_lines": set(),
                "mcp": ("succeeded", True, False, False),
            },
        )
        jobs.label.assert_any_call(text="No job running", icon="CHECKMARK")
    return view, status


class LoopbackStorage:
    """A loopback stand-in for signed storage that streams a synthetic body slowly.

    `connect` replaces `http.client.HTTPSConnection` in the transfer module, so
    the installed downloader talks plain HTTP to 127.0.0.1 and nothing leaves
    the machine. The body is `size` zero bytes at about 3 MiB/s; `fast` sends the
    rest at once, and `silent_after` stops sending after that many bytes until
    the test stops the server. `streaming` is set once 1 MiB was sent and
    `closed` once a client closed its connection mid-body.
    """

    def __init__(self, size, *, silent_after=None, etag='"loopback-fixture"'):
        import http.server
        import threading

        owner = self
        self.size, self.silent_after, self.etag = size, silent_after, etag
        self.requests, self.hosts, self.threads = [], [], []
        self.stop, self.fast = threading.Event(), threading.Event()
        self.streaming, self.closed = threading.Event(), threading.Event()

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                owner.requests.append(self.path)
                self.send_response(200)
                self.send_header("Content-Length", str(owner.size))
                self.send_header("ETag", owner.etag)
                self.send_header("Connection", "close")
                self.end_headers()
                sent, chunk = 0, bytes(64 * 1024)
                try:
                    while sent < owner.size and not owner.stop.is_set():
                        if owner.silent_after is not None and sent >= owner.silent_after:
                            # Silent: hold the connection open without sending.
                            owner.stop.wait(30)
                            break
                        part = chunk[: owner.size - sent]
                        self.wfile.write(part)
                        sent += len(part)
                        if sent >= min(owner.size, 1024 * 1024):
                            owner.streaming.set()
                        if not owner.fast.is_set():
                            owner.fast.wait(0.02)
                except OSError:
                    owner.closed.set()

            def log_message(self, *args):
                pass

        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self._thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self._thread.start()

    @property
    def port(self):
        return self.server.server_address[1]

    def connect(self, host, *, timeout, **_):
        import http.client
        import threading

        self.hosts.append(host)
        self.threads.append(threading.current_thread().name)
        return http.client.HTTPConnection("127.0.0.1", self.port, timeout=timeout)

    def close(self):
        self.stop.set()
        self.server.shutdown()
        self.server.server_close()
        self._thread.join(5)
