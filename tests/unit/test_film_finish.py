# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Composition timing, scoped sources and bounded audio planning without service I/O."""

import copy
from dataclasses import replace
from fractions import Fraction

import pytest

from scenario.core.jobs.store import JobScope
from scenario.core.scene.film_finish import AudioDuration, compose_recipe, compose_task
from scenario.core.scene.film_plan import TaskAssets, resolve_references, validate_film_plan
from scenario.core.scene.film_scene_plan import local_plan

SCOPE = JobScope("https://fixture.invalid/v1", "account")


def fixture():
    recipe = {
        "title": "Composition fixture",
        "fps": 30,
        "shots": [
            {
                "id": f"s{i}",
                "title": f"Shot {i}",
                "duration": duration,
                "scene": local_plan("studio", "", duration),
                "source_trim": 1,
                "source_duration": 6,
                "native_audio_volume": 0.75,
            }
            for i, duration in enumerate((2, 3))
        ],
        "tasks": [
            {"id": tid, "title": tid, "kind": "upload"}
            for tid in ("s0-video", "s1-video", "s0-previs", "s1-previs", "score", "voice")
        ],
    }
    records = {t["id"]: TaskAssets(SCOPE, ("asset-" + t["id"],)) for t in recipe["tasks"]}
    frames = {"score": AudioDuration(SCOPE, "asset-score", Fraction(2))}
    return recipe, records, frames


def test_exact_cut_and_audio_loops_make_an_unpaid_recipe_without_mutating_inputs():
    recipe, records, frames = fixture()
    before = copy.deepcopy(recipe)
    draft = compose_recipe(recipe, records, scope=SCOPE, audio_durations=frames)
    assert recipe == before
    assert draft["tasks"][:-1] == recipe["tasks"]
    master = draft["tasks"][-1]
    assert master["id"] == "final-master"
    assert master["model"] == "model_scenario-compose-video"
    params = master["parameters"]
    assert (params["duration"], params["fps"]) == (5, 30)
    assert [
        (layer["startTime"], layer["endTime"], layer["trimStart"]) for layer in params["layers"]
    ] == [
        (0, 2, 1),
        (2, 5, 1),
        (0, 2, 0),
        (2, 4, 0),
        (4, 5, 0),
    ]
    assert [layer["volume"] for layer in params["layers"]] == [0.75, 0.75, 0.4, 0.4, 0.4]
    assert all(not layer.get("loop", False) for layer in params["layers"])
    resolved = resolve_references(params, records, scope=SCOPE)
    assert resolved["layers"][0]["source"] == "asset-s0-video"
    assert params["layers"][0]["source"] == "$s0-video"
    assert validate_film_plan(draft)["total_frames"] == 150


def test_previs_uses_explicit_take_zero_trim_and_no_score_or_audio_measurement():
    recipe, records, _ = fixture()
    recipe["shots"][0]["previs_task"] = "s1-previs"
    recipe["previs_master_task"] = "previs-review-v2"
    task = compose_task(recipe, records, scope=SCOPE, mode="previs")
    assert task["id"] == "previs-review-v2"
    assert len(task["parameters"]["layers"]) == 2
    assert all(
        layer["trimStart"] == 0 and layer["volume"] == 1 for layer in task["parameters"]["layers"]
    )
    assert task["parameters"]["layers"][0]["source"] == "$s1-previs"


def test_explicit_empty_audio_tracks_means_silent_mix_without_implicit_score():
    recipe, records, _ = fixture()
    recipe["audio_tracks"] = []
    assert len(compose_task(recipe, records, scope=SCOPE)["parameters"]["layers"]) == 2


def test_duck_boundaries_preserve_loop_phase_and_absolute_volume():
    recipe, records, frames = fixture()
    recipe["audio_tracks"] = [
        {
            "id": "bed",
            "task": "score",
            "kind": "music",
            "start": 0,
            "end": 5,
            "trim_start": 1,
            "loop": True,
            "volume": 0.8,
            "duck": [{"start": 2, "end": 4, "volume": 0.2}],
        }
    ]
    layers = compose_task(recipe, records, scope=SCOPE, audio_durations=frames)["parameters"][
        "layers"
    ][2:]
    assert [
        (layer["startTime"], layer["endTime"], layer["trimStart"], layer["volume"])
        for layer in layers
    ] == [
        (0, 1, 1, 0.8),
        (1, 2, 0, 0.8),
        (2, 3, 1, 0.2),
        (3, 4, 0, 0.2),
        (4, 5, 1, 0.8),
    ]


