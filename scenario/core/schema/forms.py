# SPDX-FileCopyrightText: 2026 Scenario
# SPDX-License-Identifier: GPL-3.0-or-later
# Adapted from Scenario Blender Studio; see docs/SOURCE_PROVENANCE.md.
"""Schema-driven defaults, validation and Scenario LoRA/composition routing."""

from __future__ import annotations

import math
import re
from copy import deepcopy
from typing import Any


def display_label(name: str) -> str:
    """Turn API identifiers into compact, readable form labels."""
    special = {
        "numOutputs": "Outputs",
        "numImages": "Images",
        "numInferenceSteps": "Inference steps",
        "file3d": "Source mesh",
        "file3D": "Source mesh",
        "imageFile": "Reference image",
        "videoFile": "Reference video",
    }
    if name in special:
        return special[name]
    words = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", str(name))
    words = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", words).replace("_", " ").replace("-", " ")
    acronyms = {
        "uv",
        "pbr",
        "hdr",
        "hdri",
        "id",
        "url",
        "fps",
        "3d",
        "2d",
        "rgb",
        "rgba",
        "cfg",
    }
    parts = [word.upper() if word.lower() in acronyms else word.lower() for word in words.split()]
    if not parts:
        return "Parameter"
    if parts[0].lower() not in acronyms:
        parts[0] = parts[0].capitalize()
    return " ".join(parts)


def is_file_field(field: dict[str, Any]) -> bool:
    """Whether this field holds a single file reference or an array of them."""
    return field.get("type") in {"file", "file_array"}


def _fields(schema: dict[str, Any]) -> list[dict[str, Any]]:
    raw = schema.get("parameters", schema.get("inputs_definition", schema.get("inputs", [])))
    if isinstance(raw, list):
        return [
            field for field in raw if isinstance(field, dict) and isinstance(field.get("name"), str)
        ]
    if isinstance(raw, dict):
        return [dict(field, name=name) for name, field in raw.items() if isinstance(field, dict)]
    return []


def _empty(value: Any) -> bool:
    return value is None or value == "" or value == []


def _required(field: dict[str, Any]) -> bool:
    requirement = field.get("required", False)
    return (
        requirement.get("always") is True if isinstance(requirement, dict) else requirement is True
    )


def _optional_omitted(field: dict[str, Any], value: Any) -> bool:
    return not _required(field) and (
        value is None
        or (
            (is_file_field(field) or field.get("type") in {"model", "model_array"})
            and _empty(value)
        )
    )


def schema_defaults(schema: dict[str, Any]) -> dict[str, Any]:
    """Copy actual defaults, retaining false and zero without invented inputs."""
    return {
        field["name"]: deepcopy(field["default"])
        for field in _fields(schema)
        if "default" in field and not _optional_omitted(field, field["default"])
    }


def _constraint(field: dict[str, Any], *names: str) -> Any:
    for name in names:
        if name in field:
            return field[name]
    return None


def _equal_enum(value: Any, candidate: Any) -> bool:
    if isinstance(value, bool) != isinstance(candidate, bool):
        return False
    return bool(value == candidate)


def _validate_value(field: dict[str, Any], value: Any, label: str) -> list[str]:
    errors: list[str] = []
    kind = field.get("type", "string")
    is_array = kind.endswith("_array") or kind == "array" or field.get("array") is True
    if is_array:
        if not isinstance(value, list):
            return [f"{label}: expected an array, even for a single item."]
        minimum = _constraint(field, "min_length", "minLength", "minItems")
        maximum = _constraint(field, "max_length", "maxLength", "maxItems")
        if isinstance(minimum, (int, float)) and len(value) < minimum:
            errors.append(f"{label}: use at least {minimum:g} items.")
        if isinstance(maximum, (int, float)) and len(value) > maximum:
            errors.append(f"{label}: use at most {maximum:g} items.")
        item_kind = kind.removesuffix("_array") if kind != "array" else "object"
        item = {
            k: v
            for k, v in field.items()
            if k
            not in {
                "array",
                "min_length",
                "max_length",
                "minLength",
                "maxLength",
                "minItems",
                "maxItems",
            }
        }
        item["type"] = "object" if item_kind == "inputs" else item_kind
        if kind == "array" and isinstance(field.get("items"), dict):
            item = field["items"]
        for index, entry in enumerate(value, 1):
            errors.extend(_validate_value(item, entry, f"{label} [{index}]"))
        return errors
    if kind in {"number", "integer"}:
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
        ):
            return [f"{label}: enter a finite number."]
        if kind == "integer" and value != int(value):
            errors.append(f"{label}: enter a whole number.")
        minimum = _constraint(field, "min", "minimum")
        maximum = _constraint(field, "max", "maximum")
        if isinstance(minimum, (int, float)) and value < minimum:
            errors.append(f"{label}: minimum is {minimum:g}.")
        if isinstance(maximum, (int, float)) and value > maximum:
            errors.append(f"{label}: maximum is {maximum:g}.")
    elif kind == "boolean":
        if not isinstance(value, bool):
            return [f"{label}: expected true or false."]
    elif kind in {"string", "file", "model"}:
        if not isinstance(value, str):
            return [f"{label}: expected {'one asset ID' if kind == 'file' else 'text'}."]
        if kind in {"file", "model"} and not value.strip():
            errors.append(
                f"{label}: provide a nonempty {'asset' if kind == 'file' else 'model'} ID."
            )
        minimum = _constraint(field, "min_length", "minLength")
        maximum = _constraint(field, "max_length", "maxLength")
        if isinstance(minimum, (int, float)) and len(value) < minimum:
            errors.append(f"{label}: use at least {minimum:g} characters.")
        if isinstance(maximum, (int, float)) and len(value) > maximum:
            errors.append(f"{label}: use at most {maximum:g} characters.")
    elif kind in {"object", "inputs"}:
        if not isinstance(value, dict):
            return [f"{label}: expected an object."]
        nested = field.get("fields", field.get("inputs"))
        if isinstance(nested, list):
            errors.extend(
                f"{label}: {error}" for error in validate_parameters({"parameters": nested}, value)
            )
    # Unknown future field types remain editable as JSON; enforce known constraints.
    allowed = _constraint(field, "allowed_values", "allowedValues", "enum")
    if isinstance(allowed, list) and not any(
        _equal_enum(value, candidate) for candidate in allowed
    ):
        errors.append(f"{label}: select one of the allowed values.")
    return errors


