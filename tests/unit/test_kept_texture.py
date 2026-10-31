# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Which faces of a retextured mesh keep the source's own texture."""

import math
from array import array

import pytest

from scenario.core.scene import kept_texture as kt
from scenario.core.scene.mesh_correspondence import MeshArrays

SIDES = 16


def lathe(profile, *, step=0.02, offset=(0.0, 0.0), seam=False):
    """A closed surface of revolution from (height, radius) knots, one ring per `step`.

    seam=True splits every ring's first vertex in two, as a glTF export does at a
    UV seam, so the surface is one piece only once positions are welded.
    """
    bottom, top = profile[0][0], profile[-1][0]
    rings = round((top - bottom) / step) + 1
    points, faces, columns = [], [], SIDES + (1 if seam else 0)
    for ring in range(rings):
        z = bottom + (top - bottom) * ring / (rings - 1)
        for (z0, r0), (z1, r1) in zip(profile, profile[1:], strict=False):
            if z0 <= z <= z1:
                radius = r0 + (r1 - r0) * ((z - z0) / (z1 - z0) if z1 > z0 else 0.0)
                break
        for column in range(columns):
            angle = 2 * math.pi * (column % SIDES) / SIDES
            points.append(
                (offset[0] + radius * math.cos(angle), offset[1] + radius * math.sin(angle), z)
            )
    for ring in range(rings - 1):
        for column in range(SIDES):
            a = ring * columns + column
            b = ring * columns + (column + 1 if seam else (column + 1) % SIDES)
            faces.append((a, b, b + columns, a + columns))
    # Caps close both ends.
    faces.append(tuple(reversed(range(SIDES))))
    faces.append(tuple((rings - 1) * columns + column for column in range(SIDES)))
    return points, faces


def joined(*parts):
    points, faces = [], []
    for part_points, part_faces in parts:
        base = len(points)
        points.extend(part_points)
        faces.extend(tuple(base + vertex for vertex in face) for face in part_faces)
    return points, faces


def arrays(points, faces):
    loops, starts, totals = [], [], []
    for face in faces:
        starts.append(len(loops))
        totals.append(len(face))
        loops.extend(face)
    return MeshArrays(
        array("f", [component for point in points for component in point]),
        array("i", loops),
        array("i", starts),
        array("i", totals),
    )


# A 1.8 m character in one piece: legs and torso, shoulders, a neck, the jaw and head.
ONE_PIECE = [
    (0.0, 0.15),
    (1.30, 0.15),
    (1.32, 0.22),
    (1.44, 0.22),
    (1.48, 0.05),
    (1.56, 0.05),
    (1.60, 0.08),
    (1.62, 0.10),
    (1.74, 0.10),
    (1.80, 0.03),
]
# The same character as generated models often split it: a head-and-neck shell
# with a little chest, and the jacket as its own piece whose collar rises past
# the bottom of the shell.
HEAD_SHELL = [(1.44, 0.09), (1.47, 0.05), (1.56, 0.05)] + ONE_PIECE[6:]
JACKET = [(0.5, 0.17), (1.30, 0.17), (1.32, 0.24), (1.44, 0.24), (1.48, 0.07), (1.50, 0.07)]
HAIR = [(1.70, 0.11), (1.80, 0.11), (1.83, 0.02)]


def kept_vertices(weights, points, threshold=1.0):
    return [points[index] for index, value in enumerate(weights) if value >= threshold]


def test_a_standing_character_is_real_sized_and_taller_than_wide():
    assert kt.standing((0.6, 0.3, 1.8))
    assert kt.standing((30, 20, 180), metres_per_unit=0.01)
    # A table is wider than tall, a tower too tall, a figurine too small.
    assert not kt.standing((1.6, 0.8, 0.75))
    assert not kt.standing((4.0, 4.0, 20.0))
    assert not kt.standing((0.05, 0.05, 0.2))


