# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Schema-driven defaults, validation and Scenario LoRA/composition routing."""

from __future__ import annotations

import math
import re
from copy import deepcopy
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

from .params import parse_schema, validate_requirements


class RouteError(ValueError):
    """A LoRA or composition selection that cannot run, with safe, actionable text.

    The text names schema labels and positions only: never a model ID, model
    name, service reply or URL.
    """


_COMPONENT_CHANGED = (
    "This model's LoRA inputs changed or are malformed. Refresh the model and choose its "
    "LoRAs again."
)


@dataclass(frozen=True)
class LoraComponent:
    """Input names a REST schema declares in `uiConfig.lorasComponent`."""

    label: str
    model_input: str
    scale_input: str
    model_id_input: str | None = None

    @property
    def names(self):
        return tuple(
            name for name in (self.model_input, self.scale_input, self.model_id_input) if name
        )


def lora_component(schema: dict[str, Any]) -> LoraComponent | None:
    """Return the schema's declared LoRA inputs, or None when it declares none.

    Only `uiConfig.lorasComponent` names LoRA inputs; no input is recognized
    by its name. `modelInput` must name a `model_array` input, `scaleInput` a
    `number_array` input and the optional `modelIdInput` a `model` input.
    Raises RouteError for a malformed component.
    """
    ui = schema.get("uiConfig") if isinstance(schema, dict) else None
    raw = ui.get("lorasComponent") if isinstance(ui, dict) else None
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise RouteError(_COMPONENT_CHANGED)
    types = {field["name"]: field.get("type") for field in _fields(schema)}
    expected = [(raw.get("modelInput"), "model_array"), (raw.get("scaleInput"), "number_array")]
    if raw.get("modelIdInput") is not None:
        expected.append((raw.get("modelIdInput"), "model"))
    for name, kind in expected:
        if not isinstance(name, str) or not name or types.get(name) != kind:
            raise RouteError(_COMPONENT_CHANGED)
    if len({name for name, _ in expected}) != len(expected):
        raise RouteError(_COMPONENT_CHANGED)
    label = raw.get("label")
    return LoraComponent(
        label.strip() if isinstance(label, str) and label.strip() else "LoRAs",
        raw["modelInput"],
        raw["scaleInput"],
        raw.get("modelIdInput"),
    )


def record_schema(operation: str, record: dict[str, Any]) -> dict[str, Any]:
    """The form schema of one REST model or workflow record: inputs and uiConfig.

    Models keep `inputs` (or the older `parameters`); workflows keep
    `inputs_definition` (or `inputs`). A missing list stays None so form
    preparation reports it.
    """
    if not isinstance(record, dict):
        raise ValueError("A current input schema is required")
    if operation == "model":
        primary, fallback = "inputs", "parameters"
    elif operation == "workflow":
        primary, fallback = "inputs_definition", "inputs"
    else:
        raise ValueError("Unsupported generation operation")
    fields = record.get(primary)
    if fields is None:
        fields = record.get(fallback)
    return {"parameters": fields, "uiConfig": record.get("uiConfig")}


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
    if not isinstance(schema, dict):
        raise ValueError("A current input schema is required")
    raw = schema.get("parameters", schema.get("inputs_definition", schema.get("inputs", [])))
    if isinstance(raw, dict):
        if not all(isinstance(field, dict) for field in raw.values()):
            raise ValueError("Input definitions must be objects")
        raw = [dict(field, name=name) for name, field in raw.items()]
    if not isinstance(raw, list) or not all(isinstance(field, dict) for field in raw):
        raise ValueError("A current input schema is required")
    names = [field.get("name") for field in raw]
    if any(not isinstance(name, str) or not name.strip() for name in names) or len(
        set(names)
    ) != len(names):
        raise ValueError("Input names must be unique nonempty strings")
    for field in raw:
        if not isinstance(field.get("type", "string"), str) or not field.get("type", "string"):
            raise ValueError("Input types must be nonempty strings")
        required = field.get("required", False)
        if isinstance(required, dict):
            for condition in ("ifDefined", "ifNotDefined"):
                siblings = required.get(condition)
                if siblings is not None and (
                    not isinstance(siblings, dict)
                    or any(not isinstance(name, str) for name in siblings)
                ):
                    raise ValueError("Conditional requirements must name sibling inputs")
                if siblings is not None and any(name not in names for name in siblings):
                    raise ValueError(
                        f"{field['name']}: conditional requirement names an unknown input"
                    )
    return raw


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
        for field in _form_fields(schema)[0]
        if "default" in field and not _optional_omitted(field, field["default"])
    }


def _form_fields(schema):
    """Use the same conditional requirement interpretation as native forms."""
    fields = _fields(schema)
    parsed = parse_schema(SimpleNamespace(parameters=fields, ui_config={}))
    normalized = [
        {**field, "required": spec.required_always}
        for field, spec in zip(fields, parsed.specs, strict=True)
    ]
    return normalized, parsed


def _constraint(field: dict[str, Any], *names: str) -> Any:
    for name in names:
        if name in field:
            return field[name]
    return None


