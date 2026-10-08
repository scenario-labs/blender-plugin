# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Contracts for dynamic Scenario forms, including routing and reference types."""

from copy import deepcopy

import pytest


def sample_schema():
    return {
        "parameters": [
            {"name": "prompt", "type": "string", "required": True, "max_length": 10},
            {"name": "seed", "type": "number", "min": 0, "max": 10, "default": 0},
            {"name": "enabled", "type": "boolean", "default": False},
            {"name": "image", "type": "file"},
            {"name": "references", "type": "file_array", "max_length": 2},
            {"name": "quality", "type": "string", "allowed_values": ["low", "high"]},
            {"name": "weights", "type": "number_array", "min": 0, "max": 2},
        ]
    }


def test_defaults_and_prepare_keep_zero_false_and_omit_empty_optional_files():
    from scenario.core.schema.forms import prepare_run, schema_defaults

    schema = sample_schema()
    assert schema_defaults(schema) == {"seed": 0, "enabled": False}
    model, values = prepare_run(
        "model_test", schema, {"prompt": "café", "image": "", "references": []}
    )
    assert model == "model_test"
    assert values == {"prompt": "café", "seed": 0, "enabled": False}


@pytest.mark.parametrize(
    "values,fragment",
    [
        ({}, "Prompt"),
        ({"prompt": "too long a prompt"}, "10"),
        ({"prompt": "valid", "seed": True}, "Seed"),
        ({"prompt": "valid", "seed": -1}, "0"),
        ({"prompt": "valid", "seed": 11}, "10"),
        ({"prompt": "valid", "seed": float("nan")}, "Seed"),
        ({"prompt": "valid", "references": "asset_one"}, "array"),
        ({"prompt": "valid", "image": ["asset_one"]}, "Image"),
        ({"prompt": "valid", "references": ["a", "b", "c"]}, "2"),
        ({"prompt": "valid", "weights": [0, 3]}, "2"),
        ({"prompt": "valid", "quality": "invalid"}, "Quality"),
        ({"prompt": "valid", "extra": 1}, "Extra"),
        ({"prompt": "valid", "enabled": 0}, "Enabled"),
    ],
)
def test_rejects_invalid_values_with_readable_labels(values, fragment):
    from scenario.core.schema.forms import validate_parameters

    errors = validate_parameters(sample_schema(), values)
    assert errors and fragment.lower() in " ".join(errors).lower()


def test_required_file_array_and_nested_fields():
    from scenario.core.schema.forms import validate_parameters

    schema = {
        "parameters": [
            {"name": "references", "type": "file_array", "required": True},
            {
                "name": "segments",
                "type": "inputs_array",
                "fields": [{"name": "start", "type": "number", "min": 0, "required": True}],
            },
        ]
    }
    assert validate_parameters(schema, {"references": []})
    assert validate_parameters(schema, {"references": ["asset_ok"], "segments": [{"start": -1}]})
    assert not validate_parameters(schema, {"references": ["asset_ok"], "segments": [{"start": 0}]})


def test_lora_wiring_survives_default_empty_list_and_merges_additional_loras():
    from scenario.core.schema.forms import prepare_run

    schema = {
        "runs_as": "lora",
        "parameters": [
            {"name": "prompt", "type": "string", "required": True},
            {"name": "loras", "type": "model_array", "default": []},
            {"name": "lorasScale", "type": "number_array"},
        ],
        "run_with": {
            "required_arguments": {
                "model_id": "model_base",
                "parameters": {"loras": ["model_selected"]},
            }
        },
    }
    original = deepcopy(schema)
    assert prepare_run("model_selected", schema, {"prompt": "stone"}) == (
        "model_base",
        {"prompt": "stone", "loras": ["model_selected"]},
    )
    _, values = prepare_run(
        "model_selected",
        schema,
        {"prompt": "stone", "loras": ["model_other"], "lorasScale": [0.4]},
    )
    assert values["loras"] == ["model_selected", "model_other"]
    assert values["lorasScale"] == [1.0, 0.4]
    assert schema == original


def test_composition_wiring_cannot_be_lost_or_retargeted():
    from scenario.core.schema.forms import prepare_run, validate_parameters

    schema = {
        "runs_as": "composition",
        "parameters": [{"name": "prompt", "type": "string"}],
        "run_with": {
            "required_arguments": {
                "model_id": "base",
                "parameters": {"modelId": "composition"},
            }
        },
    }
    assert not validate_parameters(schema, {"prompt": "test", "modelId": "composition"})
    assert prepare_run("composition", schema, {"prompt": "test", "modelId": "other"}) == (
        "base",
        {"prompt": "test", "modelId": "composition"},
    )


def test_invalid_prepare_raises_and_missing_lora_route_does_not_submit_own_id():
    from scenario.core.schema.forms import prepare_run

    with pytest.raises(ValueError, match="Prompt"):
        prepare_run("model", sample_schema(), {})
    with pytest.raises(ValueError, match="routing"):
        prepare_run("lora", {"runs_as": "lora", "parameters": []}, {})