def _required_arguments(schema: dict[str, Any]) -> dict[str, Any]:
    routing = schema.get("run_with", {})
    arguments = routing.get("required_arguments", {}) if isinstance(routing, dict) else {}
    return arguments if isinstance(arguments, dict) else {}


def validate_parameters(schema: dict[str, Any], parameters: dict[str, Any]) -> list[str]:
    """Return human-readable errors; never mutate inputs or discard zero/false."""
    if not isinstance(parameters, dict):
        return ["Parameters must be an object."]
    fields = {field["name"]: field for field in _fields(schema)}
    required = _required_arguments(schema).get("parameters", {})
    wiring = set(required) if isinstance(required, dict) else set()
    errors = [
        f"{display_label(name)}: unknown parameter for this model."
        for name in parameters
        if name not in fields and name not in wiring
    ]
    for name, field in fields.items():
        value = parameters.get(name, field.get("default"))
        label = str(field.get("label") or display_label(name))
        if _required(field) and (_empty(value) or isinstance(value, str) and not value.strip()):
            errors.append(f"{label} is required.")
            continue
        if name not in parameters and "default" not in field or _optional_omitted(field, value):
            continue
        errors.extend(_validate_value(field, value, label))
    return errors


def _merge_wiring(user: Any, required: Any) -> Any:
    if isinstance(required, dict):
        merged = deepcopy(user) if isinstance(user, dict) else {}
        for key, value in required.items():
            merged[key] = _merge_wiring(merged.get(key), value)
        return merged
    if isinstance(required, list):
        combined = deepcopy(required)
        for value in user if isinstance(user, list) else []:
            if value not in combined:
                combined.append(deepcopy(value))
        return combined
    return deepcopy(required)


def prepare_run(
    model_id: str, schema: dict[str, Any], parameters: dict[str, Any]
) -> tuple[str, dict[str, Any]]:
    """Validate form values and preserve mandatory LoRA/composition call wiring."""
    errors = validate_parameters(schema, parameters)
    if errors:
        raise ValueError("\n".join(errors))
    arguments = _required_arguments(schema)
    target = arguments.get("model_id", model_id)
    if schema.get("runs_as") in {"lora", "composition"} and not arguments.get("model_id"):
        raise ValueError("This model is missing its base-model routing. Refresh its schema.")
    values = schema_defaults(schema)
    values.update(deepcopy(parameters))
    for field in _fields(schema):
        name = field["name"]
        if name in values and _optional_omitted(field, values[name]):
            values.pop(name)
    required = arguments.get("parameters", {})
    original_loras = values.get("loras", [])
    original_scales = values.get("lorasScale")
    if isinstance(required, dict):
        values = _merge_wiring(values, required)
    if isinstance(original_loras, list) and isinstance(original_scales, list) and "loras" in values:
        if not original_loras and len(original_scales) == len(values["loras"]):
            values["lorasScale"] = original_scales
        elif len(original_scales) != len(original_loras):
            raise ValueError("LoRA scales: provide one weight for each supplied LoRA.")
        else:
            scale_by_id = dict(zip(original_loras, original_scales, strict=False))
            values["lorasScale"] = [scale_by_id.get(item, 1.0) for item in values["loras"]]
    errors = validate_parameters(schema, values)
    if errors:
        raise ValueError("\n".join(errors))
    return str(target), values
