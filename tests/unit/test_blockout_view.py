# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
import colorsys
import math

import pytest

from scenario.core.scene import blockout_view as view


def _el(group=None, position=(0.0, 0.0, 0.5), size=(1.0, 1.0, 1.0), rotation=0.0):
    element = {"position": list(position), "size": list(size), "rotation": rotation}
    if group is not None:
        element["group"] = group
    return element


def _srgb(linear):
    return 12.92 * linear if linear <= 0.0031308 else 1.055 * linear ** (1 / 2.4) - 0.055


def _sub(a, b):
    return tuple(x - y for x, y in zip(a, b, strict=True))


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b, strict=True))


def _basis(camera):
    """Right, up and forward unit vectors of a camera from its XYZ Euler (looks down -Z, up is +Y)."""
    rx, _, rz = camera["rotation"]
    cx, sx, cz, sz = math.cos(rx), math.sin(rx), math.cos(rz), math.sin(rz)
    # Rz @ Rx applied to the local X, Y and -Z axes.
    right = (cz, sz, 0.0)
    up = (-sz * cx, cz * cx, sx)
    forward = (-sz * sx, cz * sx, -cx)
    return right, up, forward


def _project(camera, aspect, point):
    """Normalised (0..1) frame position and depth of a point, with the camera's lens shift."""
    right, up, forward = _basis(camera)
    offset = _sub(point, camera["location"])
    depth = _dot(offset, forward)
    tan_h, tan_v = view.view_tangents(aspect, camera["lens"])
    longer = 2 * max(tan_h, tan_v)  # the shift's unit: the longer side of the frame
    shift_x, shift_y = camera["shift"]
    return (
        0.5 + (_dot(offset, right) / depth - shift_x * longer) / (2 * tan_h),
        0.5 + (_dot(offset, up) / depth - shift_y * longer) / (2 * tan_v),
        depth,
    )


def _corners(low, high):
    return [
        (x, y, z) for x in (low[0], high[0]) for y in (low[1], high[1]) for z in (low[2], high[2])
    ]


def test_group_order_is_first_appearance_and_default_group_is_blockout():
    elements = [_el("Tower"), _el("Ground"), _el("Tower"), _el(), _el("Ground")]
    assert view.group_order(elements) == ["Tower", "Ground", "Blockout"]
    assert view.group_name({"group": ""}) == "Blockout"


def test_group_colours_follow_group_order_and_never_depend_on_the_names():
    one = view.group_colours([_el("B"), _el("A"), _el("C")])
    other = view.group_colours([_el("x"), _el("y"), _el("z")])
    assert list(one) == ["B", "A", "C"]
    assert list(one.values()) == list(other.values())
    assert list(one.values()) == [view.group_colour(0), view.group_colour(1), view.group_colour(2)]


def test_kept_groups_keep_their_colour_and_new_groups_take_unused_ones():
    kept = {"A": view.group_colour(0), "C": view.group_colour(1)}
    colours = view.group_colours([_el("C"), _el("New"), _el("A")], kept)
    assert colours["A"] == view.group_colour(0)
    assert colours["C"] == view.group_colour(1)
    assert colours["New"] == view.group_colour(2)
    # Colours read back from Blender are float32: they still count as taken.
    near = {"A": tuple(value + 1e-5 for value in view.group_colour(0)[:3]) + (1.0,)}
    assert view.group_colours([_el("New"), _el("A")], near)["New"] == view.group_colour(1)


def test_palette_is_distinct_muted_and_repeats_after_its_last_colour():
    colours = [view.group_colour(i) for i in range(len(view.PALETTE))]
    assert len(set(colours)) == len(view.PALETTE)
    assert all(colour[3] == 1.0 for colour in colours)
    assert view.group_colour(len(view.PALETTE)) == view.group_colour(0)
    assert view.group_colour(len(view.PALETTE) + 3) == view.group_colour(3)
    for colour in colours:
        # As the viewport shows them (sRGB): soft, not pure primaries, neither dark nor glaring.
        _, saturation, value = colorsys.rgb_to_hsv(*(_srgb(c) for c in colour[:3]))
        assert 0.15 <= saturation <= 0.65
        assert 0.55 <= value <= 0.9
    # Colours next to each other in group order are easy to tell apart.
    for a, b in zip(colours, colours[1:], strict=False):
        assert max(abs(x - y) for x, y in zip(a[:3], b[:3], strict=True)) > 0.1


def test_plan_bounds_of_nothing_is_none():
    assert view.plan_bounds([]) is None


def test_plan_bounds_encloses_every_element_turned_by_its_yaw():
    elements = [
        _el(position=(0, 0, 0.5), size=(4, 2, 1)),
        _el(position=(10, 5, 3), size=(2, 6, 6), rotation=90),  # a quarter turn swaps x and y
        _el(position=(-3, -2, 1), size=(2, 2, 2), rotation=45),  # a diagonal box is wider
    ]
    low, high = view.plan_bounds(elements)
    assert low[0] == pytest.approx(min(-2, 10 - 3, -3 - math.sqrt(2)))
    assert high[0] == pytest.approx(10 + 3)
    assert high[1] == pytest.approx(5 + 1)
    assert low[1] == pytest.approx(-2 - math.sqrt(2))
    assert (low[2], high[2]) == pytest.approx((0.0, 6.0))


def test_plan_bounds_uses_the_builders_defaults_for_missing_values():
    assert view.plan_bounds([{}]) == ((-0.5, -0.5, -0.5), (0.5, 0.5, 0.5))