def _equal_enum(value: Any, candidate: Any) -> bool:
    if isinstance(value, bool) != isinstance(candidate, bool):
        return False
    return bool(value == candidate)


def _validate_value(
    field: dict[str, Any], value: Any, label: str, *, complete: bool = True
) -> list[str]:
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
            errors.extend(_validate_value(item, entry, f"{label} [{index}]", complete=complete))
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
                f"{label}: {error}"
                for error in _parameter_errors({"parameters": nested}, value, complete=complete)
            )
    # Unknown future field types remain editable as JSON; enforce known constraints.
    allowed = _constraint(field, "allowed_values", "allowedValues", "enum")
    if isinstance(allowed, list) and not any(
        _equal_enum(value, candidate) for candidate in allowed
    ):
        errors.append(f"{label}: select one of the allowed values.")
    return errors


def append_file_reference(schema, name, asset_id, kind, current=None):
    """Prepare one file-input edit; complete required/minimum checks belong to pricing."""
    field = next((field for field in _fields(schema) if field["name"] == name), None)
    if field is None or not is_file_field(field):
        raise ValueError("Choose a file input")
    if (
        kind not in {"image", "audio", "video", "3d"}
        or str(field.get("kind") or "image").lower() != kind
    ):
        raise ValueError("Choose an input matching the reference file type")
    if not isinstance(asset_id, str) or not asset_id.strip():
        raise ValueError("Choose a nonempty asset ID")
    draft = dict(field)
    if field["type"] == "file" and field.get("array") is not True:
        if current not in (None, ""):
            raise ValueError("Clear the existing reference before replacing it")
        value = asset_id
    else:
        if current is None:
            current = []
        if not isinstance(current, list):
            raise ValueError("Use an array of asset IDs")
        if asset_id in current:
            raise ValueError("This reference is already in the input")
        value = [*current, asset_id]
        # An artist must be able to add the first reference to a multi-file
        # minimum. Preserve maximum, item types and allowed-value constraints.
        for key in ("min_length", "minLength", "minItems"):
            draft.pop(key, None)
    errors = _validate_value(draft, value, str(field.get("label") or display_label(name)))
    if errors:
        raise ValueError("\n".join(errors))
    return value


def _required_arguments(schema: dict[str, Any]) -> dict[str, Any]:
    routing = schema.get("run_with", {})
    arguments = routing.get("required_arguments", {}) if isinstance(routing, dict) else {}
    return arguments if isinstance(arguments, dict) else {}


def validate_parameters(schema: dict[str, Any], parameters: dict[str, Any]) -> list[str]:
    """Return human-readable errors; never mutate inputs or discard zero/false."""
    return _parameter_errors(schema, parameters, complete=True)


def _parameter_errors(schema, parameters, *, complete):
    if not isinstance(parameters, dict):
        return ["Parameters must be an object."]
    normalized, parsed = _form_fields(schema)
    fields = {field["name"]: field for field in normalized}
    required = _required_arguments(schema).get("parameters", {})
    wiring = set(required) if isinstance(required, dict) else set()
    errors = [
        f"{display_label(name)}: unknown parameter for this model."
        for name in parameters
        if name not in fields and name not in wiring
    ]
    for name, field in fields.items():
        if not complete and name not in parameters:
            continue
        value = parameters.get(name, field.get("default"))
        label = str(field.get("label") or display_label(name))
        if (
            complete
            and _required(field)
            and (_empty(value) or isinstance(value, str) and not value.strip())
        ):
            errors.append(f"{label} is required.")
            continue
        if name not in parameters and "default" not in field or _optional_omitted(field, value):
            continue
        errors.extend(_validate_value(field, value, label, complete=complete))
    if complete:
        values = schema_defaults(schema)
        values.update(parameters)
        errors.extend(validate_requirements(parsed.specs, values, parsed.one_of))
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


def _model_identity(value):
    if (
        not isinstance(value, str)
        or not value
        or len(value) > 256
        or value in {".", ".."}
        or any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in value)
        or any(char in value for char in "/\\?#%")
    ):
        raise ValueError("Model routing requires a nonempty opaque model ID")
    return value


def _route(model_id, schema):
    """Check supplied routing metadata; never infer a base model or coerce IDs."""
    _model_identity(model_id)
    if not isinstance(schema, dict):
        raise ValueError("A model schema is required")
    routing = schema.get("run_with", {})
    if not isinstance(routing, dict):
        raise ValueError("Model routing must be an object")
    arguments = routing.get("required_arguments", {})
    if not isinstance(arguments, dict) or not isinstance(arguments.get("parameters", {}), dict):
        raise ValueError("Model routing arguments and parameters must be objects")
    if schema.get("runs_as") in ("lora", "composition") and "model_id" not in arguments:
        raise ValueError("This model is missing its base-model routing. Refresh its schema.")
    return _model_identity(arguments.get("model_id", model_id)), arguments


def _finite_number(value):
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def _label(field):
    return str(field.get("label") or display_label(field["name"]))


