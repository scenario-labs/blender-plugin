# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
import math

import pytest

from scenario.core.scene import material_tiling as tiling


def test_tile_size_defaults_to_two_metres_and_accepts_the_range():
    assert tiling.tile_size(None) == 2.0 == tiling.DEFAULT_TILE_SIZE_M
    assert tiling.tile_size(3) == 3.0 and isinstance(tiling.tile_size(3), float)
    assert tiling.tile_size(tiling.MIN_TILE_SIZE_M) == 0.01
    assert tiling.tile_size(tiling.MAX_TILE_SIZE_M) == 1000.0


@pytest.mark.parametrize(
    "value", [0, -1, 0.009, 1000.5, math.inf, -math.inf, math.nan, 10**400, True, "2", [2.0]]
)
def test_tile_size_refuses_values_outside_the_range(value):
    with pytest.raises(ValueError, match="tile_size_m must be a length in Blender units"):
        tiling.tile_size(value)


def test_box_scale_gives_one_repeat_per_tile_in_world_metres():
    # A 40 m plane at 2 m tiles repeats 20 times: 0.5 per unit of an unscaled 40-unit plane.
    assert tiling.box_scale(2.0, (1, 1, 1)) == (0.5, 0.5, 0.5)
    # The same plane as a 2-unit plane scaled to 20 repeats 10 times per object unit.
    assert tiling.box_scale(2.0, (20, 20, 1)) == (10.0, 10.0, 0.5)
    assert tiling.box_scale(0.5, (1, 2, 4)) == (2.0, 4.0, 8.0)


def test_box_scale_reads_the_size_of_a_mirrored_or_flattened_axis():
    assert tiling.box_scale(2.0, (-4, 1, -1)) == (2.0, 0.5, 0.5)
    flat = tiling.box_scale(2.0, (1, 1, 0))
    assert flat[:2] == (0.5, 0.5) and 0 < flat[2] < 1e-6


@pytest.mark.parametrize(
    "scale", [(1, 1, math.nan), (math.inf, 1, 1), (1, 1), (1, 1, 1, 1)], ids=repr
)
def test_box_scale_refuses_an_unusable_object_scale(scale):
    with pytest.raises(ValueError, match="scale is not three finite numbers"):
        tiling.box_scale(2.0, scale)


def test_box_scale_refuses_a_bad_tile_size():
    with pytest.raises(ValueError, match="tile_size_m"):
        tiling.box_scale(0, (1, 1, 1))


def test_polygon_area_of_planar_polygons_in_two_and_three_dimensions():
    assert tiling.polygon_area([(0, 0), (1, 0), (1, 1), (0, 1)]) == pytest.approx(1.0)
    assert tiling.polygon_area([(0, 0), (4, 0), (0, 3)]) == pytest.approx(6.0)
    # Winding does not matter, and a tilted face keeps its true area.
    square = [(0, 0, 0), (0, 2, 0), (2, 2, 2), (2, 0, 2)]
    assert tiling.polygon_area(square) == pytest.approx(2 * math.sqrt(8))
    assert tiling.polygon_area(square[::-1]) == pytest.approx(2 * math.sqrt(8))
    assert tiling.polygon_area([(0, 0, 0), (1, 1, 1)]) == 0.0


def test_uv_metres_per_unit_is_the_median_face_ratio():
    # A 40 m face over the whole 0..1 tile spans 40 m per UV unit.
    assert tiling.uv_metres_per_unit([(1600.0, 1.0)]) == pytest.approx(40.0)
    # Faces whose UVs cover a quarter of the area at the same size span twice the metres.
    assert tiling.uv_metres_per_unit([(4.0, 1.0), (1.0, 0.25)]) == pytest.approx(2.0)
    # One atlas-like outlier does not move the median.
    samples = [(1.0, 1.0)] * 4 + [(1.0, 1e-6)]
    assert tiling.uv_metres_per_unit(samples) == pytest.approx(1.0)
    assert tiling.uv_metres_per_unit([(1.0, 1.0), (9.0, 1.0)]) == pytest.approx(2.0)


def test_uv_metres_per_unit_needs_a_face_with_both_areas():
    assert tiling.uv_metres_per_unit([]) is None
    assert (
        tiling.uv_metres_per_unit([(1.0, 0.0), (0.0, 1.0), (math.nan, 1.0), (1.0, math.inf)])
        is None
    )


def test_a_mesh_without_uvs_gets_box_mapping_scaled_by_its_object_scale():
    mapping = tiling.plan_mapping(2.0, uv=False, object_scale=(20, 20, 1))
    assert mapping == tiling.MaterialMapping("BOX", 2.0, (10.0, 10.0, 0.5), measured=True)
    # Whatever the UV measurement says is not used without UVs.
    assert tiling.plan_mapping(2.0, uv=False, object_scale=(1, 1, 1), metres_per_uv=9).scale == (
        0.5,
        0.5,
        0.5,
    )


def test_a_uv_mesh_scales_its_layout_by_the_measured_metres_per_unit():
    mapping = tiling.plan_mapping(2.0, uv=True, object_scale=(20, 20, 1), metres_per_uv=40.0)
    assert mapping == tiling.MaterialMapping("UV", 2.0, (20.0, 20.0, 20.0), measured=True)


@pytest.mark.parametrize("metres", [None, 0, -3.0, math.inf, math.nan])
def test_a_uv_mesh_without_a_reading_keeps_tiling_one_and_says_so(metres):
    mapping = tiling.plan_mapping(2.0, uv=True, object_scale=(1, 1, 1), metres_per_uv=metres)
    assert mapping == tiling.MaterialMapping("UV", 2.0, (1.0, 1.0, 1.0), measured=False)


def test_plan_mapping_defaults_and_refuses_the_tile_size_like_the_validator():
    assert tiling.plan_mapping(None, uv=False, object_scale=(1, 1, 1)).tile_size == 2.0
    with pytest.raises(ValueError, match="tile_size_m"):
        tiling.plan_mapping(-1, uv=True, object_scale=(1, 1, 1))
