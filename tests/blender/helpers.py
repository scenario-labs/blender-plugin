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
