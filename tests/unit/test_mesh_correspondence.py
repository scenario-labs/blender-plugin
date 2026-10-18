# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Verified correspondence between a source mesh and a triangulated, split result."""

import math

import pytest

from scenario.core.scene import mesh_correspondence as mc

# Two quads sharing an edge, plus a pentagon, all in the z = 0 plane.
SOURCE_POSITIONS = [
    (0, 0, 0),
    (1, 0, 0),
    (2, 0, 0),
    (2, 1, 0),
    (1, 1, 0),
    (0, 1, 0),
    (4, 0, 0),
    (5, 0, 0),
    (5.5, 1, 0),
    (4.5, 2, 0),
    (3.5, 1, 0),
]
SOURCE_FACES = [(0, 1, 4, 5), (1, 2, 3, 4), (6, 7, 8, 9, 10)]


def arrays(positions, faces, edges=None):
    co = [component for position in positions for component in position]
    loops, starts, totals = [], [], []
    for face in faces:
        starts.append(len(loops))
        totals.append(len(face))
        loops.extend(face)
    # Unique undirected face edges, as Blender would create them.
    edge_index = {}
    loop_edges = []
    for face in faces:
        for position, vertex in enumerate(face):
            key = frozenset((vertex, face[(position + 1) % len(face)]))
            loop_edges.append(edge_index.setdefault(key, len(edge_index)))
    count = len(edge_index) if edges is None else edges
    return mc.MeshArrays(co, loops, starts, totals, loop_edges, count)


def split(positions, faces, permutation=None):
    """Export-like result: one vertex per face corner (fully split), optionally shuffled."""
    out_positions, out_faces = [], []
    for face in faces:
        out_faces.append(tuple(range(len(out_positions), len(out_positions) + len(face))))
        out_positions.extend(positions[vertex] for vertex in face)
    if permutation:
        order = permutation(len(out_positions))
        inverse = {old: new for new, old in enumerate(order)}
        out_positions = [out_positions[old] for old in order]
        out_faces = [tuple(inverse[vertex] for vertex in face) for face in out_faces]
    return out_positions, out_faces


def triangulated(faces):
    """Fan triangulation that keeps each face's winding."""
    return [(face[0], face[i], face[i + 1]) for face in faces for i in range(1, len(face) - 1)]


def compact(positions, faces):
    """Drop vertices that no face uses, as a file exporter would."""
    used = sorted({vertex for face in faces for vertex in face})
    index = {vertex: new for new, vertex in enumerate(used)}
    return [positions[vertex] for vertex in used], [tuple(index[v] for v in f) for f in faces]


def run(result_positions, result_faces, source=None, **kwargs):
    source = source or arrays(SOURCE_POSITIONS, SOURCE_FACES)
    tolerance = mc.position_tolerance(source.co)
    return mc.match(source, arrays(result_positions, result_faces, **kwargs), tolerance)


def test_identical_mesh_maps_every_loop_and_face_to_itself():
    found = run(SOURCE_POSITIONS, SOURCE_FACES)
    assert list(found.loops) == list(range(13))
    assert list(found.polygons) == [0, 1, 2]


def test_triangulated_seam_split_and_reordered_result_is_accepted():
    positions, faces = split(
        SOURCE_POSITIONS, triangulated(SOURCE_FACES), lambda n: [*range(n)][::-1]
    )
    found = run(positions, faces)
    source = arrays(SOURCE_POSITIONS, SOURCE_FACES)
    assert list(found.polygons) == [0, 0, 1, 1, 2, 2, 2]
    for loop, target in enumerate(found.loops):
        result_vertex = arrays(positions, faces).loop_vertices[loop]
        assert positions[result_vertex] == SOURCE_POSITIONS[source.loop_vertices[target]]


def test_other_diagonal_and_rotated_start_tile_the_source():
    faces = [(1, 4, 5), (5, 0, 1), (2, 3, 4, 1), (8, 9, 10), (10, 6, 7), (7, 8, 10)]
    found = run(SOURCE_POSITIONS, faces)
    assert list(found.polygons) == [0, 0, 1, 2, 2, 2]


def test_positions_within_tolerance_match_and_beyond_fail():
    tolerance = mc.position_tolerance(arrays(SOURCE_POSITIONS, SOURCE_FACES).co)
    near = list(SOURCE_POSITIONS)
    near[0] = (tolerance * 0.5, 0, 0)
    run(near, SOURCE_FACES)
    near[0] = (tolerance * 3, 0, 0)
    with pytest.raises(mc.CorrespondenceError, match="differs from the source at 1 vertex$"):
        run(near, SOURCE_FACES)


