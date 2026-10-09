# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Synthetic Gaussian splat files for bounded decoder tests; no provider data."""

import gzip
import math
import random
import struct

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


def splat_row(index):
    """Distinct finite 3DGS values for one synthetic point."""
    return {
        "x": index * 0.5,
        "y": 1.0 + index,
        "z": -2.0 * index,
        "f_dc_0": 1.0,
        "f_dc_1": -1.0,
        "f_dc_2": 0.0,
        "opacity": 0.0,
        "scale_0": math.log(0.1),
        "scale_1": math.log(0.2 + index),
        "scale_2": math.log(0.4 + index),
    }


def ply_bytes(
    rows,
    *,
    properties=None,
    fmt="binary_little_endian",
    elements=(),
    newline=b"\n",
    comments=("synthetic",),
):
    """PLY with one vertex element. `properties` lists (name, type) pairs."""
    properties = properties or [(name, "float") for name in SPLAT_PROPERTIES]
    codes = {"float": "f", "uchar": "B", "double": "d", "int": "i", "short": "h"}
    lines = [b"ply", f"format {fmt} 1.0".encode()]
    lines += [f"comment {text}".encode() for text in comments]
    lines.append(f"element vertex {len(rows)}".encode())
    lines += [f"property {kind} {name}".encode() for name, kind in properties]
    for name, count, extra in elements:
        lines.append(f"element {name} {count}".encode())
        lines += [line.encode() for line in extra]
    lines.append(b"end_header")
    body = bytearray()
    order = "<" if fmt != "binary_big_endian" else ">"
    for row in rows:
        for name, kind in properties:
            body += struct.pack(order + codes[kind], row.get(name, 0))
    return newline.join(lines) + newline + bytes(body)


def splat_record(position, scale, rgba, rotation=(128, 128, 128, 255)):
    return struct.pack("<3f3f4B4B", *position, *scale, *rgba, *rotation)


def spz_payload(count, *, version=2, sh_degree=0, fractional_bits=12, seed=1):
    """A gzip SPZ body with pseudo-random attribute bytes, built without per-point loops."""
    rotation = 3 if version < 3 else 4
    dimensions = {0: 0, 1: 3, 2: 8, 3: 15, 4: 24}[sh_degree]
    tile = random.Random(seed).randbytes(16384)
    size = count * (16 + rotation + 3 * dimensions)
    body = (tile * (size // len(tile) + 1))[:size]
    header = struct.pack("<IIIBBBB", 0x5053474E, version, count, sh_degree, fractional_bits, 0, 0)
    return gzip.compress(header + body, compresslevel=1)