def test_the_review_starts_on_the_selection_then_a_characters_head():
    assert kt.starting_mode(10, 100, True, True) == kt.SELECTED
    # All faces selected is no choice: an import selects everything.
    assert kt.starting_mode(100, 100, True, True) == kt.HEAD
    assert kt.starting_mode(0, 100, True, True) == kt.HEAD
    assert kt.starting_mode(0, 100, True, False) == kt.NONE
    assert kt.starting_mode(0, 100, False, True) == kt.NONE
    assert kt.starting_mode(5, 100, False, False) == kt.SELECTED


def test_weld_and_pieces_join_a_surface_split_at_seams():
    points, faces = lathe(ONE_PIECE, seam=True)
    welded = kt.weld(points, 1e-6)
    assert len(set(welded)) < len(points)
    assert len(set(kt.pieces(faces, welded))) == 1
    # Unwelded, the seam's duplicated vertices still share no face across it.
    assert len(set(kt.pieces(faces, list(range(len(points)))))) == 1
    two = joined(lathe(ONE_PIECE), lathe(HAIR, offset=(1.0, 0.0)))
    assert len(set(kt.pieces(two[1], kt.weld(two[0], 1e-6)))) == 2


def test_hull_area_measures_a_cross_section():
    assert kt.hull_area([(0, 0), (1, 0), (1, 1), (0, 1), (0.5, 0.5)]) == pytest.approx(1.0)
    assert kt.hull_area([(0, 0), (1, 1)]) == 0.0
    assert kt.hull_area([(0, 0), (1, 1), (2, 2)]) == 0.0


def test_one_piece_character_keeps_its_head_above_the_shoulders_with_a_soft_band():
    points, faces = lathe(ONE_PIECE, seam=True)
    weights = kt.head_weights(points, faces)
    assert weights is not None
    kept = kept_vertices(weights, points)
    # Jaw, neck and head keep their texture; the shoulders and torso take the new one.
    assert min(z for _, _, z in kept) == pytest.approx(1.48, abs=0.07)
    assert max(z for _, _, z in kept) == pytest.approx(1.80)
    assert all(value == 0.0 for value, point in zip(weights, points, strict=True) if point[2] < 1.4)
    # The band between them is soft, not a hard seam.
    assert any(0.0 < value < 1.0 for value in weights)


def test_a_separate_head_shell_is_kept_whole_and_the_jacket_over_its_collar_is_not():
    shell = lathe(HEAD_SHELL)
    jacket = lathe(JACKET)
    hair = lathe(HAIR)
    points, faces = joined(shell, jacket, hair)
    weights = kt.head_weights(points, faces)
    assert weights is not None
    count = len(shell[0])
    assert all(value == 1.0 for value in weights[:count])
    assert all(value == 0.0 for value in weights[count : count + len(jacket[0])])
    # Hair lies above the neck and keeps its texture with the head.
    assert all(value == 1.0 for value in weights[count + len(jacket[0]) :])


@pytest.mark.parametrize(
    "profile",
    [
        # A door or a column: the same section all the way down.
        [(0.0, 0.3), (2.0, 0.3)],
        # A floor lamp: a wide shade over a thin pole that never widens again within reach.
        [(0.0, 0.25), (0.05, 0.25), (0.06, 0.02), (1.5, 0.02), (1.55, 0.25), (1.8, 0.2)],
        # A tree: a wide crown over a trunk that flares only at its roots.
        [(0.0, 0.3), (0.1, 0.08), (1.2, 0.08), (1.3, 0.6), (2.6, 0.5), (3.0, 0.1)],
    ],
)
def test_meshes_with_no_head_keep_nothing(profile):
    points, faces = lathe(profile)
    assert kt.head_weights(points, faces) is None
    region = kt.plan(arrays(points, faces), kt.HEAD)
    assert not region.kept
    assert region.faces == 0
    assert region.note.startswith("No head found on this mesh")
    assert set(region.weights) == {0.0}