@pytest.mark.parametrize(
    ("faces", "reason"),
    [
        (SOURCE_FACES[:2], "missing 1 source face"),
        ([(0, 1, 4), *SOURCE_FACES[1:]], "does not exactly cover 1 source face"),
        ([*SOURCE_FACES, (0, 1, 4)], "does not exactly cover 1 source face"),
        ([(0, 1, 2, 3, 4, 5), SOURCE_FACES[2]], "1 face outside any single source face"),
        ([(5, 4, 1, 0), *SOURCE_FACES[1:]], "1 face with reversed or crossed winding"),
        ([(0, 1, 4), (0, 4, 1), *SOURCE_FACES[1:]], "reversed or crossed winding"),
        ([SOURCE_FACES[0], (1, 2, 4), (2, 3, 4), (1, 2, 3), SOURCE_FACES[2]], "exactly cover"),
        ([*SOURCE_FACES[:2], (6, 7, 9), (7, 8, 9), (6, 8, 10)], "exactly cover"),
    ],
)
def test_changed_faces_fail_closed(faces, reason):
    with pytest.raises(mc.CorrespondenceError, match=reason):
        run(*compact(SOURCE_POSITIONS, faces))


def test_loose_result_vertices_and_edges_fail():
    with pytest.raises(mc.CorrespondenceError, match="1 loose vertex or edge"):
        run([*SOURCE_POSITIONS, (9, 9, 9)], SOURCE_FACES)
    with pytest.raises(mc.CorrespondenceError, match="loose"):
        run(SOURCE_POSITIONS, SOURCE_FACES, edges=13)


def test_seam_split_source_resolves_coincident_vertices_by_face():
    # The source is itself split along its shared edge: 1 and 4 have twins.
    positions = [*SOURCE_POSITIONS, (1, 0, 0), (1, 1, 0)]
    faces = [(0, 1, 4, 5), (11, 2, 3, 12), SOURCE_FACES[2]]
    source = arrays(positions, faces)
    found = run(SOURCE_POSITIONS, triangulated(SOURCE_FACES), source=source)
    assert [source.loop_vertices[loop] for loop in found.loops[6:12]] == [11, 2, 3, 11, 3, 12]


def test_duplicate_source_faces_are_ambiguous():
    positions = [*SOURCE_POSITIONS, (0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)]
    source = arrays(positions, [*SOURCE_FACES, (11, 12, 13, 14)])
    with pytest.raises(mc.CorrespondenceError, match="ambiguous coincident"):
        run(SOURCE_POSITIONS, SOURCE_FACES, source=source)


def test_coincident_vertices_in_one_source_face_are_ambiguous():
    positions = [(0, 0, 0), (1, 0, 0), (1, 0, 0), (1, 1, 0)]
    source = arrays(positions, [(0, 1, 2, 3)])
    with pytest.raises(mc.CorrespondenceError, match="ambiguous coincident"):
        run(positions, [(0, 1, 2, 3)], source=source)


def test_loose_source_geometry_is_not_required_and_cannot_be_matched():
    source = arrays([*SOURCE_POSITIONS, (8, 8, 8)], SOURCE_FACES)
    run(SOURCE_POSITIONS, SOURCE_FACES, source=source)
    with pytest.raises(mc.CorrespondenceError, match="differs"):
        run([*SOURCE_POSITIONS, (8, 8, 8)], [*SOURCE_FACES, (11, 0, 1)], source=source)


def test_corner_values_agree_across_split_copies_and_fail_on_inner_seams():
    positions, faces = split(SOURCE_POSITIONS, triangulated(SOURCE_FACES))
    found = run(positions, faces)
    source_uvs = [(0.1 * loop, 0.5) for loop in range(13)]
    values = [c for target in found.loops for c in source_uvs[target]]
    out = mc.corners(found, values, 2, 13, "UV coordinates")
    assert [round(value, 5) for value in out] == [round(c, 5) for uv in source_uvs for c in uv]
    values[0] += 1e-7
    mc.corners(found, values, 2, 13, "UV coordinates")
    values[0] += 0.01
    with pytest.raises(mc.CorrespondenceError, match="splits UV coordinates at 1 source face"):
        mc.corners(found, values, 2, 13, "UV coordinates")


