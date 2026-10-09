# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Bounded container preflight; Blender must still decode and verify the image."""

import re
import struct
import zlib
from dataclasses import dataclass, replace

MAX_FILE_BYTES = 128 * 1024 * 1024
MAX_PIXELS = 32 * 1024 * 1024
MAX_PNG_CHUNKS = 4096
# Every JPEG marker segment, before or between scans, counts. Blender keeps
# comment markers, and libjpeg walks its whole saved-marker list to append each
# one, so a flood of them costs quadratic main-thread time.
MAX_JPEG_SEGMENTS = 4096
# Each progressive scan makes libjpeg revisit every block of the frame, so a
# small file with thousands of scans can stall Blender's main thread. Typical
# encoders write at most about a dozen scans.
MAX_JPEG_SCANS = 64

# Saved media types offered for World application and the container their bytes
# must use. "image/aces" is a server label, not proof of ACES primaries.
WORLD_MEDIA_FORMATS = {
    "image/png": "PNG",
    "image/jpeg": "JPEG",
    "image/exr": "OPEN_EXR",
    "image/x-exr": "OPEN_EXR",
    "image/aces": "OPEN_EXR",
}
WORLD_MEDIA_TYPES = frozenset(WORLD_MEDIA_FORMATS)
_WORLD_MEDIA_LABELS = {
    "image/png": "PNG (LDR)",
    "image/jpeg": "JPEG (LDR)",
    "image/exr": "OpenEXR (float; ACES AP0 uses ACES2065-1)",
    "image/x-exr": "OpenEXR (float; ACES AP0 uses ACES2065-1)",
    "image/aces": "ACES-labelled OpenEXR (float, AP0 as ACES2065-1)",
}

# OpenEXR chromaticities: red, green, blue and white CIE xy coordinates.
_PRIMARIES = {
    "rec709": (0.64, 0.33, 0.30, 0.60, 0.15, 0.06, 0.3127, 0.3290),
    "aces_ap0": (0.7347, 0.2653, 0.0, 1.0, 0.0001, -0.0770, 0.32168, 0.33767),
}
_PRIMARY_TOLERANCE = 0.001
# OpenEXR colorInteropID values classified by the World preflight. Blender
# ignores many others, including the srgb_rec709_display it writes itself, so
# they are left to the decoded color space check.
_INTEROP_IDS = {b"lin_rec709_scene": "rec709", b"lin_ap0_scene": "aces_ap0"}

# ITU-T T.81 B.1.1.2 and B.1.1.5: after a scan header, entropy-coded data runs
# to the next marker. It stores a 0xFF data byte as FF00 and may contain
# restart markers (RST0-RST7), and fill bytes (0xFF) may precede any marker.
_JPEG_MARKER_AFTER_SCAN = re.compile(rb"\xff[^\x00\xd0-\xd7\xff]")
# ITU-T T.81 frame markers: baseline, extended sequential and progressive Huffman.
_JPEG_FRAMES = {0xC0, 0xC1, 0xC2}
# Lossless, hierarchical, arithmetic and reserved JPG frames fail closed.
_JPEG_UNSUPPORTED_FRAMES = {
    0xC3,
    0xC5,
    0xC6,
    0xC7,
    0xC8,
    0xC9,
    0xCA,
    0xCB,
    0xCD,
    0xCE,
    0xCF,
    0xDE,
    0xDF,
}


class PanoramaError(ValueError):
    """The local image cannot safely serve as the requested panorama."""


@dataclass(frozen=True)
class PanoramaInfo:
    file_format: str
    width: int
    height: int
    hdr_capable: bool
    # World preflight only: OpenEXR primaries declared by chromaticities,
    # acesImageContainerFlag or colorInteropID: None, "rec709" or "aces_ap0".
    chromaticities: str | None = None


def describe_world_media(media_type):
    """Return confirmation wording for a saved World media type without reading bytes."""
    return _WORLD_MEDIA_LABELS.get(media_type, "Unsupported media type")


