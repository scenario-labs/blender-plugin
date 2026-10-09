# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Bounded Gaussian splat snapshots decoded off Blender's main thread. No bpy.

Decoders read one saved file sequentially, in bounded chunks, and keep an evenly
strided subset of its points. The returned `SplatData` holds native-order float32
bytes in Blender's Z-up axes, so a main-thread builder can pass read-only
`floats()` views to buffer-based `foreach_set` without per-point Python work.
Blender has no Gaussian splat renderer: rotations, anisotropic scales and higher
spherical harmonics are not decoded, and the snapshot describes a point cloud.

Byte work uses C-level bytes slicing, `bytes.translate` lookup tables and
`array`; only float activations that need arithmetic run as comprehensions.
This keeps the decoders free of numpy, which the development lock does not
include and Blender 5.0 and 5.1+ bundle in different major versions.
"""

import math
import sys
import zlib
from array import array
from dataclasses import dataclass, field

MAX_SOURCE_POINTS = 20_000_000
MAX_KEPT_POINTS = 2_000_000
CHUNK_BYTES = 1 << 22
SH_C0 = 0.28209479177387814

# Saved coordinate conventions. OPENGL is right/up/back (RUB), the SPZ default when
# no coordinate-system extension is present (see `SplatData.extensions`). OPENCV is
# right/down/forward (RDF), the 3DGS PLY convention, which the reference .splat
# converter keeps. Providers can differ from these format conventions, so the
# caller chooses the axes for each reviewed import.
AXES = frozenset({"OPENGL", "OPENCV"})
FORMAT_AXES = {"spz": "OPENGL", "ply": "OPENCV", "splat": "OPENCV"}
MEDIA_FORMATS = {
    "model/spz": "spz",
    "model/ply": "ply",
    "application/x-ply": "ply",
    "model/splat": "splat",
}
SPLAT_RECORD_BYTES = 32
FLOATS = ("positions", "colors", "opacities", "radii")
_WIDTHS = {"positions": 3, "colors": 4, "opacities": 1, "radii": 1}
MAX_LOG_SCALE = 80.0
MAX_SCALE = math.exp(MAX_LOG_SCALE)
_NEGATE = bytes(value ^ 0x80 for value in range(256))
_SIGN_BYTE = 3 if sys.byteorder == "little" else 0


class SplatError(ValueError):
    """The saved splat is unsupported or invalid; it is left unchanged."""


class SplatCancelled(RuntimeError):
    """Splat preparation stopped at an explicit cancellation request."""


@dataclass(frozen=True)
class SplatOptions:
    """Reviewed decoding choices; the caller owns defaults and their approval."""

    max_points: int
    axes: str

    def __post_init__(self):
        if type(self.max_points) is not int or not 1 <= self.max_points <= MAX_KEPT_POINTS:
            raise ValueError("Keep between 1 and 2,000,000 splat points")
        if not isinstance(self.axes, str) or self.axes not in AXES:
            raise ValueError("Choose OPENGL or OPENCV splat axes")


@dataclass(frozen=True, eq=False)
class SplatData:
    """Immutable decoded points, ready for a main-thread Blender build.

    `positions` holds x, y, z in Blender axes; `colors` holds display-referred
    RGB in 0..1 with alpha equal to the opacity; `radii` is the median axis
    scale multiplied by sqrt(step) to compensate for thinning.

    `antialiased` and `extensions` copy an SPZ header's flags and are False for
    other formats. Extension records are not read; one can store positions in
    axes other than right/up/back, so an import must warn when `extensions` is
    set before it relies on the format's default axes.
    """

    format: str
    version: int | None
    axes: str
    count: int
    kept: int
    step: int
    positions: bytes = field(repr=False)
    colors: bytes = field(repr=False)
    opacities: bytes = field(repr=False)
    radii: bytes = field(repr=False)
    bounds: tuple[tuple[float, float, float], tuple[float, float, float]]
    antialiased: bool = False
    extensions: bool = False

    def __post_init__(self):
        if (
            self.format not in FORMAT_AXES
            or self.axes not in AXES
            or type(self.count) is not int
            or type(self.step) is not int
            or type(self.kept) is not int
            or not 1 <= self.count <= MAX_SOURCE_POINTS
            or not 1 <= self.step <= self.count
            or self.kept != -(-self.count // self.step)
            or self.kept > MAX_KEPT_POINTS
            or type(self.antialiased) is not bool
            or type(self.extensions) is not bool
            or (self.format != "spz" and (self.antialiased or self.extensions))
        ):
            raise ValueError("Invalid splat snapshot")
        for name in FLOATS:
            value = getattr(self, name)
            if type(value) is not bytes or len(value) != 4 * _WIDTHS[name] * self.kept:
                raise ValueError("Invalid splat snapshot arrays")
        bounds = self.bounds
        if not (
            isinstance(bounds, tuple)
            and len(bounds) == 2
            and all(isinstance(corner, tuple) and len(corner) == 3 for corner in bounds)
            and all(type(v) is float and math.isfinite(v) for corner in bounds for v in corner)
            and all(low <= high for low, high in zip(*bounds, strict=True))
        ):
            raise ValueError("Invalid splat snapshot bounds")

    def floats(self, name):
        """Read-only native float32 view for buffer-based `foreach_set`."""
        if name not in FLOATS:
            raise ValueError("Choose positions, colors, opacities or radii")
        return memoryview(getattr(self, name)).cast("f")


class Reader:
    """Exact sequential reads from a binary stream, checking cancellation per chunk."""

    def __init__(self, stream, *, cancel=None):
        self._stream = stream
        self._cancel = cancel
        self._pending = b""

    def check(self):
        if self._cancel is not None and self._cancel.is_set():
            raise SplatCancelled("Splat preparation cancelled")

    def _chunk(self, size):
        return self._stream.read(size)

    def read_some(self, size):
        """Return up to `size` bytes, or no bytes at the end of the stream."""
        self.check()
        if self._pending:
            data, self._pending = self._pending[:size], self._pending[size:]
            return data
        return self._chunk(size)

    def read(self, size):
        """Return exactly `size` bytes or fail as a truncated file."""
        parts, need = [], size
        while need:
            data = self.read_some(min(need, CHUNK_BYTES))
            if not data:
                raise SplatError("The saved splat file is truncated")
            parts.append(data)
            need -= len(data)
        return b"".join(parts)

    def skip(self, size):
        while size:
            size -= len(self.read(min(size, CHUNK_BYTES)))

    def unread(self, data):
        self._pending = bytes(data) + self._pending


class GzipReader(Reader):
    """Inflate one gzip member on demand, never more than the requested output."""

    def __init__(self, stream, *, cancel=None, prefix=b""):
        super().__init__(stream, cancel=cancel)
        self._inflate = zlib.decompressobj(zlib.MAX_WBITS | 16)
        self._input = prefix

    def _chunk(self, size):
        while not self._inflate.eof:
            if not self._input:
                self._input = self._stream.read(65536)
                if not self._input:
                    break
            try:
                data = self._inflate.decompress(self._input, size)
            except zlib.error:
                raise SplatError("The saved splat compression is damaged") from None
            self._input = self._inflate.unconsumed_tail
            if data:
                return data
            self.check()
        return b""


def plan(count, max_points):
    """Return (step, kept) for deterministic stride thinning of `count` points."""
    if type(count) is not int or not 1 <= count <= MAX_SOURCE_POINTS:
        raise SplatError("The splat point count is empty or exceeds 20,000,000")
    step = -(-count // max_points)
    return step, -(-count // step)


def kept_fields(reader, count, size, step, fields):
    """Read `count` contiguous `size`-byte records, keeping indices 0, step, 2*step...

    Only the `(offset, width)` fields are kept, each as contiguous bytes, so memory
    follows the kept points and needed columns rather than the file.
    """
    period = size * step
    out = [bytearray() for _ in fields]

    def keep(data):
        # Chunks hold whole records, so every field slice has one entry per kept record.
        kept = -(-len(data) // period)
        for buffer, (offset, width) in zip(out, fields, strict=True):
            if width == 1:
                buffer += data[offset::period]
                continue
            part = bytearray(kept * width)
            for index in range(width):
                part[index::width] = data[offset + index :: period]
            buffer += part

    if period <= CHUNK_BYTES:
        block = (CHUNK_BYTES // period) * period
        remaining = count * size
        while remaining:
            data = reader.read(min(remaining, block))
            remaining -= len(data)
            keep(data)
    else:
        for index in range(-(-count // step)):
            keep(reader.read(size))
            reader.skip(min(step - 1, count - index * step - 1) * size)
    return tuple(bytes(buffer) for buffer in out)


def native(data, typecode="f"):
    """An array from little-endian bytes in this interpreter's byte order."""
    values = array(typecode)
    values.frombytes(data)
    if sys.byteorder == "big":
        values.byteswap()
    return values


