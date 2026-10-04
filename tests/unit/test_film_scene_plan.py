# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Safety, intent preservation, and deterministic local-plan regression tests."""

from __future__ import annotations

import copy
import importlib.util
import json
import math
from pathlib import Path

import pytest

MODULE_PATH = (
    Path(__file__).resolve().parents[2] / "scenario" / "core" / "scene" / "film_scene_plan.py"
)
SPEC = importlib.util.spec_from_file_location(
    "scenario_scene_plan_under_test", MODULE_PATH
)
scene_plan = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(scene_plan)


@pytest.fixture
def plan() -> dict:
    """Use one valid primitive so invalid input cases stay easy to interpret."""
    return {
        "title": "Test scene",
        "objects": [
            {
                "name": "Hero",
                "type": "box",
                "location": [0, 0, 1],
                "scale": [1, 1, 1],
                "rotation": [0, 0, 0],
                "color": [0.1, 0.2, 0.3],
                "role": "hero",
                "bevel": 0.1,
            }
        ],
        "camera": {
            "style": "orbit",
            "lens": 50,
            "duration": 6,
            "target": [0, 0, 1],
            "distance": 8,
            "height": 3,
        },
    }


def test_normalizes_without_mutating_input(plan: dict) -> None:
    original = copy.deepcopy(plan)
    plan["objects"][0]["rotation"] = [720, -450, 45]
    original["objects"][0]["rotation"] = [720, -450, 45]
    result = scene_plan.validate_scene_plan(plan)
    assert result["objects"][0]["rotation"] == [0.0, -90.0, 45.0]
    assert plan == original
    assert result is not plan and result["objects"][0] is not plan["objects"][0]
    assert isinstance(result["camera"]["lens"], float)


@pytest.mark.parametrize(
    "value",
    [float("nan"), float("inf"), -float("inf"), True, False, "2", None, 10**1000],
)
def test_nonfinite_and_ambiguous_numeric_types_rejected(
    plan: dict, value: object
) -> None:
    plan["objects"][0]["location"][0] = value
    with pytest.raises(ValueError):
        scene_plan.validate_scene_plan(plan)


@pytest.mark.parametrize(
    "key,value",
    [
        ("location", [1000.01, 0, 0]),
        ("location", [-1000.01, 0, 0]),
        ("location", [0, 0]),
        ("location", "0,0,0"),
        ("scale", [0, 1, 1]),
        ("scale", [0.009, 1, 1]),
        ("scale", [100.01, 1, 1]),
        ("color", [0, 0, 1.01]),
        ("color", [0, -0.01, 1]),
        ("color", [0, 1]),
        ("bevel", -0.01),
        ("bevel", 0.301),
        ("rotation", [math.nan, 0, 0]),
        ("type", "python"),
        ("type", ["box"]),
        ("role", "execute"),
        ("name", ""),
        ("name", "a" * 201),
        ("name", "bad\nlabel"),
    ],
)
def test_object_schema_rejects_invalid_bounds_types_and_allowlist(
    plan: dict, key: str, value: object
) -> None:
    plan["objects"][0][key] = value
    with pytest.raises(ValueError):
        scene_plan.validate_scene_plan(plan)


@pytest.mark.parametrize(
    "key,value",
    [
        ("style", "execute"),
        ("lens", 17.99),
        ("lens", 120.01),
        ("duration", 0.999),
        ("duration", 30.01),
        ("distance", 1.99),
        ("distance", 100.01),
        ("height", 0.49),
        ("height", 50.01),
        ("target", [0, 0, 1001]),
        ("points", [[0, 0, 0]]),
        ("points", [[0, 0, 0], [1, 2, float("inf")]]),
        ("points", [[0, 0, 0]] * 101),
        ("points", "path"),
    ],
)
def test_camera_schema_bounds(plan: dict, key: str, value: object) -> None:
    plan["camera"][key] = value
    with pytest.raises(ValueError):
        scene_plan.validate_scene_plan(plan)


def test_all_150_objects_are_preserved(plan: dict) -> None:
    plan["objects"] = [
        {**copy.deepcopy(plan["objects"][0]), "name": f"Proxy {i}"} for i in range(150)
    ]
    result = scene_plan.validate_scene_plan(plan)
    assert len(result["objects"]) == 150
    assert result["objects"][-1]["name"] == "Proxy 149"
    plan["objects"].append(plan["objects"][0])
    with pytest.raises(ValueError, match="1 to 150"):
        scene_plan.validate_scene_plan(plan)


@pytest.mark.parametrize("objects", [[], None, {}, "box"])
def test_invalid_object_collections(plan: dict, objects: object) -> None:
    plan["objects"] = objects
    with pytest.raises(ValueError):
        scene_plan.validate_scene_plan(plan)