def test_finite_dialogue_cannot_overrun_measured_source():
    recipe, records, frames = fixture()
    recipe["audio_tracks"] = [
        {"id": "line", "task": "voice", "kind": "dialogue", "start": 1, "end": 4, "trim_start": 1}
    ]
    frames["voice"] = AudioDuration(SCOPE, "asset-voice", Fraction(119, 30))
    with pytest.raises(ValueError, match="beyond"):
        compose_task(recipe, records, scope=SCOPE, audio_durations=frames)
    frames["voice"] = replace(frames["voice"], seconds=Fraction(4))
    layer = compose_task(recipe, records, scope=SCOPE, audio_durations=frames)["parameters"][
        "layers"
    ][-1]
    assert (layer["startTime"], layer["endTime"], layer["trimStart"]) == (1, 4, 1)


@pytest.mark.parametrize("dimension", ["service", "account_id", "project_id", "team_id"])
def test_every_scope_dimension_is_checked_for_picture_and_audio(dimension):
    recipe, records, frames = fixture()
    other = replace(
        SCOPE, **{dimension: "https://other.invalid" if dimension == "service" else "other"}
    )
    for task in ("s0-video", "score"):
        foreign = dict(records, **{task: TaskAssets(other, records[task].asset_ids)})
        with pytest.raises(ValueError, match="scope"):
            compose_task(recipe, foreign, scope=SCOPE, audio_durations=frames)
    with pytest.raises(ValueError, match="Measure"):
        compose_task(
            recipe,
            records,
            scope=SCOPE,
            audio_durations={"score": replace(frames["score"], scope=other)},
        )


@pytest.mark.parametrize("change", ["missing", "ambiguous", "untyped", "undeclared"])
def test_source_observations_cannot_guess_a_take(change):
    recipe, records, frames = fixture()
    if change == "missing":
        del records["s0-video"]
    elif change == "ambiguous":
        records["s0-video"] = TaskAssets(SCOPE, ("one", "two"))
    elif change == "untyped":
        records["s0-video"] = {"asset_ids": ["one"], "project_id": None}
    else:
        recipe["tasks"] = [t for t in recipe["tasks"] if t["id"] != "s0-video"]
    with pytest.raises(ValueError):
        compose_task(recipe, records, scope=SCOPE, audio_durations=frames)


@pytest.mark.parametrize("change", ["missing", "asset", "untyped"])
def test_audio_measurement_is_bound_to_selected_asset(change):
    recipe, records, frames = fixture()
    if change == "missing":
        frames = {}
    elif change == "asset":
        frames["score"] = replace(frames["score"], asset_id="previous-score")
    else:
        frames["score"] = 60
    with pytest.raises(ValueError, match="Measure"):
        compose_task(recipe, records, scope=SCOPE, audio_durations=frames)


@pytest.mark.parametrize("value", [True, 0, -1, 3.5, Fraction(0), Fraction(-1), Fraction(86401)])
def test_audio_measurement_rejects_inexact_or_invalid_durations(value):
    with pytest.raises(ValueError):
        AudioDuration(SCOPE, "asset", value)


def test_layer_limit_rejects_an_excessive_mix_without_truncating_it():
    recipe, records, frames = fixture()
    frames["score"] = replace(frames["score"], seconds=Fraction(3, 30))
    with pytest.raises(ValueError, match="50"):
        compose_task(recipe, records, scope=SCOPE, audio_durations=frames)
    frames["score"] = replace(frames["score"], seconds=Fraction(4, 30))
    assert (
        len(
            compose_task(recipe, records, scope=SCOPE, audio_durations=frames)["parameters"][
                "layers"
            ]
        )
        == 40
    )


