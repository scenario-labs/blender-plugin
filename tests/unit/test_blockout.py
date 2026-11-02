# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
import json

import pytest

from scenario.core.scene import blockout


def test_parses_rich_elements():
    text = '[{"name": "Well", "category": "water", "primitive": "cylinder", "position": [0,0,0.5], "size": [1.6,1.6,1], "rotation": 45, "group": "Center"}]'
    els = blockout.parse_plan(text)
    assert len(els) == 1
    el = els[0]
    assert el["name"] == "Well" and el["category"] == "water" and el["primitive"] == "cylinder"
    assert el["rotation"] == 45.0 and el["group"] == "Center"
    assert el["size"] == [1.6, 1.6, 1.0]


def test_tolerates_fence_prose_and_fills_defaults():
    text = 'Here you go:\n```json\n[{"name": "Wall", "size": [4, 0.3, 3]}]\n```'
    el = blockout.parse_plan(text)[0]
    assert el["primitive"] == "box"  # default primitive
    assert el["category"] == "other"  # default category
    assert el["group"] == "Blockout"  # default group
    assert el["position"] == [0.0, 0.0, 1.5]  # sits on the ground (z = size_z / 2)
    assert el["rotation"] == 0.0


@pytest.mark.parametrize(
    "wrapper",
    [
        "{}",
        "```json\n{}\n```",
        "```\n{}\n```",
        "Here is the plan:\n{}\nDone.",
        "Here is the plan:\n```json\n{}\n```\nDone.",
    ],
)
def test_complete_plan_accepts_wrappers_and_preserves_every_element(wrapper):
    plan = json.dumps([{"name": "Wall", "size": [4, 0.3, 3]}, {"name": "Tower"}])
    assert blockout.parse_complete_plan(wrapper.format(plan)) == blockout.parse_plan(plan)


@pytest.mark.parametrize(
    "text",
    [
        '[{"name":"Complete prefix"},',
        '```json\n[{"name":"Complete prefix"}, {"size":[1,2,3]}\n```',
        'Here is the plan:\n[{"name":"Complete prefix"}, {"size":[1,2,3]}',
        '```json\n[{"name":"Bad"},]\n```',
        "{}",
        '{"plan":[{}]}',
        '```json\n{"plan":[{}]}\n```',
        'Here is the plan:\n{"plan":[{}]}',
        "[]",
        "[{},2]",
        '[{"size":[NaN,1,2]}]',
        json.dumps([{}] * (blockout.MAX_ELEMENTS + 1)),
    ],
)
def test_complete_plan_never_recovers_a_prefix_or_silently_drops_elements(text):
    with pytest.raises(ValueError):
        blockout.parse_complete_plan(text)


def test_bad_enums_fall_back_and_values_clamp():
    text = '[{"name": "", "category": "spaceship", "primitive": "torus", "size": [99999, -5, "x"], "rotation": 9999, "position": [1e9,0,0]}]'
    el = blockout.parse_plan(text)[0]
    assert el["name"] == "Block 1"
    assert el["category"] == "other" and el["primitive"] == "box"
    assert el["size"] == [blockout.MAX_SIZE, blockout.MIN_SIZE, 1.0]
    assert el["rotation"] == 360.0
    assert el["position"][0] == blockout.MAX_COORD


def test_recovers_elements_from_a_truncated_array():
    # a capped LLM answer cut off mid-element: keep the complete objects, drop the incomplete tail
    truncated = (
        '[{"name": "Floor", "category": "floor", "primitive": "box", "size": [10,10,0.2]}, '
        '{"name": "Wall", "category": "wall", "size": [10,0.2,5]}, '
        '{"name": "Desk", "category": "furniture", "position": [0.0, 3'
    )
    els = blockout.parse_plan(truncated)
    assert [e["name"] for e in els] == ["Floor", "Wall"]


def test_unparseable_returns_empty_and_count_is_capped():
    assert blockout.parse_plan("nope") == []
    assert blockout.parse_plan("") == []
    many = "[" + ",".join('{"name":"b"}' for _ in range(400)) + "]"
    assert len(blockout.parse_plan(many)) == blockout.MAX_ELEMENTS