def finite(values):
    """Whether every float is finite; float32 sums cannot overflow at these counts."""
    return math.isfinite(sum(values))


def byte_table(function):
    """Four translate tables mapping a byte to native float32 bytes of function(byte)."""
    raw = array("f", [function(value) for value in range(256)]).tobytes()
    return tuple(bytes(raw[4 * value + index] for value in range(256)) for index in range(4))


def lookup(values, table):
    """Native float32 bytes of the tabulated value for every input byte."""
    out = bytearray(4 * len(values))
    for index in range(4):
        out[index::4] = values.translate(table[index])
    return bytes(out)


UNIT = byte_table(lambda value: value / 255.0)


def median3(a, b, c):
    if a > b:
        a, b = b, a
    return a if c < a else (b if c > b else c)


def packed(values):
    """Native float32 bytes of an iterable of numbers."""
    return array("f", values).tobytes()


def negate(data):
    """Flip the sign bit of native float32 bytes."""
    out = bytearray(data)
    out[_SIGN_BYTE::4] = data[_SIGN_BYTE::4].translate(_NEGATE)
    return bytes(out)


def interleave(parts):
    """Interleave equally long native float32 columns into rows."""
    width = 4 * len(parts)
    out = bytearray(len(parts[0]) * len(parts))
    for index, part in enumerate(parts):
        for offset in range(4):
            out[4 * index + offset :: width] = part[offset::4]
    return bytes(out)


