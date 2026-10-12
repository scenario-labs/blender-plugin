# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Pages of a saved job's preview tiles. No bpy.

Blender panels cannot scroll sideways, so a job with more previewable results
than one row of tiles holds shows them a page at a time. ``results`` is the
job's ranked tuple of previewable asset IDs; an offset is the index of the
first drawn result. A page steps by ``SIZE`` and the last page ends at the
last result, so it is always full: six results show 1-4, then 3-6. Offsets are
transient UI state, never saved: ``PageOffsets`` keeps one per job and forgets
it when that job's results change.
"""

from dataclasses import dataclass

SIZE = 4
DIRECTIONS = (-1, 1)


@dataclass(frozen=True)
class Page:
    """One drawn page: its offset and the 1-based first and last of ``total`` results."""

    offset: int
    first: int
    last: int
    total: int

    @property
    def label(self):
        """The range under the tiles, such as ``3-6 of 6``, with a hyphen-minus."""
        return f"{self.first}-{self.last} of {self.total}"

    @property
    def previous(self):
        return self.first > 1

    @property
    def next(self):
        return self.last < self.total


def clamp(offset, total, size=SIZE):
    """The nearest offset that shows a full page of ``total`` results."""
    return max(0, min(offset, total - size))


def step(offset, total, direction, size=SIZE):
    """The offset one page back (``-1``) or forward (``1``), clamped to the results."""
    if type(direction) is not int or direction not in DIRECTIONS:
        raise ValueError("Page to the previous or next previews")
    return clamp(clamp(offset, total, size) + direction * size, total, size)


def visible(results, offset, size=SIZE):
    """The results drawn at ``offset``: all of them when they fit one page."""
    start = clamp(offset, len(results), size)
    return tuple(results[start : start + size])


def page(results, offset, size=SIZE):
    """The drawn page at ``offset``, or None when every result fits one page."""
    total = len(results)
    if total <= size:
        return None
    start = clamp(offset, total, size)
    return Page(start, start + 1, start + size, total)


class PageOffsets:
    """Transient page offsets per saved job, reset when that job's results change.

    The owner changes them only from operators and its timer, never while
    drawing; nothing here is saved with the blend file.
    """

    def __init__(self):
        self._offsets = {}  # request ID -> (results, offset)

    def offset(self, request_id, results):
        """The job's offset for these results; 0 when unset or the results changed."""
        results = tuple(results)
        entry = self._offsets.get(request_id)
        if entry is None or entry[0] != results:
            return 0
        return clamp(entry[1], len(results))

    def move(self, request_id, results, direction):
        """Page the job back or forward and return its new offset."""
        results = tuple(results)
        offset = step(self.offset(request_id, results), len(results), direction)
        if offset:
            self._offsets[request_id] = (results, offset)
        else:
            self._offsets.pop(request_id, None)
        return offset

    def prune(self, shown):
        """Keep offsets only for ``shown`` jobs, request ID to results, with unchanged results."""
        for request_id, (results, _) in tuple(self._offsets.items()):
            if shown.get(request_id) != results:
                del self._offsets[request_id]

    def items(self):
        return tuple((request_id, offset) for request_id, (_, offset) in self._offsets.items())

    def clear(self):
        self._offsets.clear()