@pytest.mark.parametrize(
    ("shot_count", "mode", "with_score", "accepted"),
    [
        (49, "final", True, True),
        (50, "final", True, False),
        (50, "final", False, True),
        (50, "previs", True, True),
    ],
)
def test_shots_and_expanded_audio_share_the_composition_layer_budget(
    shot_count, mode, with_score, accepted
):
    recipe, _, _ = fixture()
    recipe["shots"] = [dict(recipe["shots"][0], id=f"s{i}") for i in range(shot_count)]
    recipe["tasks"] = [
        {"id": task_id, "title": task_id, "kind": "upload"}
        for task_id in [
            *(f"s{i}-{kind}" for i in range(shot_count) for kind in ("video", "previs")),
            "score",
        ]
    ]
    records = {task["id"]: TaskAssets(SCOPE, ("asset-" + task["id"],)) for task in recipe["tasks"]}
    durations = {"score": AudioDuration(SCOPE, "asset-score", Fraction(2 * shot_count))}
    if not with_score:
        recipe["audio_tracks"] = []
    before = copy.deepcopy(recipe)
    assert len(validate_film_plan(recipe)["shots"]) == shot_count
    if accepted:
        draft = compose_recipe(recipe, records, scope=SCOPE, mode=mode, audio_durations=durations)
        layers = draft["tasks"][-1]["parameters"]["layers"]
        assert len(layers) == 50
        assert sum(layer["type"] == "video" for layer in layers) == shot_count
        assert sum(layer["type"] == "audio" for layer in layers) == (shot_count == 49)
    else:
        with pytest.raises(ValueError, match="including score loops and duck segments"):
            compose_recipe(recipe, records, scope=SCOPE, mode=mode, audio_durations=durations)
    assert recipe == before


def test_existing_master_task_and_full_recipe_are_preserved():
    recipe, records, frames = fixture()
    draft = compose_recipe(recipe, records, scope=SCOPE, audio_durations=frames)
    before = copy.deepcopy(draft)
    with pytest.raises(ValueError, match="new master"):
        compose_recipe(draft, records, scope=SCOPE, audio_durations=frames)
    assert draft == before
    draft["final_master_task"] = "final-master-v2"
    second = compose_recipe(draft, records, scope=SCOPE, audio_durations=frames)
    assert [t["id"] for t in second["tasks"][-2:]] == ["final-master", "final-master-v2"]


def test_explicit_recipe_project_requires_exact_selected_override():
    recipe, records, frames = fixture()
    recipe["project_id"] = "unselected-project"
    with pytest.raises(ValueError, match="project"):
        compose_task(recipe, records, scope=SCOPE, audio_durations=frames)


def test_bad_recipe_or_mode_cannot_create_a_partial_draft():
    recipe, records, frames = fixture()
    with pytest.raises(ValueError):
        compose_recipe(recipe, records, scope=SCOPE, mode="automatic", audio_durations=frames)
    recipe["shots"][0]["duration"] = 1.001
    with pytest.raises(ValueError):
        compose_recipe(recipe, records, scope=SCOPE, audio_durations=frames)


def test_same_audio_source_rounds_separately_for_loop_and_finite_tracks():
    recipe, records, durations = fixture()
    durations["score"] = AudioDuration(SCOPE, "asset-score", Fraction(61, 60))
    recipe["audio_tracks"] = [
        {"id": "repeat", "task": "score", "kind": "music", "start": 0, "end": 3, "loop": True},
        {"id": "finite", "task": "score", "kind": "sfx", "start": 3, "end": 3 + 31 / 30},
    ]
    layers = compose_task(recipe, records, scope=SCOPE, audio_durations=durations)["parameters"][
        "layers"
    ][2:]
    assert [(item["startTime"], item["endTime"]) for item in layers] == [
        (0, 1),
        (1, 2),
        (2, 3),
        (3, 3 + 31 / 30),
    ]


def test_short_loop_rejects_zero_whole_frames_and_long_title_remains_valid():
    recipe, records, durations = fixture()
    durations["score"] = AudioDuration(SCOPE, "asset-score", Fraction(1, 31))
    with pytest.raises(ValueError, match="one editorial frame"):
        compose_task(recipe, records, scope=SCOPE, audio_durations=durations)
    recipe["audio_tracks"] = []
    recipe["title"] = "x" * 120
    draft = compose_recipe(recipe, records, scope=SCOPE)
    assert len(draft["tasks"][-1]["title"]) == 120
    assert draft["title"] == recipe["title"]
