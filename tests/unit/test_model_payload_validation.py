# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Captured REST input rules and explicitly separate remote-MCP route validation."""

import copy
import json
import socket
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from scenario.core.api.sdk_adapter import Credentials, SDKAdapter
from scenario.core.schema.forms import prepare_run, validate_parameters
from scenario.core.schema.params import parse_schema, validate

FIXTURES = Path(__file__).parents[1] / "fixtures/models"


def model(name):
    # Reuse input/identity fields from existing captured records, not invented
    # model schemas or copied account metadata in a new fixture.
    value = json.loads((FIXTURES / (name + ".json")).read_text())["model"]
    return {key: value[key] for key in ("id", "type", "inputs")}


@pytest.fixture(autouse=True)
def forbid_network(monkeypatch):
    def deny(*args, **kwargs):
        pytest.fail("Payload contracts must not open sockets")

    monkeypatch.setattr(socket.socket, "connect", deny)
    monkeypatch.setattr(socket.socket, "connect_ex", deny)
    monkeypatch.setattr(socket, "create_connection", deny)


@pytest.mark.parametrize(
    "name,invalid,valid",
    [
        (
            "model_minimax-h3",
            {"prompt": "fixture", "lastFrameImage": "last"},
            {"firstFrameImage": "first"},
        ),
        ("model_cartwheel-text-to-motion", {"prompt": "walk"}, {"characterFile": "reference"}),
        ("model_patina-material", {"prompt": "fixture", "mask": "mask"}, {"image": "reference"}),
        (
            "model_openai-gpt-image-2",
            {"prompt": "fixture", "mask": "mask"},
            {"referenceImages": ["reference"]},
        ),
        ("model_rodin-hyper3d-bang", {"model": "mesh"}, {"prompt": "bronze"}),
    ],
)
def test_captured_requirements_match_pure_preparation_and_sdk_before_dispatch(name, invalid, valid):
    record = model(name)
    schema = {"parameters": record["inputs"]}
    original = copy.deepcopy((record, invalid, valid))
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(200, json={"creativeUnitsCost": 1})

    with SDKAdapter(
        Credentials("fixture-key", "fixture-secret"),
        online=lambda: True,
        project_id="fixture-project",
        transport=httpx.MockTransport(respond),
    ) as adapter:
        assert validate_parameters(schema, invalid)
        with pytest.raises(ValueError):
            prepare_run(record["id"], schema, invalid)
        with pytest.raises(ValueError):
            adapter.estimate_model(record, invalid)
        assert calls == []
        parameters = {**invalid, **valid}
        assert not validate_parameters(schema, parameters)
        target, payload = prepare_run(record["id"], schema, parameters)
        quote = adapter.estimate_model(record, parameters)
        assert (quote.target_id, quote.payload) == (target, payload)
        assert json.loads(calls[0].content) == payload
        assert dict(calls[0].url.params) == {"dryRun": "true", "projectId": "fixture-project"}
        assert len(calls) == 1
    assert (record, invalid, valid) == original


def overlap_schema():
    # A synthetic edge case for the SDK-documented ifNotDefined relationship:
    # each field keeps its own requirement, even when groups overlap.
    return {
        "parameters": [
            {"name": "a", "type": "file", "required": {"ifNotDefined": {"b": {}}}},
            {"name": "b", "type": "file", "required": {"ifNotDefined": {"c": {}}}},
            {"name": "c", "type": "file"},
        ]
    }


@pytest.mark.parametrize(
    "names,allowed",
    [
        ((), False),
        (("a",), False),
        (("c",), False),
        (("b",), True),
        (("a", "c"), True),
        (("a", "b", "c"), True),
    ],
)
def test_overlapping_either_or_groups_remain_separate_requirements(names, allowed):
    schema = overlap_schema()
    parsed = parse_schema(SimpleNamespace(parameters=schema["parameters"], ui_config={}))
    assert parsed.one_of == [("a", "b"), ("b", "c")]
    values = dict.fromkeys(names, "fixture-asset")
    assert (not validate(parsed.specs, values, parsed.one_of)) == allowed
    assert (not validate_parameters(schema, values)) == allowed
    if allowed:
        assert prepare_run("base", schema, values) == ("base", values)
    else:
        with pytest.raises(ValueError, match="Provide one"):
            prepare_run("base", schema, values)


def test_nested_inputs_keep_conditional_rules_and_array_paths():
    schema = {
        "parameters": [
            {
                "name": "clips",
                "type": "inputs_array",
                "inputs": [
                    {"name": "first", "type": "file", "required": {"ifDefined": {"last": {}}}},
                    {"name": "last", "type": "file"},
                ],
            }
        ]
    }
    with pytest.raises(ValueError, match=r"Clips \[1\].*first is required"):
        prepare_run("base", schema, {"clips": [{"last": "last"}]})
    payload = {"clips": [{"first": "first", "last": "last"}]}
    assert prepare_run("base", schema, payload)[1] == payload


