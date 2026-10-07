# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Protect editorial timing, reference identity, and bounded scene input."""

import copy
import importlib
import json
import sys
from dataclasses import replace

import pytest

from scenario.core.jobs.store import JobScope

SCOPE = JobScope("https://api.cloud.scenario.com", "synthetic-account")


def film_module():
    return importlib.import_module("scenario.core.scene.film_plan")


def fixture():
    from scenario.core.scene.film_scene_plan import local_plan

    return {
        "title": "Signal At Dawn",
        "project_id": "proj_test",
        "fps": 24,
        "style": "Dawn over a cloud sea",
        "story": "A beacon answers.",
        "tags": ["signal-at-dawn"],
        "heroes": {
            "courier": {
                "name": "Courier",
                "description": "Ivory armor, black visor",
                "mesh": "courier-mesh",
                "reference": "courier-design",
                "height": 1.8,
            }
        },
        "shots": [
            {
                "id": f"s{i + 1:02}",
                "title": f"Shot {i + 1}",
                "duration": d,
                "scene": local_plan("landscape", "", d),
                "actors": [{"hero": "courier", "location": [0, 0, 0]}],
                "placeholders": {"mountain": "weathered granite cliffs"},
                "action": "Walk toward the tower",
                "entry": "Arriving",
                "exit": "At the gate",
            }
            for i, d in enumerate([10, 15, 15, 20, 15, 15])
        ],
        "tasks": [],
    }


def test_hero_size_rejects_both_dimensions_without_changing_recipe():
    raw = fixture()
    raw["heroes"]["courier"]["width"] = 2
    before = copy.deepcopy(raw)
    with pytest.raises(ValueError, match="either width or height, not both"):
        film_module().validate_film_plan(raw)
    assert raw == before


@pytest.mark.parametrize("size", [{}, {"width": 2}, {"height": 1.8}])
def test_hero_size_accepts_one_dimension_or_original_size(size):
    raw = fixture()
    hero = raw["heroes"]["courier"]
    hero.pop("height")
    hero.update(size)
    before = copy.deepcopy(raw)
    plan = film_module().validate_film_plan(raw)
    assert {k: v for k, v in plan["heroes"]["courier"].items() if k in {"width", "height"}} == size
    assert raw == before


def test_six_shots_cover_exactly_ninety_seconds_without_overlaps():
    mod = film_module()
    value = fixture()
    before = copy.deepcopy(value)
    plan = mod.validate_film_plan(value)
    assert [(s["start_frame"], s["end_frame"]) for s in plan["shots"]] == [
        (1, 240),
        (241, 600),
        (601, 960),
        (961, 1440),
        (1441, 1800),
        (1801, 2160),
    ]
    assert plan["total_frames"] == 2160
    assert plan["duration"] == 90
    assert value == before


@pytest.mark.parametrize("field", ["hero", "object", "audio_kind", "task_kind"])
@pytest.mark.parametrize("value", [[], {}])
def test_unhashable_names_and_kinds_raise_validation_errors(field, value):
    raw = fixture()
    if field == "hero":
        raw["shots"][0]["actors"][0]["hero"] = value
    elif field == "object":
        raw["shots"][0]["motion"] = [{"object": value, "keyframes": []}]
    elif field == "audio_kind":
        raw["audio_tracks"] = [
            {"id": "score", "task": "score", "kind": value, "start": 0, "end": 1}
        ]
    else:
        raw["tasks"] = [{"id": "task", "title": "Task", "kind": value}]
    with pytest.raises(ValueError):
        film_module().validate_film_plan(raw)


def test_deep_task_parameters_report_validation_error_after_json_encoding_succeeds():
    parameters = {"prompt": "fixture"}
    for _ in range(600):
        parameters = {"nested": parameters}
    raw = fixture()
    raw["tasks"] = [
        {"id": "task", "title": "Task", "kind": "model", "model": "model", "parameters": parameters}
    ]
    json.dumps(raw, allow_nan=False)
    with pytest.raises(ValueError, match="nesting"):
        film_module().validate_film_plan(raw)