def snapshot(
    fmt,
    version,
    axes,
    count,
    step,
    xyz,
    rgb,
    opacities,
    radii,
    *,
    antialiased=False,
    extensions=False,
):
    """Assemble an immutable snapshot from saved-axis native float32 columns."""
    x, y, z = xyz
    # OPENGL (x, y, z) is Blender (x, -z, y); OPENCV is Blender (x, z, -y).
    blender = (x, negate(z), y) if axes == "OPENGL" else (x, z, negate(y))
    values = [array("f", part) for part in blender]
    bounds = (tuple(min(v) for v in values), tuple(max(v) for v in values))
    return SplatData(
        format=fmt,
        version=version,
        axes=axes,
        count=count,
        kept=len(opacities) // 4,
        step=step,
        positions=interleave(blender),
        colors=interleave((*rgb, opacities)),
        opacities=opacities,
        radii=radii,
        bounds=bounds,
        antialiased=antialiased,
        extensions=extensions,
    )


def decode_splat(stream, *, options, size, cancel=None):
    """Decode a .splat file: 32-byte records of float32 position and linear scale,
    RGBA bytes and a byte quaternion. The file size must be a whole record count.

    Layout reference: https://github.com/antimatter15/splat/blob/main/convert.py
    """
    if type(size) is not int or size <= 0 or size % SPLAT_RECORD_BYTES:
        raise SplatError("A .splat file must contain whole 32-byte records")
    count = size // SPLAT_RECORD_BYTES
    step, _ = plan(count, options.max_points)
    reader = Reader(stream, cancel=cancel)
    # Float32 x, y, z and linear scales, then red, green, blue and alpha bytes.
    fields = [(4 * index, 4) for index in range(6)] + [(24 + index, 1) for index in range(4)]
    *numbers, red, green, blue, alpha = kept_fields(reader, count, SPLAT_RECORD_BYTES, step, fields)
    reader.check()
    values = [native(part) for part in numbers]
    if not all(map(finite, values)):
        raise SplatError("The .splat file contains non-finite values")
    density = math.sqrt(step)
    radii = packed(
        [
            (0.0 if value < 0.0 else (value if value < MAX_SCALE else MAX_SCALE)) * density
            for value in map(median3, *values[3:])
        ]
    )
    return snapshot(
        "splat",
        None,
        options.axes,
        count,
        step,
        tuple(part.tobytes() for part in values[:3]),
        tuple(lookup(channel, UNIT) for channel in (red, green, blue)),
        lookup(alpha, UNIT),
        radii,
    )


def decode(stream, media_type, *, options, size, cancel=None):
    """Decode one saved splat by its declared media type.

    Returns None for a mesh PLY (see `splat_ply.PlyHeader.classify`), so the
    caller can route it to a mesh importer; other non-splat PLY layouts fail.
    Unexpected parser failures fail closed as SplatError.
    """
    if not isinstance(options, SplatOptions):
        raise TypeError("Use reviewed splat options")
    fmt = MEDIA_FORMATS.get(media_type)
    if fmt is None:
        raise SplatError("Choose a saved SPZ, PLY or .splat result")
    try:
        if fmt == "spz":
            from .spz import decode_spz

            return decode_spz(stream, options=options, size=size, cancel=cancel)
        if fmt == "ply":
            from . import splat_ply

            reader = Reader(stream, cancel=cancel)
            header = splat_ply.read_header(reader)
            if header.classify() == "mesh":
                return None
            return splat_ply.decode(reader, header, options=options, size=size)
        return decode_splat(stream, options=options, size=size, cancel=cancel)
    except (SplatError, SplatCancelled):
        raise
    except (ValueError, OverflowError, IndexError, zlib.error):
        raise SplatError("The saved splat file is invalid") from None
