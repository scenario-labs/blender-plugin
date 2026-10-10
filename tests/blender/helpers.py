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
