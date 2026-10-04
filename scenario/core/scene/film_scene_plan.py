# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Bounded, data-only scene plans for editable Blender blockouts.

This module intentionally has no Blender or network dependency. Local templates
are deterministic and are always identified as local templates in their title.
"""

from __future__ import annotations

import math
from typing import Any

PRIMITIVES = frozenset({"box", "sphere", "cylinder", "cone", "torus", "plane"})
ROLES = frozenset({"hero", "environment", "character", "prop"})
CAMERA_STYLES = frozenset({"orbit", "dolly", "crane", "path"})
PRESETS = frozenset({"studio", "architecture", "city", "landscape"})

SCENE_PLAN_PROMPT = """Return one JSON object only, with no Markdown or Python.
Design an editable scene blockout using the following exact schema. Do not use
file paths, scripts, executable code, Blender operators, URLs, or extra keys.
{
  "title": "short descriptive title",
  "objects": [{
    "name": "descriptive unique label",
    "type": "box|sphere|cylinder|cone|torus|plane",
    "location": [x,y,z], "scale": [x,y,z],
    "rotation": [x_degrees,y_degrees,z_degrees],
    "color": [r,g,b] or [r,g,b,a],
    "role": "hero|environment|character|prop", "bevel": 0.06
  }],
  "camera": {
    "style": "orbit|dolly|crane|path", "lens": 50, "duration": 6,
    "target": [x,y,z], "distance": 8, "height": 3,
    "points": [[x,y,z],[x,y,z]]
  },
  "world": {"color": [0.04,0.05,0.08], "strength": 0.35}
}
Use 1 to 150 objects, preserving useful visual intent and composition. Objects
are centered primitives. A box has base dimensions 2x2x2; sphere radius 1;
cylinder radius 1 and depth 2; cone base radius 1 and depth 2; torus major radius
1 and minor radius 0.20; plane is 2x2 in XY. Scale is local to the primitive.
Coordinates are finite numbers in [-1000,1000], scales in [0.01,100], RGBA in
[0,1], and bevel in [0,0.3]. Rotation is finite degrees. All fields shown for
objects are required except bevel. Camera lens is [18,120] mm, duration [1,30]
seconds, distance [2,100], height [0.5,50]. Path points are optional for other
styles, required for path, and contain 2 to 100 coordinate triples. Camera
target is required. World is optional; strength is [0,10], color RGB in [0,1].
Z is up. Use roles and colors deliberately so a legend can describe which
proxies should become final assets. The scene will add lighting and a ground
plane when none is supplied. Do not call a primitive blockout a finished asset.
"""


def _number(value: Any, label: str, low: float, high: float) -> float:
    """Validate a real JSON number without accepting bool or nonfinite values."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a finite number.")
    try:
        result = float(value)
    except (OverflowError, ValueError) as exc:
        raise ValueError(f"{label} must be a finite number.") from exc
    if not math.isfinite(result) or not low <= result <= high:
        raise ValueError(f"{label} must be between {low:g} and {high:g}.")
    return result


def _vector(
    value: Any,
    label: str,
    low: float = -1000.0,
    high: float = 1000.0,
    sizes: tuple[int, ...] = (3,),
) -> list[float]:
    """Normalize a small numeric vector from a JSON array."""
    if not isinstance(value, (list, tuple)) or len(value) not in sizes:
        raise ValueError(f"{label} must contain {' or '.join(map(str, sizes))} numbers.")
    return [_number(item, f"{label}[{i}]", low, high) for i, item in enumerate(value)]


def _label(value: Any, field: str) -> str:
    """Normalize a bounded human label, never interpreting its contents."""
    if not isinstance(value, str) or not value.strip() or len(value) > 200:
        raise ValueError(f"{field} must be a nonempty string of at most 200 characters.")
    if any(ord(char) < 32 for char in value):
        raise ValueError(f"{field} cannot contain control characters.")
    return value.strip()


def _keys(value: Any, allowed: set[str], label: str, required: set[str]) -> dict[str, Any]:
    """Reject unsupported instructions rather than silently discarding them."""
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object.")
    if any(not isinstance(key, str) for key in value):
        raise ValueError(f"{label} keys must be strings.")
    unknown = set(value) - allowed
    missing = required - set(value)
    if unknown:
        raise ValueError(f"{label} contains unsupported keys: {', '.join(sorted(unknown))}.")
    if missing:
        raise ValueError(f"{label} is missing: {', '.join(sorted(missing))}.")
    return value