def chosen_inputs(schema: dict[str, Any], parameters: dict[str, Any]) -> set[str]:
    """Names the caller set to a value other than empty or the schema's own default.

    A form may echo declared defaults back as parameters; those values remain
    the service's own choice, like the defaults form preparation adds.
    """
    fields = {field["name"]: field for field in _fields(schema)}
    return {
        name
        for name, value in parameters.items()
        if not _empty(value)
        and not (name in fields and "default" in fields[name] and value == fields[name]["default"])
    }


def _component_in_use(schema, parameters):
    """Whether the caller chose any input a malformed LoRA component could name."""
    chosen = chosen_inputs(schema, parameters)
    return any(
        field["name"] in chosen and field.get("type") in {"model", "model_array", "number_array"}
        for field in _fields(schema)
    )


def _align_lora_scales(component, fields, selected, values):
    """Apply the strength policy to a LoRA selection named by `selected` inputs.

    `selected` holds the caller's chosen parameters plus any mandatory wiring.
    A selection supplied only by schema defaults, added here or echoed by a
    form, is the service's own and is left unchanged. No strength is invented:
    a LoRA without a strength takes the scale input's declared default, or the
    request is refused.
    """
    if not any(name in selected for name in component.names):
        return
    model, scale = fields[component.model_input], fields[component.scale_input]
    loras = values.get(component.model_input, [])
    if component.model_id_input and not _empty(values.get(component.model_id_input)) and loras:
        raise RouteError(
            f"Use {_label(fields[component.model_id_input])} on its own, or remove it to stack "
            f"{_label(model)} with strengths."
        )
    if not isinstance(loras, list) or any(not isinstance(item, str) for item in loras):
        return  # Final validation reports the malformed value.
    scales = selected.get(component.scale_input)
    if not loras:
        if isinstance(scales, list) and scales:
            raise RouteError(
                f"{_label(scale)}: choose a LoRA in {_label(model)} for each strength."
            )
        return
    chosen = selected.get(component.model_input)
    # Merging mandatory wiring drops repeats, so check the caller's own list too.
    repeated = (
        isinstance(chosen, list)
        and all(isinstance(item, str) for item in chosen)
        and len(set(chosen)) != len(chosen)
    )
    if repeated or len(set(loras)) != len(loras):
        raise RouteError(f"{_label(model)}: choose each LoRA once.")
    default = scale.get("default")
    per_item = default if _finite_number(default) else None
    missing = RouteError(f"{_label(scale)}: provide a strength for each LoRA in {_label(model)}.")
    if scales is None:
        if isinstance(default, list) and len(default) == len(loras):
            # An empty caller value may have replaced the copied default.
            values[component.scale_input] = deepcopy(default)
            return
        if per_item is None:
            raise missing
        values[component.scale_input] = [per_item] * len(loras)
        return
    if not isinstance(scales, list):
        return  # Final validation reports the malformed value.
    mismatch = RouteError(
        f"{_label(scale)}: provide one strength for each LoRA in {_label(model)}."
    )
    if isinstance(chosen, list) and chosen and chosen != loras:
        # Mandatory wiring added LoRAs: align the caller's strengths by LoRA.
        if len(scales) != len(chosen):
            raise mismatch
        by_id = dict(zip(chosen, scales, strict=True))
        if any(item not in by_id for item in loras) and per_item is None:
            raise missing
        values[component.scale_input] = [by_id.get(item, per_item) for item in loras]
    elif len(scales) != len(loras):
        raise mismatch


def prepare_run(
    model_id: str, schema: dict[str, Any], parameters: dict[str, Any]
) -> tuple[str, dict[str, Any]]:
    """Validate form values and preserve mandatory LoRA/composition call wiring.

    LoRA inputs are the ones the schema's `uiConfig.lorasComponent` names. A
    LoRA selection needs one strength per LoRA, or the scale input's declared
    default, and cannot be combined with a model in `modelIdInput`. A malformed
    component refuses only a request that sets a model or number-array input.
    """
    target, arguments = _route(model_id, schema)
    # Check explicit user values before merging so invalid arrays cannot be
    # silently replaced. Defaults and mandatory wiring may supply missing fields;
    # validate all required relationships only on the final payload below.
    errors = _parameter_errors(schema, parameters, complete=False)
    if errors:
        raise ValueError("\n".join(errors))
    try:
        component = lora_component(schema)
    except RouteError:
        if _component_in_use(schema, parameters):
            raise
        component = None
    fields = {field["name"]: field for field in _form_fields(schema)[0]}
    values = schema_defaults(schema)
    values.update(deepcopy(parameters))
    for name, field in fields.items():
        if name in values and _optional_omitted(field, values[name]):
            values.pop(name)
    required = arguments.get("parameters", {})
    if isinstance(required, dict):
        values = _merge_wiring(values, required)
    if component is not None:
        # Mandatory wiring selects too; the caller's own values take precedence so
        # the caller's strengths stay aligned with the caller's LoRAs.
        chosen = chosen_inputs(schema, parameters)
        selected = dict(required) if isinstance(required, dict) else {}
        selected.update((name, value) for name, value in parameters.items() if name in chosen)
        _align_lora_scales(component, fields, selected, values)
    errors = validate_parameters(schema, values)
    if errors:
        raise ValueError("\n".join(errors))
    return target, values