@pytest.mark.parametrize("kind", ["list", "dict"])
def test_deep_reference_input_reports_validation_error(kind):
    value = "ordinary text"
    # Python 3.13 inlines comprehensions, so 600 levels need not exhaust its stack.
    for _ in range(sys.getrecursionlimit() + 100):
        value = [value] if kind == "list" else {"nested": value}
    with pytest.raises(ValueError, match="nesting"):
        film_module().resolve_references(value, {}, scope=SCOPE)


@pytest.mark.parametrize("first,second", [("Prop A", " Prop A "), (" Prop A", "Prop A ")])
def test_placeholder_legend_rejects_normalized_name_collisions(first, second):
    raw = fixture()
    raw["shots"][0]["placeholders"] = {first: "stone tower", second: "wooden bridge"}
    before = copy.deepcopy(raw)
    with pytest.raises(ValueError, match="Placeholder names must be unique after trimming"):
        film_module().validate_film_plan(raw)
    assert raw == before


def test_placeholder_legend_preserves_distinct_normalized_entries():
    raw = fixture()
    raw["shots"][0]["placeholders"] = {" Prop A ": "stone tower", "Prop B ": "wooden bridge"}
    before = copy.deepcopy(raw)
    plan = film_module().validate_film_plan(raw)
    assert plan["shots"][0]["placeholders"] == {"Prop A": "stone tower", "Prop B": "wooden bridge"}
    assert raw == before


@pytest.mark.parametrize(
    "field,maximum",
    [
        ("style", 12000),
        ("story", 12000),
        ("action", 5000),
        ("entry", 5000),
        ("exit", 5000),
        ("notes", 5000),
        ("description", 4000),
        ("dialogue", 4000),
        ("placeholders", 2000),
    ],
)
def test_normalized_recipe_text_obeys_its_field_limit(field, maximum):
    raw = fixture()
    shot = raw["shots"][0]
    if field in {"style", "story"}:
        target, key = raw, field
    elif field == "description":
        target, key = raw["heroes"]["courier"], field
    elif field == "dialogue":
        shot["dialogue"] = {"text": "", "speaker": "Courier", "task": "speech", "offset": 0}
        target, key = shot["dialogue"], "text"
    elif field == "placeholders":
        target, key = shot["placeholders"], "mountain"
    else:
        target, key = shot, field
    target[key] = "x" * (maximum - 3) + "\u2014x"
    film_module().validate_film_plan(raw)
    target[key] += "x"
    with pytest.raises(ValueError, match=f"at most {maximum} characters"):
        film_module().validate_film_plan(raw)


@pytest.mark.parametrize("source_duration", [None, 30])
def test_impossible_editorial_window_names_trim_and_duration(source_duration):
    raw = fixture()
    shot = raw["shots"][0]
    shot["source_trim"] = 20
    if source_duration is not None:
        shot["source_duration"] = source_duration
    result = film_module().validate_film_plan(raw)
    assert result["shots"][0]["source_duration"] == 30
    shot["source_trim"] += 1 / raw["fps"]
    with pytest.raises(ValueError, match="source_trim plus duration cannot exceed 30 seconds"):
        film_module().validate_film_plan(raw)


@pytest.mark.parametrize(
    "change",
    ["unknown_hero", "duplicate_shot", "nan_duration", "executable_scene", "negative_keyframe"],
)
def test_unsafe_or_ambiguous_recipes_fail_before_scene_mutation(change):
    mod = film_module()
    plan = fixture()
    if change == "unknown_hero":
        plan["shots"][0]["actors"][0]["hero"] = "unknown"
    if change == "duplicate_shot":
        plan["shots"][1]["id"] = "s01"
    if change == "nan_duration":
        plan["shots"][0]["duration"] = float("nan")
    if change == "executable_scene":
        plan["shots"][0]["scene"]["python"] = "print('not data')"
    if change == "negative_keyframe":
        plan["shots"][0]["actors"][0]["keyframes"] = [{"time": -1, "location": [0, 0, 0]}]
    with pytest.raises(ValueError):
        mod.validate_film_plan(plan)