def test_face_values_must_agree_inside_each_source_face():
    found = run(SOURCE_POSITIONS, triangulated(SOURCE_FACES))
    assert list(mc.faces(found, [0, 0, 1, 1, 2, 2, 2], 3, "materials")) == [0, 1, 2]
    with pytest.raises(mc.CorrespondenceError, match="several materials inside 1 source face"):
        mc.faces(found, [0, 1, 1, 1, 2, 2, 2], 3, "materials")


def test_vertex_weights_merge_split_copies_and_require_every_vertex():
    positions, faces = split(SOURCE_POSITIONS, SOURCE_FACES)
    found = run(positions, faces)
    source = arrays(SOURCE_POSITIONS, SOURCE_FACES)
    result = arrays(positions, faces)
    weights = [((0, 1.0),) if positions[v][0] < 3 else ((1, 0.5), (0, 0.5)) for v in range(13)]
    out = mc.vertex_weights(found, source.loop_vertices, result.loop_vertices, 11, weights)
    assert out[0] == ((0, 1.0),) and out[6] == ((1, 0.5), (0, 0.5))
    # Source vertex 1 has two result copies: 1 in the first quad and 4 in the second.
    weights[4] = ((0, 1.0), (1, 0.00001))
    mc.vertex_weights(found, source.loop_vertices, result.loop_vertices, 11, weights)
    weights[4] = ((0, 0.9), (1, 0.1))
    with pytest.raises(mc.CorrespondenceError, match="split copies of 1 source vertex$"):
        mc.vertex_weights(found, source.loop_vertices, result.loop_vertices, 11, weights)
    with pytest.raises(mc.CorrespondenceError, match="missing 1 source vertex$"):
        mc.vertex_weights(found, source.loop_vertices, result.loop_vertices, 12, [((0, 1.0),)] * 13)


def test_tolerance_scales_with_size_and_origin_distance():
    co = [0, 0, 0, 3, 4, 0]
    assert mc.position_tolerance(co) == pytest.approx(5e-5)
    assert mc.position_tolerance(co, origin_distance=1000) == pytest.approx(1e-3)
    assert mc.position_tolerance([]) == mc.MIN_POSITION_TOLERANCE
    with pytest.raises(mc.CorrespondenceError):
        mc.position_tolerance([math.inf, 0, 0])


def test_transformed_applies_affine_rows_in_double_precision():
    rows = ((0, -1, 0, 1), (1, 0, 0, 2), (0, 0, 2, 3), (0, 0, 0, 1))
    assert list(mc.transformed([1, 0, 0, 0, 1, 1], rows)) == [1, 3, 3, 0, 2, 5]


def test_concatenated_parts_match_as_one_surface_and_attribute_faces():
    positions, faces = split(SOURCE_POSITIONS, triangulated(SOURCE_FACES))
    first = arrays(positions[:12], faces[:4])
    second_faces = [tuple(vertex - 12 for vertex in face) for face in faces[4:]]
    second = arrays(positions[12:], second_faces)
    joined, offsets = mc.concatenate((first, second))
    source = arrays(SOURCE_POSITIONS, SOURCE_FACES)
    found = mc.match(source, joined, mc.position_tolerance(source.co))
    assert list(found.polygons) == [0, 0, 1, 1, 2, 2, 2]
    assert offsets == ((0, 0, 0), (12, 12, 4))
    assert [mc.part_of(offsets, face) for face in range(7)] == [0, 0, 0, 0, 1, 1, 1]
    assert mc.sources(found.polygons, 3) == ((0, 1), (2, 3), (4, 5, 6))


def test_similarity_fit_recovers_uniform_scale_and_offset_for_verification():
    source = arrays(SOURCE_POSITIONS, SOURCE_FACES)
    normalized = [(0.2 * x - 3, 0.2 * y + 1, 0.2 * z + 0.5) for x, y, z in SOURCE_POSITIONS]
    result = arrays(normalized, SOURCE_FACES)
    scale, offset = mc.similarity_fit(source, result)
    assert scale == pytest.approx(5)
    assert offset == pytest.approx((15, -5, -2.5))
    fitted = mc.MeshArrays(
        mc.scaled(result.co, scale, offset),
        result.loop_vertices,
        result.polygon_starts,
        result.polygon_totals,
        result.loop_edges,
        result.edge_count,
    )
    assert list(mc.match(source, fitted, mc.position_tolerance(source.co)).polygons) == [0, 1, 2]