def _dimensions(file_format, width, height, *, panorama=True):
    if panorama and (width < 4 or height < 2 or width != height * 2 or width * height > MAX_PIXELS):
        raise PanoramaError("Use a 2:1 panorama within the supported pixel limit")
    if width < 1 or height < 1 or width * height > MAX_PIXELS:
        raise PanoramaError("Use an image within the supported pixel limit")
    return PanoramaInfo(file_format, width, height, file_format == "OPEN_EXR")


def _png(data, *, panorama=True):
    offset, info, has_data, ended = 8, None, False, False
    chunks = 0
    while offset + 12 <= len(data):
        # Bound per-chunk main-thread work independently of file/pixel size.
        # Count IDAT too, so empty data chunks cannot bypass the same budget.
        if chunks >= MAX_PNG_CHUNKS:
            raise PanoramaError("PNG exceeds the supported chunk limit")
        chunks += 1
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
                or color not in ((2, 6) if panorama else (0, 2, 6))
                or compression
                or filtering
                or interlace > 1
            ):
                if panorama:
                    raise PanoramaError("Use a standard RGB or RGBA PNG panorama")
                raise PanoramaError("Use an 8- or 16-bit grayscale, RGB or RGBA PNG image")
            info = _dimensions("PNG", width, height, panorama=panorama)
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


def _exr(data, *, panorama=True):
    if len(data) < 9:
        raise PanoramaError("OpenEXR header is incomplete")
    version = struct.unpack_from("<I", data, 4)[0]
    # OpenEXR File Layout: v2 + optional long-name (bit 10) flag. This
    # initial slice accepts scanline files; tiled/deep/multipart fail closed.
    if version & 0xFF != 2 or version & ~0x402:
        raise PanoramaError("Use a single-part non-deep scanline OpenEXR panorama")
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
    info = _dimensions("OPEN_EXR", x1 - x0 + 1, y1 - y0 + 1, panorama=panorama)
    if panorama:
        info = replace(info, chromaticities=_primaries(attributes))
    _exr_chunks(data, offset + 1, attributes, info.height, y0)
    return info


def _primaries(attributes):
    # Blender 5.0-5.2 select ACES2065-1 for AP0 chromaticities or an ACES
    # container flag (SMPTE ST 2065-4), honour some colorInteropID values and
    # decode other chromaticities as linear Rec.709. Classify these declarations
    # and refuse other primaries or conflicts, which would mis-tint lighting.
    declared = set()
    kind, value = attributes.get(b"chromaticities", (None, b""))
    if kind is not None:
        if kind != b"chromaticities" or len(value) != 32:
            raise PanoramaError("OpenEXR color primaries are invalid")
        values = struct.unpack("<8f", value)
        matches = [
            name
            for name, expected in _PRIMARIES.items()
            if all(
                abs(actual - wanted) <= _PRIMARY_TOLERANCE
                for actual, wanted in zip(values, expected, strict=True)
            )
        ]
        if not matches:
            raise PanoramaError("Use Rec.709 or ACES AP0 primaries for an OpenEXR panorama")
        declared.add(matches[0])
    kind, value = attributes.get(b"acesImageContainerFlag", (None, b""))
    if kind is not None:
        if kind != b"int" or len(value) != 4:
            raise PanoramaError("OpenEXR color primaries are invalid")
        # Blender treats only 1 as an ACES container, whose primaries are AP0.
        if struct.unpack("<i", value)[0] == 1:
            declared.add("aces_ap0")
    kind, value = attributes.get(b"colorInteropID", (None, b""))
    if kind is not None:
        if kind != b"string":
            raise PanoramaError("OpenEXR color primaries are invalid")
        if bytes(value) in _INTEROP_IDS:
            declared.add(_INTEROP_IDS[bytes(value)])
    if len(declared) > 1:
        raise PanoramaError("OpenEXR color declarations conflict")
    return declared.pop() if declared else None