def test_render_aspect_includes_pixel_aspect():
    assert view.render_aspect(1920, 1080) == pytest.approx(16 / 9)
    assert view.render_aspect(1080, 1920) == pytest.approx(9 / 16)
    assert view.render_aspect(1000, 1000, 2.0, 1.0) == pytest.approx(2.0)


def test_view_tangents_fit_the_sensor_to_the_longer_side():
    horizontal, vertical = view.view_tangents(2.0, lens=36.0, sensor=36.0)
    assert (horizontal, vertical) == pytest.approx((0.5, 0.25))
    horizontal, vertical = view.view_tangents(0.5, lens=36.0, sensor=36.0)
    assert (horizontal, vertical) == pytest.approx((0.25, 0.5))


@pytest.mark.parametrize(
    "direction",
    [(0, 1, 0), (1, 0, 0), (-1, -1, -1), (0.3, -0.8, -0.4), (0, 0, -1), (0.2, 0.9, 0.1)],
)
def test_look_euler_points_the_minus_z_axis_along_the_direction(direction):
    rx, ry, rz = view.look_euler(direction)
    assert ry == 0.0  # no roll
    length = math.sqrt(sum(c * c for c in direction))
    want = tuple(c / length for c in direction)
    # Rz(rz) @ Rx(rx) applied to (0, 0, -1)
    got = (-math.sin(rx) * math.sin(rz), math.sin(rx) * math.cos(rz), -math.cos(rx))
    assert got == pytest.approx(want, abs=1e-9)


@pytest.mark.parametrize("aspect", [16 / 9, 1.0, 9 / 16, 2.39, 4 / 3])
@pytest.mark.parametrize(
    "bounds",
    [
        ((-20, -12, -0.1), (20, 12, 0.0)),  # a ground slab
        ((-50, -30, -0.1), (50, 30, 10)),  # a wide scene with a tower
        ((-0.5, -0.5, 0), (0.5, 0.5, 1)),  # one crate
        ((100, -200, 5), (130, -150, 40)),  # far from the origin
        ((-1000, -1000, 0), (1000, 1000, 120)),  # the largest plan
    ],
)
def test_the_camera_keeps_every_corner_in_frame_with_room_to_spare(aspect, bounds):
    camera = view.frame_camera(*bounds, aspect)
    margin = view.MARGIN
    worst = 0.0
    for corner in _corners(*bounds):
        x, y, depth = _project(camera, aspect, corner)
        assert camera["clip_start"] < depth < camera["clip_end"]
        for axis in (x, y):
            assert 0.0 <= axis <= 1.0
            worst = max(worst, abs(axis - 0.5))
    # The framing is the tightest that fits: some corner sits on the margin, none outside it.
    assert worst == pytest.approx(0.5 / (1 + margin), abs=1e-6)


@pytest.mark.parametrize("aspect", [16 / 9, 9 / 16])
def test_a_flat_plan_seen_from_above_is_centred_in_the_frame(aspect):
    bounds = ((-20, -12, -0.1), (20, 12, 0.5))
    camera = view.frame_camera(*bounds, aspect)
    projected = [_project(camera, aspect, corner) for corner in _corners(*bounds)]
    for axis in (0, 1):
        values = [point[axis] for point in projected]
        assert (min(values) + max(values)) / 2 == pytest.approx(0.5, abs=1e-6)
    assert camera["shift"][1] < 0  # the frame moves down to the ground
    assert camera["lens"] >= view.LENS


def test_the_camera_looks_at_the_middle_from_the_side_and_slightly_above():
    low, high = (-10, -5, 0), (30, 15, 8)
    camera = view.frame_camera(low, high, 16 / 9)
    centre = tuple((a + b) / 2 for a, b in zip(low, high, strict=True))
    _, _, forward = _basis(camera)
    offset = _sub(centre, camera["location"])
    distance = math.sqrt(_dot(offset, offset))
    assert tuple(c / distance for c in offset) == pytest.approx(forward, abs=1e-9)
    location = _sub(camera["location"], centre)
    assert location[0] > 0 and location[1] < 0  # a three-quarter view from the -y, +x side
    elevation = math.degrees(math.atan2(location[2], math.hypot(location[0], location[1])))
    assert elevation == pytest.approx(view.ELEVATION)
    azimuth = math.degrees(math.atan2(location[0], -location[1]))
    assert azimuth == pytest.approx(view.AZIMUTH)


def test_a_portrait_frame_needs_a_longer_distance_than_a_wide_one():
    bounds = ((-30, -10, 0), (30, 10, 10))
    wide = view.frame_camera(*bounds, 16 / 9)["location"]
    tall = view.frame_camera(*bounds, 9 / 16)["location"]
    assert math.dist(tall, (0, 0, 5)) > math.dist(wide, (0, 0, 5))


def test_the_sun_shines_down_toward_the_scene_from_the_cameras_left():
    low, high = (-10, -5, 0), (30, 15, 8)
    sun = view.frame_sun(low, high)
    rx, _, rz = sun["rotation"]
    travel = (-math.sin(rx) * math.sin(rz), math.sin(rx) * math.cos(rz), -math.cos(rx))
    assert travel[2] < 0  # shines downward
    centre = (10, 5, 4)
    to_centre = _sub(centre, sun["location"])
    length = math.sqrt(_dot(to_centre, to_centre))
    assert tuple(c / length for c in to_centre) == pytest.approx(travel, abs=1e-9)
    camera = view.frame_camera(low, high, 16 / 9)
    right, _, _ = _basis(camera)
    assert _dot(_sub(sun["location"], centre), right) < 0  # on the camera's left