def test_prompt_binds_hero_and_placeholder_roles_to_exact_reference_order():
    mod = film_module()
    plan = mod.validate_film_plan(fixture())
    prompt = mod.shot_prompt(plan, plan["shots"][0], ["courier"], style_reference=True)
    assert "@video1" in prompt and "@image1" in prompt and "@image2" in prompt
    assert "Ivory armor, black visor" in prompt
    assert "weathered granite cliffs" in prompt
    assert "diegetic" in prompt.lower()


def test_symbolic_references_cannot_silently_resolve_to_another_task():
    mod = film_module()
    records = {"design": mod.TaskAssets(SCOPE, ("asset_hero",))}
    assert mod.resolve_references({"referenceImages": ["$design"]}, records, scope=SCOPE) == {
        "referenceImages": ["asset_hero"]
    }
    with pytest.raises(ValueError):
        mod.resolve_references({"image": "$missing"}, records, scope=SCOPE)


def test_actor_stop_and_camera_target_keys_are_bounded_by_the_shot():
    mod = film_module()
    raw = fixture()
    raw["shots"][0]["target_keyframes"] = [
        {"time": 0, "location": [0, 1, 2]},
        {"time": 10, "location": [0, 5, 2]},
    ]
    raw["shots"][0]["actors"][0]["action_until"] = 7
    plan = mod.validate_film_plan(raw)
    assert plan["shots"][0]["target_keyframes"][-1]["location"] == [0, 5, 2]
    assert plan["shots"][0]["actors"][0]["action_until"] == 7
    raw["shots"][0]["actors"][0]["action_until"] = 11
    with pytest.raises(ValueError):
        mod.validate_film_plan(raw)


def test_explicit_approved_take_ids_preserve_original_task_records():
    mod = film_module()
    raw = fixture()
    raw["shots"][0].update(
        {"style_task": "s01-style-v2", "previs_task": "s01-previs-v2", "video_task": "s01-video-v2"}
    )
    plan = mod.validate_film_plan(raw)
    assert plan["shots"][0]["style_task"] == "s01-style-v2"
    assert plan["shots"][0]["previs_task"] == "s01-previs-v2"
    assert plan["shots"][0]["video_task"] == "s01-video-v2"
    raw["shots"][0]["style_task"] = "../../credentials.json"
    with pytest.raises(ValueError):
        mod.validate_film_plan(raw)


@pytest.mark.parametrize("kind", ["style", "previs", "video"])
def test_long_shot_id_reports_the_explicit_take_needed(kind):
    raw = fixture()
    shot = raw["shots"][0]
    shot.update({name + "_task": "approved-" + name for name in ("style", "previs", "video")})
    field = kind + "_task"
    del shot[field]
    shot["id"] = "s" * (96 - len(kind) - 1)
    assert film_module().validate_film_plan(raw)["shots"][0][field] == shot["id"] + "-" + kind
    shot["id"] += "s"
    with pytest.raises(ValueError, match=f"set an explicit {field} of at most 96 characters"):
        film_module().validate_film_plan(raw)


def test_maximum_length_shot_id_accepts_explicit_take_names_without_rewriting():
    raw = fixture()
    shot = raw["shots"][0]
    shot["id"] = "s" * 96
    takes = {kind + "_task": kind + "x" * (96 - len(kind)) for kind in ("style", "previs", "video")}
    shot.update(takes)
    result = film_module().validate_film_plan(raw)["shots"][0]
    assert result["id"] == shot["id"]
    assert {field: result[field] for field in takes} == takes


def test_approved_master_take_names_are_validated_without_rewriting_original_tasks():
    raw = fixture()
    raw.update({"previs_master_task": "previs-master-v2", "final_master_task": "final-master-v3"})
    result = film_module().validate_film_plan(raw)
    assert result["previs_master_task"] == "previs-master-v2"
    assert result["final_master_task"] == "final-master-v3"
    raw["final_master_task"] = "../unrelated"
    with pytest.raises(ValueError):
        film_module().validate_film_plan(raw)


def acting_fixture():
    raw = fixture()
    template = raw["shots"][0]
    raw["title"] = "Please Dont Explode"
    raw["style"] = "Stylized 3D feature animation."
    raw["shots"] = [
        {**copy.deepcopy(template), "id": f"cut_{index}", "duration": duration}
        for index, duration in enumerate([2, 4, 2, 3, 2, 2, 5, 5], 1)
    ]
    raw["audio_tracks"] = []
    return raw