def lora_route():
    # Sanitized structural projection of Studio's captured model_schema_get
    # LoRA route at e2b0277. This is remote-MCP metadata, NOT a REST contract.
    return {
        "runs_as": "lora",
        "parameters": [
            {"name": "prompt", "type": "string", "required": True},
            {"name": "loras", "type": "model_array", "default": []},
            {"name": "lorasScale", "type": "number_array"},
        ],
        "run_with": {
            "tool": "model_run",
            "required_arguments": {
                "model_id": "fixture-base",
                "parameters": {"loras": ["fixture-selected"]},
            },
        },
    }


@pytest.mark.parametrize(
    "identifier",
    [
        None,
        123,
        True,
        [],
        {},
        "",
        "..",
        "padded ",
        "bad/id",
        "bad?query",
        "bad%2fid",
        "bad\u00a0id",
        "bad\x7fid",
    ],
)
def test_route_targets_are_rejected_not_coerced(identifier):
    schema = lora_route()
    schema["run_with"]["required_arguments"]["model_id"] = identifier
    with pytest.raises(ValueError, match="model ID"):
        prepare_run("fixture-selected", schema, {"prompt": "fixture"})


@pytest.mark.parametrize(
    "routing",
    [
        None,
        [],
        {"required_arguments": None},
        {"required_arguments": []},
        {"required_arguments": {"model_id": "base", "parameters": []}},
    ],
)
def test_malformed_route_structure_cannot_fall_back_to_selected_model(routing):
    with pytest.raises(ValueError, match="routing"):
        prepare_run("selected", {**lora_route(), "run_with": routing}, {"prompt": "fixture"})


def test_valid_lora_wiring_survives_but_sdk_trained_model_gate_stays_closed():
    schema = lora_route()
    original = copy.deepcopy(schema)
    target, values = prepare_run(
        "fixture-selected", schema, {"prompt": "fixture", "lorasScale": [0.6]}
    )
    assert target == "fixture-base" and values == {
        "prompt": "fixture",
        "loras": ["fixture-selected"],
        "lorasScale": [0.6],
    }
    assert schema == original
    with SDKAdapter(
        Credentials("key", "secret"),
        online=lambda: True,
        transport=httpx.MockTransport(lambda r: pytest.fail("Unverified route reached REST")),
    ) as adapter:
        with pytest.raises(ValueError, match="verified REST schema"):
            adapter.estimate_model(
                {"id": "fixture-selected", "type": "flux.1-lora", **schema}, {"prompt": "fixture"}
            )


def test_synthetic_composition_route_keeps_mandatory_wiring():
    schema = {
        "runs_as": "composition",
        "parameters": [{"name": "prompt", "type": "string"}],
        "run_with": {
            "required_arguments": {"model_id": "base", "parameters": {"modelId": "composition"}}
        },
    }
    assert prepare_run("composition", schema, {"prompt": "fixture", "modelId": "wrong"}) == (
        "base",
        {"prompt": "fixture", "modelId": "composition"},
    )


@pytest.mark.parametrize("parameters", [{"fileA": "a"}, {"fileB": "b"}, {}])
def test_implicit_file_alternatives_each_require_a_file_or_prompt(parameters):
    # Synthetic overlap case using the same bounded description heuristic as
    # the captured Rodin fixture: each file is required in the absence of prompt.
    fields = [
        {"name": "prompt", "type": "string", "prompt": True},
        *[
            {
                "name": name,
                "type": "file",
                "required": True,
                "description": "Required if no prompt is provided.",
            }
            for name in ("fileA", "fileB")
        ],
    ]
    schema = {"parameters": fields}
    parsed = parse_schema(SimpleNamespace(parameters=fields, ui_config={}))
    assert parsed.one_of == [("fileA", "prompt"), ("fileB", "prompt")]
    with pytest.raises(ValueError, match="Provide one"):
        prepare_run("base", schema, parameters)
    for valid in ({"prompt": "fixture"}, {"fileA": "a", "fileB": "b"}):
        assert prepare_run("base", schema, valid)[1] == valid


def test_required_default_and_mandatory_wiring_are_validated_after_merge():
    schema = {
        "parameters": [
            {"name": "prompt", "type": "string", "required": True, "default": "fixture"},
            {"name": "first", "type": "file", "required": {"ifDefined": {"last": {}}}},
            {"name": "last", "type": "file", "required": True},
        ],
        "run_with": {
            "required_arguments": {"model_id": "base", "parameters": {"first": "a", "last": "b"}}
        },
    }
    assert prepare_run("selected", schema, {}) == (
        "base",
        {"prompt": "fixture", "first": "a", "last": "b"},
    )


