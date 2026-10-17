# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Contact sheet layout, Targa reading and PNG encoding without Blender."""

import struct
import zlib

import pytest

from scenario.core.scene import contact_sheet as sheet


def targa(width, height, pixels, *, depth=24, top_down=False):
    descriptor = 0x20 if top_down else 0
    header = struct.pack("<BBBHHBHHHHBB", 0, 0, 2, 0, 0, 0, 0, 0, width, height, depth, descriptor)
    body = b"".join(bytes((b, g, r)) + (b"\xff" if depth == 32 else b"") for r, g, b in pixels)
    return header + body


def decode_png(data):
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    offset, chunks = 8, {}
    while offset < len(data):
        (length,) = struct.unpack_from(">I", data, offset)
        kind = data[offset + 4 : offset + 8]
        body = data[offset + 8 : offset + 8 + length]
        (crc,) = struct.unpack_from(">I", data, offset + 8 + length)
        assert crc == zlib.crc32(kind + body) & 0xFFFFFFFF
        chunks[kind] = chunks.get(kind, b"") + body
        offset += 12 + length
    width, height, depth, colour = struct.unpack(">IIBB", chunks[b"IHDR"][:10])
    assert (depth, colour) == (8, 2)
    raw = zlib.decompress(chunks[b"IDAT"])
    stride = width * 3 + 1
    rows = [raw[row * stride : (row + 1) * stride] for row in range(height)]
    assert all(row[0] == 0 for row in rows)
    return width, height, [row[1:] for row in rows]


def pixel(rows, x, y):
    return tuple(rows[y][x * 3 : x * 3 + 3])


@pytest.mark.parametrize(
    ("count", "max_size", "aspect", "grid"),
    [
        (1, 1280, 1.0, (1, 1, 1272, 1272)),
        (4, 1280, 1.0, (2, 2, 634, 634)),
        (3, 1280, 1.0, (2, 2, 634, 634)),
        (6, 1280, 16 / 9, (3, 2, 421, 236)),
        (12, 256, 1.0, (4, 3, 59, 59)),
    ],
)
def test_layout_fills_the_longest_side_within_the_bound(count, max_size, aspect, grid):
    layout = sheet.layout(count, max_size, aspect)
    assert (layout.columns, layout.rows, layout.tile_width, layout.tile_height) == grid
    assert max(layout.width, layout.height) <= max_size
    assert layout.origin(0) == (sheet.GAP, sheet.GAP)
    if count > 1:
        assert layout.origin(1) == (2 * sheet.GAP + layout.tile_width, sheet.GAP)


def test_layout_refuses_tiles_too_small_to_read():
    with pytest.raises(ValueError, match="under 16 pixels"):
        sheet.layout(12, 64, 1.0)
    with pytest.raises(ValueError, match="at least one tile"):
        sheet.layout(0, 1280, 1.0)


def test_targa_rows_come_back_top_down_rgb_in_both_origins_and_depths():
    # Bottom-up file: the first stored row is the bottom of the image.
    bottom_up = targa(2, 2, [(1, 2, 3), (4, 5, 6), (7, 8, 9), (10, 11, 12)])
    assert sheet.read_targa(bottom_up) == (2, 2, bytes([7, 8, 9, 10, 11, 12, 1, 2, 3, 4, 5, 6]))
    top_down = targa(2, 1, [(1, 2, 3), (4, 5, 6)], depth=32, top_down=True)
    assert sheet.read_targa(top_down) == (2, 1, bytes([1, 2, 3, 4, 5, 6]))


@pytest.mark.parametrize(
    "data",
    [
        b"short",
        bytes(18),  # image type 0
        struct.pack("<BBBHHBHHHHBB", 0, 0, 10, 0, 0, 0, 0, 0, 2, 2, 24, 0) + bytes(12),
        struct.pack("<BBBHHBHHHHBB", 0, 0, 2, 0, 0, 0, 0, 0, 2, 2, 24, 0) + bytes(5),
    ],
)
def test_unsupported_or_truncated_targa_is_refused(data):
    with pytest.raises(ValueError):
        sheet.read_targa(data)


def test_compose_places_tiles_in_reading_order_with_labels():
    layout = sheet.layout(3, 256, 1.0)
    size = layout.tile_width
    colours = [(200, 0, 0), (0, 200, 0), (0, 0, 200)]
    tiles = [targa(size, size, [colour] * (size * size)) for colour in colours]
    width, height, rows = decode_png(sheet.compose(layout, tiles, ["FRONT", "RIGHT", "3/4"]))
    assert (width, height) == (layout.width, layout.height)
    for index, colour in enumerate(colours):
        x, y = layout.origin(index)
        # Bottom-right corner of the tile: away from the label band.
        assert pixel(rows, x + size - 2, y + size - 2) == colour
        # Top-left corner: the dark label band.
        assert pixel(rows, x + 1, y + 1) == sheet.LABEL_BACK
    label_pixels = {
        pixel(rows, x, y)
        for y in range(layout.origin(0)[1], layout.origin(0)[1] + 20)
        for x in range(layout.origin(0)[0], layout.origin(0)[0] + 60)
    }
    assert sheet.LABEL_TEXT in label_pixels
    # The unused fourth cell keeps the background.
    x, y = layout.origin(3)
    assert pixel(rows, x + 5, y + 5) == sheet.BACKGROUND


def test_compose_refuses_mismatched_tiles_and_labels():
    layout = sheet.layout(1, 256, 1.0)
    tile = targa(10, 10, [(0, 0, 0)] * 100)
    with pytest.raises(ValueError, match="expected"):
        sheet.compose(layout, [tile], ["FRONT"])
    with pytest.raises(ValueError, match="one label"):
        sheet.compose(layout, [tile], [])


def test_labels_clip_to_the_tile_and_skip_unknown_characters():
    canvas = sheet.Sheet(40, 30)
    height = canvas.label(0, 0, "FRAME 1234567 é", 2, 40)
    assert height == 7 * 2 + 2 * 4
    assert canvas.label(0, 0, "X", 2, 4) == 0