def test_eight_editorial_shots_cover_600_frames_with_distinct_generation_lengths():
    raw = acting_fixture()
    raw["shots"][0]["source_trim"] = 1 / 24
    result = film_module().validate_film_plan(raw)
    assert result["duration"] == 25 and result["total_frames"] == 600
    assert [shot["start_frame"] for shot in result["shots"]] == [
        1,
        49,
        145,
        193,
        265,
        313,
        361,
        481,
    ]
    assert [shot["source_duration"] for shot in result["shots"]] == [4, 4, 4, 4, 4, 4, 5, 5]
    assert result["shots"][0]["source_trim"] == 1 / 24
    assert result["shots"][0]["scene"]["camera"]["duration"] == 2
    assert film_module().effective_audio_tracks(result) == []


@pytest.mark.parametrize("length", [1, 1 + 1 / 24, 30])
def test_native_supported_editorial_lengths_are_frame_aligned(length):
    raw = acting_fixture()
    raw["shots"] = raw["shots"][:1]
    raw["shots"][0]["duration"] = length
    result = film_module().validate_film_plan(raw)
    assert result["total_frames"] == round(length * 24)


@pytest.mark.parametrize(
    "field,value",
    [
        ("duration", 0.5),
        ("duration", 2.001),
        ("duration", 31),
        ("source_trim", -1),
        ("source_trim", 0.01),
        ("source_duration", 3),
        ("source_duration", 4.5),
        ("source_duration", 31),
        ("native_audio_volume", -0.1),
        ("native_audio_volume", 2.1),
        ("native_audio_volume", True),
    ],
)
def test_invalid_source_and_editorial_timing_is_rejected(field, value):
    raw = acting_fixture()
    raw["shots"][0][field] = value
    with pytest.raises(ValueError):
        film_module().validate_film_plan(raw)


def test_source_window_must_fit_within_generation_duration():
    raw = acting_fixture()
    raw["shots"][0].update(source_trim=3, source_duration=4)
    with pytest.raises(ValueError, match="cover source trim"):
        film_module().validate_film_plan(raw)


def test_fifty_shots_are_supported_and_fifty_one_are_rejected():
    raw = acting_fixture()
    template = raw["shots"][0]
    raw["shots"] = [{**copy.deepcopy(template), "id": f"cut_{i}"} for i in range(50)]
    assert len(film_module().validate_film_plan(raw)["shots"]) == 50
    raw["shots"].append({**copy.deepcopy(template), "id": "extra"})
    with pytest.raises(ValueError, match="fifty"):
        film_module().validate_film_plan(raw)


def test_audio_track_defaults_and_duck_gains_preserve_absolute_source_progress():
    mod = film_module()
    raw = acting_fixture()
    raw["audio_tracks"] = [
        {
            "id": "bed",
            "task": "score-take-2",
            "kind": "music",
            "start": 1,
            "end": 25,
            "trim_start": 0.5,
            "volume": 0.4,
            "duck": [{"start": 2, "end": 4, "volume": 0.1}],
        }
    ]
    track = mod.validate_film_plan(raw)["audio_tracks"][0]
    assert track["loop"] is False
    assert mod.audio_segments(track, 24) == [
        {"start": 1, "end": 2, "trim_start": 0.5, "volume": 0.4, "loop": False},
        {"start": 2, "end": 4, "trim_start": 1.5, "volume": 0.1, "loop": False},
        {"start": 4, "end": 25, "trim_start": 3.5, "volume": 0.4, "loop": False},
    ]
    legacy = mod.validate_film_plan(fixture())
    assert "audio_tracks" not in legacy
    assert mod.effective_audio_tracks(legacy)[0]["volume"] == 0.4
    assert mod.effective_audio_tracks(legacy)[0]["loop"] is True