def test_plan_summary_counts_by_category_and_group():
    els = blockout.parse_plan(
        '[{"name":"a","category":"wall","group":"G1"},{"name":"b","category":"wall","group":"G2"},{"name":"c","category":"prop","group":"G1"}]'
    )
    summary = blockout.plan_summary(els)
    assert summary["total"] == 3
    assert summary["by_category"] == {"wall": 2, "prop": 1}
    assert summary["by_group"] == {"G1": 2, "G2": 1}


def test_instruction_carries_density_budget_and_refine():
    base = blockout.instruction("a square", density="simple")
    assert "market" not in base and "JSON array" in base and "Scene to block out: a square" in base
    assert "Use 30 to 60 elements" in base and "reference image" not in base
    assert "Use 200 to 350 elements" in blockout.instruction("a square", density="expert")
    assert "Use 120 to 200 elements" in blockout.instruction("a square", density="unknown")
    refine = blockout.instruction("add a tower", previous=[{"name": "x"}])
    assert "UPDATED" in refine and "add a tower" in refine


def test_image_instruction_follows_the_picture_and_allows_an_empty_prompt():
    text = blockout.instruction("", image=True)
    assert "A reference image is attached" in text
    assert text.endswith("Scene to block out: the place in the reference image")


@pytest.mark.parametrize(
    ("tier", "allowed", "expected"),
    [
        ("best", None, {"model": "claude-opus-5-5"}),
        ("fast", None, {"model": "gemini-3.7-flash", "thinkingLevel": "low"}),
        ("best", ["gemini-3.7-flash", "claude-opus-5-5"], {"model": "claude-opus-5-5"}),
        # A newer model Scenario adds later is picked without a plugin release.
        (
            "best",
            ["claude-opus-5-5", "claude-opus-6", "claude-opus-5-10"],
            {"model": "claude-opus-6"},
        ),
        ("best", ["claude-opus-5-5", "claude-opus-5-10"], {"model": "claude-opus-5-10"}),
        (
            "fast",
            ["gemini-3.5-flash-lite", "gemini-3.7-flash", "gemini-4-flash"],
            {"model": "gemini-4-flash", "thinkingLevel": "low"},
        ),
        # A retired family falls back to the next fixed choice the list offers.
        ("best", ["claude-fable-5-1", "gemini-3.7-flash"], {"model": "claude-fable-5-1"}),
        ("fast", ["gemini-3.5-flash-lite", "claude-sonnet-5-5"], {"model": "claude-sonnet-5-5"}),
        ("unknown", None, {"model": "claude-opus-5-5"}),
    ],
)
def test_model_tiers_pick_the_newest_family_member(tier, allowed, expected):
    assert blockout.model_parameters(tier, allowed) == expected


def test_model_tiers_respect_thinking_levels_and_refuse_an_empty_family():
    assert blockout.model_parameters("fast", ["gemini-3.7-flash"], ["none", "high"]) == {
        "model": "gemini-3.7-flash"
    }
    with pytest.raises(ValueError):
        blockout.model_parameters("fast", ["gemini-3.5-flash-lite"])


@pytest.mark.parametrize(
    ("model", "label"),
    [
        ("claude-opus-5-5", "Claude Opus 5.5"),
        ("claude-opus-6", "Claude Opus 6"),
        ("gemini-3.7-flash", "Gemini 3.7 Flash"),
        ("gpt-6-astra", "GPT 6 Astra"),
    ],
)
def test_model_label(model, label):
    assert blockout.model_label(model) == label


@pytest.mark.parametrize(
    "wrapper",
    [
        '{{"results": [{{"text": {text}, "probability": 0.99}}]}}',
        '```json\n{{"results": [{{"text": {text}, "probability": 0.99}}]}}\n```',
    ],
)
def test_complete_plan_unwraps_the_scenario_llm_answer_wrapper(wrapper):
    plan = json.dumps([{"name": "Wall", "size": [4, 0.3, 3]}, {"name": "Tower"}])
    text = wrapper.format(text=json.dumps(plan))
    assert blockout.parse_complete_plan(text) == blockout.parse_plan(plan)
    listed = json.dumps({"results": json.loads(plan)})
    assert blockout.parse_complete_plan(listed) == blockout.parse_plan(plan)