def test_rest_workflow_constraint_aliases_and_labels():
    from scenario.core.schema.forms import display_label, is_file_field, validate_parameters

    schema = {
        "parameters": [
            {
                "name": "names",
                "type": "string_array",
                "allowedValues": ["a"],
                "maxLength": 1,
            }
        ]
    }
    assert validate_parameters(schema, {"names": ["b"]})
    assert validate_parameters(schema, {"names": ["a", "a"]})
    assert display_label("referenceImages") == "Reference images"
    assert display_label("uvMode") == "UV mode"
    assert is_file_field({"type": "file_array"})
    assert not is_file_field({"type": "string", "kind": "image"})


def test_workflow_required_objects_and_field_labels_are_respected():
    from scenario.core.schema.forms import prepare_run, validate_parameters

    schema = {
        "parameters": [
            {
                "name": "image1",
                "label": "Main image",
                "type": "file",
                "required": {"always": True},
            },
            {
                "name": "text1",
                "label": "Instructions",
                "type": "string",
                "default": "",
                "required": {"always": False},
            },
            {"name": "image2", "type": "file", "required": {"always": False}},
        ]
    }
    assert validate_parameters(schema, {}) == ["Main image is required."]
    assert prepare_run("workflow", schema, {"image1": "asset_one", "image2": ""}) == (
        "workflow",
        {"text1": "", "image1": "asset_one"},
    )


def test_lora_weight_can_address_selected_lora_without_repeating_its_id():
    from scenario.core.schema.forms import prepare_run

    schema = {
        "parameters": [
            {"name": "loras", "type": "model_array", "default": []},
            {"name": "lorasScale", "type": "number_array"},
        ],
        "runs_as": "lora",
        "run_with": {
            "required_arguments": {
                "model_id": "base",
                "parameters": {"loras": ["chosen"]},
            }
        },
    }
    assert prepare_run("chosen", schema, {"lorasScale": [0.6]}) == (
        "base",
        {"loras": ["chosen"], "lorasScale": [0.6]},
    )


def test_composition_omits_empty_lora_default_that_would_override_its_concepts():
    from scenario.core.schema.forms import prepare_run

    schema = {
        "runs_as": "composition",
        "parameters": [
            {"name": "prompt", "type": "string", "required": True},
            {"name": "modelId", "type": "model", "default": ""},
            {"name": "loras", "type": "model_array", "default": []},
        ],
        "run_with": {
            "required_arguments": {
                "model_id": "base",
                "parameters": {"modelId": "composition"},
            }
        },
    }
    assert prepare_run("composition", schema, {"prompt": "cube"}) == (
        "base",
        {"prompt": "cube", "modelId": "composition"},
    )


def test_file_reference_edit_allows_incomplete_form_without_weakening_final_validation():
    from scenario.core.schema.forms import append_file_reference, validate_parameters

    schema = {
        "parameters": [
            {"name": "prompt", "type": "string", "required": True},
            {"name": "images", "type": "file_array", "kind": "image", "minItems": 2, "maxItems": 2},
        ]
    }
    before = deepcopy(schema)
    one = append_file_reference(schema, "images", "first", "image")
    assert one == ["first"]
    assert validate_parameters(schema, {"images": one})
    two = append_file_reference(schema, "images", "second", "image", one)
    assert validate_parameters(schema, {"prompt": "cup", "images": two}) == []
    with pytest.raises(ValueError, match="at most 2"):
        append_file_reference(schema, "images", "third", "image", two)
    assert schema == before
    assert one == ["first"]


@pytest.mark.parametrize("kind", ["image", "audio", "video", "3d"])
def test_file_reference_edit_preserves_input_kind_and_rejects_replacement(kind):
    from scenario.core.schema.forms import append_file_reference

    schema = {"parameters": [{"name": "reference", "type": "file", "kind": kind}]}
    assert append_file_reference(schema, "reference", "asset", kind) == "asset"
    with pytest.raises(ValueError, match="existing reference"):
        append_file_reference(schema, "reference", "new", kind, "old")
    with pytest.raises(ValueError, match="file type"):
        append_file_reference(schema, "reference", "asset", "audio" if kind == "image" else "image")


@pytest.mark.parametrize(
    "existing,asset,fragment",
    [
        ([], "other", "allowed values"),
        (["asset"], "asset", "already"),
        ("asset", "asset", "array"),
        ([42], "asset", "one asset ID"),
        ([], "", "nonempty"),
    ],
)
def test_reference_edit_rejects_invalid_ids_arrays_duplicates_and_enum_values(
    existing, asset, fragment
):
    from scenario.core.schema.forms import append_file_reference

    schema = {"parameters": [{"name": "refs", "type": "file_array", "allowedValues": ["asset"]}]}
    with pytest.raises(ValueError, match=fragment):
        append_file_reference(schema, "refs", asset, "image", existing)


def test_reference_edit_accepts_conditional_input_before_sibling_is_complete():
    from scenario.core.schema.forms import append_file_reference

    schema = {
        "parameters": [
            {"name": "image", "type": "file", "required": {"ifDefined": {"prompt": True}}},
            {"name": "prompt", "type": "string", "required": True},
        ]
    }
    assert append_file_reference(schema, "image", "asset", "image") == "asset"
    with pytest.raises(ValueError, match="file input"):
        append_file_reference(schema, "prompt", "asset", "image")
