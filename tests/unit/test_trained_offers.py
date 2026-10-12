# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Trained models the picker offers per lane, from captured REST records, without any request.

The bases and public trained records are the sanitized captures under
tests/fixtures/models/trained; synthetic variants change one field at a time.
"""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from scenario.core.api import catalog, trained_offers, trained_routes
from scenario.core.api.trained_routes import LoraSlot, Pick

TRAINED = Path(__file__).resolve().parents[1] / "fixtures/models/trained"
FLUX1 = "model_bfl-flux-1-dev"
FLUX2 = "model_bfl-flux-2-dev"
KONTEXT = "model_flux-kontext-editing"
QWEN = "model_qwen-image-edit-2511"
ZIMAGE = "model_z-image"
LORA_A = "model_YQrES2iPys22nYwh3YhVfMh8"
LORA_B = "model_2taP2G9BJL1Rw8t81NwiXGZA"
FLUX2_LORA = "model_CMUu7BjxV8TpdhG3FKoxZRxC"
KONTEXT_LORA = "model_hFh8M6nQbqGFSKJdP536GXhE"
COMPOSITION = "model_7oiHtKChpcLpy4jq3Jq2BG8n"


def _load(relative):
    return json.loads((TRAINED / relative).read_text(encoding="utf-8"))["model"]


BASES = {name: _load(f"bases/{name}.json") for name in (FLUX1, FLUX2, KONTEXT, QWEN, ZIMAGE)}
PUBLIC = {
    name: _load(f"public/{name}.json")
    for name in (LORA_A, LORA_B, FLUX2_LORA, KONTEXT_LORA, COMPOSITION)
}


def record(raw, **changes):
    return catalog.ModelRecord.from_api({**deepcopy(raw), **changes})


def bases(lane="image"):
    return trained_offers.lora_bases(lane, [record(raw) for raw in BASES.values()])


def pairs(*ids, kind=None):
    return [
        (kind or catalog.trained_kind(record(PUBLIC[model_id])), record(PUBLIC[model_id]))
        for model_id in ids
    ]


def scale_input(raw):
    return next(field for field in raw["inputs"] if field["name"] == "lorasScale")


def test_lora_bases_keep_detailed_lane_models_with_a_slot_curated_first():
    assert [base.id for base in bases("image")] == [ZIMAGE, FLUX2, KONTEXT, FLUX1, QWEN]
    assert [base.id for base in bases("render_image")] == [QWEN, ZIMAGE, FLUX2, KONTEXT, FLUX1]
    assert bases("video") == []
    slot = next(base.slot for base in bases() if base.id == FLUX1)
    assert (slot.model_label, slot.max_items, slot.scale_min, slot.scale_max) == (
        "Flux LoRA",
        6,
        0,
        2,
    )


def test_list_rows_and_malformed_or_absent_slots_are_not_bases():
    row = {key: value for key, value in BASES[FLUX1].items() if key not in ("inputs", "uiConfig")}
    rows = [record(row, parameters={})]
    assert trained_offers.lora_bases("image", rows) == []
    plain = deepcopy(BASES[FLUX1])
    plain["uiConfig"] = {}
    assert trained_offers.lora_bases("image", [record(plain)]) == []
    malformed = deepcopy(BASES[FLUX1])
    for field in malformed["inputs"]:
        if field["name"] == "loras":
            field.pop("modelTypes")
    assert trained_offers.lora_bases("image", [record(malformed)]) == []
    trained = record(BASES[FLUX1], type="flux.1-lora")
    assert trained_offers.lora_bases("image", [trained]) == []


def test_offers_name_every_base_that_runs_each_trained_model():
    offered = trained_offers.offers(
        pairs(LORA_A, FLUX2_LORA, KONTEXT_LORA, COMPOSITION, LORA_B), bases()
    )
    assert [(offer.id, [base.id for base in offer.bases]) for offer in offered] == [
        (LORA_A, [FLUX1]),
        (FLUX2_LORA, [FLUX2]),
        (KONTEXT_LORA, [KONTEXT]),
        (COMPOSITION, [FLUX1]),
        (LORA_B, [FLUX1]),
    ]
    assert all(offer.available and offer.reason == "" for offer in offered)
    assert offered[3].kind == catalog.TRAINED_COMPOSITION


def test_unavailable_offers_explain_why_and_follow_available_ones():
    voice = record(PUBLIC[LORA_A], id="model_voice", type="elevenlabs-voice")
    private_custom = record(BASES[ZIMAGE], id="model_private", privacy="private")
    untrained = record(PUBLIC[LORA_B], id="model_training", status="training")
    odd = record(PUBLIC[LORA_A], id="model_odd", type="flux.9-lora\n<b>")
    rows = [
        (catalog.TRAINED_UNSUPPORTED, voice),
        (catalog.PRIVATE_CUSTOM, private_custom),
        (catalog.TRAINED_LORA, untrained),
        (catalog.TRAINED_LORA, odd),
        *pairs(LORA_A),
    ]
    offered = trained_offers.offers(rows, bases())
    assert [(offer.id, offer.reason) for offer in offered] == [
        (LORA_A, ""),
        ("model_voice", "Not available in Blender: no base model runs this type."),
        ("model_training", "This model is not trained and ready to use."),
        ("model_odd", "No base model in this form accepts unsupported models."),
    ]
    waiting = trained_offers.offers(pairs(LORA_A), [], unknown="Checking base models...")
    assert [(offer.available, offer.reason) for offer in waiting] == [
        (False, "Checking base models...")
    ]
    nothing = trained_offers.offers(pairs(FLUX2_LORA), [b for b in bases() if b.id == ZIMAGE])
    assert nothing[0].reason == "No base model in this form accepts flux.2-dev-lora models."


def test_strength_uses_declared_bounds_and_a_visible_starting_value():
    slot = LoraSlot.from_record(BASES[FLUX1])
    strength = trained_offers.strength(slot)
    # The Scenario web app's starting strength when the LoRA declares none.
    assert trained_offers.DEFAULT_STRENGTH == 0.75
    assert strength == trained_offers.Strength(0.0, 2.0, 0.05, 0.75)
    assert strength.clamp(0.800000011920929) == 0.8  # 32-bit storage reads back exactly
    assert strength.clamp(-1) == 0.0 and strength.clamp(9) == 2.0
    # A base's declared default fills an omitted strength (trained_routes.apply); it
    # does not move the visible start.
    declared = deepcopy(BASES[FLUX1])
    scale_input(declared)["default"] = 0.65
    assert trained_offers.strength(LoraSlot.from_record(declared)).initial == 0.75
    narrow = deepcopy(BASES[FLUX1])
    scale_input(narrow).update({"min": 0.9, "max": 1.5})
    assert trained_offers.strength(LoraSlot.from_record(narrow)).initial == 0.9  # clamped
    scale_input(narrow).update({"min": 0.1, "max": 0.5})
    assert trained_offers.strength(LoraSlot.from_record(narrow)).initial == 0.5
    for change in ({"min": 3}, {"max": None}, {"min": None}):
        changed = deepcopy(BASES[FLUX1])
        scale_input(changed).update(change)
        assert trained_offers.strength(LoraSlot.from_record(changed)) is None


def test_a_lora_starts_at_its_own_declared_strength_within_the_base_range():
    slot = LoraSlot.from_record(BASES[FLUX1])
    # The captured public LoRA lists itself as its first concept, with scale 0.8.
    assert PUBLIC[LORA_A]["concepts"][0] == {"modelId": LORA_A, "scale": 0.8}
    assert trained_offers.declared_strength(PUBLIC[LORA_A]) == 0.8
    assert trained_offers.declared_strength(record(PUBLIC[LORA_A])) == 0.8
    assert trained_offers.strength(slot, record(PUBLIC[LORA_A])).initial == 0.8
    assert trained_offers.strength(slot, PUBLIC[LORA_A]) == trained_offers.Strength(
        0.0, 2.0, 0.05, 0.8
    )
    # A base declaring its own default does not override the LoRA's strength.
    defaulted = deepcopy(BASES[FLUX1])
    scale_input(defaulted)["default"] = 0.65
    assert trained_offers.strength(LoraSlot.from_record(defaulted), PUBLIC[LORA_A]).initial == 0.8
    # The first concept's scale counts, clamped to the base's declared range.
    first = {"concepts": [{"modelId": "self", "scale": 1.6}, {"modelId": "x", "scale": 0.2}]}
    assert trained_offers.declared_strength(first) == 1.6
    assert trained_offers.strength(slot, first).initial == 1.6
    above = {"concepts": [{"modelId": "self", "scale": 7}]}
    assert trained_offers.strength(slot, above).initial == 2.0
    below = {"concepts": [{"modelId": "self", "scale": -1}]}
    assert trained_offers.strength(slot, below).initial == 0.0
    # Without a usable first scale, the LoRA starts at the web app's default.
    for raw in (
        PUBLIC[KONTEXT_LORA],  # carries no concepts
        {},
        {"concepts": []},
        {"concepts": None},
        {"concepts": [{"modelId": "self"}, {"modelId": "x", "scale": 0.4}]},
        {"concepts": [{"modelId": "self", "scale": True}]},
        {"concepts": [{"modelId": "self", "scale": "0.9"}]},
        {"concepts": [{"modelId": "self", "scale": float("nan")}]},
        {"concepts": [{"modelId": "self", "scale": float("inf")}]},
    ):
        assert trained_offers.declared_strength(raw) is None, raw
        assert trained_offers.strength(slot, raw).initial == trained_offers.DEFAULT_STRENGTH, raw


def test_a_reset_strength_starts_where_a_newly_chosen_lora_does():
    """The form's reset strength field without a base range uses the same start, unclamped."""
    assert trained_offers.starting_strength() == trained_offers.DEFAULT_STRENGTH == 0.75
    assert trained_offers.starting_strength(None) == 0.75
    assert trained_offers.starting_strength(PUBLIC[KONTEXT_LORA]) == 0.75  # declares none
    assert trained_offers.starting_strength(PUBLIC[LORA_A]) == 0.8
    assert trained_offers.starting_strength(record(PUBLIC[LORA_A])) == 0.8
    # Unbounded here: the field's update keeps it within the range the field kept.
    assert trained_offers.starting_strength({"concepts": [{"modelId": "self", "scale": 7}]}) == 7
    slot = LoraSlot.from_record(BASES[FLUX1])
    narrow = deepcopy(BASES[FLUX1])
    scale_input(narrow).update({"min": 0.78, "max": 1.5})
    for base in (slot, LoraSlot.from_record(narrow)):
        for raw in (
            PUBLIC[LORA_A],
            PUBLIC[KONTEXT_LORA],
            {"concepts": [{"modelId": "self", "scale": 1.9}]},
            {"concepts": [{"modelId": "self", "scale": float("nan")}]},
        ):
            start = trained_offers.starting_strength(raw)
            bounded = min(max(start, base.scale_min), base.scale_max)
            assert trained_offers.strength(base, raw).initial == bounded, raw