@pytest.mark.parametrize(
    "location,key,value",
    [
        ("plan", "python", "print('unsafe')"),
        ("object", "operator", "wm.open_mainfile"),
        ("object", "filepath", "/some/file.blend"),
        ("camera", "script", "do_something()"),
    ],
)
def test_unrecognized_instructions_are_rejected(
    plan: dict, location: str, key: str, value: str
) -> None:
    target = (
        plan
        if location == "plan"
        else plan["objects"][0] if location == "object" else plan["camera"]
    )
    target[key] = value
    with pytest.raises(ValueError, match="unsupported keys"):
        scene_plan.validate_scene_plan(plan)


def test_missing_keys_and_non_dictionary_values(plan: dict) -> None:
    for invalid in (None, [], "{}", {1: "no"}):
        with pytest.raises(ValueError):
            scene_plan.validate_scene_plan(invalid)
    plan["objects"][0].pop("role")
    with pytest.raises(ValueError, match="missing"):
        scene_plan.validate_scene_plan(plan)


def test_exact_boundaries_and_all_primitives(plan: dict) -> None:
    plan["objects"] = [
        {
            **plan["objects"][0],
            "type": kind,
            "location": [-1000, 0, 1000],
            "scale": [0.01, 1, 100],
            "color": [0, 1, 0.5, 0],
            "bevel": 0.3,
        }
        for kind in scene_plan.PRIMITIVES
    ]
    result = scene_plan.validate_scene_plan(plan)
    assert len(result["objects"]) == 6
    assert result["objects"][0]["scale"] == [0.01, 1.0, 100.0]


def test_path_requires_points_and_accepts_maximum(plan: dict) -> None:
    plan["camera"]["style"] = "path"
    with pytest.raises(ValueError, match="requires"):
        scene_plan.validate_scene_plan(plan)
    plan["camera"]["points"] = [[i, i, i] for i in range(100)]
    assert len(scene_plan.validate_scene_plan(plan)["camera"]["points"]) == 100


def test_world_schema(plan: dict) -> None:
    plan["world"] = {}
    assert scene_plan.validate_scene_plan(plan)["world"]["strength"] == 0.35
    for invalid in (
        {"strength": -1},
        {"strength": float("nan")},
        {"color": [2, 0, 0]},
        {"url": "https://example.com"},
    ):
        plan["world"] = invalid
        with pytest.raises(ValueError):
            scene_plan.validate_scene_plan(plan)


@pytest.mark.parametrize("preset", sorted(scene_plan.PRESETS))
def test_local_templates_are_valid_deterministic_and_labeled(preset: str) -> None:
    first = scene_plan.local_plan(preset, "warm tall wide crane", 1)
    assert first == scene_plan.local_plan(preset, "warm tall wide crane", 1)
    assert first == scene_plan.validate_scene_plan(first)
    assert first["title"].startswith("Local template:")
    assert first["camera"]["duration"] == 1
    assert 1 <= len(first["objects"]) <= 150
    json.dumps(first, allow_nan=False)


def test_template_keyword_choices_are_real() -> None:
    normal = scene_plan.local_plan("city")
    tall = scene_plan.local_plan("city", "tall")
    assert tall["objects"][3]["scale"] != normal["objects"][3]["scale"] or len(
        tall["objects"]
    ) != len(normal["objects"])
    for keyword in ("red", "green", "forest", "purple", "warm", "sunset", "desert"):
        changed = scene_plan.local_plan("studio", keyword)
        assert (
            changed["objects"][2]["color"]
            != scene_plan.local_plan("studio")["objects"][2]["color"]
        )
    assert (
        scene_plan.local_plan("studio", "night")["world"]["strength"]
        < scene_plan.local_plan()["world"]["strength"]
    )
    assert scene_plan.local_plan("studio", "dolly")["camera"]["style"] == "dolly"
    assert scene_plan.local_plan("studio", "crane")["camera"]["style"] == "crane"
    assert (
        scene_plan.local_plan("studio", "wide")["camera"]["distance"]
        > scene_plan.local_plan()["camera"]["distance"]
    )


@pytest.mark.parametrize("preset", ["unknown", "", None, ["studio"]])
def test_unknown_local_preset_rejected(preset: object) -> None:
    with pytest.raises(ValueError):
        scene_plan.local_plan(preset)


def test_invalid_prompt_and_duration_rejected() -> None:
    with pytest.raises(ValueError):
        scene_plan.local_plan(prompt=1)
    with pytest.raises(ValueError):
        scene_plan.local_plan(duration=math.nan)


def test_prompt_is_data_only() -> None:
    assert "JSON object only" in scene_plan.SCENE_PLAN_PROMPT
    assert "150" in scene_plan.SCENE_PLAN_PROMPT
    assert "Do not use" in scene_plan.SCENE_PLAN_PROMPT
