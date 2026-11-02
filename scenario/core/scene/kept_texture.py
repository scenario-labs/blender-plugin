# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Which faces keep the source's own texture when a retexture is applied. No bpy.

A retexture model repaints the whole surface, and a character's face drifts with
it. The faces selected in Edit Mode, or else the head of a mesh that reads as a
standing character, keep their texture: the application composites the source's
maps over the result's on them (`blender/kept_texture.py`). This module decides
those faces from plain mesh buffers in scene coordinates (Z up), as a weight per
vertex: 1 on kept faces, falling to 0 over a short band, so no seam shows where
a kept region meets repainted surface on one piece of skin.

The head is found from the shape alone. Vertices at the same position are
welded, so a mesh split at UV seams is one surface again, and its connected
pieces are told apart: generated characters often model clothes as their own
pieces. The piece that holds the top of the mesh and reaches lowest is the body;
its horizontal cross-sections, read downward from the widest one near the top,
narrow to a neck and widen again at the shoulders, or at a collar modelled in
the same piece. Other pieces mostly above the neck (hair, eyes, brows) are kept
whole, pieces mostly below it (a jacket and its collar) are not. The body piece
is kept whole when most of it lies above the neck, as a separate head-and-neck
shell does, and is otherwise cut there with a soft band. A mesh with no such
neck keeps nothing.
"""

import heapq
import math
from array import array
from dataclasses import dataclass, field

SELECTED, HEAD, NONE = "SELECTED", "HEAD", "NONE"
MODES = (SELECTED, HEAD, NONE)
# The review's starting choice: selection, else the head of a standing character.
AUTO = "AUTO"

# A standing character is between these heights in metres and taller than its
# widest horizontal extent; this cheap bounds test also runs while the form draws.
MIN_HEIGHT = 0.5
MAX_HEIGHT = 3.0
# Cross-sections are 1% of the height on a dense mesh, and thicker on a sparse
# one so each holds about this many vertices on average.
MAX_SLICES = 100
MIN_SLICES = 20
SLICE_VERTICES = 50
# The head's widest section lies in the top quarter of the height, and the
# shoulders within this fraction of the height below it.
HEAD_ZONE = 0.25
NECK_WINDOW = 0.30
# A section wider than the narrowest so far by this factor ends the neck, and
# the neck must be at most this fraction of the head's widest section. On the
# Tripo P2 test character (1.83 m), whose jacket is its own piece, the head peaks
# at 404 cm2, the neck narrows to 158 cm2 and the next section opens to 203 cm2.
# A one-piece character's collar hides its neck: there the narrowest section, at
# the jaw, is 0.65 to 0.8 of the head's widest.
WIDEN = 1.25
NECK_RATIO = 0.85
# The body piece is kept whole when its area below the neck is at most this
# fraction of its area above it (a head-and-neck shell with a little chest).
# Other pieces are kept whole when most of their area lies above the neck.
SHELL_BELOW = 0.5
# Soft bands as fractions of the height: across the neck cut, and beyond a
# selection along the surface.
NECK_BAND = 0.02
SELECTION_BAND = 0.01
# Pieces whose top lies within this fraction of the height below the mesh top
# can be the body piece.
TOP_BAND = 0.05
# Positions within this fraction of the bounding-box diagonal are welded.
WELD = 1e-6

ROLES = ("base_color", "normal", "roughness", "metallic")


@dataclass(frozen=True)
class KeptRegion:
    """The resolved kept region of the joined sources, in vertex order.

    `mode` is the choice the review shows (SELECTED, HEAD or NONE); `source` says
    what found the faces ("selection", "head_bones" or "head"), or is None when
    nothing is kept. `faces` counts the selected faces, or else the faces whose
    every vertex weighs 1.
    """

    mode: str
    source: str | None
    faces: int
    note: str
    weights: array = field(default_factory=lambda: array("f"), repr=False)

    @property
    def kept(self):
        return self.source is not None


def standing(size, metres_per_unit=1.0):
    """Whether (x, y, z) bounds read as a standing character: real size, taller than wide."""
    height = size[2]
    return MIN_HEIGHT <= height * metres_per_unit <= MAX_HEIGHT and height > max(size[:2])


def starting_mode(selected_faces, total_faces, standing_mesh, keep_head):
    """The kept region a review starts on: selected faces win, then a standing character's head."""
    if 0 < selected_faces < total_faces:
        return SELECTED
    if keep_head and standing_mesh:
        return HEAD
    return NONE


