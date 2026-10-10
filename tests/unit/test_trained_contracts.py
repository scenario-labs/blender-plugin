# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Pin the captured trained-model REST contracts: public records and dry-run replies.

The fixtures come from tools/capture_trained_contracts.py, which makes reads and
dryRun=true quotes only. They establish schema and request shapes and the
service's answers to zero-spend quotes. They do not establish a paid run,
result quality, the strength a service applies by default, or the behavior of
private trained models (the captured scope had none).
"""

import json
import re
from decimal import Decimal
from pathlib import Path

import httpx
import pytest

from scenario.core.api import catalog, trained_routes
from scenario.core.api.sdk_adapter import AdapterUnavailable, Credentials, SDKAdapter
from scenario.core.schema.forms import prepare_run, record_schema
from tools import capture_trained_contracts as capture

TRAINED = Path(__file__).resolve().parents[1] / "fixtures/models/trained"


def _load(relative):
    return json.loads((TRAINED / relative).read_text(encoding="utf-8"))


CONTRACTS = _load("contracts.json")
BASES = {path.stem: _load(f"bases/{path.name}")["model"] for path in (TRAINED / "bases").iterdir()}
PUBLIC = {
    path.stem: _load(f"public/{path.name}")["model"] for path in (TRAINED / "public").iterdir()
}
CASES = {case["case"]: case for case in CONTRACTS["dryRuns"]}
FLUX1 = "model_bfl-flux-1-dev"
KONTEXT = "model_flux-kontext-editing"

# base: (modelIdInput types or None, modelInput types, modelInput maxLength, LoRAs change price)
LORA_SLOTS = {
    FLUX1: (["flux.1-lora", "flux.1-composition"], ["flux.1-lora"], 6, False),
    "model_bfl-flux-2-dev": (
        ["flux.2-dev-lora", "flux.2-dev-edit-lora"],
        ["flux.2-dev-lora", "flux.2-dev-edit-lora"],
        6,
        False,
    ),
    KONTEXT: (None, ["flux.1-kontext-lora"], 1, True),
    "model_qwen-image-edit-2511": (
        ["qwen-image-edit-2511-lora"],
        ["qwen-image-edit-2511-lora"],
        6,
        False,
    ),
    "model_z-image": (
        ["zimage-lora", "zimage-turbo-lora", "zimage-de-turbo-lora"],
        ["zimage-lora", "zimage-turbo-lora", "zimage-de-turbo-lora"],
        6,
        False,
    ),
}
# The service's answer to each validation probe. Accepted (269) probes are rules
# the client must enforce itself before quoting.
SERVER_CHECKS = {
    "check_without_scale": (269, None),
    "check_scale_count_mismatch": (269, None),
    "check_scale_below_min": (269, None),
    "check_scale_above_max": (400, "Input lorasScale must be at most 2"),
    "check_over_item_limit": (400, "Input loras must be at most 6 items long"),
    "check_incompatible_type": (
        400,
        "Invalid model(s): model_CMUu7BjxV8TpdhG3FKoxZRxC.\n"
        "Allowed model types: flux.1-lora, flux.1-composition",
    ),
    "check_composition_in_loras": (
        400,
        "Invalid model(s): model_7oiHtKChpcLpy4jq3Jq2BG8n.\nAllowed model types: flux.1-lora",
    ),
    "check_unknown_model": (404, "Model model_FIXTUREMISSING0000000000 not found"),
}
# What the shared preparation and the quote-time reference check do with each
# captured request, before any quote: None means both accept it. The service
# accepts several of these; the client refuses them on purpose.
LOCAL_OUTCOMES = {
    "base_only": None,
    "stack_one": None,
    "stack_two": None,
    "stack_flux2": None,
    "kontext_reference_only": None,
    "stack_kontext": None,
    # Accepted by the service, which then applies a strength nobody chose.
    "model_id_lora": (
        "LoRA or Composition Model is a LoRA. Add it to Flux LoRA with a strength instead."
    ),
    "composition": None,
    "composition_unlisted_concept": None,
    # Accepted by the service, but its schema says `loras` overrides the
    # composition's own LoRAs.
    "composition_with_loras": (
        "Use LoRA or Composition Model on its own, or remove it to stack Flux LoRA with strengths."
    ),
    "check_without_scale": "LoRA Scale: provide a strength for each LoRA in Flux LoRA.",
    "check_scale_count_mismatch": "LoRA Scale: provide one strength for each LoRA in Flux LoRA.",
    "check_scale_below_min": "LoRA Scale [1]: minimum is 0.",
    "check_scale_above_max": "LoRA Scale [1]: maximum is 2.",
    "check_over_item_limit": "Flux LoRA: use at most 6 items.",
    "check_incompatible_type": (
        "Flux LoRA [1] is a flux.2-dev-lora model; Flux LoRA accepts flux.1-lora."
    ),
    "check_composition_in_loras": (
        "Flux LoRA [1] is a flux.1-composition model; Flux LoRA accepts flux.1-lora."
    ),
    "check_unknown_model": (
        "Flux LoRA [1] is not available to the selected credentials or project (HTTP 404). "
        "Remove it or choose another model."
    ),
}


def _captured_read(model_id):
    """Answer a reference read from the captured records only.

    A composition concept is answered from its recorded type and readability.
    The capture did not record a concept's status; a readable concept LoRA is
    taken as trained here.
    """
    if model_id in PUBLIC:
        return PUBLIC[model_id]
    for role, rows in CONTRACTS["catalog"]["compositionConcepts"].items():
        concepts = PUBLIC[capture.PUBLIC_TRAINED[role]]["concepts"]
        for concept, row in zip(concepts, rows, strict=True):
            if concept["modelId"] == model_id and row["readable"]:
                return {"id": model_id, "type": row["type"], "status": "trained"}
    raise AdapterUnavailable(404)


def _local_outcome(case):
    """Prepare and check one captured request as a quote would, without a request."""
    base = BASES[case["target"]]
    schema = record_schema("model", base)
    try:
        _, payload = prepare_run(case["target"], schema, case["body"])
        trained_routes.check_references(schema, payload, _captured_read, names=case["body"])
    except ValueError as error:
        return str(error)
    return None


def _inputs(base_id):
    return {field["name"]: field for field in BASES[base_id]["inputs"]}


def test_fixture_inventory_matches_the_recorder():
    assert set(BASES) == set(capture.BASE_IDS)
    assert set(PUBLIC) == set(capture.PUBLIC_TRAINED.values())
    assert CONTRACTS["publicTrained"] == capture.PUBLIC_TRAINED
    assert list(CASES) == [case[0] for case in capture.CASES]
    assert CONTRACTS["recorder"] == "tools/capture_trained_contracts.py"
    assert CONTRACTS["scope"]["credentials"] == "explicit API-key pair"
    assert set(LORA_SLOTS) == set(BASES)


@pytest.mark.parametrize("base_id", sorted(LORA_SLOTS))
def test_base_models_declare_their_lora_slots(base_id):
    record = BASES[base_id]
    model_id_types, model_types, max_items, cost_impact = LORA_SLOTS[base_id]
    component = record["uiConfig"]["lorasComponent"]
    inputs = _inputs(base_id)
    model_input = inputs[component["modelInput"]]
    scale_input = inputs[component["scaleInput"]]
    assert (component["modelInput"], component["scaleInput"]) == ("loras", "lorasScale")
    assert model_input["type"] == "model_array"
    assert model_input["modelTypes"] == model_types
    assert model_input["maxLength"] == max_items
    assert model_input["default"] == []
    assert model_input["costImpact"] is cost_impact
    # Strength bounds are declared on every base, but no default strength is.
    assert scale_input["type"] == "number_array"
    assert (scale_input["min"], scale_input["max"], scale_input["step"]) == (0, 2, 0.05)
    assert "default" not in scale_input
    if model_id_types is None:
        assert "modelIdInput" not in component
    else:
        model_id = inputs[component["modelIdInput"]]
        assert component["modelIdInput"] == "modelId"
        assert model_id["type"] == "model"
        assert model_id["modelTypes"] == model_id_types
        assert model_id["default"] == ""


@pytest.mark.parametrize("base_id", sorted(LORA_SLOTS))
def test_base_models_are_plain_public_lane_models(base_id):
    record = catalog.ModelRecord.from_api(BASES[base_id])
    assert (record.type, record.privacy, record.status) == ("custom", "public", "trained")
    assert BASES[base_id]["custom"] is True and not BASES[base_id].get("parentModelId")
    assert catalog.trained_kind(record) is None and not catalog.is_trained(record)
    assert record.lanes == {"image", "render_image"}


def test_compositions_reach_flux1_only_through_the_model_id_input():
    inputs = _inputs(FLUX1)
    assert "flux.1-composition" in inputs["modelId"]["modelTypes"]
    assert "flux.1-composition" not in inputs["loras"]["modelTypes"]
    for base_id in set(BASES) - {FLUX1}:
        assert not any(
            "composition" in kind
            for field in _inputs(base_id).values()
            for kind in field.get("modelTypes") or ()
        )


@pytest.mark.parametrize("model_id", sorted(capture.PUBLIC_TRAINED.values()))
def test_public_trained_records_carry_no_runnable_schema(model_id):
    record = PUBLIC[model_id]
    fields = set(record["observedFields"])
    assert {"inputs", "uiConfig"}.isdisjoint(fields)
    assert {"parameters", "concepts", "type", "custom"} & fields
    assert record["custom"] is False
    assert (record["privacy"], record["status"]) == ("public", "trained")
    kind = catalog.trained_kind(catalog.ModelRecord.from_api(record))
    assert kind == ("composition" if record["type"].endswith("-composition") else "lora")
    assert kind in catalog.USABLE_TRAINED_KINDS
    assert set(CONTRACTS["catalog"]["trainedDetailsCarry"]) == set(capture.PUBLIC_TRAINED)
    assert all(
        carries == {"inputs": False, "uiConfig": False}
        for carries in CONTRACTS["catalog"]["trainedDetailsCarry"].values()
    )


def test_composition_concepts_name_flux1_loras_with_unit_scales():
    compositions = [record for record in PUBLIC.values() if record["type"] == "flux.1-composition"]
    assert len(compositions) == 2
    for record in compositions:
        assert record["concepts"]
        for concept in record["concepts"]:
            assert isinstance(concept["modelId"], str) and concept["modelId"]
            assert 0 <= concept["scale"] <= 1
    unlisted = PUBLIC[capture.PUBLIC_TRAINED["flux1_composition_unlisted_concept"]]
    assert any("FIXTURE" in concept["modelId"] for concept in unlisted["concepts"])
    # Every concept, including one missing from the public list, was readable by
    # ID, so a quote-time check can read concept types fresh.
    reads = CONTRACTS["catalog"]["compositionConcepts"]
    public = {"listedPublic": True, "readable": True, "type": "flux.1-lora", "privacy": "public"}
    assert reads == {
        "flux1_composition": [public] * 3,
        "flux1_composition_unlisted_concept": [
            {**public, "listedPublic": False, "privacy": "unlisted"},
            public,
        ],
    }
    for role, rows in reads.items():
        assert len(rows) == len(PUBLIC[capture.PUBLIC_TRAINED[role]]["concepts"])


@pytest.mark.parametrize("model_id", sorted(capture.PUBLIC_TRAINED.values()))
def test_the_adapter_still_refuses_to_quote_a_trained_model_directly(model_id):
    def refuse(request):
        raise AssertionError("no request may be sent for a trained target")

    with SDKAdapter(
        Credentials("fixture-key", "fixture-secret"),
        online=lambda: True,
        base_url="https://service.example.invalid/v1",
        transport=httpx.MockTransport(refuse),
    ) as client:
        with pytest.raises(ValueError, match="verified REST schema contract"):
            client.estimate_model(PUBLIC[model_id], {"prompt": "p", "aspectRatio": "1:1"})


def test_catalog_reads_carry_no_form_schemas():
    observed = CONTRACTS["catalog"]
    no_schema = {"inputs": False, "uiConfig": False}
    assert observed["public"]["listRowsCarry"] == no_schema
    assert observed["bulk"]["rowsCarry"] == no_schema
    assert observed["bulk"]["returned"] == observed["bulk"]["requested"] == 11
    private = observed["privateTrained"]
    assert private == {"present": False} or set(private) == {"present", "listRowsCarry", "types"}


def test_stack_cases_cover_every_base_with_a_public_lora_type():
    public_types = set(CONTRACTS["catalog"]["public"]["types"])
    stacked = {case["target"] for case in CASES.values() if case["route"] == "stack"}
    stackable = {
        base_id for base_id in BASES if set(_inputs(base_id)["loras"]["modelTypes"]) & public_types
    }
    assert stacked == stackable == {FLUX1, "model_bfl-flux-2-dev", KONTEXT}


def test_route_decisions_match_the_recorded_dry_runs():
    assert CONTRACTS["routes"] == capture.decide(CONTRACTS["dryRuns"])
    assert {route: value["result"] for route, value in CONTRACTS["routes"].items()} == {
        "stack": "accepted",
        "model_id": "accepted",
        "composition": "accepted",
        "direct": "rejected",
    }


@pytest.mark.parametrize(
    "name", sorted(name for name, case in CASES.items() if case["route"] == "direct")
)
def test_trained_ids_are_rejected_as_generation_targets(name):
    case = CASES[name]
    assert case["target"] in capture.PUBLIC_TRAINED.values()
    assert case["status"] == 400
    assert case["reply"] == {"reason": "Custom models only are supported for this endpoint"}


@pytest.mark.parametrize(
    "name",
    sorted(name for name, case in CASES.items() if case["route"] in capture.QUOTED_ROUTES),
)
def test_accepted_routes_quote_exactly_through_the_existing_adapter_path(name):
    case = CASES[name]
    assert case["status"] == 269
    assert set(case["reply"]) == {"creativeUnitsCost", "creativeUnitsDiscount", "costDetails"}
    cost = Decimal(str(case["reply"]["creativeUnitsCost"]))
    assert cost > 0
    quote = case["adapterQuote"]
    if "rejected" in quote:
        # A capture made with the client policy records its refusal of a
        # request the service accepts.
        assert quote["rejected"] == LOCAL_OUTCOMES[name]
        return
    assert Decimal(str(quote["reply"]["creativeUnitsCost"])) == cost
    if LOCAL_OUTCOMES[name] is not None:
        return  # Recorded before the client policy; see the local outcome test.
    # The shared form preparation keeps the selection and only adds defaults.
    target, payload = prepare_run(
        case["target"], record_schema("model", BASES[case["target"]]), case["body"]
    )
    assert target == case["target"]
    assert {key: payload[key] for key in case["body"]} == case["body"]
    assert sorted(set(payload) - set(case["body"])) == quote["addedDefaults"]


def test_lora_selection_changes_the_price_only_where_declared():
    def cost(name):
        return CASES[name]["reply"]["creativeUnitsCost"]

    assert cost("stack_one") == cost("stack_two") == cost("model_id_lora") == cost("base_only")
    assert cost("composition") == cost("base_only")
    assert cost("stack_kontext") > cost("kontext_reference_only")


@pytest.mark.parametrize("name", sorted(SERVER_CHECKS))
def test_server_validation_of_lora_inputs(name):
    status, reason = SERVER_CHECKS[name]
    case = CASES[name]
    assert case["route"] == "check" and case["target"] == FLUX1
    assert case["status"] == status
    if reason is None:
        assert set(case["reply"]) == {"creativeUnitsCost", "creativeUnitsDiscount", "costDetails"}
    else:
        assert case["reply"] == {"reason": reason}


def test_every_captured_request_has_a_local_outcome():
    assert set(LOCAL_OUTCOMES) == {
        name for name, case in CASES.items() if case["route"] != "direct"
    }


@pytest.mark.parametrize("name", sorted(LOCAL_OUTCOMES))
def test_local_policy_compared_with_the_server(name):
    case = CASES[name]
    expected = LOCAL_OUTCOMES[name]
    assert _local_outcome(case) == expected
    if expected is None:
        # Every request the client accepts was accepted by the service too.
        assert case["status"] == 269


def test_reference_inputs_and_identifiers_are_placeholders():
    text = "\n".join(path.read_text(encoding="utf-8") for path in sorted(TRAINED.rglob("*.json")))
    assert not re.findall(r"\basset_(?!FIXTURE)\w+", text)
    assert "projectId" not in text and "proj_" not in text.replace("proj_FIXTURE", "")
    kept = set(capture.PUBLIC_TRAINED.values())
    for record in PUBLIC.values():
        kept |= {concept["modelId"] for concept in record.get("concepts") or ()}
        kept.add(record.get("parentModelId"))
    # Every other random model identifier was checked against the public list
    # at capture time; anything else would have been replaced by a placeholder.
    assert set(re.findall(r"\bmodel_(?!FIXTURE)[A-Za-z0-9]{16,}\b", text)) <= kept