@pytest.mark.parametrize(
    "text",
    [
        '{"results": [{"text": "[...blockout json...]", "probability": 0.99}]}',
        '{"results": []}',
        '{"results": [{"text": "[{\\"name\\": \\"cut"}]}',
        '{"results": [{"text": "[{}]"}], "plan": []}',
    ],
)
def test_wrapped_placeholders_and_prefixes_are_not_plans(text):
    with pytest.raises(ValueError):
        blockout.parse_complete_plan(text)


def test_refinement_instruction_preserves_complete_plan_without_design_framing():
    previous = [{"name": "Long named layout element " + str(index)} for index in range(200)]
    instruction = blockout.instruction("add one door", previous=previous)
    assert "Scene to block out:" not in instruction
    assert "UPDATED full plan applying this change: add one door" in instruction
    rows = instruction.split("\nCurrent plan:\n")[1]
    assert blockout.parse_complete_plan(rows) == blockout.parse_plan(json.dumps(previous))


def test_grouped_rows_parse_to_the_same_elements_as_keyed_objects():
    keyed = [
        {
            "name": "Pond",
            "category": "water",
            "primitive": "cylinder",
            "position": [-9, 5, 0.1],
            "size": [8, 6, 0.2],
            "rotation": 20,
            "group": "Garden",
        },
        {
            "name": "Roof",
            "category": "structure",
            "primitive": "wedge",
            "position": [8, -4, 4.75],
            "size": [8, 6, 1.5],
            "rotation": 30,
            "group": "Teahouse",
        },
    ]
    rows = blockout.encode_rows(keyed)
    assert json.loads(rows) == [
        "Garden",
        ["Pond", "water", "cylinder", -9.0, 5.0, 0.1, 8.0, 6.0, 0.2, 20.0],
        "Teahouse",
        ["Roof", "structure", "wedge", 8.0, -4.0, 4.75, 8.0, 6.0, 1.5, 30.0],
    ]
    assert len(rows) < 0.6 * len(json.dumps(keyed, separators=(",", ":")))
    expected = blockout.parse_plan(json.dumps(keyed))
    assert blockout.parse_complete_plan(rows) == blockout.parse_plan(rows) == expected
    assert blockout.parse_complete_plan(f"```json\n{rows}\n```") == expected


def test_rows_before_any_label_and_mixed_keyed_objects_still_parse():
    text = '[["Rock", "prop", "sphere", 1, 2, 0.3, 0.6, 0.6, 0.6, 0], {"name": "Gate"}, "Fence", ["Post", "structure", "box", 0, 0, 0.5, 0.1, 0.1, 1, 0]]'
    plan = blockout.parse_complete_plan(text)
    assert [(e["name"], e["group"]) for e in plan] == [
        ("Rock", "Blockout"),
        ("Gate", "Blockout"),
        ("Post", "Fence"),
    ]


@pytest.mark.parametrize(
    "text",
    [
        '["Fence", ["Post", "structure", "box", 0, 0, 0.5, 0.1, 1, 0]]',  # a value is missing
        '["Fence", ["Post", "structure", "box", 0, 0, 0.5, 0.1, 0.1, 1, 0, 9]]',
        '["Fence"]',
        '["Fence", 3]',
    ],
)
def test_complete_plan_refuses_a_row_that_lost_or_gained_a_value(text):
    with pytest.raises(ValueError):
        blockout.parse_complete_plan(text)


def test_a_lenient_parse_skips_an_incomplete_row():
    text = '["Fence", ["Post", "structure", "box", 0, 0, 0.5, 0.1, 1, 0], ["Rail", "structure", "box", 0, 0, 0.8, 4, 0.1, 0.1, 0]]'
    assert [e["name"] for e in blockout.parse_plan(text)] == ["Rail"]