def _positions(mesh):
    co = mesh.co
    return [(co[i], co[i + 1], co[i + 2]) for i in range(0, len(co), 3)]


def _faces(mesh):
    loops = mesh.loop_vertices
    return [
        tuple(loops[start : start + total])
        for start, total in zip(mesh.polygon_starts, mesh.polygon_totals, strict=True)
    ]


def _bounds(points):
    if not points:
        return (0.0, 0.0, 0.0), (0.0, 0.0, 0.0)
    return (
        tuple(min(p[axis] for p in points) for axis in range(3)),
        tuple(max(p[axis] for p in points) for axis in range(3)),
    )


def weld(points, tolerance):
    """One id per vertex; vertices on the same tolerance grid cell share it."""
    scale = 1.0 / tolerance if tolerance > 0 else 1.0
    ids, welded = {}, []
    for x, y, z in points:
        key = (round(x * scale), round(y * scale), round(z * scale))
        welded.append(ids.setdefault(key, len(ids)))
    return welded


def pieces(faces, welded):
    """Connected piece per face, faces joined through shared welded vertices."""
    parent = list(range(max(welded, default=-1) + 1))

    def find(item):
        while parent[item] != item:
            parent[item] = parent[parent[item]]
            item = parent[item]
        return item

    for face in faces:
        if not face:
            continue
        root = find(welded[face[0]])
        for vertex in face[1:]:
            other = find(welded[vertex])
            if other != root:
                parent[other] = root
    return [find(welded[face[0]]) if face else -1 for face in faces]


def _area(points, face):
    """Polygon area by a fan of triangles."""
    total = 0.0
    a = points[face[0]]
    for b_index, c_index in zip(face[1:-1], face[2:], strict=True):
        b, c = points[b_index], points[c_index]
        u = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
        v = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
        cross = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
        total += 0.5 * math.sqrt(cross[0] ** 2 + cross[1] ** 2 + cross[2] ** 2)
    return total


def hull_area(points):
    """Area of the convex hull of 2D points (monotone chain); 0 for fewer than three."""
    points = sorted(set(points))
    if len(points) < 3:
        return 0.0

    def half(sequence):
        hull = []
        for p in sequence:
            while len(hull) >= 2:
                (ax, ay), (bx, by) = hull[-2], hull[-1]
                if (bx - ax) * (p[1] - ay) - (by - ay) * (p[0] - ax) > 0:
                    break
                hull.pop()
            hull.append(p)
        return hull[:-1]

    hull = half(points) + half(reversed(points))
    return 0.5 * abs(
        sum(hull[i][0] * hull[i - 1][1] - hull[i - 1][0] * hull[i][1] for i in range(len(hull)))
    )


def _smooth(value):
    value = min(1.0, max(0.0, value))
    return value * value * (3.0 - 2.0 * value)


