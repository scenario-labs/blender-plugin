# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Bounded PLY header classification and 3D Gaussian splat decoding. No bpy.

A splat PLY is binary little-endian with a first `vertex` element of scalar
properties that include float32 x, y, z, f_dc_0..2, opacity and scale_0..2, and
no faces. A mesh PLY, for a separate importer, has a non-empty first `vertex`
element with scalar x, y and z and none of the Gaussian splat property names.
Every other layout fails closed, including splats with other encodings and the
compressed splat PLY (a `chunk` element and a `packed_position` vertex property).
Opacity is stored before its sigmoid, scales as natural logarithms and colour as
the SH DC term; coordinates follow the 3DGS right/down/forward (OPENCV) convention.
"""

import math
import re
from dataclasses import dataclass

from .splats import (
    MAX_LOG_SCALE,
    SH_C0,
    SplatError,
    finite,
    kept_fields,
    median3,
    native,
    packed,
    plan,
    snapshot,
)

MAX_HEADER_BYTES = 65536
FORMATS = frozenset({"ascii", "binary_little_endian", "binary_big_endian"})
SCALARS = {
    "char": 1,
    "int8": 1,
    "uchar": 1,
    "uint8": 1,
    "short": 2,
    "int16": 2,
    "ushort": 2,
    "uint16": 2,
    "int": 4,
    "int32": 4,
    "uint": 4,
    "uint32": 4,
    "float": 4,
    "float32": 4,
    "double": 8,
    "float64": 8,
}
_INTEGERS = frozenset(name for name in SCALARS if "float" not in name and name != "double")
SPLAT_PROPERTIES = (
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
_NAME = re.compile(r"[!-~]{1,128}")
_COUNT = re.compile(r"[0-9]{1,10}")
# Vertex properties of 3D Gaussian splat exports; a mesh PLY has none of them.
_SPLAT_NAME = re.compile(r"f_dc_[0-9]+|f_rest_[0-9]+|opacity|scale_[0-9]+|rot_[0-9]+")
_KEPT = "; the saved file is kept"


@dataclass(frozen=True)
class PlyElement:
    name: str
    count: int
    # (name, list count type or None, value type)
    properties: tuple[tuple[str, str | None, str], ...]


@dataclass(frozen=True)
class PlyHeader:
    format: str
    elements: tuple[PlyElement, ...]
    length: int

    @property
    def splat(self):
        """Whether the PLY carries the Gaussian splat properties this decoder reads."""
        vertex = self.elements[0] if self.elements else None
        if self.format != "binary_little_endian" or vertex is None or vertex.name != "vertex":
            return False
        types = {name: kind for name, listed, kind in vertex.properties if listed is None}
        return (
            vertex.count >= 1
            and len(types) == len(vertex.properties)
            and all(types.get(name) in ("float", "float32") for name in SPLAT_PROPERTIES)
            and not any(item.name == "face" and item.count for item in self.elements)
        )

    def classify(self):
        """Return "splat" or "mesh"; any other PLY layout raises SplatError."""
        if self.splat:
            return "splat"
        names = {
            name
            for item in self.elements
            if item.name == "vertex"
            for name, _, _ in item.properties
        }
        # PlayCanvas compressed PLY: per-chunk bounds and packed vertex words.
        if "packed_position" in names:
            raise SplatError("Compressed splat PLY files are not supported" + _KEPT)
        if any(_SPLAT_NAME.fullmatch(name) for name in names):
            raise SplatError("This Gaussian splat PLY layout is not supported" + _KEPT)
        vertex = self.elements[0]
        scalars = {name for name, listed, _ in vertex.properties if listed is None}
        if vertex.name != "vertex" or vertex.count < 1 or not {"x", "y", "z"} <= scalars:
            raise SplatError("Unsupported PLY layout" + _KEPT)
        return "mesh"


def read_header(reader):
    """Parse a PLY header of at most 64 KiB; the reader is left at the body."""
    buffer, start, lines = bytearray(), 0, []
    while True:
        newline = buffer.find(b"\n", start)
        if newline < 0:
            if len(buffer) >= MAX_HEADER_BYTES:
                raise SplatError("The PLY header exceeds 64 KiB")
            data = reader.read_some(min(4096, MAX_HEADER_BYTES - len(buffer)))
            if not data:
                raise SplatError("The PLY header is incomplete")
            buffer += data
            continue
        line = bytes(buffer[start:newline]).rstrip(b"\r")
        start = newline + 1
        lines.append(line)
        if line.strip() == b"end_header":
            break
    reader.unread(buffer[start:])
    try:
        text = [line.decode("ascii").split() for line in lines]
    except UnicodeDecodeError:
        raise SplatError("The PLY header is not ASCII") from None
    return _parse(text, start)


def _parse(lines, length):
    if lines[0] != ["ply"]:
        raise SplatError("Not a PLY file")
    fmt, elements = None, []
    for words in lines[1:-1]:
        keyword = words[0] if words else "comment"
        if keyword in ("comment", "obj_info"):
            continue
        if keyword == "format" and fmt is None and len(words) == 3:
            if words[1] not in FORMATS or words[2] != "1.0":
                raise SplatError("Unsupported PLY format")
            fmt = words[1]
        elif keyword == "element" and len(words) == 3 and _COUNT.fullmatch(words[2]):
            if not _NAME.fullmatch(words[1]) or int(words[2]) > 2**31 - 1:
                raise SplatError("Invalid PLY element")
            elements.append((words[1], int(words[2]), []))
        elif keyword == "property" and elements:
            properties = elements[-1][2]
            if len(words) == 3 and words[1] in SCALARS:
                properties.append((words[2], None, words[1]))
            elif len(words) == 5 and words[1] == "list" and words[2] in _INTEGERS:
                if words[3] not in SCALARS:
                    raise SplatError("Invalid PLY list property")
                properties.append((words[4], words[2], words[3]))
            else:
                raise SplatError("Invalid PLY property")
            if not _NAME.fullmatch(properties[-1][0]) or len(
                {name for name, _, _ in properties}
            ) != len(properties):
                raise SplatError("Invalid PLY property name")
        else:
            raise SplatError("Unsupported PLY header line")
    if fmt is None or not elements:
        raise SplatError("The PLY header has no format or elements")
    return PlyHeader(
        fmt,
        tuple(PlyElement(name, count, tuple(items)) for name, count, items in elements),
        length,
    )


def _sigmoid(value):
    return 1.0 / (1.0 + math.exp(-value)) if value > -MAX_LOG_SCALE else 0.0


def _channel(values):
    return packed(
        [
            0.0 if (color := 0.5 + SH_C0 * value) < 0.0 else (1.0 if color > 1.0 else color)
            for value in values
        ]
    )


def _radius(a, b, c):
    value = median3(a, b, c)
    if value > MAX_LOG_SCALE:
        value = MAX_LOG_SCALE
    elif value < -MAX_LOG_SCALE:
        value = -MAX_LOG_SCALE
    return math.exp(value)


def decode(reader, header, *, options, size=None):
    """Decode the vertex rows of a splat PLY after `read_header`.

    Rows are read in bounded chunks and thinned by stride; later elements are not
    read. `size` is the whole file's byte count when known.
    """
    if not header.splat:
        raise SplatError("This PLY has no Gaussian splat data")
    vertex = header.elements[0]
    offsets, stride = {}, 0
    for name, _, kind in vertex.properties:
        offsets[name] = stride
        stride += SCALARS[kind]
    count = vertex.count
    step, _ = plan(count, options.max_points)
    if size is not None and header.length + count * stride > size:
        raise SplatError("The saved splat file is truncated")
    columns = kept_fields(
        reader, count, stride, step, [(offsets[name], 4) for name in SPLAT_PROPERTIES]
    )
    reader.check()
    values = {name: native(part) for name, part in zip(SPLAT_PROPERTIES, columns, strict=True)}
    if not all(map(finite, values.values())):
        raise SplatError("The PLY splat contains non-finite values")
    density = math.sqrt(step)
    radii = map(_radius, values["scale_0"], values["scale_1"], values["scale_2"])
    return snapshot(
        "ply",
        None,
        options.axes,
        count,
        step,
        tuple(values[name].tobytes() for name in ("x", "y", "z")),
        tuple(_channel(values[f"f_dc_{channel}"]) for channel in range(3)),
        packed([_sigmoid(value) for value in values["opacity"]]),
        packed([radius * density for radius in radii]),
    )