@pytest.mark.parametrize(
    "change",
    [
        "outside",
        "backwards",
        "fractional",
        "bad_trim",
        "bad_gain",
        "bad_loop",
        "duplicate",
        "wrong_kind",
        "duck_outside",
        "duck_overlap",
        "duck_dialogue",
    ],
)
def test_invalid_audio_mix_fails_during_recipe_validation(change):
    raw = acting_fixture()
    track = {"id": "bed", "task": "music", "kind": "music", "start": 0, "end": 25}
    raw["audio_tracks"] = [track]
    if change == "outside":
        track["end"] = 26
    elif change == "backwards":
        track["end"] = 0
    elif change == "fractional":
        track["start"] = 0.001
    elif change == "bad_trim":
        track["trim_start"] = -1
    elif change == "bad_gain":
        track["volume"] = 2.5
    elif change == "bad_loop":
        track["loop"] = 1
    elif change == "duplicate":
        raw["audio_tracks"].append(copy.deepcopy(track))
    elif change == "wrong_kind":
        track["kind"] = "voiceover"
    elif change == "duck_outside":
        track["duck"] = [{"start": 24, "end": 26, "volume": 0.1}]
    elif change == "duck_overlap":
        track["duck"] = [
            {"start": 1, "end": 4, "volume": 0.1},
            {"start": 3, "end": 5, "volume": 0.2},
        ]
    else:
        track.update(kind="dialogue", duck=[{"start": 1, "end": 4, "volume": 0.1}])
    with pytest.raises(ValueError):
        film_module().validate_film_plan(raw)


def test_declared_continuity_compares_only_adjacent_shared_states_and_declared_cut_changes():
    mod = film_module()
    raw = acting_fixture()
    raw["shots"][0]["continuity"] = {
        "entry": {"eyes": "off"},
        "exit": {"eyes": "amber", "axis": "west"},
    }
    raw["shots"][1]["continuity"] = {
        "entry": {"eyes": "off", "axis": "east"},
        "exit": {"eyes": "blue"},
        "intentional_changes": ["axis"],
    }
    raw["shots"][2]["continuity"] = {"entry": {"eyes": "blue"}}
    result = mod.validate_film_plan(raw)
    audit = result["continuity_audit"]
    assert audit["visual_verification"] is False and audit["ok"] is False
    assert audit["compared_states"] == 3
    assert audit["mismatches"] == [
        {"previous_shot": "cut_1", "shot": "cut_2", "key": "eyes", "exit": "amber", "entry": "off"}
    ]
    assert [row["key"] for row in audit["intentional_changes"]] == ["axis"]
    prompt = mod.shot_prompt(result, result["shots"][1], ["courier"])
    assert "eyes=off" in prompt and "eyes=blue" in prompt
    assert "live-action science-fiction" not in prompt


def test_dialogue_directions_use_source_window_and_preserve_exact_words():
    raw = acting_fixture()
    raw["shots"][0].update(
        source_trim=1,
        source_duration=4,
        dialogue={
            "text": "Please don't explode.",
            "speaker": "Mina",
            "task": "mina-line",
            "offset": 0.5,
        },
    )
    result = film_module().validate_film_plan(raw)
    prompt = film_module().shot_prompt(result, result["shots"][0], ["courier"])
    assert "@audio1" in prompt and "source second 1.5" in prompt
    assert "source seconds 1 to 3" in prompt
    assert "4 seconds, one continuous take" in prompt
    assert "Please don't explode." in prompt
    raw["shots"][0]["dialogue"]["offset"] = 2
    with pytest.raises(ValueError, match="inside the editorial shot"):
        film_module().validate_film_plan(raw)


def test_dialogue_reference_resolution_rejects_a_different_production_project():
    mod = film_module()
    records = {"line": mod.TaskAssets(replace(SCOPE, project_id="proj_other"), ("asset_voice",))}
    with pytest.raises(ValueError, match="scope"):
        mod.resolve_references(
            {"referenceAudio": ["$line"]}, records, scope=replace(SCOPE, project_id="proj_test")
        )


@pytest.mark.parametrize("project", [None, "project-explicit"])
def test_recipe_uses_credential_bound_scope_with_optional_exact_project_override(project):
    mod = film_module()
    raw = fixture()
    raw.pop("project_id")
    if project is not None:
        raw["project_id"] = project
    before = copy.deepcopy(raw)
    plan = mod.validate_film_plan(raw)
    assert plan["project_id"] == project
    mod.require_plan_scope(plan, replace(SCOPE, project_id=project))
    assert raw == before
    if project is not None:
        with pytest.raises(ValueError, match="override"):
            mod.require_plan_scope(plan, SCOPE)