def neck(points, top, height):
    """The height to cut one piece's head at, or None when it has no neck.

    Sections are read downward from the top. The head's widest section comes
    first, within the top `HEAD_ZONE`; once one has narrowed from it by `WIDEN`,
    the neck is the narrowest section before one opens by `WIDEN` again: the
    shoulders, or a collar on a one-piece mesh. The cut lies where it opens, so
    the jaw and neck above stay with the head. A piece that ends first is a
    head-and-neck shell, cut at its bottom.
    """
    count = max(MIN_SLICES, min(MAX_SLICES, len(points) // SLICE_VERTICES))
    step = height / count
    sections = [[] for _ in range(count)]
    for x, y, z in points:
        index = int((top - z) / step) if step > 0 else 0
        if 0 <= index < count:
            sections[index].append((x, y))
    areas = [hull_area(section) if len(section) >= 3 else None for section in sections]
    filled = [index for index, area in enumerate(areas) if area]
    if not filled:
        return None
    last = filled[-1]
    peak = narrowest = cut = None
    for index in filled:
        area = areas[index]
        if narrowest is None:
            if peak is None or area >= areas[peak]:
                peak = index
            elif area * WIDEN < areas[peak]:
                narrowest = index
            continue
        if (index - peak) * step > NECK_WINDOW * height:
            # No shoulders within reach: a pole, a door or a lamp, not a character.
            return None
        if area > WIDEN * areas[narrowest]:
            cut = top - index * step
            break
        if area < areas[narrowest]:
            narrowest = index
    else:
        if narrowest is not None:
            cut = top - (last + 1) * step
    if cut is None or peak * step > HEAD_ZONE * height:
        return None
    if areas[narrowest] > NECK_RATIO * areas[peak]:
        return None
    return cut


def head_weights(points, faces):
    """Per-vertex weights of the head found from the shape, or None when there is none."""
    # Loose vertices have no surface: bounds come from faces only.
    low, high = _bounds([points[vertex] for face in faces for vertex in face])
    height = high[2] - low[2]
    if height <= 0:
        return None
    diagonal = math.dist(low, high)
    welded = weld(points, WELD * diagonal)
    piece_of = pieces(faces, welded)
    members, bottom, crest = {}, {}, {}
    for face, piece in zip(faces, piece_of, strict=True):
        if piece < 0:
            continue
        members.setdefault(piece, set()).update(face)
    for piece, vertices in members.items():
        heights = [points[vertex][2] for vertex in vertices]
        bottom[piece], crest[piece] = min(heights), max(heights)
    near_top = [piece for piece in members if crest[piece] >= high[2] - TOP_BAND * height]
    body = min(near_top, key=lambda piece: (bottom[piece], -len(members[piece])))
    cut = neck([points[vertex] for vertex in members[body]], crest[body], height)
    if cut is None:
        return None
    above, below = {}, {}
    for face, piece in zip(faces, piece_of, strict=True):
        if piece < 0:
            continue
        side = above if sum(points[vertex][2] for vertex in face) / len(face) >= cut else below
        side[piece] = side.get(piece, 0.0) + _area(points, face)
    weights = array("f", bytes(4 * len(points)))
    band = NECK_BAND * height
    for piece, vertices in members.items():
        up, down = above.get(piece, 0.0), below.get(piece, 0.0)
        if piece == body and down > SHELL_BELOW * up:
            for vertex in vertices:
                weights[vertex] = _smooth((points[vertex][2] - cut) / band + 0.5)
        elif piece == body or up > down:
            # Hair, eyes and brows lie mostly above the neck; a collar mostly below.
            for vertex in vertices:
                weights[vertex] = 1.0
    return weights


def selection_weights(points, faces, selected):
    """1 on the selected faces, falling to 0 along the surface over `SELECTION_BAND`."""
    low, high = _bounds(points)
    diagonal = math.dist(low, high)
    band = SELECTION_BAND * diagonal
    welded = weld(points, WELD * diagonal)
    distance, edges = {}, {}
    for face, chosen in zip(faces, selected, strict=True):
        if chosen:
            for vertex in face:
                distance[welded[vertex]] = 0.0
        for a, b in zip(face, face[1:] + face[:1], strict=True):
            length = math.dist(points[a], points[b])
            edges.setdefault(welded[a], {})[welded[b]] = length
            edges.setdefault(welded[b], {})[welded[a]] = length
    queue = [(0.0, item) for item in distance]
    heapq.heapify(queue)
    while queue:
        reached, item = heapq.heappop(queue)
        if reached > distance[item]:
            continue
        for other, length in edges.get(item, {}).items():
            total = reached + length
            if total < band and total < distance.get(other, math.inf):
                distance[other] = total
                heapq.heappush(queue, (total, other))

    def weight(item):
        if item not in distance:
            return 0.0
        return _smooth(1.0 - distance[item] / band) if band > 0 else 1.0

    return array("f", (weight(item) for item in welded))


def bone_weights(head):
    """Weights from a rig's head vertex groups: kept from half weight, soft around it."""
    return array("f", (_smooth((min(1.0, value) - 0.25) / 0.5) for value in head))


def _kept_faces(faces, weights):
    return sum(1 for face in faces if face and all(weights[vertex] >= 1.0 for vertex in face))


def plan(mesh, mode, *, selected=None, head_bones=None):
    """Resolve SELECTED, HEAD or NONE on a `mesh_correspondence.MeshArrays` in scene space.

    `selected` holds one flag per face; only a nonempty strict subset counts.
    `head_bones` holds a rig's head weight per vertex; when any is set it
    replaces the shape rule for HEAD.
    """
    if mode not in MODES:
        raise ValueError("Choose SELECTED, HEAD or NONE")
    points, faces = _positions(mesh), _faces(mesh)
    empty = array("f", bytes(4 * len(points)))
    weights, source = None, None
    if mode == SELECTED:
        chosen = list(selected or ())
        if len(chosen) == len(faces) and 0 < sum(map(bool, chosen)) < len(faces):
            weights, source = selection_weights(points, faces, chosen), "selection"
        else:
            note = "No faces selected in Edit Mode: the whole surface takes the new texture"
    elif mode == HEAD:
        if head_bones is not None and any(value > 0 for value in head_bones):
            weights, source = bone_weights(head_bones), "head_bones"
        else:
            weights = head_weights(points, faces)
            source = "head" if weights is not None else None
        if weights is None:
            note = "No head found on this mesh: the whole surface takes the new texture"
    else:
        note = "The whole surface takes the new texture"
    if weights is None:
        return KeptRegion(mode, None, 0, note, empty)
    # A selection reports what the artist picked; the feather around it is extra.
    count = sum(map(bool, chosen)) if source == "selection" else _kept_faces(faces, weights)
    if count == 0:
        return KeptRegion(
            mode, None, 0, "No face is kept: the whole surface takes the new texture", empty
        )
    note = {
        "selection": f"The selected faces keep their texture ({count:,})",
        "head_bones": f"The head keeps its texture ({count:,} faces, from its head bone weights)",
        "head": f"The head keeps its texture ({count:,} faces)",
    }[source]
    return KeptRegion(mode, source, count, note, weights)


def pair_maps(original, result, *, same_layout=True):
    """Pair the source's maps with the result's, role by role.

    Each side maps a role in `ROLES` to (image key, channels, colour) where
    channels index the image's RGB (one channel for a packed value) and colour
    names the base colour's colour space and storage, which must match. Normal
    maps are kept only on the same UV layout: their tangent frame follows it.
    Returns ({result image key: [(result channels, original image key, original
    channels), ...]}, {role: reason}) for roles that are not kept.
    """
    pairs, skipped = {}, {}
    for role in ROLES:
        if role not in result:
            continue
        if role not in original:
            skipped[role] = "the source has no such map"
            continue
        result_key, result_channels, result_colour = result[role]
        original_key, original_channels, original_colour = original[role]
        if role == "base_color" and result_colour != original_colour:
            skipped[role] = "the maps use different colour spaces"
            continue
        if role == "normal" and not same_layout:
            skipped[role] = "the result has another UV layout"
            continue
        entry = (tuple(result_channels), original_key, tuple(original_channels))
        if entry not in pairs.setdefault(result_key, []):
            pairs[result_key].append(entry)
    return pairs, skipped
