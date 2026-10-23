# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""What makes a built blockout readable at once: a colour per group and a camera and sun to see it with. No bpy.

The Blender builder gives each top-level group a muted colour from PALETTE (deterministic by group order), and,
when the scene has none, adds a three-quarter camera that frames the plan's bounds and one sun light. The maths
lives here so it is testable without Blender: group order, plan bounds, the camera distance that keeps every
corner of the bounds in frame for the render aspect, and the Euler angles that aim a camera or light."""

from math import acos, atan2, cos, radians, sin, sqrt

# Muted viewport colours, picked in sRGB and stored scene-linear, ordered so neighbours differ in hue.
PALETTE = (
    (0.212, 0.366, 0.195),  # sage
    (0.571, 0.216, 0.114),  # terracotta
    (0.159, 0.275, 0.491),  # slate blue
    (0.638, 0.402, 0.084),  # ochre
    (0.584, 0.246, 0.314),  # dusty rose
    (0.114, 0.381, 0.361),  # teal
    (0.328, 0.270, 0.552),  # lavender
    (0.571, 0.462, 0.262),  # sand
    (0.332, 0.150, 0.279),  # plum
    (0.262, 0.323, 0.402),  # steel
    (0.275, 0.328, 0.084),  # moss
    (0.462, 0.130, 0.109),  # brick
)
DEFAULT_GROUP = "Blockout"

# A three-quarter view from the side, a little above, through a moderate wide lens.
AZIMUTH = (
    35.0  # degrees from the -y axis (the side the plan prompt orients its view from) toward +x
)
ELEVATION = 22.0  # degrees above the horizon
LENS = 35.0  # millimetres
SENSOR = 36.0  # millimetres, fitted to the longer side of the render
MARGIN = 0.06  # share of the frame left around the bounds
SUN_AZIMUTH = AZIMUTH - 55.0  # the sun stands to the camera's left, so the near faces are lit
SUN_ELEVATION = 50.0
SUN_STRENGTH = 3.0


def group_name(element):
    """The top-level group an element belongs to."""
    return element.get("group") or DEFAULT_GROUP


def group_order(elements):
    """Group names in order of first appearance, each once."""
    return list(dict.fromkeys(group_name(element) for element in elements))


def group_colour(index):
    """RGBA of the group at `index` in group order; the palette repeats after its last colour."""
    r, g, b = PALETTE[index % len(PALETTE)]
    return (r, g, b, 1.0)


def group_colours(elements):
    """{group name: RGBA} for every group of the plan, by group order."""
    return {name: group_colour(index) for index, name in enumerate(group_order(elements))}


def plan_bounds(elements):
    """((x, y, z) low, (x, y, z) high) enclosing every element, or None for an empty plan.

    An element is its box of `size` centred on `position` and turned by its yaw about Z, which also encloses
    every other primitive (a cylinder, cone, sphere or wedge fits inside its box).
    """
    low = [float("inf")] * 3
    high = [float("-inf")] * 3
    for element in elements:
        position = element.get("position") or (0.0, 0.0, 0.0)
        size = element.get("size") or (1.0, 1.0, 1.0)
        yaw = radians(element.get("rotation", 0.0) or 0.0)
        c, s = abs(cos(yaw)), abs(sin(yaw))
        half = (
            (c * size[0] + s * size[1]) / 2.0,
            (s * size[0] + c * size[1]) / 2.0,
            size[2] / 2.0,
        )
        for axis in range(3):
            low[axis] = min(low[axis], position[axis] - half[axis])
            high[axis] = max(high[axis], position[axis] + half[axis])
    if low[0] == float("inf"):
        return None
    return tuple(low), tuple(high)


def render_aspect(width, height, pixel_x=1.0, pixel_y=1.0):
    """Width over height of the rendered frame, pixel aspect included."""
    return (width * pixel_x) / (height * pixel_y)


def view_tangents(aspect, lens=LENS, sensor=SENSOR):
    """(horizontal, vertical) half-frame tangents of a camera whose sensor fits the longer side."""
    if aspect >= 1.0:
        horizontal = sensor / (2.0 * lens)
        return horizontal, horizontal / aspect
    vertical = sensor / (2.0 * lens)
    return vertical * aspect, vertical


def _direction(azimuth, elevation):
    """Unit vector from the target toward a camera or light at this azimuth and elevation (degrees)."""
    a, e = radians(azimuth), radians(elevation)
    return (sin(a) * cos(e), -cos(a) * cos(e), sin(e))


def look_euler(direction):
    """XYZ Euler (radians) of a camera or light whose -Z axis points along `direction`, with no roll."""
    x, y, z = direction
    length = sqrt(x * x + y * y + z * z)
    x, y, z = x / length, y / length, z / length
    return (acos(max(-1.0, min(1.0, -z))), 0.0, atan2(-x, y))


def _corners(low, high):
    return [
        (x, y, z) for x in (low[0], high[0]) for y in (low[1], high[1]) for z in (low[2], high[2])
    ]


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def frame_camera(low, high, aspect, *, lens=LENS, sensor=SENSOR, margin=MARGIN):
    """A three-quarter camera, slightly above, that keeps the whole box low..high in frame.

    Returns {"location", "rotation", "lens", "clip_start", "clip_end"} for a camera that looks at the box's
    centre. The distance is the smallest that puts all eight corners inside the frame with `margin` to spare
    for a render of this `aspect`, for a pinhole camera (no lens shift).
    """
    centre = tuple((a + b) / 2.0 for a, b in zip(low, high, strict=True))
    toward = _direction(AZIMUTH, ELEVATION)
    forward = (-toward[0], -toward[1], -toward[2])
    right = (forward[1], -forward[0], 0.0)
    norm = sqrt(right[0] ** 2 + right[1] ** 2)
    right = (right[0] / norm, right[1] / norm, 0.0)
    up = (
        right[1] * forward[2] - right[2] * forward[1],
        right[2] * forward[0] - right[0] * forward[2],
        right[0] * forward[1] - right[1] * forward[0],
    )
    tan_h, tan_v = view_tangents(aspect, lens, sensor)
    tan_h, tan_v = tan_h / (1.0 + margin), tan_v / (1.0 + margin)
    offsets = [
        tuple(c - m for c, m in zip(corner, centre, strict=True)) for corner in _corners(low, high)
    ]
    # The camera sits `distance` behind the centre, so a corner at offset o has depth distance + o.forward.
    distance = 0.0
    for offset in offsets:
        depth = _dot(offset, forward)
        distance = max(
            distance,
            abs(_dot(offset, right)) / tan_h - depth,
            abs(_dot(offset, up)) / tan_v - depth,
            1e-3 - depth,
        )
    depths = [distance + _dot(offset, forward) for offset in offsets]
    return {
        "location": tuple(c + t * distance for c, t in zip(centre, toward, strict=True)),
        "rotation": look_euler(forward),
        "lens": lens,
        "clip_start": max(0.001, 0.02 * min(depths)),
        "clip_end": max(100.0, 2.0 * max(depths)),
    }


def frame_sun(low, high):
    """{"location", "rotation"} of a sun above the box, shining from the camera's left and above."""
    centre = tuple((a + b) / 2.0 for a, b in zip(low, high, strict=True))
    radius = sqrt(sum((b - a) ** 2 for a, b in zip(low, high, strict=True))) / 2.0
    toward = _direction(SUN_AZIMUTH, SUN_ELEVATION)
    return {
        "location": tuple(c + t * (radius + 5.0) for c, t in zip(centre, toward, strict=True)),
        "rotation": look_euler(tuple(-t for t in toward)),
    }
