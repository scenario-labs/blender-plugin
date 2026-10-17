# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Lay out labelled tiles on one contact sheet and encode it as PNG. No bpy, standard library only.

Tiles arrive as uncompressed Targa files, the simplest format Blender writes, so
neither image datablocks nor version-specific image APIs are needed.
"""

import math
import struct
import zlib
from dataclasses import dataclass

GAP = 4  # pixels between tiles and around the sheet
BACKGROUND = (24, 24, 24)
LABEL_TEXT, LABEL_BACK = (255, 255, 255), (0, 0, 0)

# 5x7 bitmap glyphs, one 5-bit row per entry, most significant bit on the left.
_FONT = {
    " ": (0, 0, 0, 0, 0, 0, 0),
    "-": (0, 0, 0, 31, 0, 0, 0),
    "/": (1, 1, 2, 4, 8, 16, 16),
    ".": (0, 0, 0, 0, 0, 12, 12),
    ":": (0, 12, 12, 0, 12, 12, 0),
    "_": (0, 0, 0, 0, 0, 0, 31),
    "0": (14, 17, 19, 21, 25, 17, 14),
    "1": (4, 12, 4, 4, 4, 4, 14),
    "2": (14, 17, 1, 2, 4, 8, 31),
    "3": (31, 2, 4, 2, 1, 17, 14),
    "4": (2, 6, 10, 18, 31, 2, 2),
    "5": (31, 16, 30, 1, 1, 17, 14),
    "6": (6, 8, 16, 30, 17, 17, 14),
    "7": (31, 1, 2, 4, 8, 8, 8),
    "8": (14, 17, 17, 14, 17, 17, 14),
    "9": (14, 17, 17, 15, 1, 2, 12),
    "A": (14, 17, 17, 31, 17, 17, 17),
    "B": (30, 17, 17, 30, 17, 17, 30),
    "C": (14, 17, 16, 16, 16, 17, 14),
    "D": (28, 18, 17, 17, 17, 18, 28),
    "E": (31, 16, 16, 30, 16, 16, 31),
    "F": (31, 16, 16, 30, 16, 16, 16),
    "G": (14, 17, 16, 23, 17, 17, 15),
    "H": (17, 17, 17, 31, 17, 17, 17),
    "I": (14, 4, 4, 4, 4, 4, 14),
    "J": (7, 2, 2, 2, 2, 18, 12),
    "K": (17, 18, 20, 24, 20, 18, 17),
    "L": (16, 16, 16, 16, 16, 16, 31),
    "M": (17, 27, 21, 21, 17, 17, 17),
    "N": (17, 17, 25, 21, 19, 17, 17),
    "O": (14, 17, 17, 17, 17, 17, 14),
    "P": (30, 17, 17, 30, 16, 16, 16),
    "Q": (14, 17, 17, 17, 21, 18, 13),
    "R": (30, 17, 17, 30, 20, 18, 17),
    "S": (15, 16, 16, 14, 1, 1, 30),
    "T": (31, 4, 4, 4, 4, 4, 4),
    "U": (17, 17, 17, 17, 17, 17, 14),
    "V": (17, 17, 17, 17, 17, 10, 4),
    "W": (17, 17, 17, 21, 21, 21, 10),
    "X": (17, 17, 10, 4, 10, 17, 17),
    "Y": (17, 17, 10, 4, 4, 4, 4),
    "Z": (31, 1, 2, 4, 8, 16, 31),
}


@dataclass(frozen=True)
class Layout:
    columns: int
    rows: int
    tile_width: int
    tile_height: int

    @property
    def width(self):
        return self.columns * self.tile_width + (self.columns + 1) * GAP

    @property
    def height(self):
        return self.rows * self.tile_height + (self.rows + 1) * GAP

    def origin(self, index):
        """Top-left pixel of a tile, in reading order."""
        row, column = divmod(index, self.columns)
        return (
            GAP + column * (self.tile_width + GAP),
            GAP + row * (self.tile_height + GAP),
        )


def layout(count, max_size, aspect):
    """The most even grid for count tiles of width/height aspect, longest side at most max_size."""
    if type(count) is not int or count < 1:
        raise ValueError("A contact sheet needs at least one tile")
    if not aspect > 0 or not math.isfinite(aspect):
        raise ValueError("Tile aspect must be a positive number")
    columns = math.ceil(math.sqrt(count))
    rows = math.ceil(count / columns)
    by_width = (max_size - (columns + 1) * GAP) / columns
    by_height = (max_size - (rows + 1) * GAP) / rows * aspect
    tile_width = math.floor(min(by_width, by_height))
    tile_height = math.floor(tile_width / aspect)
    if tile_width < 16 or tile_height < 16:
        raise ValueError("Tiles would be under 16 pixels; raise max_size or use fewer views")
    return Layout(columns, rows, tile_width, tile_height)


def read_targa(data):
    """Width, height and top-down RGB rows of an uncompressed 24 or 32 bit Targa file."""
    if len(data) < 18:
        raise ValueError("Truncated Targa header")
    id_length, colormap_type, image_type = data[0], data[1], data[2]
    width, height = struct.unpack_from("<HH", data, 12)
    depth, descriptor = data[16], data[17]
    if colormap_type != 0 or image_type != 2 or depth not in (24, 32):
        raise ValueError("Expected an uncompressed true-colour Targa tile")
    channels = depth // 8
    start = 18 + id_length
    size = width * height * channels
    pixels = data[start : start + size]
    if width < 1 or height < 1 or len(pixels) != size:
        raise ValueError("Truncated Targa pixel data")
    rgb = bytearray(width * height * 3)
    rgb[0::3], rgb[1::3], rgb[2::3] = (
        pixels[2::channels],
        pixels[1::channels],
        pixels[0::channels],
    )
    if not descriptor & 0x20:  # bottom-up rows, Targa's default origin
        stride = width * 3
        rgb = b"".join(rgb[row * stride : (row + 1) * stride] for row in reversed(range(height)))
    return width, height, bytes(rgb)


class Sheet:
    """An RGB canvas that tiles and labels are copied onto."""

    def __init__(self, width, height, background=BACKGROUND):
        self.width, self.height = width, height
        self.pixels = bytearray(bytes(background) * (width * height))

    def paste(self, x, y, width, height, rgb):
        if x < 0 or y < 0 or x + width > self.width or y + height > self.height:
            raise ValueError("Tile does not fit on the sheet")
        if len(rgb) != width * height * 3:
            raise ValueError("Tile size does not match its pixels")
        stride = width * 3
        for row in range(height):
            offset = ((y + row) * self.width + x) * 3
            self.pixels[offset : offset + stride] = rgb[row * stride : (row + 1) * stride]

    def fill(self, x, y, width, height, colour):
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.width, x + width), min(self.height, y + height)
        if x1 <= x0 or y1 <= y0:
            return
        run = bytes(colour) * (x1 - x0)
        for row in range(y0, y1):
            offset = (row * self.width + x0) * 3
            self.pixels[offset : offset + len(run)] = run

    def label(self, x, y, text, scale, max_width):
        """Draw text on a dark band at (x, y), clipped to max_width pixels; returns the band height."""
        glyphs = [_FONT.get(ch, _FONT[" "]) for ch in text.upper()]
        advance, pad = 6 * scale, 2 * scale
        fit = max(0, (max_width - 2 * pad) // advance)
        glyphs = glyphs[:fit]
        band_height = 7 * scale + 2 * pad
        if not glyphs:
            return 0
        self.fill(x, y, len(glyphs) * advance - scale + 2 * pad, band_height, LABEL_BACK)
        for index, glyph in enumerate(glyphs):
            left = x + pad + index * advance
            for row, bits in enumerate(glyph):
                for column in range(5):
                    if bits & (16 >> column):
                        self.fill(
                            left + column * scale, y + pad + row * scale, scale, scale, LABEL_TEXT
                        )
        return band_height

    def png(self):
        stride = self.width * 3
        raw = b"".join(
            b"\x00" + bytes(self.pixels[row * stride : (row + 1) * stride])
            for row in range(self.height)
        )

        def chunk(kind, body):
            return (
                struct.pack(">I", len(body))
                + kind
                + body
                + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF)
            )

        header = struct.pack(">IIBBBBB", self.width, self.height, 8, 2, 0, 0, 0)
        return (
            b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", header)
            + chunk(b"IDAT", zlib.compress(raw, 6))
            + chunk(b"IEND", b"")
        )


def label_scale(tile_width):
    """Text size that stays legible after a client scales the sheet down: 2 to 4 pixels per dot."""
    return max(2, min(4, tile_width // 160))


def compose(grid, tiles, labels):
    """One PNG from Targa tiles (bytes) in reading order, each with its label."""
    if len(tiles) != len(labels) or not tiles or len(tiles) > grid.columns * grid.rows:
        raise ValueError("Each tile needs one label and a place on the grid")
    sheet = Sheet(grid.width, grid.height)
    scale = label_scale(grid.tile_width)
    for index, (data, text) in enumerate(zip(tiles, labels, strict=True)):
        width, height, rgb = read_targa(data)
        if (width, height) != (grid.tile_width, grid.tile_height):
            raise ValueError(
                f"Tile {index + 1} is {width}x{height}, expected "
                f"{grid.tile_width}x{grid.tile_height}"
            )
        x, y = grid.origin(index)
        sheet.paste(x, y, width, height, rgb)
        sheet.label(x, y, text, scale, width)
    return sheet.png()