@pytest.mark.parametrize(
    "field,value",
    [
        ("service", "https://other.scenario.example"),
        ("account_id", "other-credential-pseudonym"),
        ("project_id", "other-project"),
        ("team_id", "other-team"),
    ],
)
def test_task_assets_reject_every_foreign_scope_dimension(field, value):
    mod = film_module()
    records = {"design": mod.TaskAssets(replace(SCOPE, **{field: value}), ("asset_hero",))}
    with pytest.raises(ValueError, match="scope"):
        mod.resolve_references({"image": "$design"}, records, scope=SCOPE)


def test_reference_resolution_preserves_output_order_and_accepts_opaque_asset_ids():
    mod = film_module()
    assets = ("550e8400-e29b-41d4-a716-446655440000", "asset-second")
    records = {"design": mod.TaskAssets(SCOPE, assets)}
    value = {"images": ["$design:1", "$design:0"], "seed": 0, "nested": {"text": "literal"}}
    before = copy.deepcopy(value)
    assert mod.resolve_references(value, records, scope=SCOPE) == {
        "images": [assets[1], assets[0]],
        "seed": 0,
        "nested": {"text": "literal"},
    }
    assert value == before and records["design"].asset_ids == assets


@pytest.mark.parametrize(
    "reference",
    [
        "$",
        "$design:-1",
        "$design:+1",
        "$design:01",
        "$design: 1",
        "$design:0:1",
        "$design:128",
        "$missing",
    ],
)
def test_ambiguous_missing_and_out_of_range_task_references_are_rejected(reference):
    mod = film_module()
    records = {"design": mod.TaskAssets(SCOPE, ("asset-first",))}
    with pytest.raises(ValueError):
        mod.resolve_references(reference, records, scope=SCOPE)


def test_recipe_project_field_alone_cannot_authorize_asset_resolution():
    mod = film_module()
    with pytest.raises(ValueError, match="scope"):
        mod.resolve_references(
            "$design", {"design": {"project_id": None, "asset_ids": ["asset_hero"]}}, scope=SCOPE
        )
    with pytest.raises(ValueError):
        mod.resolve_references("$design", {}, scope=None)


@pytest.mark.parametrize(
    "assets",
    [
        [],
        (),
        ("asset-one", "asset-one"),
        ("https://example.com/a",),
        tuple(f"asset-{i}" for i in range(129)),
    ],
)
def test_invalid_task_output_observations_are_rejected(assets):
    with pytest.raises(ValueError):
        film_module().TaskAssets(SCOPE, assets)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), object()])
def test_non_json_model_parameters_are_rejected_before_a_recipe_is_accepted(value):
    raw = fixture()
    raw["tasks"] = [
        {
            "id": "take",
            "title": "Take",
            "kind": "model",
            "model": "model-fixture",
            "parameters": {"seed": value},
        }
    ]
    with pytest.raises(ValueError, match="finite JSON"):
        film_module().validate_film_plan(raw)


@pytest.mark.parametrize("tags", ["wrong", ["tag"] * 31])
def test_task_tags_are_a_bounded_list(tags):
    raw = fixture()
    raw["tasks"] = [{"id": "take", "title": "Take", "kind": "upload", "tags": tags}]
    with pytest.raises(ValueError, match="task tags"):
        film_module().validate_film_plan(raw)


def test_recipe_size_limit_counts_utf8_bytes_and_rejects_cycles():
    raw = fixture()
    raw["tasks"] = [
        {
            "id": "take",
            "title": "Take",
            "kind": "model",
            "model": "model-fixture",
            "parameters": {"prompt": "界" * 700_000},
        }
    ]
    with pytest.raises(ValueError, match="2 MB"):
        film_module().validate_film_plan(raw)
    raw["tasks"][0]["parameters"] = raw
    with pytest.raises(ValueError, match="finite JSON"):
        film_module().validate_film_plan(raw)