def test_a_selection_keeps_its_faces_and_feathers_along_the_surface():
    # A 1 m strip of 100 quads, 1 cm wide each; the first 30 are selected.
    points = [(x / 100, y, 0.0) for x in range(101) for y in (0.0, 0.01)]
    faces = [(2 * i, 2 * i + 2, 2 * i + 3, 2 * i + 1) for i in range(100)]
    selected = [index < 30 for index in range(100)]
    weights = kt.selection_weights(points, faces, selected)
    assert all(weights[2 * i] == 1.0 for i in range(31))
    # The band is 1% of the diagonal, about 1 cm: one quad beyond the selection.
    assert 0.0 <= weights[2 * 31] < 1.0
    assert all(weights[2 * i] == 0.0 for i in range(33, 101))
    region = kt.plan(arrays(points, faces), kt.SELECTED, selected=selected)
    assert region.kept and region.source == "selection"
    # The selected faces, not the feather around them.
    assert region.faces == 30
    assert region.note == "The selected faces keep their texture (30)"


def test_selected_mode_without_a_partial_selection_keeps_nothing():
    points, faces = lathe(ONE_PIECE)
    mesh = arrays(points, faces)
    for selected in (None, [False] * len(faces), [True] * len(faces)):
        region = kt.plan(mesh, kt.SELECTED, selected=selected)
        assert not region.kept
        assert region.note.startswith("No faces selected in Edit Mode")


def test_plan_resolves_the_head_and_none():
    points, faces = lathe(ONE_PIECE, seam=True)
    mesh = arrays(points, faces)
    head = kt.plan(mesh, kt.HEAD)
    assert head.kept and head.source == "head" and head.mode == kt.HEAD
    assert head.faces > 0
    assert head.note == f"The head keeps its texture ({head.faces:,} faces)"
    assert len(head.weights) == len(points)
    nothing = kt.plan(mesh, kt.NONE)
    assert not nothing.kept and nothing.note == "The whole surface takes the new texture"
    with pytest.raises(ValueError):
        kt.plan(mesh, "FACE")


def test_head_bone_weights_replace_the_shape_rule():
    points, faces = lathe(ONE_PIECE)
    bones = [1.0 if z > 1.5 else (0.5 if z > 1.45 else 0.0) for _, _, z in points]
    region = kt.plan(arrays(points, faces), kt.HEAD, head_bones=bones)
    assert region.source == "head_bones"
    assert set(region.weights) == {0.0, 0.5, 1.0}
    # No head weight at all falls back to the shape.
    unweighted = kt.plan(arrays(points, faces), kt.HEAD, head_bones=[0.0] * len(points))
    assert unweighted.source == "head"
    assert kt.bone_weights([0.0, 0.25, 0.5, 0.75, 1.2]).tolist() == [0.0, 0.0, 0.5, 1.0, 1.0]


GLTF = {
    "base_color": ("colour", (0, 1, 2), ("sRGB", False)),
    "normal": ("normal", (0, 1, 2), None),
    "roughness": ("orm", (1,), None),
    "metallic": ("orm", (2,), None),
}


def test_maps_pair_role_by_role_into_the_results_images():
    result = {
        "base_color": ("new colour", (0, 1, 2), ("sRGB", False)),
        "normal": ("new normal", (0, 1, 2), None),
        "roughness": ("new mr", (1,), None),
        "metallic": ("new mr", (2,), None),
    }
    pairs, skipped = kt.pair_maps(GLTF, result)
    assert skipped == {}
    assert pairs == {
        "new colour": [((0, 1, 2), "colour", (0, 1, 2))],
        "new normal": [((0, 1, 2), "normal", (0, 1, 2))],
        "new mr": [((1,), "orm", (1,)), ((2,), "orm", (2,))],
    }


def test_maps_the_result_cannot_take_are_skipped_with_a_reason():
    result = {
        "base_color": ("new colour", (0, 1, 2), ("Linear Rec.709", True)),
        "normal": ("new normal", (0, 1, 2), None),
        "roughness": ("new roughness", (0, 1, 2), None),
    }
    pairs, skipped = kt.pair_maps({"normal": GLTF["normal"]}, result, same_layout=False)
    assert pairs == {}
    assert skipped == {
        "base_color": "the source has no such map",
        "normal": "the result has another UV layout",
        "roughness": "the source has no such map",
    }
    pairs, skipped = kt.pair_maps(GLTF, result)
    assert skipped == {"base_color": "the maps use different colour spaces"}
    # A packed source channel fills every channel of a grey result map.
    assert pairs["new roughness"] == [((0, 1, 2), "orm", (1,))]
