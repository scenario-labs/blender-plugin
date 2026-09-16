# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Bounded container preflight; Blender must still decode and verify the image."""

import struct
import zlib
from dataclasses import dataclass

MAX_FILE_BYTES = 128 * 1024 * 1024
MAX_PIXELS = 32 * 1024 * 1024


class PanoramaError(ValueError):
    """The local image cannot safely serve as the requested panorama."""


@dataclass(frozen=True)
class PanoramaInfo:
    file_format: str
    width: int
    height: int
    hdr_capable: bool


def _dimensions(file_format, width, height):
    if width < 4 or height < 2 or width != height * 2 or width * height > MAX_PIXELS:
        raise PanoramaError("Use a 2:1 panorama within the supported pixel limit")
    return PanoramaInfo(file_format, width, height, file_format == "OPEN_EXR")


def _png(data):
    offset, info, has_data, ended = 8, None, False, False
    while offset + 12 <= len(data):
        size = struct.unpack_from(">I", data, offset)[0]
        kind = data[offset + 4 : offset + 8]
        end = offset + 12 + size
        if end > len(data):
            raise PanoramaError("PNG data is incomplete")
        payload = memoryview(data)[offset + 8 : end - 4]
        crc = struct.unpack_from(">I", data, end - 4)[0]
        if zlib.crc32(memoryview(data)[offset + 4 : end - 4]) != crc:
            raise PanoramaError("PNG integrity check failed")
        if info is None:
            if kind != b"IHDR" or size != 13:
                raise PanoramaError("PNG dimensions are unavailable")
            width, height, depth, color, compression, filtering, interlace = struct.unpack(
                ">IIBBBBB", payload
            )
            if (
                depth not in (8, 16)
                or color not in (2, 6)
                or compression
                or filtering
                or interlace > 1
            ):
                raise PanoramaError("Use a standard RGB or RGBA PNG panorama")
            info = _dimensions("PNG", width, height)
        elif kind == b"IHDR":
            raise PanoramaError("PNG has conflicting dimensions")
        elif kind in (b"acTL", b"cICP", b"mDCV", b"cLLI"):
            raise PanoramaError("Animated or HDR-metadata PNG panoramas are unsupported")
        elif kind == b"IDAT":
            has_data = True
        elif kind == b"IEND":
            if size or end != len(data):
                raise PanoramaError("PNG end marker is invalid")
            ended = True
            break
        offset = end
    if info is None or not has_data or not ended:
        raise PanoramaError("PNG data is incomplete")
    return info


def _exr(data):
    if len(data) < 9:
        raise PanoramaError("OpenEXR header is incomplete")
    version = struct.unpack_from("<I", data, 4)[0]
    # OpenEXR File Layout, Version Field: v2 + optional tiled (bit 9) and
    # long-name (bit 10) flags. Deep, multipart and unused flags fail closed.
    if version & 0xFF != 2 or version & ~0x602:
        raise PanoramaError("Use a single-part non-deep OpenEXR panorama")
    limit, offset, attributes = min(len(data), 1024 * 1024), 8, {}
    name_limit = 255 if version & 0x400 else 31
    while offset < limit:
        if data[offset] == 0:
            break
        fields = []
        for _ in range(2):
            end = data.find(b"\0", offset, min(offset + name_limit + 1, limit))
            if end < 0 or end == offset:
                raise PanoramaError("OpenEXR attribute header is invalid")
            fields.append(data[offset:end])
            offset = end + 1
        if offset + 4 > limit:
            raise PanoramaError("OpenEXR attribute header is incomplete")
        size = struct.unpack_from("<I", data, offset)[0]
        offset += 4
        if offset + size > limit or fields[0] in attributes:
            raise PanoramaError("OpenEXR header is oversized or conflicting")
        attributes[fields[0]] = (fields[1], memoryview(data)[offset : offset + size])
        offset += size
    else:
        raise PanoramaError("OpenEXR header is incomplete or oversized")
    window_type, window = attributes.get(b"dataWindow", (None, b""))
    display_type, display = attributes.get(b"displayWindow", (None, b""))
    if (
        window_type != b"box2i"
        or len(window) != 16
        or display_type != window_type
        or display != window
    ):
        raise PanoramaError("OpenEXR must have matching full data and display windows")
    if b"envmap" in attributes and attributes[b"envmap"] != (b"envmap", b"\0"):
        raise PanoramaError("Cubemap OpenEXR images are unsupported")
    x0, y0, x1, y1 = struct.unpack("<iiii", window)
    return _dimensions("OPEN_EXR", x1 - x0 + 1, y1 - y0 + 1)


def inspect_panorama(data):
    """Check actual PNG/EXR headers, never the filename or an HDR claim.

    HDR-capable means an OpenEXR container; it does not assert measured pixel
    range, seamless content or a verified cloud model's projection contract.
    """
    if not isinstance(data, bytes) or not data or len(data) > MAX_FILE_BYTES:
        raise PanoramaError("Panorama file is empty or exceeds the byte limit")
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return _png(data)
    if data.startswith(b"\x76\x2f\x31\x01"):
        return _exr(data)
    raise PanoramaError("Use a supported PNG or OpenEXR panorama")
