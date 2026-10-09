# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Container preflight contracts; actual decoding is covered by native fixtures."""

import struct
import zlib
from unittest.mock import patch

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
    header = (
        b"\x76\x2f\x31\x01"
        + struct.pack("<I", version)
        + attribute(b"dataWindow", b"box2i", window)
        + attribute(b"displayWindow", b"box2i", display if display is not None else window)
        + attribute(b"compression", b"compression", b"\x03")
        + extra
        + b"\0"
    )
    count = max(0, (height + 15) // 16)
    chunks = [struct.pack("<ii", index * 16, 7) + b"fixture" for index in range(count)]
    start = len(header) + count * 8
    table = b"".join(struct.pack("<Q", start + index * 15) for index in range(count))
    return header + table + b"".join(chunks)


def segment(marker, payload=b""):
    return bytes((0xFF, marker)) + struct.pack(">H", len(payload) + 2) + payload


def frame(width=4, height=2, precision=8, components=3):
    header = struct.pack(">BHHB", precision, height, width, components)
    return header + b"\x01\x11\x00" * components


def jpeg(width=4, height=2, *, marker=0xC0, sof=None, before=b"", scan=b"\x12\x34", tail=b""):
    # Five header segments: APP0, DQT, frame, DHT and scan. Only the frame header
    # is interpreted; Blender decodes tables and entropy-coded data natively.
    return (
        b"\xff\xd8"
        + segment(0xE0, b"JFIF\0\x01\x01\0\0\x01\0\x01\0\0")
        + before
        + segment(0xDB, bytes(65))
        + segment(marker, frame(width, height) if sof is None else sof)
        + segment(0xC4, bytes(20))
        + segment(0xDA, b"\x03\x01\x00\x02\x11\x03\x11\x00\x3f\x00")
        + scan
        + b"\xff\xd9"
        + tail
    )


def chromaticities(values):
    return attribute(b"chromaticities", b"chromaticities", struct.pack("<8f", *values))


REC709 = (0.64, 0.33, 0.30, 0.60, 0.15, 0.06, 0.3127, 0.3290)
ACES_AP0 = (0.7347, 0.2653, 0.0, 1.0, 0.0001, -0.0770, 0.32168, 0.33767)
ACES_AP1 = (0.713, 0.293, 0.165, 0.830, 0.128, 0.044, 0.32168, 0.33767)
REC2020 = (0.708, 0.292, 0.170, 0.797, 0.131, 0.046, 0.3127, 0.3290)


@pytest.mark.parametrize("depth", [8, 16])
@pytest.mark.parametrize("color", [2, 6])
def test_standard_png_is_ldr_container(depth, color):
    assert panorama.inspect_panorama(png(depth=depth, color=color)) == panorama.PanoramaInfo(
        "PNG", 4, 2, False
    )


@pytest.mark.parametrize("depth", [8, 16])
def test_grayscale_images_are_supported_without_expanding_panorama_formats(depth):
    data = png(width=4, height=2, depth=depth, color=0)
    assert panorama.inspect_image(data) == panorama.PanoramaInfo("PNG", 4, 2, False)
    with pytest.raises(panorama.PanoramaError, match="RGB"):
        panorama.inspect_panorama(data)


@pytest.mark.parametrize("depth,color", [(1, 0), (2, 0), (4, 0), (32, 0), (8, 3), (8, 4)])
def test_general_images_still_reject_unaccepted_png_encodings(depth, color):
    with pytest.raises(panorama.PanoramaError):
        panorama.inspect_image(png(depth=depth, color=color))


def test_grayscale_images_keep_integrity_and_pixel_limits():
    damaged = bytearray(png(color=0))
    damaged[20] ^= 1
    with pytest.raises(panorama.PanoramaError, match="integrity"):
        panorama.inspect_image(bytes(damaged))
    with pytest.raises(panorama.PanoramaError, match="pixel limit"):
        panorama.inspect_image(png(width=16384, height=8192, color=0))


@pytest.mark.parametrize("version", [2, 0x402])
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


@pytest.mark.parametrize("make", [png, jpeg, exr])
@pytest.mark.parametrize("size", [(1, 1), (2, 1), (4, 3), (0, 2), (4, 0), (16384, 8192)])
def test_dimensions_bounded_before_decode(make, size):
    with pytest.raises(panorama.PanoramaError, match="2:1"):
        panorama.inspect_panorama(make(*size))


@pytest.mark.parametrize("make", [png, jpeg, exr])
def test_byte_limit(monkeypatch, make):
    monkeypatch.setattr(panorama, "MAX_FILE_BYTES", 8)
    with pytest.raises(panorama.PanoramaError, match="byte limit"):
        panorama.inspect_panorama(make())


@pytest.mark.parametrize("make", [png, exr])
@pytest.mark.parametrize("size", [(1, 1), (3, 5), (5, 3)])
def test_general_image_preflight_accepts_non_panorama_dimensions(make, size):
    info = panorama.inspect_image(make(*size))
    assert (info.width, info.height) == size
    with pytest.raises(panorama.PanoramaError, match="2:1"):
        panorama.inspect_panorama(make(*size))


@pytest.mark.parametrize("make", [png, exr])
@pytest.mark.parametrize("size", [(0, 2), (16384, 8192)])
def test_general_image_preflight_keeps_pixel_bounds(make, size):
    with pytest.raises(panorama.PanoramaError):
        panorama.inspect_image(make(*size))


def test_general_image_preflight_keeps_integrity_and_byte_bounds(monkeypatch):
    damaged = bytearray(png(3, 5))
    damaged[20] ^= 1
    with pytest.raises(panorama.PanoramaError, match="integrity"):
        panorama.inspect_image(bytes(damaged))
    monkeypatch.setattr(panorama, "MAX_FILE_BYTES", 8)
    with pytest.raises(panorama.PanoramaError, match="byte limit"):
        panorama.inspect_image(png(3, 5))


def test_png_crc_corruption_rejected():
    data = bytearray(png())
    data[20] ^= 1
    with pytest.raises(panorama.PanoramaError, match="integrity"):
        panorama.inspect_panorama(bytes(data))


@pytest.mark.parametrize("kind", [b"vpAg", b"IDAT"])
def test_png_chunk_limit_includes_all_chunks_and_accepts_boundary(kind):
    # IHDR, the existing IDAT and IEND also consume the chunk budget.
    data = png(extra=chunk(kind) * (panorama.MAX_PNG_CHUNKS - 3))
    assert panorama.inspect_panorama(data) == panorama.PanoramaInfo("PNG", 4, 2, False)


@pytest.mark.parametrize("kind", [b"vpAg", b"IDAT"])
def test_png_excess_chunks_rejected_before_further_crc_work(kind):
    data = png(extra=chunk(kind) * (panorama.MAX_PNG_CHUNKS * 2))
    assert len(data) < panorama.MAX_FILE_BYTES
    with patch.object(panorama.zlib, "crc32", wraps=zlib.crc32) as crc:
        with pytest.raises(panorama.PanoramaError, match="chunk limit"):
            panorama.inspect_panorama(data)
        assert crc.call_count == panorama.MAX_PNG_CHUNKS


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


@pytest.mark.parametrize("version", [1, 3, 0x202, 0x602, 0x802, 0x1002, 0x2002, 0x102])
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


def test_exr_long_names_require_version_flag():
    extra = attribute(b"a" * 32, b"string", b"fixture")
    with pytest.raises(panorama.PanoramaError, match="attribute header"):
        panorama.inspect_panorama(exr(extra=extra))
    assert panorama.inspect_panorama(exr(version=0x402, extra=extra)).hdr_capable


@pytest.mark.parametrize("removed", [1, 7, 15, 23])
def test_exr_truncated_pixel_data_or_table_rejected(removed):
    with pytest.raises(panorama.PanoramaError):
        panorama.inspect_panorama(exr()[:-removed])


@pytest.mark.parametrize("offset", [0, 1, 2**63])
def test_exr_invalid_chunk_offsets_rejected(offset):
    data = bytearray(exr())
    struct.pack_into("<Q", data, len(data) - 23, offset)
    with pytest.raises(panorama.PanoramaError, match="offset"):
        panorama.inspect_panorama(bytes(data))


@pytest.mark.parametrize("y,size", [(2, 7), (0, -1), (0, 1000)])
def test_exr_invalid_chunk_coordinates_and_sizes(y, size):
    data = bytearray(exr())
    struct.pack_into("<ii", data, len(data) - 15, y, size)
    with pytest.raises(panorama.PanoramaError, match="pixel block"):
        panorama.inspect_panorama(bytes(data))


def test_exr_trailing_data_rejected():
    with pytest.raises(panorama.PanoramaError, match="trailing"):
        panorama.inspect_panorama(exr() + b"trailing")


def test_exr_scanline_table_allows_reversed_physical_blocks():
    data = bytearray(exr(width=64, height=32))
    start = len(data) - 30
    first, second = bytes(data[start : start + 15]), bytes(data[start + 15 :])
    data[start:] = second + first
    struct.pack_into("<QQ", data, start - 16, start + 15, start)
    assert panorama.inspect_panorama(bytes(data)).height == 32


@pytest.mark.parametrize(
    "extra",
    [
        attribute(b"chunkCount", b"int", struct.pack("<i", 2)),
        attribute(b"type", b"string", b"tiledimage"),
    ],
)
def test_exr_conflicting_declared_layout_rejected(extra):
    with pytest.raises(panorama.PanoramaError):
        panorama.inspect_panorama(exr(extra=extra))


def test_exr_duplicate_block_cannot_hide_missing_pixels():
    data = bytearray(exr(width=64, height=32))
    start = len(data) - 30
    struct.pack_into("<QQ", data, start - 16, start, start)
    with pytest.raises(panorama.PanoramaError):
        panorama.inspect_panorama(bytes(data))


@pytest.mark.parametrize("marker", [0xC0, 0xC1, 0xC2])
def test_baseline_extended_and_progressive_jpeg_are_ldr_containers(marker):
    assert panorama.inspect_panorama(jpeg(marker=marker)) == panorama.PanoramaInfo(
        "JPEG", 4, 2, False
    )


@pytest.mark.parametrize("marker", [0xC3, 0xC5, 0xC7, 0xC8, 0xC9, 0xCA, 0xCB, 0xCD, 0xCF])
def test_lossless_hierarchical_and_arithmetic_jpeg_fail_closed(marker):
    with pytest.raises(panorama.PanoramaError, match="baseline or progressive"):
        panorama.inspect_panorama(jpeg(marker=marker))


@pytest.mark.parametrize("marker", [0xDE, 0xDF])
def test_hierarchical_jpeg_markers_fail_closed_before_any_frame(marker):
    with pytest.raises(panorama.PanoramaError, match="baseline or progressive"):
        panorama.inspect_panorama(jpeg(before=segment(marker, bytes(5))))


@pytest.mark.parametrize("precision,components", [(12, 3), (16, 3), (8, 1), (8, 4)])
def test_jpeg_requires_8bit_three_component_color(precision, components):
    data = jpeg(sof=frame(precision=precision, components=components))
    with pytest.raises(panorama.PanoramaError, match="8-bit color"):
        panorama.inspect_panorama(data)


@pytest.mark.parametrize("sof", [frame()[:-1], frame() + b"\0", frame()[:5]])
def test_jpeg_frame_length_must_match_its_components(sof):
    with pytest.raises(panorama.PanoramaError, match="frame header is invalid"):
        panorama.inspect_panorama(jpeg(sof=sof))


def test_duplicate_jpeg_frame_rejected():
    with pytest.raises(panorama.PanoramaError, match="conflicting"):
        panorama.inspect_panorama(jpeg(before=segment(0xC0, frame())))


def test_jpeg_scan_without_preceding_frame_rejected():
    data = b"\xff\xd8" + segment(0xDA, bytes(10)) + b"\x12\x34\xff\xd9"
    with pytest.raises(panorama.PanoramaError, match="dimensions are unavailable"):
        panorama.inspect_panorama(data)


@pytest.mark.parametrize(
    "before",
    [
        b"\xff" + segment(0xFE, b"fill byte before a marker"),
        segment(0xD0),
        b"\xff\x01\x00\x02",
        segment(0x02, b"reserved"),
        b"\xff\xd8\x00\x02",
        b"\xff\xe1\x00\x01",
        b"\x00\x00\x00\x00",
    ],
)
def test_jpeg_invalid_markers_before_scan_rejected(before):
    with pytest.raises(panorama.PanoramaError, match="incomplete or invalid"):
        panorama.inspect_panorama(jpeg(before=before))


@pytest.mark.parametrize(
    "data",
    [
        jpeg()[:-1],
        jpeg()[:-2],
        jpeg(scan=b""),
        jpeg(tail=b"trailing"),
        jpeg(tail=b"\xff\xd9\x00"),
    ],
)
def test_jpeg_truncated_scan_or_trailing_data_rejected(data):
    with pytest.raises(panorama.PanoramaError, match="incomplete or has trailing"):
        panorama.inspect_panorama(data)


@pytest.mark.parametrize("cut", [3, 6, 30, 90])
def test_jpeg_truncated_header_rejected(cut):
    with pytest.raises(panorama.PanoramaError, match="incomplete or invalid"):
        panorama.inspect_panorama(jpeg()[:cut])


def test_jpeg_segment_limit_includes_all_segments_and_accepts_boundary():
    comments = segment(0xFE, b"fixture") * (panorama.MAX_JPEG_SEGMENTS - 5)
    assert panorama.inspect_panorama(jpeg(before=comments)).file_format == "JPEG"
    with pytest.raises(panorama.PanoramaError, match="segment limit"):
        panorama.inspect_panorama(jpeg(before=comments + segment(0xFE)))


def test_jpeg_excess_segments_rejected_before_further_header_work():
    data = jpeg(before=segment(0xFE) * (panorama.MAX_JPEG_SEGMENTS * 2))
    assert len(data) < panorama.MAX_FILE_BYTES
    with patch.object(panorama.struct, "unpack_from", wraps=struct.unpack_from) as unpack:
        with pytest.raises(panorama.PanoramaError, match="segment limit"):
            panorama.inspect_panorama(data)
        assert unpack.call_count == panorama.MAX_JPEG_SEGMENTS


def test_jpeg_metadata_segments_are_left_to_blender():
    # EXIF orientation 6 is not interpreted; Blender decodes stored pixel order.
    tiff = b"MM\x00\x2a" + struct.pack(">IH", 8, 1) + struct.pack(">HHII", 0x0112, 3, 1, 6 << 16)
    data = jpeg(before=segment(0xE1, b"Exif\0\0" + tiff + bytes(4)) + segment(0xE2, b"ICC"))
    assert panorama.inspect_panorama(data) == panorama.PanoramaInfo("JPEG", 4, 2, False)


def test_general_image_preflight_does_not_accept_jpeg():
    with pytest.raises(panorama.PanoramaError, match="PNG and scanline OpenEXR"):
        panorama.inspect_image(jpeg())


@pytest.mark.parametrize(
    "values,expected",
    [
        (REC709, "rec709"),
        ((0.64, 0.33, 0.30, 0.60, 0.15, 0.06, 0.31271, 0.32902), "rec709"),
        (ACES_AP0, "aces_ap0"),
    ],
)
def test_exr_declared_primaries_are_classified(values, expected):
    info = panorama.inspect_panorama(exr(extra=chromaticities(values)))
    assert info == panorama.PanoramaInfo("OPEN_EXR", 4, 2, True, expected)


def test_exr_without_primaries_keeps_blender_default():
    assert panorama.inspect_panorama(exr()).chromaticities is None


@pytest.mark.parametrize(
    "values",
    [ACES_AP1, REC2020, ACES_AP0[:6] + REC709[6:], (float("nan"),) * 8],
)
def test_exr_other_primaries_fail_closed_for_world(values):
    with pytest.raises(panorama.PanoramaError, match="Rec.709 or ACES AP0"):
        panorama.inspect_panorama(exr(extra=chromaticities(values)))


@pytest.mark.parametrize(
    "extra",
    [
        attribute(b"chromaticities", b"v2f", struct.pack("<8f", *ACES_AP0)),
        attribute(b"chromaticities", b"chromaticities", struct.pack("<7f", *ACES_AP0[:7])),
    ],
)
def test_malformed_exr_primaries_rejected(extra):
    with pytest.raises(panorama.PanoramaError, match="primaries are invalid"):
        panorama.inspect_panorama(exr(extra=extra))


def test_general_image_preflight_does_not_classify_exr_primaries():
    info = panorama.inspect_image(exr(3, 5, extra=chromaticities(ACES_AP1)))
    assert info == panorama.PanoramaInfo("OPEN_EXR", 3, 5, True)


def test_world_media_types_name_their_required_container_and_wording():
    assert panorama.WORLD_MEDIA_TYPES == set(panorama.WORLD_MEDIA_FORMATS)
    assert set(panorama.WORLD_MEDIA_FORMATS.values()) == {"PNG", "JPEG", "OPEN_EXR"}
    assert panorama.WORLD_MEDIA_FORMATS["image/aces"] == "OPEN_EXR"
    for media_type, container in panorama.WORLD_MEDIA_FORMATS.items():
        label = panorama.describe_world_media(media_type)
        assert ("LDR" in label) == (container != "OPEN_EXR")
        assert ("ACES2065-1" in label) == (container == "OPEN_EXR")
    assert panorama.describe_world_media("image/aces").startswith("ACES-labelled OpenEXR")
    for unsupported in ("image/webp", "image/vnd.radiance", "image/jpg", ""):
        assert unsupported not in panorama.WORLD_MEDIA_TYPES
        assert panorama.describe_world_media(unsupported) == "Unsupported media type"
