# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Fuzz the bounded preflight of downloaded GLB results, ``inspect_glb``.

Any bytes either raise GLBError or return a glTF 2.0 document with no URI and no
nonfinite number anywhere, positive integer accessor counts within the limit, one
buffer that fits the binary chunk and, for a static import, no animation or skin.
"""

import json
import math
import struct
import sys

from samples import RIGGED_GLTF, STATIC_GLTF, glb
from support import DataProvider, json_value, split

from scenario.core.scene.glb import MAX_ACCESSOR_ENTRIES, GLBError, inspect_glb

PROVIDER = DataProvider
WORDS = ["asset", "version", "2.0", "scene", "scenes", "nodes", "buffers", "byteLength"]
WORDS += ["accessors", "count", "skins", "joints", "animations", "channels", "target", "node"]
WORDS += ["path", "rotation", "weights", "uri", "data:,"]


COUNTS = [1, 3, 10_000_000, 10_000_001, 2**31, 0, -1, True, 1.0, "1", None]
URIS = ["model.bin", "data:,", "", "../texture.png", "https://example.invalid/model.bin"]
LENGTHS = [4, 3, 5, 0, -1, "4", 4.0, None, True]


def nodes(value):
    """Every dict and list inside a document, the document included."""
    found, pending = [], [value]
    while pending:
        item = pending.pop()
        if isinstance(item, (dict, list)):
            found.append(item)
            pending.extend(item.values() if isinstance(item, dict) else item)
    return found


def document(fdp):
    """A valid static or rigged document with one to three hostile edits."""
    value = json.loads(json.dumps(STATIC_GLTF if fdp.ConsumeBool() else RIGGED_GLTF))
    for _ in range(fdp.ConsumeIntInRange(1, 3)):
        edit = fdp.ConsumeIntInRange(0, 5)
        target = fdp.PickValueInList(nodes(value))
        if edit == 0:
            accessors = fdp.ConsumeIntInRange(0, 3)
            value["accessors"] = [{"count": fdp.PickValueInList(COUNTS)} for _ in range(accessors)]
        elif edit == 1 and isinstance(target, dict):
            target["uri"] = fdp.PickValueInList(URIS)
        elif edit == 2:
            value["buffers"] = [{"byteLength": fdp.PickValueInList(LENGTHS)}]
        elif edit == 3 and isinstance(target, dict) and target:
            target[fdp.PickValueInList(sorted(target))] = json_value(fdp, WORDS, 2)
        elif edit == 4 and isinstance(target, list) and target:
            target[fdp.ConsumeIntInRange(0, len(target) - 1)] = json_value(fdp, WORDS, 2)
        elif edit == 5 and isinstance(target, dict) and target:
            del target[fdp.PickValueInList(sorted(target))]
    return value


def check(document, data, static_only):
    assert isinstance(document, dict)
    assert document["asset"]["version"] == "2.0"
    if static_only:
        assert not document.get("animations") and not document.get("skins")
    (json_length,) = struct.unpack_from("<I", data, 12)
    (binary_length,) = struct.unpack_from("<I", data, 20 + json_length)
    (buffer,) = document["buffers"]
    assert type(buffer["byteLength"]) is int and 0 <= binary_length - buffer["byteLength"] <= 3
    counts = [accessor["count"] for accessor in document.get("accessors", [])]
    assert all(type(count) is int and count >= 1 for count in counts)
    assert sum(counts) <= MAX_ACCESSOR_ENTRIES
    pending = [document]
    while pending:
        value = pending.pop()
        if isinstance(value, dict):
            assert "uri" not in value, "a URI reference passed the preflight"
            pending.extend(value.values())
        elif isinstance(value, list):
            pending.extend(value)
        else:
            assert not isinstance(value, float) or math.isfinite(value)


def TestOneInput(data):
    mode, rest = split(data)
    mode %= 3
    if mode < 2:
        candidate, static_only = rest, mode == 0
    else:
        fdp = PROVIDER(rest)
        static_only = fdp.ConsumeBool()
        text = json.dumps(document(fdp)).encode()
        candidate = glb(text, fdp.ConsumeBytes(fdp.ConsumeIntInRange(0, 12)))
    try:
        result = inspect_glb(candidate, static_only=static_only)
    except GLBError:
        return
    check(result, candidate, static_only)


if __name__ == "__main__":
    import atheris

    PROVIDER = atheris.FuzzedDataProvider
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