def _choice(value: Any, options: frozenset[str], label: str) -> str:
    """Validate a string allowlist without coercion."""
    if not isinstance(value, str) or value not in options:
        raise ValueError(f"{label} must be one of {', '.join(sorted(options))}.")
    return value


def validate_scene_plan(plan: dict[str, Any]) -> dict[str, Any]:
    """Return a new, normalized plan or raise ValueError for unsafe input.

    Unknown keys, arbitrary operations, invalid transforms, and ambiguous types
    are rejected. The function never mutates the caller's plan or executes text.
    """
    plan = _keys(
        plan,
        {"title", "objects", "camera", "world"},
        "Plan",
        {"title", "objects", "camera"},
    )
    items = plan["objects"]
    if not isinstance(items, list) or not 1 <= len(items) <= 150:
        raise ValueError("Plan objects must be a list with 1 to 150 objects.")
    required = {"name", "type", "location", "scale", "rotation", "color", "role"}
    normalized: list[dict[str, Any]] = []
    for index, raw in enumerate(items):
        label = f"objects[{index}]"
        item = _keys(raw, required | {"bevel"}, label, required)
        rotation = _vector(item["rotation"], f"{label}.rotation", -math.inf, math.inf)
        normalized.append(
            {
                "name": _label(item["name"], f"{label}.name"),
                "type": _choice(item["type"], PRIMITIVES, f"{label}.type"),
                "location": _vector(item["location"], f"{label}.location"),
                "scale": _vector(item["scale"], f"{label}.scale", 0.01, 100),
                "rotation": [math.fmod(angle, 360.0) for angle in rotation],
                "color": _vector(item["color"], f"{label}.color", 0, 1, (3, 4)),
                "role": _choice(item["role"], ROLES, f"{label}.role"),
                "bevel": _number(item.get("bevel", 0.0), f"{label}.bevel", 0, 0.3),
            }
        )
    camera_keys = {
        "style",
        "lens",
        "duration",
        "target",
        "distance",
        "height",
        "points",
    }
    raw_camera = _keys(plan["camera"], camera_keys, "Camera", camera_keys - {"points"})
    camera: dict[str, Any] = {
        "style": _choice(raw_camera["style"], CAMERA_STYLES, "Camera style"),
        "lens": _number(raw_camera["lens"], "Camera lens", 18, 120),
        "duration": _number(raw_camera["duration"], "Camera duration", 1, 30),
        "target": _vector(raw_camera["target"], "Camera target"),
        "distance": _number(raw_camera["distance"], "Camera distance", 2, 100),
        "height": _number(raw_camera["height"], "Camera height", 0.5, 50),
    }
    if "points" in raw_camera:
        points = raw_camera["points"]
        if not isinstance(points, list) or not 2 <= len(points) <= 100:
            raise ValueError("Camera points must contain 2 to 100 coordinate triples.")
        camera["points"] = [_vector(point, f"Camera points[{i}]") for i, point in enumerate(points)]
    if camera["style"] == "path" and "points" not in camera:
        raise ValueError("Camera path style requires at least two points.")
    result: dict[str, Any] = {
        "title": _label(plan["title"], "Plan title"),
        "objects": normalized,
        "camera": camera,
    }
    if "world" in plan:
        world = _keys(plan["world"], {"color", "strength"}, "World", set())
        result["world"] = {
            "color": _vector(world.get("color", [0.04, 0.05, 0.08]), "World color", 0, 1),
            "strength": _number(world.get("strength", 0.35), "World strength", 0, 10),
        }
    return result


def _object(
    name: str,
    kind: str,
    location: tuple[float, float, float],
    scale: tuple[float, float, float],
    color: tuple[float, ...],
    role: str = "prop",
    rotation: tuple[float, float, float] = (0.0, 0.0, 0.0),
    bevel: float = 0.04,
) -> dict[str, Any]:
    """Create a template primitive using the same schema as remote plans."""
    return {
        "name": name,
        "type": kind,
        "location": list(location),
        "scale": list(scale),
        "rotation": list(rotation),
        "color": list(color),
        "role": role,
        "bevel": bevel,
    }