@pytest.mark.parametrize("source", ["default", "wiring"])
def test_final_payload_cannot_introduce_unsatisfied_requirements(source):
    fields = [
        {"name": "first", "type": "file", "required": {"ifDefined": {"last": {}}}},
        {"name": "last", "type": "file"},
    ]
    schema = {"parameters": fields}
    if source == "default":
        fields[1]["default"] = "last"
    else:
        schema["run_with"] = {"required_arguments": {"parameters": {"last": "last"}}}
    with pytest.raises(ValueError, match="first is required"):
        prepare_run("base", schema, {})


def test_nested_required_wiring_is_merged_before_complete_validation():
    schema = {
        "parameters": [
            {
                "name": "options",
                "type": "inputs",
                "inputs": [
                    {"name": "count", "type": "number", "required": True},
                    {"name": "enabled", "type": "boolean", "required": True},
                ],
            }
        ],
        "run_with": {"required_arguments": {"parameters": {"options": {"count": 0}}}},
    }
    assert prepare_run("base", schema, {"options": {"enabled": False}})[1] == {
        "options": {"count": 0, "enabled": False}
    }


@pytest.mark.parametrize("value", [False, 0])
def test_false_and_zero_are_defined_for_conditional_requirements(value):
    schema = {
        "parameters": [
            {"name": "dependent", "type": "string", "required": {"ifDefined": {"trigger": {}}}},
            {"name": "trigger", "type": "boolean" if value is False else "number"},
        ]
    }
    with pytest.raises(ValueError, match="dependent is required"):
        prepare_run("base", schema, {"trigger": value})
    assert (
        prepare_run("base", schema, {"trigger": value, "dependent": "yes"})[1]["trigger"] == value
    )


def test_bad_user_array_is_not_silently_discarded_by_mandatory_wiring():
    with pytest.raises(ValueError, match="expected an array"):
        prepare_run("fixture-selected", lora_route(), {"prompt": "fixture", "loras": "bad"})


@pytest.mark.parametrize(
    "fields",
    [
        None,
        "bad",
        [None],
        [{"name": ""}],
        [{"name": "  "}],
        [{"name": "x"}, {"name": "x"}],
        [{"name": "x", "type": None}],
        [{"name": "x", "required": {"ifDefined": []}}],
        {"x": None},
    ],
)
def test_malformed_fields_fail_consistently_before_sdk_dispatch(fields):
    with pytest.raises(ValueError):
        prepare_run("base", {"parameters": fields}, {})
    with SDKAdapter(
        Credentials("key", "secret"),
        online=lambda: True,
        transport=httpx.MockTransport(lambda r: pytest.fail("Malformed schema reached REST")),
    ) as adapter:
        with pytest.raises(ValueError):
            adapter.estimate_model({"id": "base", "type": "custom", "inputs": fields}, {})


@pytest.mark.parametrize("condition", ["ifDefined", "ifNotDefined"])
@pytest.mark.parametrize("sibling", ["missing", "", " "])
def test_unknown_conditional_siblings_fail_closed(condition, sibling):
    fields = [{"name": "dependent", "type": "file", "required": {condition: {sibling: {}}}}]
    with pytest.raises(ValueError, match="unknown input"):
        parse_schema(SimpleNamespace(parameters=fields, ui_config={}))
    with pytest.raises(ValueError, match="unknown input"):
        prepare_run("base", {"parameters": fields}, {})
    with SDKAdapter(
        Credentials("key", "secret"),
        online=lambda: True,
        transport=httpx.MockTransport(lambda r: pytest.fail("Unknown sibling reached REST")),
    ) as adapter:
        with pytest.raises(ValueError, match="unknown input"):
            adapter.estimate_model({"id": "base", "type": "custom", "inputs": fields}, {})


@pytest.mark.parametrize("condition,trigger", [("ifDefined", True), ("ifNotDefined", None)])
def test_blank_strings_cannot_satisfy_conditional_requirements(condition, trigger):
    fields = [
        {"name": "dependent", "type": "string", "required": {condition: {"trigger": {}}}},
        {"name": "trigger", "type": "boolean"},
    ]
    values = {"dependent": "  ", "trigger": trigger}
    with pytest.raises(ValueError):
        prepare_run("base", {"parameters": fields}, values)
    parsed = parse_schema(SimpleNamespace(parameters=fields, ui_config={}))
    assert validate(parsed.specs, values, parsed.one_of)


def test_blank_trigger_does_not_require_dependent_but_self_alternative_does():
    schema = {
        "parameters": [
            {"name": "dependent", "required": {"ifDefined": {"trigger": {}}}},
            {"name": "trigger"},
        ]
    }
    assert prepare_run("base", schema, {"trigger": " "})[1] == {"trigger": " "}
    schema = {
        "parameters": [{"name": "file", "type": "file", "required": {"ifNotDefined": {"file": {}}}}]
    }
    with pytest.raises(ValueError, match="Provide one"):
        prepare_run("base", schema, {})
