# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Static GLB bounds and self-contained import policy."""

import json
import struct
from pathlib import Path

import pytest

from scenario.core.scene.glb import MAX_ACCESSOR_ENTRIES, GLBError, inspect_glb

FIXTURE = Path(__file__).parents[1] / "fixtures/synthetic/static-triangle.glb"


def modified(change):
    data = FIXTURE.read_bytes()
    length = struct.unpack_from("<I", data, 12)[0]
    document = json.loads(data[20 : 20 + length])
    change(document)
    value = json.dumps(document).encode()
    value += b" " * (-len(value) % 4)
    tail = data[20 + length :]
    return (
        struct.pack("<4sIII4s", b"glTF", 2, 20 + len(value) + len(tail), len(value), b"JSON")
        + value
        + tail
    )


def test_textured_static_hierarchy_passes():
    result = inspect_glb(FIXTURE.read_bytes())
    assert result["nodes"][0]["children"] == [1]
    assert result["images"][0]["mimeType"] == "image/png"


@pytest.mark.parametrize(
    "mutation",
    [
        lambda d: d["buffers"][0].update(uri="https://example.invalid/model.bin"),
        lambda d: d["images"][0].update(uri="../another.png"),
        lambda d: d.update(animations=[{}]),
        lambda d: d.update(skins=[{}]),
        lambda d: d["scenes"].append({"nodes": [0]}),
        lambda d: d["accessors"][0].update(count=MAX_ACCESSOR_ENTRIES + 1),
        lambda d: d["accessors"][0].update(count=True),
        lambda d: d["buffers"][0].update(byteLength=1),
        lambda d: d.update(nodes=[]),
        lambda d: d["nodes"][0].update(matrix=[float("nan")] * 16),
    ],
)
def test_unsupported_dependencies_and_allocation_bounds_are_rejected(mutation):
    with pytest.raises(GLBError):
        inspect_glb(modified(mutation))


@pytest.mark.parametrize(
    "data", [b"glTF", b"x" * 32, FIXTURE.read_bytes()[:-1], FIXTURE.read_bytes() + b"extra"]
)
def test_incomplete_or_malformed_container_is_rejected(data):
    with pytest.raises(GLBError):
        inspect_glb(data)


def test_new_group_policy_allows_bounded_skins_and_node_animation():
    data = modified(
        lambda d: d.update(
            skins=[{"joints": [0]}],
            animations=[{"channels": [{"target": {"node": 0, "path": "translation"}}]}],
        )
    )
    assert inspect_glb(data, static_only=False)["skins"]
    with pytest.raises(GLBError, match="own application policy"):
        inspect_glb(data)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda d: d.update(animations=[{}] * 129),
        lambda d: d.update(skins=[{}] * 129),
        lambda d: d.update(skins=[{"joints": [0] * 10001}]),
        lambda d: d.update(skins=[{"joints": [True]}]),
        lambda d: d.update(skins=[{"joints": [999]}]),
        lambda d: d.update(animations=[{"channels": [{"target": {"node": 0, "path": "pointer"}}]}]),
        lambda d: d["images"][0].update(uri="../external.png"),
    ],
)
def test_dynamic_policy_keeps_resource_and_animation_bounds(mutation):
    with pytest.raises(GLBError):
        inspect_glb(modified(mutation), static_only=False)