def test_a_lora_needs_a_strength_control_or_a_declared_default():
    unbounded = deepcopy(BASES[FLUX1])
    scale_input(unbounded).pop("min")
    slot = LoraSlot.from_record(unbounded)
    assert trained_offers.runs(slot, PUBLIC[LORA_A]) == (
        None,
        "LoRA Scale declares no strength range.",
    )
    assert trained_offers.runs(slot, PUBLIC[COMPOSITION]) == (trained_routes.ROUTE_COMPOSITION, "")
    scale_input(unbounded)["default"] = 0.5
    defaulted = LoraSlot.from_record(unbounded)
    assert trained_offers.strength(defaulted) is None
    assert trained_offers.runs(defaulted, PUBLIC[LORA_A]) == (trained_routes.ROUTE_STACK, "")
    offered = trained_offers.offers(pairs(LORA_A), [trained_offers.Base(record(unbounded), slot)])
    assert offered[0].reason == "No base model in this form accepts flux.1-lora models."


def test_base_candidates_list_unknown_lane_models_in_lane_order_once():
    detailed = [record(raw) for raw in BASES.values()]
    rows = [
        record({k: v for k, v in raw.items() if k not in ("inputs", "parameters")}, id=f"{key}-row")
        for key, raw in BASES.items()
    ]
    names = [row.id for row in rows]
    assert trained_offers.base_candidates("image", detailed) == []
    order = trained_offers.base_candidates("image", rows)
    assert sorted(order) == sorted(names) and len(order) == 5
    assert trained_offers.base_candidates("image", rows, attempted=order[:2]) == order[2:]
    assert trained_offers.base_candidates("image", rows, limit=2) == order[:2]
    assert trained_offers.base_candidates("image", rows, limit=-1) == []