def _exr_chunks(data, start, attributes, height, y0):
    # OpenEXR File Layout: scanline offsets are ordered by increasing y,
    # regardless of physical block order. Each block stores y, size, payload.
    compression_type, compression = attributes.get(b"compression", (None, b""))
    lines_per_chunk = (1, 1, 1, 16, 32, 16, 32, 32, 32, 256)
    if (
        compression_type != b"compression"
        or len(compression) != 1
        or compression[0] >= len(lines_per_chunk)
    ):
        raise PanoramaError("OpenEXR compression is unsupported")
    lines = lines_per_chunk[compression[0]]
    count = (height + lines - 1) // lines
    if b"type" in attributes and attributes[b"type"] != (b"string", b"scanlineimage"):
        raise PanoramaError("OpenEXR image layout is unsupported")
    if b"chunkCount" in attributes and attributes[b"chunkCount"] != (
        b"int",
        struct.pack("<i", count),
    ):
        raise PanoramaError("OpenEXR chunk count conflicts with its dimensions")
    table_end = start + count * 8
    if table_end > len(data):
        raise PanoramaError("OpenEXR offset table is incomplete")
    ranges = []
    for index in range(count):
        chunk = struct.unpack_from("<Q", data, start + index * 8)[0]
        if chunk < table_end or chunk + 8 > len(data):
            raise PanoramaError("OpenEXR chunk offset is invalid")
        y, size = struct.unpack_from("<ii", data, chunk)
        end = chunk + 8 + size
        if y != y0 + index * lines or size <= 0 or end > len(data):
            raise PanoramaError("OpenEXR pixel block is incomplete or invalid")
        ranges.append((chunk, end))
    end = table_end
    for chunk, chunk_end in sorted(ranges):
        if chunk != end:
            raise PanoramaError("OpenEXR pixel blocks overlap or contain gaps")
        end = chunk_end
    if end != len(data):
        raise PanoramaError("OpenEXR has unexpected trailing data")


def _exif_orientation(payload):
    # EXIF 2.32 (CIPA DC-008) APP1: "Exif\0\0", a TIFF 6.0 header, then IFD0
    # entries of tag, type, count and a 4-byte value. Read only Orientation
    # (0x0112, one SHORT) inside this segment; unreadable metadata fails closed.
    tiff = payload[6:]
    if len(tiff) < 8 or tiff[:2] not in (b"II", b"MM"):
        raise PanoramaError("JPEG EXIF metadata is invalid")
    order = "<" if tiff[:2] == b"II" else ">"
    magic, ifd = struct.unpack_from(order + "HI", tiff, 2)
    if magic != 42 or ifd < 8 or ifd + 2 > len(tiff):
        raise PanoramaError("JPEG EXIF metadata is invalid")
    count = struct.unpack_from(order + "H", tiff, ifd)[0]
    if ifd + 2 + count * 12 > len(tiff):
        raise PanoramaError("JPEG EXIF metadata is invalid")
    for index in range(count):
        tag, kind, number, value = struct.unpack_from(order + "HHIH", tiff, ifd + 2 + index * 12)
        if tag == 0x0112:
            if kind != 3 or number != 1:
                raise PanoramaError("JPEG EXIF metadata is invalid")
            return value
    return 1


