# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""SPZ Gaussian splats (Niantic's compressed format, returned by Marble and HY World). No bpy.

Versions 1 to 3 are one gzip stream: a 16-byte header (magic "NGSP", version, point
count, SH degree, fractional bits, flags, reserved), then one block per attribute for
all points in fixed order: positions, alphas, colours (the SH DC term), log scales,
rotations and spherical harmonics. Version 2 stores positions as signed 24-bit fixed
point; version 1 stored float16 and is rejected rather than misread. Version 3 changed
only the rotation encoding, which is skipped. Version 4 starts with a plaintext NGSP
header followed by ZSTD streams; Python 3.11 and 3.13 have no ZSTD decoder, so it is
rejected and the saved file is kept. Reference: https://github.com/nianticlabs/spz
(README, extensions/README.md and src/cc/load-spz.cc). Coordinates are stored
right/up/back (OPENGL) unless an extension declares otherwise. Extension records
follow the spherical harmonics and are not read; one of them
(SPZ_ADOBE_coordinate_system) can store positions in other axes. The snapshot keeps
the header's extension and antialiasing flags so a reviewed import can warn.
"""

import gzip
import math
import os
import struct
from array import array

from .splats import (
    MAX_KEPT_POINTS,
    SH_C0,
    UNIT,
    GzipReader,
    SplatCancelled,
    SplatError,
    SplatOptions,
    byte_table,
    kept_fields,
    lookup,
    median3,
    native,
    packed,
    plan,
    snapshot,
)

MAGIC = 0x5053474E  # "NGSP"
COLOR_SCALE = 0.15
FLAG_ANTIALIASED = 0x1
FLAG_HAS_EXTENSIONS = 0x2
# The reference loader allows SH degree 4. The compressed-size bound is borrowed from
# its v4 (NGSP) path: at most 1024x compression of 9-byte position records. Its gzip
# path bounds the count by the inflated bytes instead. The 23 fractional bits are this
# release's own limit, as is the 20,000,000-point bound in `splats.plan`.
MAX_SH_DEGREE = 4
MAX_FRACTIONAL_BITS = 23
MAX_COMPRESSION_RATIO = 1024
MIN_BYTES_PER_POINT = 9
_KEPT = "; the saved file is kept"
_SH_DIMENSIONS = {0: 0, 1: 3, 2: 8, 3: 15, 4: 24}
_SIGN = bytes(0xFF if value & 0x80 else 0 for value in range(256))
_INT32 = "i" if array("i").itemsize == 4 else "l"
_COLOR = byte_table(
    lambda value: min(1.0, max(0.0, 0.5 + SH_C0 * ((value / 255.0 - 0.5) / COLOR_SCALE)))
)


class SpzError(SplatError):
    pass


def sniff_spz(path):
    """True when a gzip stream starts with the SPZ magic (a splat saved as .bin)."""
    try:
        with gzip.open(str(path), "rb") as handle:
            head = handle.read(4)
    except (OSError, EOFError, ValueError):
        return False
    return len(head) == 4 and struct.unpack("<I", head)[0] == MAGIC


def _fixed(values, scale):
    """Native float32 bytes of signed 24-bit little-endian fixed-point values."""
    high = values[2::3]
    out = bytearray(4 * len(high))
    out[0::4] = values[0::3]
    out[1::4] = values[1::3]
    out[2::4] = high
    out[3::4] = high.translate(_SIGN)
    return packed([value * scale for value in native(out, _INT32)])


def decode_spz(stream, *, options, size=None, cancel=None):
    """Decode SPZ v2/v3 from a binary stream into a bounded `SplatData`.

    Only the position, alpha, colour and scale blocks are inflated, chunk by chunk;
    rotations, spherical harmonics and any extension records are neither decoded
    nor validated. The header's antialiasing and extension flags are kept on the
    snapshot. `size` is the compressed byte count when known.
    """
    if cancel is not None and cancel.is_set():
        raise SplatCancelled("Splat preparation cancelled")
    prefix = b""
    while len(prefix) < 4:
        data = stream.read(4 - len(prefix))
        if not data:
            break
        prefix += data
    if prefix == b"NGSP":
        raise SpzError("SPZ v4 (ZSTD) cannot be decoded in this release" + _KEPT)
    if prefix[:2] != b"\x1f\x8b":
        raise SpzError("Not an SPZ file")
    reader = GzipReader(stream, cancel=cancel, prefix=prefix)
    magic, version, count, sh_degree, fractional_bits, flags, _reserved = struct.unpack(
        "<IIIBBBB", reader.read(16)
    )
    if magic != MAGIC:
        raise SpzError("Not an SPZ file")
    if version == 1:
        raise SpzError("SPZ v1 (float16 positions) is not supported" + _KEPT)
    if version not in (2, 3):
        raise SpzError("Only SPZ versions 2 and 3 can be decoded" + _KEPT)
    if sh_degree > MAX_SH_DEGREE or fractional_bits > MAX_FRACTIONAL_BITS:
        raise SpzError("The SPZ header has an unsupported layout")
    if size is not None and count > size * MAX_COMPRESSION_RATIO // MIN_BYTES_PER_POINT:
        raise SpzError("The SPZ point count exceeds its compressed size")
    step, _ = plan(count, options.max_points)
    # Blocks for every point: x, y, z, then alpha, then colour bytes, then log scales.
    positions = kept_fields(reader, count, 9, step, ((0, 3), (3, 3), (6, 3)))
    (alphas,) = kept_fields(reader, count, 1, step, ((0, 1),))
    colors = kept_fields(reader, count, 3, step, ((0, 1), (1, 1), (2, 1)))
    scales = kept_fields(reader, count, 3, step, ((0, 1), (1, 1), (2, 1)))
    reader.check()
    scale = 1.0 / (1 << fractional_bits)
    density = math.sqrt(step)
    radius = byte_table(lambda value: math.exp(value / 16.0 - 10.0) * density)
    return snapshot(
        "spz",
        version,
        options.axes,
        count,
        step,
        tuple(_fixed(values, scale) for values in positions),
        tuple(lookup(channel, _COLOR) for channel in colors),
        lookup(alphas, UNIT),
        lookup(bytes(map(median3, *scales)), radius),
        antialiased=bool(flags & FLAG_ANTIALIASED),
        extensions=bool(flags & FLAG_HAS_EXTENSIONS),
    )


def read_spz(path, max_points=None):
    """Prototype wrapper: decode an .spz file into Python lists.

    Returns `count`, `kept`, `step`, `version`, `positions` [(x, y, z)] in the file's
    Y-up axes, `colors` [(r, g, b)], `alphas` and `scales` (median world scale per
    point). `max_points` keeps every n-th point; at most 2,000,000 points are kept.
    """
    limit = min(max_points or MAX_KEPT_POINTS, MAX_KEPT_POINTS)
    with open(str(path), "rb") as handle:
        data = decode_spz(
            handle,
            options=SplatOptions(limit, "OPENGL"),
            size=os.fstat(handle.fileno()).st_size,
        )
    # OPENGL decoding gives Blender (x, -z, y); undo it to return file axes.
    xyz = data.floats("positions").tolist()
    rgba = data.floats("colors").tolist()
    density = math.sqrt(data.step)
    return {
        "count": data.count,
        "kept": data.kept,
        "step": data.step,
        "version": data.version,
        "positions": [(xyz[i], xyz[i + 2], -xyz[i + 1]) for i in range(0, len(xyz), 3)],
        "colors": [tuple(rgba[i : i + 3]) for i in range(0, len(rgba), 4)],
        "alphas": data.floats("opacities").tolist(),
        "scales": [radius / density for radius in data.floats("radii").tolist()],
    }


def y_up_to_z_up(position):
    """SPZ files are Y-up (glTF convention); Blender is Z-up."""
    x, y, z = position
    return (x, -z, y)


def write_spz(
    path, positions, colors, alphas=None, scales=None, fractional_bits=12, version=2, sh_degree=0
):
    """Encode a minimal SPZ (version 2 or 3, identity rotations, zero SH). Used by tests."""
    if version not in (2, 3) or sh_degree not in _SH_DIMENSIONS:
        raise ValueError("Write SPZ version 2 or 3 with a supported SH degree")
    count = len(positions)
    alphas = alphas or [1.0] * count
    scales = scales or [0.01] * count
    out = bytearray(
        struct.pack("<IIIBBBB", MAGIC, version, count, sh_degree, fractional_bits, 0, 0)
    )
    scale = float(1 << fractional_bits)
    for x, y, z in positions:
        for v in (x, y, z):
            raw = int(round(v * scale)) & 0xFFFFFF
            out += bytes((raw & 0xFF, (raw >> 8) & 0xFF, (raw >> 16) & 0xFF))
    out += bytes(int(round(min(1.0, max(0.0, a)) * 255)) for a in alphas)
    for r, g, b in colors:
        for v in (r, g, b):
            sh0 = (min(1.0, max(0.0, v)) - 0.5) / SH_C0
            out.append(int(round(min(1.0, max(0.0, sh0 * COLOR_SCALE + 0.5)) * 255)))
    for s in scales:
        byte = int(round((math.log(max(1e-6, s)) + 10.0) * 16.0))
        out += bytes((min(255, max(0, byte)),) * 3)
    # Version 3 packs the largest component's index (w = 3) in the top two bits.
    out += bytes(count * 3) if version == 2 else b"\x00\x00\x00\xc0" * count
    out += b"\x80" * (count * 3 * _SH_DIMENSIONS[sh_degree])
    with gzip.open(str(path), "wb") as handle:
        handle.write(bytes(out))
    return path
