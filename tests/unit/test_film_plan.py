# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Protect editorial timing, reference identity, and bounded scene input."""

import copy
import importlib

import pytest


def film_module():
    try:
        return importlib.import_module("scenario.core.scene.film_plan")
    except ModuleNotFoundError:
        pytest.fail("The plugin does not yet support a bounded film plan")


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
    records = {"design": {"asset_ids": ["asset_hero"]}}
    assert mod.resolve_references({"referenceImages": ["$design"]}, records) == {
        "referenceImages": ["asset_hero"]
    }
    with pytest.raises(ValueError):
        mod.resolve_references({"image": "$missing"}, records)


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
    records = {"line": {"asset_ids": ["asset_voice"], "project_id": "proj_other"}}
    with pytest.raises(ValueError, match="does not belong"):
        film_module().resolve_references(
            {"referenceAudio": ["$line"]}, records, project_id="proj_test"
        )
