# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Finished generations as a grid of preview tiles: pages, tile sizes and facts. No bpy.

Studio's Results page, and the sidebar's Generations panel when chosen, show
finished generations newest first as preview tiles, a page at a time, and one
selected result large with its facts and actions. Pages split the results
without overlap: fourteen results show 1-12, then 13-14. A page index and the
selection are unsaved window state that only operators change; drawing clamps
a page that no longer exists instead of writing it back.

Widths are interface units: Blender's units at a UI scale of 1.
"""

from dataclasses import dataclass
from datetime import UTC, datetime

from ..jobs.store import parse_time

# As many results as the list draws, and as many as the previews hold per list.
PAGE_SIZE = 12
DIRECTIONS = (-1, 1)
# One icon scale step, and the space Blender leaves between a row's items.
STEP_UNITS = 20
ITEM_SPACING = 8
# A tile aims to be this wide (icon scale 4); the columns share the row's width.
TILE_UNITS = 80
MIN_COLUMNS, MAX_COLUMNS = 2, 6
TILE_MIN_SCALE, TILE_MAX_SCALE = 2.5, 8.0
# Previews are at most 256 pixels per side, so the large one stops at 240 units.
DETAIL_MIN_SCALE, DETAIL_MAX_SCALE = 4.0, 12.0
KIND_LABEL = {
    "image": "Image",
    "video": "Video",
    "3d": "3D model",
    "audio": "Audio",
    "material": "Material",
    "workflow": "Workflow",
}
SIZE_UNITS = ("KiB", "MiB", "GiB", "TiB")


@dataclass(frozen=True)
class GridPage:
    """One drawn page: its index and the 1-based first and last of ``total`` results."""

    index: int
    first: int
    last: int
    total: int

    @property
    def label(self):
        """The range above the tiles, such as ``13-14 of 14``, with a hyphen-minus."""
        return f"{self.first}-{self.last} of {self.total}"

    @property
    def previous(self):
        return self.index > 0

    @property
    def next(self):
        return self.last < self.total


def clamp(index, total, size=PAGE_SIZE):
    """The nearest page index that exists for ``total`` results; 0 for anything else."""
    if type(index) is not int:
        return 0
    return max(0, min(index, max(0, total - 1) // size))


def page(total, index, size=PAGE_SIZE):
    """The drawn page at ``index``, or None when every result fits one page."""
    if total <= size:
        return None
    index = clamp(index, total, size)
    first = index * size + 1
    return GridPage(index, first, min(total, first + size - 1), total)


def visible(items, index, size=PAGE_SIZE):
    """The items of page ``index``, clamped to the pages that exist."""
    start = clamp(index, len(items), size) * size
    return tuple(items[start : start + size])


def step(index, total, direction, size=PAGE_SIZE):
    """The page index one page back (``-1``) or forward (``1``), clamped to the results."""
    if type(direction) is not int or direction not in DIRECTIONS:
        raise ValueError("Page to the previous or next results")
    return clamp(clamp(index, total, size) + direction, total, size)


def page_of(position, size=PAGE_SIZE):
    """The page holding the 0-based ``position``."""
    return max(0, position) // size


def neighbors(identifiers, selected):
    """The results listed before and after ``selected``, each None at an end.

    Both are None when ``selected`` is not listed.
    """
    identifiers = tuple(identifiers)
    if selected not in identifiers:
        return None, None
    position = identifiers.index(selected)
    previous = identifiers[position - 1] if position else None
    following = identifiers[position + 1] if position + 1 < len(identifiers) else None
    return previous, following


def tile_layout(width):
    """Columns and icon scale of a grid ``width`` interface units wide.

    The columns aim at ``TILE_UNITS`` each and share the width; a narrow
    region keeps two columns of small icons, a wide one at most six.
    """
    columns = int((width + ITEM_SPACING) // (TILE_UNITS + ITEM_SPACING))
    columns = max(MIN_COLUMNS, min(MAX_COLUMNS, columns))
    share = (width - (columns - 1) * ITEM_SPACING) / columns / STEP_UNITS
    return columns, max(TILE_MIN_SCALE, min(TILE_MAX_SCALE, share))


def detail_scale(width):
    """The icon scale of the selected result's preview in ``width`` interface units."""
    return max(DETAIL_MIN_SCALE, min(DETAIL_MAX_SCALE, width / STEP_UNITS))


def kind_label(kind):
    return KIND_LABEL.get(kind, "Result")


def size_label(size):
    """A saved file's size in binary units, such as ``2.4 MiB``; empty when unknown."""
    if type(size) is not int or size < 0:
        return ""
    if size < 1024:
        return "1 byte" if size == 1 else f"{size} bytes"
    value, index = size / 1024, 0
    # Round first, so 1,048,575 bytes read 1.0 MiB rather than 1024.0 KiB.
    while round(value, 1) >= 1024 and index < len(SIZE_UNITS) - 1:
        value, index = value / 1024, index + 1
    return f"{value:.1f} {SIZE_UNITS[index]}"


def summary(kind, size, count):
    """The kind line of a selected result: ``Image, 2.4 MiB, 6 results``.

    ``size`` is the drawn result's saved size in bytes, when known; ``count``
    is how many results the generation saved.
    """
    parts = [kind_label(kind)]
    size = size_label(size)
    if size:
        parts.append(size)
    if type(count) is int and count > 1:
        parts.append(f"{count} results")
    return ", ".join(parts)


def submitted_label(claimed_at=None, created_at=0.0, tz=None):
    """When the generation was submitted, as local ``YYYY-MM-DD HH:MM``; empty when unknown.

    ``claimed_at`` is the UTC time saved with the submission. A row without
    one falls back to ``created_at``, seconds since the epoch, set when this
    session made the row; recovered rows have 0 there. ``tz`` overrides the
    local time zone.
    """
    moment = parse_time(claimed_at)
    if moment is None and type(created_at) in (int, float) and created_at > 0:
        try:
            moment = datetime.fromtimestamp(created_at, UTC)
        except (OverflowError, OSError, ValueError):
            moment = None
    if moment is None:
        return ""
    return moment.astimezone(tz).strftime("%Y-%m-%d %H:%M")
