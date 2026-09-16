# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Container preflight contracts; actual decoding is covered by native fixtures."""

import struct
import zlib

import pytest

from scenario.core.scene import panorama


def chunk(kind, payload=b""):
    body = kind + payload
    return struct.pack(">I", len(payload)) + body + struct.pack(">I", zlib.crc32(body))


def png(width=4, height=2, depth=8, color=6, extra=b""):
    header = struct.pack(">IIBBBBB", width, height, depth, color, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + extra
        + chunk(b"IDAT", b"fixture")
        + chunk(b"IEND")
    )


def attribute(name, kind, payload):
    return name + b"\0" + kind + b"\0" + struct.pack("<I", len(payload)) + payload


def exr(width=4, height=2, version=2, extra=b"", display=None):
    window = struct.pack("<iiii", 0, 0, width - 1, height - 1)
    return (
        b"\x76\x2f\x31\x01"
        + struct.pack("<I", version)
        + attribute(b"dataWindow", b"box2i", window)
        + attribute(b"displayWindow", b"box2i", display if display is not None else window)
        + extra
        + b"\0"
    )


@pytest.mark.parametrize("depth", [8, 16])
@pytest.mark.parametrize("color", [2, 6])
def test_standard_png_is_ldr_container(depth, color):
    assert panorama.inspect_panorama(png(depth=depth, color=color)) == panorama.PanoramaInfo(
        "PNG", 4, 2, False
    )


@pytest.mark.parametrize("version", [2, 0x202, 0x402, 0x602])
def test_supported_single_part_exr_flags(version):
    assert panorama.inspect_panorama(exr(version=version)) == panorama.PanoramaInfo(
        "OPEN_EXR", 4, 2, True
    )


@pytest.mark.parametrize(
    "data",
    [
        b"",
        b".exr",
        b"\x89PNG\r\n\x1a\n",
        b"\x76\x2f\x31\x01",
        png()[:-1],
        png() + b"trailing",
        exr()[:-1],
    ],
)
def test_missing_truncated_and_unknown_containers_rejected(data):
    with pytest.raises(panorama.PanoramaError):
        panorama.inspect_panorama(data)


@pytest.mark.parametrize("make", [png, exr])
@pytest.mark.parametrize("size", [(1, 1), (2, 1), (4, 3), (0, 2), (16384, 8192)])
def test_dimensions_bounded_before_decode(make, size):
    with pytest.raises(panorama.PanoramaError, match="2:1"):
        panorama.inspect_panorama(make(*size))


def test_byte_limit(monkeypatch):
    monkeypatch.setattr(panorama, "MAX_FILE_BYTES", 8)
    with pytest.raises(panorama.PanoramaError, match="byte limit"):
        panorama.inspect_panorama(png())


def test_png_crc_corruption_rejected():
    data = bytearray(png())
    data[20] ^= 1
    with pytest.raises(panorama.PanoramaError, match="integrity"):
        panorama.inspect_panorama(bytes(data))


@pytest.mark.parametrize("kind", [b"acTL", b"cICP", b"mDCV", b"cLLI"])
def test_png_animation_and_hdr_metadata_fail_closed(kind):
    with pytest.raises(panorama.PanoramaError, match="unsupported"):
        panorama.inspect_panorama(png(extra=chunk(kind)))


@pytest.mark.parametrize("depth,color", [(1, 6), (32, 6), (8, 0), (8, 3)])
def test_unsupported_png_encoding(depth, color):
    with pytest.raises(panorama.PanoramaError, match="RGB"):
        panorama.inspect_panorama(png(depth=depth, color=color))


def test_duplicate_png_dimensions_rejected():
    with pytest.raises(panorama.PanoramaError, match="conflicting"):
        panorama.inspect_panorama(png(extra=chunk(b"IHDR", b"duplicate")))


@pytest.mark.parametrize("version", [1, 3, 0x802, 0x1002, 0x2002, 0x102])
def test_unsupported_exr_version_flags(version):
    with pytest.raises(panorama.PanoramaError, match="non-deep"):
        panorama.inspect_panorama(exr(version=version))


def test_cropped_exr_rejected():
    with pytest.raises(panorama.PanoramaError, match="matching"):
        panorama.inspect_panorama(exr(display=struct.pack("<iiii", 0, 0, 7, 3)))


def test_exr_latlong_metadata_accepted_but_cube_rejected():
    assert panorama.inspect_panorama(exr(extra=attribute(b"envmap", b"envmap", b"\0"))).hdr_capable
    with pytest.raises(panorama.PanoramaError, match="Cubemap"):
        panorama.inspect_panorama(exr(extra=attribute(b"envmap", b"envmap", b"\1")))


def test_duplicate_exr_attribute_rejected():
    with pytest.raises(panorama.PanoramaError, match="conflicting"):
        panorama.inspect_panorama(exr(extra=attribute(b"dataWindow", b"box2i", bytes(16))))


def test_exr_oversized_header_rejected_before_decode():
    with pytest.raises(panorama.PanoramaError, match="oversized"):
        panorama.inspect_panorama(exr(extra=attribute(b"padding", b"string", bytes(1024 * 1024))))