@pytest.mark.parametrize(
    ("current", "choice", "same", "expected"),
    [
        ([], ("a", "lora", 0.5), True, [("a", "lora", 0.5)]),
        ([("a", "lora", 0.5)], ("b", "lora", 1.0), True, [("a", "lora", 0.5), ("b", "lora", 1.0)]),
        ([("a", "lora", 0.5), ("b", "lora", 1.0)], ("a", "lora", 0.7), True,
         [("a", "lora", 0.7), ("b", "lora", 1.0)]),
        ([("a", "lora", 0.5)], ("b", "lora", 1.0), False, [("b", "lora", 1.0)]),
        ([("a", "lora", 0.5)], ("c", "composition", None), True, [("c", "composition", None)]),
        ([("c", "composition", None)], ("a", "lora", 0.5), True, [("a", "lora", 0.5)]),
    ],
)  # fmt: skip
def test_merged_adds_replaces_or_restrengths_explicitly(current, choice, same, expected):
    assert trained_offers.merged(current, choice, same_base=same) == expected


def test_equal_choices_build_byte_identical_payloads():
    base = BASES[FLUX1]
    records = {model_id: PUBLIC[model_id] for model_id in (LORA_A, LORA_B)}
    first = trained_offers.merged([], (LORA_A, "lora", 0.8), same_base=True)
    first = trained_offers.merged(first, (LORA_B, "lora", 1.25), same_base=True)
    payloads = [
        json.dumps(
            trained_routes.apply(
                base, [Pick(i, s) for i, _k, s in chosen], records, {"prompt": "p"}
            ),
            sort_keys=True,
        )
        for chosen in (first, [(LORA_A, "lora", 0.8), (LORA_B, "lora", 1.25)])
    ]
    assert payloads[0] == payloads[1]
    assert json.loads(payloads[0]) == {
        "prompt": "p",
        "loras": [LORA_A, LORA_B],
        "lorasScale": [0.8, 1.25],
    }


