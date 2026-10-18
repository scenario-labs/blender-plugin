# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Verified result-to-source mesh correspondence for in-place edits. No bpy.

An exported source comes back triangulated, split at UV seams and sharp normals,
and possibly reordered. `match` accepts such a result only when it is provably
the same surface: every result vertex lies on exactly one source vertex of its
face, and the result faces of each source polygon tile it exactly, with the same
orientation. Anything else fails closed with a counted reason; it never guesses.

The caller supplies the result-to-source mapping. `similarity_fit` can propose a
uniform scale and translation for normalized results; that hypothesis is used
only when this same match verifies it.
"""

import math
from array import array
from dataclasses import dataclass

# Positions agree within 1e-5 of the source's local size (the larger of its
# bounding-box diagonal and its farthest vertex from the local origin)...
POSITION_TOLERANCE = 1e-5
# ...widened to 1e-6 of the scene origin's distance in source-local units, since
# float32 file transforms lose precision far from the scene origin...
ORIGIN_TOLERANCE = 1e-6
# ...and never below this absolute floor, in source-local units.
MIN_POSITION_TOLERANCE = 1e-9
# Split copies of one source corner must carry the same UV within 1e-5 units
# (relative to the coordinate's magnitude above 1).
UV_TOLERANCE = 1e-5
# Split copies of one source vertex must carry the same bone weights within this.
WEIGHT_TOLERANCE = 1e-4


class CorrespondenceError(ValueError):
    """The result is not verifiably the same surface as the source."""


@dataclass(frozen=True)
class MeshArrays:
    """Flat mesh buffers: positions (x, y, z per vertex) and polygon corner lists."""

    co: object
    loop_vertices: object
    polygon_starts: object
    polygon_totals: object
    loop_edges: object = ()
    edge_count: int = 0


@dataclass(frozen=True)
class Correspondence:
    """Result loop -> source loop and result polygon -> source polygon indices."""

    loops: array
    polygons: array


def transformed(co, rows):
    """Apply an affine 4x4 matrix (row-major rows) to flat positions in double precision."""
    (a, b, c, d), (e, f, g, h), (i, j, k, m) = (tuple(row) for row in rows[:3])
    out = array("d", bytes(8 * len(co)))
    for index in range(0, len(co), 3):
        x, y, z = co[index], co[index + 1], co[index + 2]
        out[index] = a * x + b * y + c * z + d
        out[index + 1] = e * x + f * y + g * z + h
        out[index + 2] = i * x + j * y + k * z + m
    return out


def position_tolerance(co, origin_distance=0.0):
    """The documented matching radius for one source mesh, in source-local units."""
    extent = 0.0
    if len(co):
        low = [min(co[axis::3]) for axis in range(3)]
        high = [max(co[axis::3]) for axis in range(3)]
        diagonal = math.dist(low, high)
        reach = math.hypot(*(max(abs(a), abs(b)) for a, b in zip(low, high, strict=True)))
        extent = max(diagonal, reach)
    if not math.isfinite(extent) or not math.isfinite(origin_distance):
        raise CorrespondenceError("nonfinite positions cannot be matched")
    return max(
        POSITION_TOLERANCE * extent, ORIGIN_TOLERANCE * origin_distance, MIN_POSITION_TOLERANCE
    )


def concatenate(parts):
    """Join several meshes' buffers into one; returns the joined mesh and start offsets.

    Offsets are (vertex, loop, polygon) starts per part, so a joined index can be
    attributed back to the result mesh it came from with `part_of`.
    """
    co = array("d")
    loop_vertices = array("i")
    starts = array("i")
    totals = array("i")
    loop_edges = array("i")
    offsets = []
    vertices = loops = edges = 0
    for part in parts:
        offsets.append((vertices, loops, len(starts)))
        co.extend(array("d", part.co))
        loop_vertices.extend(array("i", (vertex + vertices for vertex in part.loop_vertices)))
        starts.extend(array("i", (start + loops for start in part.polygon_starts)))
        totals.extend(array("i", part.polygon_totals))
        loop_edges.extend(array("i", (edge + edges for edge in part.loop_edges)))
        vertices += len(part.co) // 3
        loops += len(part.loop_vertices)
        edges += part.edge_count
    return MeshArrays(co, loop_vertices, starts, totals, loop_edges, edges), tuple(offsets)


def part_of(offsets, index, kind=2):
    """Which concatenated part owns a joined vertex (0), loop (1) or polygon (2) index."""
    found = 0
    for part, starts in enumerate(offsets):
        if starts[kind] <= index:
            found = part
    return found


def _used_bounds(co, vertices):
    low = [math.inf] * 3
    high = [-math.inf] * 3
    for vertex in vertices:
        for axis in range(3):
            value = co[3 * vertex + axis]
            low[axis] = min(low[axis], value)
            high[axis] = max(high[axis], value)
    return low, high


def similarity_fit(source, result):
    """Uniform scale and translation taking the result's bounds onto the source's.

    Rotation stays fixed: providers normalize size and position, not orientation.
    The estimate is only a hypothesis; `match` must verify it before any use.
    Returns (scale, (x, y, z) offset) so that source = scale * result + offset.
    """
    low, high = _used_bounds(source.co, set(source.loop_vertices))
    result_low, result_high = _used_bounds(result.co, range(len(result.co) // 3))
    size = math.dist(low, high) if low[0] <= high[0] else 0.0
    result_size = math.dist(result_low, result_high) if result_low[0] <= result_high[0] else 0.0
    if not (size > 0 and result_size > 0) or not math.isfinite(size / result_size):
        raise CorrespondenceError("the result or source has no extent to fit")
    scale = size / result_size
    offset = tuple(
        (a + b) / 2 - scale * (c + d) / 2
        for a, b, c, d in zip(low, high, result_low, result_high, strict=True)
    )
    return scale, offset


def scaled(co, scale, offset):
    """Apply source = scale * result + offset to flat positions."""
    out = array("d", co)
    for index in range(len(out)):
        out[index] = scale * out[index] + offset[index % 3]
    return out


def sources(indices, count):
    """Invert a result -> source index map: per source index, its result indices."""
    out = [[] for _ in range(count)]
    for result, source in enumerate(indices):
        out[source].append(result)
    return tuple(tuple(items) for items in out)


def _count(count, noun, plural=None):
    return f"{count} {noun}" if count == 1 else f"{count} {plural or noun + 's'}"


def _candidates(source, used, result_co, result_used, tolerance):
    """Source vertices within tolerance of each used result vertex (8-cell hash)."""
    cell = 2.0 * tolerance
    grid = {}
    co = source.co
    for vertex in used:
        x, y, z = co[3 * vertex], co[3 * vertex + 1], co[3 * vertex + 2]
        key = (math.floor(x / cell), math.floor(y / cell), math.floor(z / cell))
        grid.setdefault(key, []).append(vertex)
    limit = tolerance * tolerance
    candidates = {}
    unmatched = 0
    for vertex in result_used:
        x, y, z = result_co[3 * vertex], result_co[3 * vertex + 1], result_co[3 * vertex + 2]
        # A ball of radius `cell / 2` overlaps at most two cells per axis.
        spans = []
        for value in (x, y, z):
            scaled = value / cell
            base = math.floor(scaled)
            spans.append((base - 1, base) if scaled - base < 0.5 else (base, base + 1))
        found = []
        for kx in spans[0]:
            for ky in spans[1]:
                for kz in spans[2]:
                    for other in grid.get((kx, ky, kz), ()):
                        dx = co[3 * other] - x
                        dy = co[3 * other + 1] - y
                        dz = co[3 * other + 2] - z
                        if dx * dx + dy * dy + dz * dz <= limit:
                            found.append(other)
        if not found:
            unmatched += 1
        candidates[vertex] = found
    return candidates, unmatched


def _tiles(local, total):
    """Whether oriented faces (polygon-local corner cycles) tile one n-gon exactly."""
    edges = {}
    for corners in local:
        for position, start in enumerate(corners):
            edge = (start, corners[(position + 1) % len(corners)])
            if edge in edges:
                return False
            edges[edge] = True
    boundary = 0
    diagonals = 0
    for start, end in edges:
        if end == (start + 1) % total:
            boundary += 1
        elif start == (end + 1) % total or (end, start) not in edges:
            return False
        else:
            diagonals += 1
    # A disk subdivided by D chords without interior vertices has D + 1 faces.
    return boundary == total and len(local) == diagonals // 2 + 1


def match(source, result, tolerance):
    """Prove `result` (positions already in source-local space) is the source surface.

    Returns per-loop and per-polygon indices into the source. Coincident source
    vertices are resolved only by the one source polygon a result face lies in.
    Loose source geometry carries no corners and is not matched.
    """
    vertex_count = len(source.co) // 3
    starts, totals = source.polygon_starts, source.polygon_totals
    corner = {}
    vertex_polygons = {}
    for polygon, (start, total) in enumerate(zip(starts, totals, strict=True)):
        for loop in range(start, start + total):
            vertex = source.loop_vertices[loop]
            corner[polygon * vertex_count + vertex] = loop
            vertex_polygons.setdefault(vertex, []).append(polygon)

    result_used = set(result.loop_vertices)
    loose = len(result.co) // 3 - len(result_used)
    loose += result.edge_count - len(set(result.loop_edges))
    if loose:
        raise CorrespondenceError(
            f"the result has {_count(loose, 'loose vertex or edge', 'loose vertices or edges')}"
        )
    candidates, unmatched = _candidates(source, vertex_polygons, result.co, result_used, tolerance)
    if unmatched:
        raise CorrespondenceError(
            f"result geometry differs from the source at {_count(unmatched, 'vertex', 'vertices')}"
        )

    result_starts, result_totals = result.polygon_starts, result.polygon_totals
    loops = array("i", [-1]) * len(result.loop_vertices)
    polygons = array("i", [-1]) * len(result_starts)
    by_polygon = {}
    outside = ambiguous = reversed_faces = 0
    for face, (start, total) in enumerate(zip(result_starts, result_totals, strict=True)):
        corners = result.loop_vertices[start : start + total]
        options = []
        unclear = False
        tried = set()
        for first in candidates[corners[0]]:
            for polygon in vertex_polygons[first]:
                if polygon in tried:
                    continue
                tried.add(polygon)
                resolved = []
                for vertex in corners:
                    hits = [
                        corner[key]
                        for other in candidates[vertex]
                        if (key := polygon * vertex_count + other) in corner
                    ]
                    if len(hits) != 1:
                        unclear |= len(hits) > 1
                        break
                    resolved.append(hits[0])
                else:
                    if len(set(resolved)) == total:
                        options.append((polygon, resolved))
        if len(options) != 1:
            if options or unclear:
                ambiguous += 1
            else:
                outside += 1
            continue
        polygon, resolved = options[0]
        size, base = totals[polygon], starts[polygon]
        local = [loop - base for loop in resolved]
        # Corners keep the source winding when they advance once around the polygon.
        if sum((local[(n + 1) % total] - local[n]) % size for n in range(total)) != size:
            reversed_faces += 1
            continue
        polygons[face] = polygon
        loops[start : start + total] = array("i", resolved)
        by_polygon.setdefault(polygon, []).append(local)
    if outside:
        raise CorrespondenceError(
            f"the result has {_count(outside, 'face')} outside any single source face"
        )
    if ambiguous:
        raise CorrespondenceError(
            f"the result has {_count(ambiguous, 'face')} on ambiguous coincident source geometry"
        )
    if reversed_faces:
        raise CorrespondenceError(
            f"the result has {_count(reversed_faces, 'face')} with reversed or crossed winding"
        )
    missing = len(starts) - len(by_polygon)
    if missing:
        raise CorrespondenceError(f"the result is missing {_count(missing, 'source face')}")
    uneven = sum(
        1
        for polygon, local in by_polygon.items()
        if not (len(local) == 1 and len(local[0]) == totals[polygon])
        and not _tiles(local, totals[polygon])
    )
    if uneven:
        raise CorrespondenceError(
            f"the result does not exactly cover {_count(uneven, 'source face')}"
        )
    return Correspondence(loops, polygons)


def corners(correspondence, values, width, count, label):
    """Per-source-loop values; every split copy of one source corner must agree."""
    out = array("f", bytes(4 * width * count))
    filled = bytearray(count)
    split = set()
    for loop, target in enumerate(correspondence.loops):
        value = values[loop * width : (loop + 1) * width]
        if not filled[target]:
            out[target * width : (target + 1) * width] = array("f", value)
            filled[target] = 1
            continue
        kept = out[target * width : (target + 1) * width]
        if any(
            abs(a - b) > UV_TOLERANCE * max(1.0, abs(a), abs(b))
            for a, b in zip(kept, value, strict=True)
        ):
            split.add(target)
    if split:
        raise CorrespondenceError(
            f"the result splits {label} at {_count(len(split), 'source face corner')}"
        )
    if not all(filled):
        raise CorrespondenceError(f"the result has no {label} for some source face corners")
    return out


def faces(correspondence, values, count, label):
    """Per-source-polygon integers; every result face of one source face must agree."""
    out = array("i", [0]) * count
    filled = bytearray(count)
    split = set()
    for face, target in enumerate(correspondence.polygons):
        if not filled[target]:
            out[target] = values[face]
            filled[target] = 1
        elif out[target] != values[face]:
            split.add(target)
    if split:
        raise CorrespondenceError(
            f"the result assigns several {label} inside {_count(len(split), 'source face')}"
        )
    return out


def _same_weights(a, b):
    a, b = dict(a), dict(b)
    return all(
        abs(a.get(group, 0.0) - b.get(group, 0.0)) <= WEIGHT_TOLERANCE
        for group in a.keys() | b.keys()
    )


def vertex_weights(correspondence, source_loops, result_loops, count, weights):
    """Per-source-vertex (group, weight) tuples; split copies must carry the same weights."""
    out = [None] * count
    split = set()
    for loop, target in enumerate(correspondence.loops):
        vertex = source_loops[target]
        value = weights[result_loops[loop]]
        if out[vertex] is None:
            out[vertex] = value
        elif out[vertex] != value and not _same_weights(out[vertex], value):
            split.add(vertex)
    if split:
        raise CorrespondenceError(
            f"the result gives different weights to split copies of "
            f"{_count(len(split), 'source vertex', 'source vertices')}"
        )
    missing = out.count(None)
    if missing:
        raise CorrespondenceError(
            f"the result is missing {_count(missing, 'source vertex', 'source vertices')}"
        )
    return tuple(out)
