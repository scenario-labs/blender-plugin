# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Bounded preflight for self-contained static GLB result imports."""

import json
import math
import struct

MAX_GLB_BYTES = 256 * 1024 * 1024
MAX_JSON_BYTES = 8 * 1024 * 1024
MAX_ACCESSOR_ENTRIES = 10_000_000


class GLBError(ValueError):
    """Keep the saved asset for another explicit import policy."""


def _reject_constant(_value):
    raise GLBError("Nonfinite JSON values are unsupported")


def inspect_glb(data):
    """Validate the container and policy; Blender still validates actual geometry.

    Layout: glTF 2.0 GLB specification, linked from docs/MESH_APPLICATION.md.
    This is deliberately not a complete glTF schema validator.
    """
    try:
        if not 28 <= len(data) <= MAX_GLB_BYTES:
            raise GLBError("GLB size exceeds the supported import limit")
        magic, version, size = struct.unpack_from("<4sII", data)
        if magic != b"glTF" or version != 2 or size != len(data):
            raise GLBError("Use a complete GLB 2.0 file")
        chunks, offset = [], 12
        while offset < size:
            length, kind = struct.unpack_from("<I4s", data, offset)
            offset += 8
            if length % 4 or offset + length > size:
                raise GLBError("Invalid GLB chunk bounds")
            chunks.append((kind, offset, length))
            offset += length
        if [chunk[0] for chunk in chunks] != [b"JSON", b"BIN\0"]:
            raise GLBError("Use one JSON chunk followed by one embedded binary buffer")
        _, start, length = chunks[0]
        if length > MAX_JSON_BYTES:
            raise GLBError("GLB description exceeds the supported import limit")
        document = json.loads(data[start : start + length], parse_constant=_reject_constant)
        if document["asset"]["version"] != "2.0":
            raise GLBError("Use glTF 2.0")
        if document.get("animations") or document.get("skins"):
            raise GLBError("Rigged or animated results require their own application policy")
        if len(document.get("scenes", [])) != 1 or document.get("scene", 0) != 0:
            raise GLBError("Choose a GLB with one model scene")
        if not 0 < len(document.get("nodes", [])) <= 10_000:
            raise GLBError("GLB node count exceeds the supported import limit")
        buffers = document["buffers"]
        if len(buffers) != 1 or type(buffers[0]["byteLength"]) is not int:
            raise GLBError("Use one embedded binary buffer")
        if not 0 <= chunks[1][2] - buffers[0]["byteLength"] <= 3:
            raise GLBError("The embedded buffer size does not match")
        counts = [accessor["count"] for accessor in document.get("accessors", [])]
        if any(type(value) is not int or value < 1 for value in counts):
            raise GLBError("Invalid accessor count")
        if sum(counts) > MAX_ACCESSOR_ENTRIES:
            raise GLBError("GLB geometry exceeds the synchronous import limit")
        pending = [document]
        while pending:
            value = pending.pop()
            if isinstance(value, dict):
                if "uri" in value:
                    raise GLBError("Use embedded buffers and images without URI references")
                pending.extend(value.values())
            elif isinstance(value, list):
                pending.extend(value)
            elif isinstance(value, float) and not math.isfinite(value):
                raise GLBError("Nonfinite GLB values are unsupported")
        return document
    except (KeyError, TypeError, ValueError, struct.error, RecursionError) as error:
        if isinstance(error, GLBError):
            raise
        raise GLBError("Malformed or unsupported GLB description") from None