def test_similarity_fit_never_rotates_or_accepts_a_wrong_hypothesis():
    source = arrays(SOURCE_POSITIONS, SOURCE_FACES)
    turned = [(-y, x, z) for x, y, z in SOURCE_POSITIONS]
    result = arrays(turned, SOURCE_FACES)
    scale, offset = mc.similarity_fit(source, result)
    fitted = mc.MeshArrays(
        mc.scaled(result.co, scale, offset),
        result.loop_vertices,
        result.polygon_starts,
        result.polygon_totals,
        result.loop_edges,
        result.edge_count,
    )
    with pytest.raises(mc.CorrespondenceError, match="differs"):
        mc.match(source, fitted, mc.position_tolerance(source.co))
    flat = arrays([(0, 0, 0)] * 4, [(0, 1, 2, 3)])
    with pytest.raises(mc.CorrespondenceError, match="no extent"):
        mc.similarity_fit(source, flat)


def fine_strip(x0):
    """A 1-unit strip whose first ten faces are 0.0005 wide, starting at `x0`."""
    xs = [x0 + 0.0005 * step for step in range(11)] + [x0 + 1]
    positions = [(x, y, 0) for x in xs for y in (0, 1)]
    faces = [(2 * i, 2 * i + 2, 2 * i + 3, 2 * i + 1) for i in range(len(xs) - 1)]
    return positions, faces


def test_per_vertex_tolerance_keeps_fine_sources_far_apart_unambiguous():
    parts, results = [], []
    for x0 in (-200, 200):
        positions, faces = fine_strip(x0)
        parts.append(arrays(positions, faces))
        results.append(arrays(*split(positions, faces)))
    source, offsets = mc.concatenate(parts)
    result, _ = mc.concatenate(results)
    # One radius from the joined extent is wider than the fine faces.
    with pytest.raises(mc.CorrespondenceError, match="ambiguous"):
        mc.match(source, result, mc.position_tolerance(source.co))
    # Each source's own radius resolves every face.
    radii = [2e-4] * (len(source.co) // 3)
    found = mc.match(source, result, radii)
    assert sorted(found.polygons) == list(range(len(source.polygon_starts)))
    with pytest.raises(mc.CorrespondenceError, match="one radius per source vertex"):
        mc.match(source, result, radii[1:])


def test_dense_small_source_beside_a_huge_one_scans_only_its_own_cells():
    # A 50 x 50 lattice 1 mm apart, radius 1e-5, beside a sparse 1 km plane, radius 0.1.
    dense = [(0.001 * i, 0.001 * j, 0) for i in range(50) for j in range(50)]
    huge = [(x, y, 0) for x in (-500, 500) for y in (-500, 500)]
    co = [c for p in (*dense, *huge) for c in p]
    source = mc.MeshArrays(co, [], [], [], [], 0)
    radii = [1e-5] * len(dense) + [0.1] * len(huge)
    buckets = mc._buckets(source, range(len(radii)), radii)
    scanned = sum(len(list(mc._scan(buckets, x, y, z))) for x, y, z in dense)
    # Each dense position meets only its own vertex, not the whole lattice.
    assert scanned <= 2 * len(dense)
    found, unmatched = mc._candidates(source, range(len(radii)), co, range(len(radii)), radii)
    assert unmatched == 0
    assert all(found[vertex] == [vertex] for vertex in range(len(radii)))


# Two coincident quads, each with its own vertices, like touching crate faces.
CARD = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)] * 2


def test_opposite_winding_coincident_faces_resolve_by_winding():
    source = arrays(CARD, [(0, 1, 2, 3), (7, 6, 5, 4)])
    # The result lists the faces swapped, each split and triangulated.
    positions, faces = split(CARD, [(7, 6, 5), (7, 5, 4), (0, 1, 2), (0, 2, 3)])
    found = run(positions, faces, source=source)
    assert list(found.polygons) == [1, 1, 0, 0]
    # A crossed face matching neither winding keeps the reversed reason.
    with pytest.raises(mc.CorrespondenceError, match="1 face with reversed or crossed winding"):
        run(CARD, [(0, 1, 2, 3), (7, 6, 5, 4), (0, 2, 1, 3)], source=source)


def test_same_winding_coincident_faces_stay_ambiguous():
    source = arrays(CARD, [(0, 1, 2, 3), (4, 5, 6, 7)])
    with pytest.raises(mc.CorrespondenceError, match="2 faces on ambiguous coincident"):
        run(CARD, [(0, 1, 2, 3), (4, 5, 6, 7)], source=source)