def test_concepts_lists_a_composition_and_skips_malformed_entries():
    listed = trained_offers.concepts(record(PUBLIC[COMPOSITION]))
    assert len(listed) == len(PUBLIC[COMPOSITION]["concepts"]) >= 2
    assert all(isinstance(model_id, str) for model_id, _scale in listed)
    raw = {"concepts": [{"modelId": "a", "scale": True}, {"scale": 1}, "b", {"modelId": "c"}]}
    assert trained_offers.concepts(raw) == [("a", None), ("c", None)]
    assert trained_offers.concepts({"concepts": "none"}) == []


def test_picks_from_a_saved_payload_restore_the_route_it_names():
    slot = LoraSlot.from_record(BASES[FLUX1])
    read = trained_offers.picks_from_payload
    assert read(slot, {"modelId": COMPOSITION}) == (Pick(COMPOSITION),)
    assert read(slot, {"loras": [LORA_A, LORA_B], "lorasScale": [0.8, 1]}) == (
        Pick(LORA_A, 0.8),
        Pick(LORA_B, 1.0),
    )
    assert read(slot, {"loras": [LORA_A]}) == (Pick(LORA_A),)
    for payload in (
        {},
        None,
        {"loras": []},
        {"loras": [LORA_A], "lorasScale": [0.8, 1]},
        {"loras": [LORA_A], "lorasScale": [True]},
        {"loras": [LORA_A], "lorasScale": "0.8"},
        {"loras": [5]},
        {"modelId": COMPOSITION, "loras": [LORA_A]},
    ):
        assert read(slot, payload) == (), payload
    kontext = LoraSlot.from_record(BASES[KONTEXT])
    assert read(kontext, {"modelId": COMPOSITION}) == ()


def test_saved_ids_count_a_payload_s_trained_models_without_a_valid_slot():
    read = trained_offers.saved_ids
    payload = {"modelId": COMPOSITION, "loras": [LORA_A, LORA_B, LORA_A, 5], "lorasScale": [1]}
    assert read(BASES[FLUX1], payload) == [COMPOSITION, LORA_A, LORA_B]
    changed = deepcopy(BASES[FLUX1])
    changed["uiConfig"]["lorasComponent"]["scaleInput"] = "missing"
    with pytest.raises(ValueError):
        LoraSlot.from_record(changed)  # picks_from_payload has no slot to read
    assert read(changed, {"loras": [LORA_A]}) == [LORA_A]
    for raw, saved in (
        (BASES[FLUX1], {"prompt": "a cabin"}),
        (BASES[FLUX1], None),
        ({**BASES[FLUX1], "uiConfig": {}}, {"loras": [LORA_A]}),
        ({"uiConfig": {"lorasComponent": "loras"}}, {"loras": [LORA_A]}),
        (None, {"loras": [LORA_A]}),
    ):
        assert read(raw, saved) == [], (raw, saved)


def test_selection_label_names_the_first_trained_model_and_counts_the_rest():
    assert trained_offers.selection_label("FLUX.1 Dev", []) == "FLUX.1 Dev"
    assert trained_offers.selection_label("FLUX.1 Dev", ["", ""]) == "FLUX.1 Dev"
    assert trained_offers.selection_label("FLUX.1 Dev", ["Studio"]) == "FLUX.1 Dev \u00b7 Studio"
    assert (
        trained_offers.selection_label("FLUX.1 Dev", ["Studio", "Ink", "Grain"])
        == "FLUX.1 Dev \u00b7 Studio (+2)"
    )