def _jpeg(data):
    # ITU-T T.81 Annex B: marker segments precede the first scan and may sit
    # between later scans. A small file can declare billions of pixels, so read
    # only the frame header before Blender allocates a decoded buffer, and
    # charge every marker segment, before or after the first scan, to one
    # budget. Tables, entropy-coded data, color transforms and APPn metadata
    # other than EXIF orientation stay Blender's.
    offset, info, exif, marker, segments, scans = 2, None, False, None, 0, 0
    while True:
        if scans:
            # Find the marker that ends this entropy-coded data (or segment).
            match = _JPEG_MARKER_AFTER_SCAN.search(data, offset)
            # libjpeg conceals an empty or truncated scan with gray pixels;
            # requiring scan data and the end-of-image marker as the final
            # bytes catches simple truncation, not every malformed scan.
            if match is None or (marker == 0xDA and match.start() == offset):
                raise PanoramaError("JPEG data is incomplete or has trailing bytes")
            offset = match.start()
            if data[offset + 1] == 0xD9:
                if match.end() != len(data):
                    raise PanoramaError("JPEG data is incomplete or has trailing bytes")
                return info
        segments += 1
        if segments > MAX_JPEG_SEGMENTS:
            raise PanoramaError("JPEG exceeds the supported segment limit")
        if offset + 4 > len(data) or data[offset] != 0xFF:
            raise PanoramaError("JPEG header is incomplete or invalid")
        marker = data[offset + 1]
        size = struct.unpack_from(">H", data, offset + 2)[0]
        end = offset + 2 + size
        # Accept no fill bytes, standalone markers or reserved codes before the
        # first scan, nor SOI or reserved codes later; libjpeg also rejects
        # reserved markers.
        if marker < 0xC0 or 0xD0 <= marker <= 0xD9 or marker == 0xFF or size < 2:
            raise PanoramaError("JPEG header is incomplete or invalid")
        if end > len(data):
            raise PanoramaError("JPEG header is incomplete or invalid")
        if marker == 0xDA:
            if info is None:
                raise PanoramaError("JPEG dimensions are unavailable")
            scans += 1
            if scans > MAX_JPEG_SCANS:
                raise PanoramaError("JPEG exceeds the supported scan limit")
        if marker == 0xE1 and data.startswith(b"Exif\0\0", offset + 4, end):
            if exif:
                raise PanoramaError("JPEG has conflicting EXIF metadata")
            exif = True
            # Blender 5.0-5.2 ignore EXIF orientation, so a rotated or mirrored
            # panorama would become a World in its stored pixel order.
            if _exif_orientation(data[offset + 4 : end]) != 1:
                raise PanoramaError("EXIF-rotated or mirrored JPEG panoramas are unsupported")
        if marker in _JPEG_UNSUPPORTED_FRAMES:
            raise PanoramaError("Use a baseline or progressive JPEG panorama")
        if marker in _JPEG_FRAMES:
            if info is not None:
                raise PanoramaError("JPEG has conflicting frame headers")
            if size < 8:
                raise PanoramaError("JPEG frame header is invalid")
            precision, height, width, components = struct.unpack_from(">BHHB", data, offset + 4)
            if size != 8 + 3 * components:
                raise PanoramaError("JPEG frame header is invalid")
            if precision != 8 or components != 3:
                raise PanoramaError("Use a standard 8-bit color JPEG panorama")
            info = _dimensions("JPEG", width, height)
        offset = end


def inspect_panorama(data):
    """Check actual PNG/JPEG/EXR headers, never the filename or an HDR claim.

    HDR-capable means an OpenEXR container; it does not assert measured pixel
    range, seamless content or a verified cloud model's projection contract.
    PNG and JPEG are LDR. Blender remains the decoder for every format.
    """
    if not isinstance(data, bytes) or not data or len(data) > MAX_FILE_BYTES:
        raise PanoramaError("Panorama file is empty or exceeds the byte limit")
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return _png(data)
    if data.startswith(b"\xff\xd8"):
        return _jpeg(data)
    if data.startswith(b"\x76\x2f\x31\x01"):
        return _exr(data)
    raise PanoramaError("Use a supported PNG, JPEG or OpenEXR panorama")


def inspect_image(data):
    """The same bounded PNG/scanline-EXR preflight, without panorama aspect rules."""
    if not isinstance(data, bytes) or not data or len(data) > MAX_FILE_BYTES:
        raise PanoramaError("Image file is empty or exceeds the byte limit")
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return _png(data, panorama=False)
    if data.startswith(b"\x76\x2f\x31\x01"):
        return _exr(data, panorama=False)
    raise PanoramaError(
        "Automatic application supports grayscale/RGB/RGBA PNG and scanline OpenEXR images"
    )