def local_plan(preset: str = "studio", prompt: str = "", duration: float = 6.0) -> dict[str, Any]:
    """Build a deterministic local template, without a network request.

    Keyword choices: red, purple, green/forest, warm/sunset/desert set the accent
    palette; night dims the environment; tall adds height to city/architecture;
    wide increases camera distance; dolly or crane chooses that camera movement.
    Other text is not claimed to be understood by these local templates.
    """
    _choice(preset, PRESETS, "Local preset")
    if not isinstance(prompt, str):
        raise ValueError("Template prompt must be text.")
    duration = _number(duration, "Duration", 1, 30)
    words = set(prompt.lower().replace(",", " ").replace("-", " ").split())
    accent = (0.018, 0.38, 0.72)
    if words & {"warm", "sunset", "desert"}:
        accent = (0.72, 0.24, 0.095)
    if words & {"green", "forest"}:
        accent = (0.12, 0.46, 0.27)
    if "purple" in words:
        accent = (0.40, 0.13, 0.67)
    if "red" in words:
        accent = (0.70, 0.055, 0.08)
    dark, pale, stone = (0.028, 0.04, 0.065), (0.76, 0.80, 0.84), (0.33, 0.38, 0.44)
    items: list[dict[str, Any]] = []
    if preset == "studio":
        title = "Prism Audio Studio"
        target, distance, height = [0, 0, 1.5], 7.7, 3.0
        items = [
            _object(
                "Stage / graphite",
                "plane",
                (0, 0, -0.075),
                (100, 100, 1),
                dark,
                "environment",
                bevel=0,
            ),
            _object(
                "Pedestal / lower disc",
                "cylinder",
                (0, 0, 0.08),
                (1.65, 1.65, 0.08),
                (0.06, 0.08, 0.12),
            ),
            _object(
                "Pedestal / light reveal",
                "cylinder",
                (0, 0, 0.18),
                (1.57, 1.57, 0.035),
                accent,
            ),
            _object("Pedestal / top", "cylinder", (0, 0, 0.27), (1.61, 1.61, 0.065), stone),
            _object(
                "Prism / enclosure",
                "box",
                (0, 0, 1.52),
                (0.66, 0.40, 1.15),
                (0.045, 0.07, 0.105),
                "hero",
                bevel=0.16,
            ),
            _object(
                "Prism / front baffle",
                "box",
                (0, -0.409, 1.53),
                (0.59, 0.022, 1.035),
                (0.018, 0.025, 0.04),
                "hero",
                bevel=0.06,
            ),
            _object(
                "Prism / woofer rim",
                "torus",
                (0, -0.45, 1.17),
                (0.36, 0.36, 0.20),
                accent,
                "hero",
                (90, 0, 0),
                0,
            ),
            _object(
                "Prism / woofer cone",
                "cylinder",
                (0, -0.447, 1.17),
                (0.337, 0.337, 0.025),
                (0.025, 0.035, 0.05),
                "hero",
                (90, 0, 0),
                0.02,
            ),
            _object(
                "Prism / woofer center",
                "sphere",
                (0, -0.479, 1.17),
                (0.14, 0.07, 0.14),
                (0.08, 0.105, 0.14),
                "hero",
                bevel=0,
            ),
            _object(
                "Prism / tweeter rim",
                "torus",
                (0, -0.45, 2.02),
                (0.18, 0.18, 0.15),
                stone,
                "hero",
                (90, 0, 0),
                0,
            ),
            _object(
                "Prism / tweeter",
                "sphere",
                (0, -0.45, 2.02),
                (0.145, 0.07, 0.145),
                dark,
                "hero",
                bevel=0,
            ),
            _object(
                "Prism / indicator",
                "sphere",
                (0, -0.46, 2.36),
                (0.035, 0.012, 0.012),
                accent,
                "hero",
                bevel=0,
            ),
            _object(
                "Prism / top dial",
                "cylinder",
                (0.37, 0, 2.69),
                (0.09, 0.09, 0.035),
                stone,
                "hero",
            ),
            _object(
                "Set / architectural halo",
                "torus",
                (8.5, 11.0, 1.0),
                (4.8, 4.8, 0.7),
                (0.09, 0.16, 0.22),
                "environment",
                (90, 0, 0),
                0,
            ),
            _object(
                "Set / left plinth",
                "box",
                (-3.0, 1.3, 0.75),
                (0.38, 0.38, 0.8),
                (0.085, 0.16, 0.24),
                "environment",
                (0, 0, -12),
                0.12,
            ),
            _object(
                "Set / accent sphere",
                "sphere",
                (-3.0, 1.3, 1.84),
                (0.3, 0.3, 0.3),
                accent,
                "prop",
                bevel=0,
            ),
            _object(
                "Set / right low block",
                "box",
                (2.8, 1.4, 0.22),
                (0.7, 0.5, 0.26),
                (0.11, 0.17, 0.24),
                "environment",
                (0, 0, 8),
                0.12,
            ),
        ]
    elif preset == "architecture":
        title = "Courtyard Pavilion"
        target, distance, height = [0, -0.3, 1.1], 18.5, 6.0
        roof = 4.0 if "tall" in words else 3.2
        items = [
            _object(
                "Terrain / courtyard",
                "plane",
                (0, 0, -0.12),
                (100, 100, 1),
                (0.28, 0.32, 0.31),
                "environment",
                bevel=0,
            ),
            _object(
                "Pavilion / foundation",
                "box",
                (0, 0, 0.16),
                (4.2, 2.8, 0.23),
                pale,
                "hero",
                bevel=0.06,
            ),
            _object(
                "Pavilion / floating roof",
                "box",
                (0, 0, roof),
                (4.4, 2.9, 0.16),
                pale,
                "hero",
                bevel=0.045,
            ),
            _object(
                "Pavilion / rear wall",
                "box",
                (0, 2.2, roof / 2),
                (3.9, 0.14, roof / 2 - 0.15),
                (0.61, 0.52, 0.39),
                "hero",
            ),
            _object(
                "Pavilion / service volume",
                "box",
                (2.75, 0.8, roof / 2),
                (0.85, 1.4, roof / 2 - 0.15),
                accent,
                "hero",
                bevel=0.07,
            ),
            _object(
                "Water / reflecting pool",
                "box",
                (-1.4, -4.2, -0.005),
                (3.0, 1.1, 0.045),
                (0.045, 0.16, 0.22),
                "environment",
                bevel=0.01,
            ),
        ]
        for x in (-3.4, 0.2, 3.4):
            items.append(
                _object(
                    f"Pavilion / column {x:g}",
                    "box",
                    (x, -1.8, roof / 2),
                    (0.065, 0.065, roof / 2),
                    dark,
                    "hero",
                    bevel=0.015,
                )
            )
        for i in range(3):
            items.append(
                _object(
                    f"Entry / step {i + 1}",
                    "box",
                    (1.5, -3.05 - i * 0.36, 0.20 - i * 0.07),
                    (1.2, 0.32, 0.07),
                    pale,
                )
            )
        for i, (x, y) in enumerate(((-5.4, 1.5), (5.3, 2.8), (-5.8, -3.0))):
            items.extend(
                [
                    _object(
                        f"Tree {i + 1} / trunk",
                        "cylinder",
                        (x, y, 0.9),
                        (0.09, 0.09, 0.9),
                        (0.23, 0.15, 0.09),
                        "environment",
                    ),
                    _object(
                        f"Tree {i + 1} / canopy",
                        "sphere",
                        (x, y, 2.25),
                        (0.85, 0.8, 1.05),
                        (0.15, 0.31, 0.22),
                        "environment",
                        bevel=0,
                    ),
                ]
            )
        items.extend(
            [
                _object(
                    "Scale person / body",
                    "cylinder",
                    (0.1, -2.1, 0.98),
                    (0.17, 0.17, 0.52),
                    accent,
                    "character",
                ),
                _object(
                    "Scale person / head",
                    "sphere",
                    (0.1, -2.1, 1.67),
                    (0.17, 0.17, 0.17),
                    pale,
                    "character",
                    bevel=0,
                ),
            ]
        )
    elif preset == "city":
        title = "Blue Hour City District"
        target, distance, height = [0, 0, 2.0], 30.0, 14.0
        items = [
            _object(
                "District / terrain",
                "plane",
                (0, 0, -0.15),
                (100, 100, 1),
                (0.06, 0.09, 0.125),
                "environment",
                bevel=0,
            )
        ]
        for i, x in enumerate((-5.4, -1.8, 1.8, 5.4)):
            for j, y in enumerate((-4.0, 0.0, 4.0)):
                z = 1.25 + ((i * 7 + j * 3) % 6) * (0.62 if "tall" in words else 0.4)
                color = (
                    accent
                    if (i + j) % 4 == 0
                    else (0.16 + i * 0.025, 0.23 + j * 0.035, 0.32 + i * 0.025)
                )
                items.append(
                    _object(
                        f"Block {i + 1}{j + 1} / tower",
                        "box",
                        (x, y, z),
                        (1.13, 1.3, z),
                        color,
                        "hero" if i == 2 and j == 1 else "environment",
                        bevel=0.08,
                    )
                )
                items.append(
                    _object(
                        f"Block {i + 1}{j + 1} / roof",
                        "box",
                        (x, y, z * 2 + 0.12),
                        (0.75, 0.85, 0.12),
                        dark,
                        "prop",
                        bevel=0.025,
                    )
                )
                for floor in range(1, int(z * 2)):
                    items.append(
                        _object(
                            f"Block {i + 1}{j + 1} / facade {floor}",
                            "box",
                            (x, y - 1.315, floor * 0.85),
                            (0.9, 0.015, 0.055),
                            pale if (i + j + floor) % 3 == 0 else stone,
                            "prop",
                            bevel=0,
                        )
                    )
        for i, x in enumerate((-3.6, 0.0, 3.6)):
            items.append(
                _object(
                    f"Road / avenue {i + 1}",
                    "box",
                    (x, 0, -0.09),
                    (0.51, 8, 0.025),
                    (0.025, 0.035, 0.045),
                    "environment",
                    bevel=0,
                )
            )
        for i, y in enumerate((-2.0, 2.0)):
            items.append(
                _object(
                    f"Road / cross street {i + 1}",
                    "box",
                    (0, y, -0.055),
                    (8, 0.45, 0.025),
                    (0.025, 0.035, 0.045),
                    "environment",
                    bevel=0,
                )
            )
        items.append(
            _object(
                "Plaza / beacon",
                "cylinder",
                (8.0, 2.5, 2.1),
                (0.6, 0.6, 2.1),
                accent,
                "hero",
            )
        )
    else:
        title = "Terraced Monolith Landscape"
        target, distance, height = [0, 0, 1.25], 22.0, 8.0
        sand = (0.52, 0.38, 0.24) if words & {"desert", "warm", "sunset"} else (0.20, 0.29, 0.25)
        items = [
            _object(
                "Landscape / horizon",
                "plane",
                (0, 0, -0.2),
                (100, 100, 1),
                sand,
                "environment",
                bevel=0,
            )
        ]
        for i in range(5):
            items.append(
                _object(
                    f"Terrain / terrace {i + 1}",
                    "cylinder",
                    (0, 0, 0.1 + i * 0.18),
                    (7.2 - i, 5.4 - i * 0.68, 0.22),
                    tuple(channel + i * 0.025 for channel in sand),
                    "environment",
                    (0, 0, i * 7),
                    0.09,
                )
            )
        items.append(
            _object(
                "Monolith / portal",
                "torus",
                (0, 0, 3.15),
                (1.55, 1.55, 0.6),
                accent,
                "hero",
                (90, 0, 0),
                0,
            )
        )
        for i, (x, y) in enumerate(((-4, 1), (3.5, 2), (-3.2, -2), (2.8, -2.5))):
            items.extend(
                [
                    _object(
                        f"Stone {i + 1} / base",
                        "sphere",
                        (x, y, 0.65),
                        (0.8, 0.5, 0.6),
                        stone,
                        "prop",
                        (0, 20, i * 22),
                        0,
                    ),
                    _object(
                        f"Tree {i + 1} / crown",
                        "cone",
                        (x - 0.7, y + 0.2, 1.5),
                        (0.55, 0.55, 1.3),
                        (0.08, 0.18, 0.13),
                        "environment",
                        bevel=0,
                    ),
                ]
            )
    style = "crane" if "crane" in words else "dolly" if "dolly" in words else "orbit"
    if "wide" in words:
        distance *= 1.2
    return validate_scene_plan(
        {
            "title": f"Local template: {title}",
            "objects": items,
            "camera": {
                "style": style,
                "lens": 50,
                "duration": duration,
                "target": target,
                "distance": distance,
                "height": height,
            },
            "world": {
                "color": [0.055, 0.075, 0.11],
                "strength": 0.08 if "night" in words else 0.35,
            },
        }
    )
