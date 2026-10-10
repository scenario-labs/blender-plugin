# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Trained-model routes from captured base-model REST schemas, without any request.

The base and trained records are the sanitized captures under
tests/fixtures/models/trained. Synthetic variants change one field at a time to
cover malformed or changed schemas and service answers the capture did not see.
"""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from scenario.core.api import catalog, trained_routes
from scenario.core.api.sdk_adapter import AdapterError, AdapterUnavailable
from scenario.core.api.trained_routes import LoraSlot, Pick, RouteError
from scenario.core.schema.forms import chosen_inputs, prepare_run, record_schema

TRAINED = Path(__file__).resolve().parents[1] / "fixtures/models/trained"


def _load(relative):
    return json.loads((TRAINED / relative).read_text(encoding="utf-8"))["model"]


FLUX1 = "model_bfl-flux-1-dev"
FLUX2 = "model_bfl-flux-2-dev"
KONTEXT = "model_flux-kontext-editing"
QWEN = "model_qwen-image-edit-2511"
ZIMAGE = "model_z-image"
BASES = {name: _load(f"bases/{name}.json") for name in (FLUX1, FLUX2, KONTEXT, QWEN, ZIMAGE)}
LORA_A = "model_YQrES2iPys22nYwh3YhVfMh8"
LORA_B = "model_2taP2G9BJL1Rw8t81NwiXGZA"
FLUX2_LORA = "model_CMUu7BjxV8TpdhG3FKoxZRxC"
KONTEXT_LORA = "model_hFh8M6nQbqGFSKJdP536GXhE"
COMPOSITION = "model_7oiHtKChpcLpy4jq3Jq2BG8n"
PUBLIC = {
    model_id: _load(f"public/{model_id}.json")
    for model_id in (LORA_A, LORA_B, FLUX2_LORA, KONTEXT_LORA, COMPOSITION)
}
PROMPT = {"prompt": "a small wooden cabin in a snowy forest"}


def base(model_id=FLUX1, **changes):
    record = deepcopy(BASES[model_id])
    record.update(changes)
    return record


def inputs(record):
    return {field["name"]: field for field in record["inputs"]}


class Reader:
    """Fresh reads from a dict of records; unknown IDs are HTTP 404."""

    def __init__(self, records=None, denied=None):
        self.records = {**PUBLIC, **(records or {})}
        self.denied = dict(denied or {})
        self.calls = []

    def __call__(self, model_id):
        self.calls.append(model_id)
        if model_id in self.denied:
            raise AdapterUnavailable(self.denied[model_id])
        if model_id not in self.records:
            raise AdapterUnavailable(404)
        return deepcopy(self.records[model_id])


def concept_records(composition=COMPOSITION, **changes):
    return {
        concept["modelId"]: {
            "id": concept["modelId"],
            "type": "flux.1-lora",
            "status": "trained",
            **changes,
        }
        for concept in PUBLIC[composition]["concepts"]
    }


def check(payload, *, record=None, reader=None, names=None):
    schema = record_schema("model", record or base())
    reader = reader or Reader(concept_records())
    return trained_routes.check_references(
        schema, payload, reader, names=payload if names is None else names
    )


# Slots


@pytest.mark.parametrize(
    "model_id,model_types,max_items,model_id_types",
    [
        (FLUX1, ("flux.1-lora",), 6, ("flux.1-lora", "flux.1-composition")),
        (FLUX2, ("flux.2-dev-lora", "flux.2-dev-edit-lora"), 6, None),
        (KONTEXT, ("flux.1-kontext-lora",), 1, None),
        (QWEN, ("qwen-image-edit-2511-lora",), 6, ("qwen-image-edit-2511-lora",)),
        (ZIMAGE, ("zimage-lora", "zimage-turbo-lora", "zimage-de-turbo-lora"), 6, None),
    ],
)
def test_captured_bases_declare_their_slot(model_id, model_types, max_items, model_id_types):
    slot = LoraSlot.from_record(BASES[model_id])
    assert slot.model_types == model_types
    assert slot.max_items == max_items and slot.min_items == 0
    assert (slot.scale_min, slot.scale_max, slot.scale_step) == (0, 2, 0.05)
    assert slot.scale_default is None
    assert (slot.component.model_input, slot.component.scale_input) == ("loras", "lorasScale")
    if model_id == KONTEXT:
        assert slot.model_id_input is None and slot.model_id_types == ()
    else:
        assert slot.model_id_input == "modelId"
        assert slot.model_id_types == (model_id_types or model_types)
    # A catalog.ModelRecord works the same as a raw record.
    assert LoraSlot.from_record(catalog.ModelRecord.from_api(BASES[model_id])) == slot


def test_a_schema_without_a_lora_component_has_no_slot():
    assert LoraSlot.from_record(base(uiConfig={})) is None
    assert LoraSlot.from_record(base(uiConfig=None)) is None
    assert LoraSlot.from_schema({"parameters": [{"name": "prompt", "type": "string"}]}) is None


def _malformed(change):
    record = base()
    change(record)
    return record


@pytest.mark.parametrize(
    "change",
    [
        lambda r: r["uiConfig"].update(lorasComponent="loras"),
        lambda r: r["uiConfig"]["lorasComponent"].update(modelInput="missing"),
        lambda r: r["uiConfig"]["lorasComponent"].update(scaleInput=7),
        lambda r: r["uiConfig"]["lorasComponent"].pop("scaleInput"),
        lambda r: r["uiConfig"]["lorasComponent"].update(modelIdInput="prompt"),
        lambda r: r["uiConfig"]["lorasComponent"].update(scaleInput="loras"),
        lambda r: r["uiConfig"]["lorasComponent"].update(modelInput="modelId"),
        lambda r: inputs(r)["loras"].pop("modelTypes"),
        lambda r: inputs(r)["loras"].update(modelTypes=[]),
        lambda r: inputs(r)["loras"].update(modelTypes="flux.1-lora"),
        lambda r: inputs(r)["modelId"].update(modelTypes=[3]),
        lambda r: inputs(r)["lorasScale"].update(type="number"),
    ],
)
def test_malformed_or_changed_lora_components_are_refused(change):
    record = _malformed(change)
    with pytest.raises(RouteError, match="LoRA inputs changed or are malformed"):
        LoraSlot.from_record(record)
    assert trained_routes.compatibility("image", record, PUBLIC[LORA_A])[0] is None


# Compatibility


@pytest.mark.parametrize(
    "lane,model_id,trained,expected",
    [
        ("image", FLUX1, LORA_A, trained_routes.ROUTE_STACK),
        ("render_image", FLUX1, LORA_B, trained_routes.ROUTE_STACK),
        ("image", FLUX1, COMPOSITION, trained_routes.ROUTE_COMPOSITION),
        ("image", FLUX2, FLUX2_LORA, trained_routes.ROUTE_STACK),
        ("render_image", KONTEXT, KONTEXT_LORA, trained_routes.ROUTE_STACK),
        ("image", FLUX1, FLUX2_LORA, None),
        ("image", FLUX2, LORA_A, None),
        ("image", KONTEXT, COMPOSITION, None),
        ("image", QWEN, LORA_A, None),
        ("video", FLUX1, LORA_A, None),
    ],
)
def test_compatibility_follows_the_base_schema(lane, model_id, trained, expected):
    route, reason = trained_routes.compatibility(lane, BASES[model_id], PUBLIC[trained])
    assert route == expected
    assert bool(reason) is (expected is None)
    assert trained not in reason and model_id not in reason


def test_incompatible_reasons_are_actionable():
    def reason(trained, model_id=FLUX1, lane="image"):
        return trained_routes.compatibility(lane, BASES[model_id], trained)[1]

    assert reason(PUBLIC[FLUX2_LORA]) == (
        "Flux LoRA accepts flux.1-lora models, not flux.2-dev-lora."
    )
    assert reason(PUBLIC[LORA_A], lane="video") == "This base model does not run in this lane."
    assert reason({**PUBLIC[LORA_A], "status": "training"}) == (
        "This model is not trained and ready to use."
    )
    assert reason({"id": "model_x", "type": "custom", "status": "trained"}) == (
        "Only LoRAs and compositions run through a base model."
    )
    assert reason(PUBLIC[LORA_A], model_id=KONTEXT, lane="render_image") == (
        "Flux Kontext LoRA accepts flux.1-kontext-lora models, not flux.1-lora."
    )
    trained_base = {**PUBLIC[LORA_A], "uiConfig": BASES[FLUX1]["uiConfig"]}
    assert trained_routes.compatibility("image", trained_base, PUBLIC[LORA_B]) == (
        None,
        "Choose a base model, not a trained model.",
    )
    no_slot = base(uiConfig={})
    assert trained_routes.compatibility("image", no_slot, PUBLIC[LORA_A]) == (
        None,
        "This base model does not accept LoRAs or compositions.",
    )


def test_list_rows_without_schemas_never_show_a_route():
    row = {key: value for key, value in BASES[FLUX1].items() if key not in {"inputs", "uiConfig"}}
    assert trained_routes.compatibility("image", row, PUBLIC[LORA_A])[0] is None


def test_compatible_bases_lists_every_choice_curated_first():
    twin = base(id="model_another-flux-1", name="Another Flux")
    bases = [twin, *BASES.values()]
    assert [r.id for r in trained_routes.compatible_bases("image", PUBLIC[LORA_A], bases)] == [
        "model_another-flux-1",
        FLUX1,
    ]
    # Z-Image is curated first in the image lane, but accepts no Flux LoRA.
    assert [r.id for r in trained_routes.compatible_bases("image", PUBLIC[COMPOSITION], bases)] == [
        "model_another-flux-1",
        FLUX1,
    ]
    assert [
        r.id for r in trained_routes.compatible_bases("render_image", PUBLIC[KONTEXT_LORA], bases)
    ] == [KONTEXT]
    assert trained_routes.compatible_bases("video", PUBLIC[LORA_A], bases) == []


# Applying a selection


def test_a_lora_stack_writes_ids_and_one_float_strength_each():
    payload = trained_routes.apply(
        BASES[FLUX1], [Pick(LORA_A, 0.8), Pick(LORA_B, 1)], PUBLIC, PROMPT
    )
    assert payload == {**PROMPT, "loras": [LORA_A, LORA_B], "lorasScale": [0.8, 1.0]}
    assert isinstance(payload["lorasScale"][1], float)
    target, prepared = prepare_run(FLUX1, record_schema("model", BASES[FLUX1]), payload)
    assert target == FLUX1 and {k: prepared[k] for k in payload} == payload
    assert check(prepared, names=payload).keys() == {LORA_A, LORA_B}


def test_equal_selections_build_identical_payload_bytes():
    def build(scale, parameters):
        payload = trained_routes.apply(BASES[FLUX1], [Pick(LORA_A, scale)], PUBLIC, parameters)
        return json.dumps(payload, ensure_ascii=False, allow_nan=False).encode()

    stale = {**PROMPT, "loras": [LORA_B], "lorasScale": [0.3], "modelId": COMPOSITION}
    assert build(1, PROMPT) == build(1.0, dict(PROMPT)) == build(1, stale)


def test_apply_replaces_the_previous_selection_without_mutating_inputs():
    parameters = {**PROMPT, "loras": [LORA_B], "lorasScale": [0.3]}
    original = deepcopy(parameters)
    payload = trained_routes.apply(BASES[FLUX1], [Pick(COMPOSITION)], PUBLIC, parameters)
    assert payload == {**PROMPT, "modelId": COMPOSITION}
    assert parameters == original
    assert trained_routes.apply(BASES[FLUX1], [], PUBLIC, parameters) == PROMPT


def test_a_composition_runs_alone_with_its_own_strengths():
    payload = trained_routes.apply(BASES[FLUX1], [Pick(COMPOSITION)], PUBLIC, PROMPT)
    assert payload == {**PROMPT, "modelId": COMPOSITION}
    prepare_run(FLUX1, record_schema("model", BASES[FLUX1]), payload)
    with pytest.raises(RouteError, match="composition on its own"):
        trained_routes.apply(BASES[FLUX1], [Pick(COMPOSITION), Pick(LORA_A, 1)], PUBLIC, PROMPT)
    with pytest.raises(RouteError, match="applies its own strengths"):
        trained_routes.apply(BASES[FLUX1], [Pick(COMPOSITION, 0.5)], PUBLIC, PROMPT)


def test_declared_default_strength_fills_a_pick_without_one():
    record = base()
    inputs(record)["lorasScale"]["default"] = 0.65
    payload = trained_routes.apply(record, [Pick(LORA_A), Pick(LORA_B, 0.2)], PUBLIC)
    assert payload["lorasScale"] == [0.65, 0.2]


@pytest.mark.parametrize(
    "picks,base_id,message",
    [
        ([Pick(LORA_A)], FLUX1, "LoRA Scale: provide a strength for each LoRA."),
        ([Pick(LORA_A, 2.5)], FLUX1, "LoRA Scale: use a strength from 0 to 2."),
        ([Pick(LORA_A, -0.5)], FLUX1, "LoRA Scale: use a strength from 0 to 2."),
        ([Pick(LORA_A, float("nan"))], FLUX1, "LoRA Scale: enter a finite strength."),
        ([Pick(LORA_A, True)], FLUX1, "LoRA Scale: enter a finite strength."),
        ([Pick(LORA_A, 1), Pick(LORA_A, 0.5)], FLUX1, "Flux LoRA: choose each LoRA once."),
        (
            [Pick(FLUX2_LORA, 1)],
            FLUX1,
            "Flux LoRA accepts flux.1-lora models, not flux.2-dev-lora.",
        ),
        ([Pick("model_unlisted", 1)], FLUX1, "a selected model is no longer listed"),
        ([Pick(KONTEXT_LORA, 1)] * 1 + [Pick(LORA_A, 1)], KONTEXT, "flux.1-kontext-lora models"),
        (["not a pick"], FLUX1, "Choose trained models from the model list."),
        ([Pick("", 1)], FLUX1, "Choose trained models from the model list."),
    ],
)
def test_invalid_selections_are_refused(picks, base_id, message):
    with pytest.raises(RouteError) as error:
        trained_routes.apply(BASES[base_id], picks, PUBLIC, PROMPT)
    assert message in str(error.value)


def test_the_stack_limit_and_minimum_come_from_the_schema():
    second = {**PUBLIC[KONTEXT_LORA], "id": "model_SecondKontextLora000000"}
    records = {**PUBLIC, second["id"]: second}
    with pytest.raises(RouteError, match="use at most 1 LoRAs"):
        trained_routes.apply(
            BASES[KONTEXT], [Pick(KONTEXT_LORA, 1), Pick(second["id"], 1)], records
        )
    record = base()
    inputs(record)["loras"]["minLength"] = 2
    with pytest.raises(RouteError, match="use at least 2 LoRAs"):
        trained_routes.apply(record, [Pick(LORA_A, 1)], PUBLIC)


def test_a_base_without_lora_inputs_cannot_apply_a_selection():
    with pytest.raises(RouteError, match="does not accept LoRAs"):
        trained_routes.apply(base(uiConfig={}), [Pick(LORA_A, 1)], PUBLIC)


# References and fresh-record checks


def test_references_name_inputs_and_positions_the_caller_set():
    payload = {**PROMPT, "loras": [LORA_A, LORA_B], "modelId": COMPOSITION, "lorasScale": [1, 1]}
    schema = record_schema("model", BASES[FLUX1])
    references = trained_routes.model_references(schema, payload)
    assert [(r.input, r.index, r.model_id, r.where) for r in references] == [
        ("modelId", None, COMPOSITION, "LoRA or Composition Model"),
        ("loras", 1, LORA_A, "Flux LoRA [1]"),
        ("loras", 2, LORA_B, "Flux LoRA [2]"),
    ]
    assert [r.input for r in trained_routes.model_references(schema, payload, {"loras"})] == [
        "loras",
        "loras",
    ]
    assert trained_routes.model_references(schema, {"loras": "bad", "modelId": 4}) == []
    assert trained_routes.model_references(schema, {"loras": ["", 3, LORA_A]})[0].index == 3


def test_a_request_without_references_reads_nothing():
    reader = Reader()
    assert check(PROMPT, reader=reader) == {}
    # Values from schema defaults are the service's own and are not read.
    assert check({**PROMPT, "loras": [LORA_A]}, reader=reader, names=PROMPT) == {}
    assert reader.calls == []


def test_a_stack_reads_each_lora_once_in_the_selected_order():
    reader = Reader()
    records = check({"loras": [LORA_A, LORA_B], "lorasScale": [1, 1]}, reader=reader)
    assert reader.calls == [LORA_A, LORA_B]
    assert set(records) == {LORA_A, LORA_B}


def test_a_composition_reads_each_concept_fresh():
    reader = Reader(concept_records())
    records = check({"modelId": COMPOSITION}, reader=reader)
    concepts = [concept["modelId"] for concept in PUBLIC[COMPOSITION]["concepts"]]
    assert reader.calls == [COMPOSITION, *concepts]
    assert set(records) == {COMPOSITION, *concepts}


@pytest.mark.parametrize("status", [403, 404])
def test_a_deleted_or_inaccessible_model_is_refused(status):
    reader = Reader(denied={LORA_B: status})
    with pytest.raises(RouteError) as error:
        check({"loras": [LORA_A, LORA_B], "lorasScale": [1, 1]}, reader=reader)
    assert str(error.value) == (
        f"Flux LoRA [2] is not available to the selected credentials or project (HTTP {status}). "
        "Remove it or choose another model."
    )
    assert LORA_B not in str(error.value)


@pytest.mark.parametrize(
    "change,message",
    [
        ({"status": "training"}, "Flux LoRA [1] is not ready to use (status: training)."),
        ({"status": "deleted"}, "Flux LoRA [1] is not ready to use (status: deleted)."),
        ({"status": "odd<value>"}, "Flux LoRA [1] is not ready to use (status: unknown)."),
        ({"status": None}, "Flux LoRA [1] is not ready to use (status: unknown)."),
        (
            {"type": "flux.2-dev-lora"},
            "Flux LoRA [1] is a flux.2-dev-lora model; Flux LoRA accepts flux.1-lora.",
        ),
        (
            {"type": "<script>"},
            "Flux LoRA [1] is a unsupported model; Flux LoRA accepts flux.1-lora.",
        ),
    ],
)
def test_a_changed_trained_record_is_refused(change, message):
    reader = Reader({LORA_A: {**PUBLIC[LORA_A], **change}})
    with pytest.raises(RouteError) as error:
        check({"loras": [LORA_A], "lorasScale": [1]}, reader=reader)
    assert str(error.value) == message


def test_a_lora_in_the_composition_input_must_join_the_stack():
    with pytest.raises(RouteError) as error:
        check({"modelId": LORA_A})
    assert str(error.value) == (
        "LoRA or Composition Model is a LoRA. Add it to Flux LoRA with a strength instead."
    )


@pytest.mark.parametrize(
    "records,denied,message",
    [
        (
            concept_records(type="flux.2-dev-lora"),
            {},
            "LoRA or Composition Model combines flux.2-dev-lora LoRAs; Flux LoRA accepts "
            "flux.1-lora.",
        ),
        (
            concept_records(status="failed"),
            {},
            "A LoRA in LoRA or Composition Model is not ready to use (status: failed).",
        ),
        (
            concept_records(),
            {PUBLIC[COMPOSITION]["concepts"][1]["modelId"]: 403},
            "LoRA or Composition Model uses a LoRA that is not available to the selected "
            "credentials or project (HTTP 403). Choose another composition.",
        ),
        (
            {COMPOSITION: {**PUBLIC[COMPOSITION], "concepts": []}},
            {},
            "LoRA or Composition Model lists no LoRAs to apply; choose another composition.",
        ),
        (
            {COMPOSITION: {**PUBLIC[COMPOSITION], "concepts": [{"modelId": "bad/id"}]}},
            {},
            "LoRA or Composition Model lists a malformed LoRA; choose another composition.",
        ),
        (
            {COMPOSITION: {**PUBLIC[COMPOSITION], "concepts": ["model_x"]}},
            {},
            "LoRA or Composition Model lists no LoRAs to apply; choose another composition.",
        ),
    ],
)
def test_a_composition_whose_loras_cannot_run_is_refused(records, denied, message):
    reader = Reader(records, denied)
    with pytest.raises(RouteError) as error:
        check({"modelId": COMPOSITION}, reader=reader)
    assert str(error.value) == message


def test_reads_are_bounded_per_quote():
    record = base()
    inputs(record)["loras"]["maxLength"] = 40
    loras = [f"model_Lora{index:020d}" for index in range(17)]
    records = {model_id: {**PUBLIC[LORA_A], "id": model_id} for model_id in loras}
    reader = Reader(records)
    with pytest.raises(RouteError, match="Too many models to check"):
        check({"loras": loras}, record=record, reader=reader)
    assert len(reader.calls) == trained_routes.MAX_REFERENCE_READS
    reader = Reader(records)
    check({"loras": loras[:16]}, record=record, reader=reader)
    assert len(reader.calls) == 16


def test_a_composition_concept_counts_toward_the_read_bound():
    reader = Reader(concept_records())
    with pytest.raises(RouteError, match="at most 2"):
        trained_routes.check_references(
            record_schema("model", BASES[FLUX1]), {"modelId": COMPOSITION}, reader, limit=2
        )
    assert len(reader.calls) == 2


def test_invalid_ids_are_refused_before_any_read():
    reader = Reader()
    with pytest.raises(RouteError, match=r"Flux LoRA \[1\]: enter a valid model ID."):
        check({"loras": ["bad/../id"], "lorasScale": [1]}, reader=reader)
    assert reader.calls == []


def test_another_identity_from_the_read_is_refused():
    with pytest.raises(RouteError, match="another model"):
        check({"loras": [LORA_A]}, reader=lambda model_id: dict(PUBLIC[LORA_B]))


def test_other_read_failures_propagate_unchanged():
    def fail(model_id):
        raise AdapterError("Could not reach Scenario")

    with pytest.raises(AdapterError, match="Could not reach Scenario"):
        check({"loras": [LORA_A]}, reader=fail)


def test_generic_model_inputs_get_type_and_status_checks_only():
    schema = {
        "parameters": [
            {"name": "style", "type": "model", "modelTypes": ["flux.1-lora"]},
            {"name": "any", "type": "model"},
        ]
    }
    reader = Reader()
    assert set(
        trained_routes.check_references(schema, {"style": LORA_A, "any": COMPOSITION}, reader)
    )
    with pytest.raises(
        RouteError, match="Style is a flux.1-composition model; Style accepts flux.1-lora."
    ):
        trained_routes.check_references(schema, {"style": COMPOSITION}, Reader())


def test_a_malformed_component_refuses_a_request_that_uses_model_inputs():
    record = _malformed(lambda r: r["uiConfig"]["lorasComponent"].update(scaleInput="missing"))
    with pytest.raises(RouteError, match="LoRA inputs changed"):
        check({"loras": [LORA_A], "lorasScale": [1]}, record=record)
    assert check(PROMPT, record=record) == {}


# The shared form preparation's strength policy on the captured schemas


def prepare(payload, record=None, model_id=FLUX1):
    return prepare_run(model_id, record_schema("model", record or base(model_id)), payload)[1]


def test_prepare_refuses_a_stack_combined_with_a_model_id():
    with pytest.raises(RouteError) as error:
        prepare({**PROMPT, "modelId": COMPOSITION, "loras": [LORA_A], "lorasScale": [1]})
    assert str(error.value) == (
        "Use LoRA or Composition Model on its own, or remove it to stack Flux LoRA with strengths."
    )
    # Empty values are unset, so either input alone still runs.
    assert prepare({**PROMPT, "modelId": COMPOSITION, "loras": [], "lorasScale": []}) == {
        **prepare(PROMPT),
        "modelId": COMPOSITION,
        "lorasScale": [],
    }


@pytest.mark.parametrize(
    "payload,message",
    [
        ({"lorasScale": [0.5]}, "LoRA Scale: choose a LoRA in Flux LoRA for each strength."),
        ({"loras": [LORA_A, LORA_A], "lorasScale": [1, 1]}, "Flux LoRA: choose each LoRA once."),
        ({"loras": [LORA_A]}, "LoRA Scale: provide a strength for each LoRA in Flux LoRA."),
        ({"loras": [LORA_A], "lorasScale": None}, "provide a strength for each LoRA"),
        ({"loras": [LORA_A], "lorasScale": []}, "provide a strength for each LoRA"),
        ({"loras": [LORA_A], "lorasScale": [1, 1]}, "provide one strength for each LoRA"),
    ],
)
def test_prepare_refuses_unaligned_or_missing_strengths(payload, message):
    with pytest.raises(RouteError) as error:
        prepare({**PROMPT, **payload})
    assert message in str(error.value)


def test_prepare_takes_a_declared_strength_default_but_never_invents_one():
    record = base()
    inputs(record)["lorasScale"]["default"] = 0.65
    assert prepare({**PROMPT, "loras": [LORA_A, LORA_B]}, record)["lorasScale"] == [0.65, 0.65]
    inputs(record)["lorasScale"]["default"] = [0.4, 0.6]
    assert prepare({**PROMPT, "loras": [LORA_A, LORA_B]}, record)["lorasScale"] == [0.4, 0.6]
    with pytest.raises(RouteError, match="provide a strength"):
        prepare({**PROMPT, "loras": [LORA_A]}, record)
    inputs(record)["lorasScale"]["default"] = True
    with pytest.raises(RouteError, match="provide a strength"):
        prepare({**PROMPT, "loras": [LORA_A]}, record)


def test_a_selection_from_schema_defaults_alone_is_left_to_the_service():
    record = base()
    inputs(record)["loras"]["default"] = [LORA_A]
    assert prepare(PROMPT, record)["loras"] == [LORA_A]
    assert "lorasScale" not in prepare(PROMPT, record)
    # A form that echoes the default back has not chosen anything either.
    assert "lorasScale" not in prepare({**PROMPT, "loras": [LORA_A]}, record)
    schema = record_schema("model", record)
    assert chosen_inputs(schema, {**PROMPT, "loras": [LORA_A], "modelId": ""}) == {"prompt"}
    with pytest.raises(RouteError, match="provide a strength"):
        prepare({**PROMPT, "loras": [LORA_B]}, record)


def test_a_malformed_component_refuses_only_requests_that_set_model_inputs():
    record = _malformed(lambda r: r["uiConfig"]["lorasComponent"].update(modelInput="missing"))
    assert prepare(PROMPT, record) == prepare(PROMPT)
    for payload in ({"loras": [LORA_A], "lorasScale": [1]}, {"modelId": COMPOSITION}):
        with pytest.raises(RouteError, match="LoRA inputs changed"):
            prepare({**PROMPT, **payload}, record)
