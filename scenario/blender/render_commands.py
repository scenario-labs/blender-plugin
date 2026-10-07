# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Main-thread render form commands shared with native preparation and pricing."""

import hashlib
import json
import math
from dataclasses import replace

from ..core.api.catalog import RENDER_LANES
from ..core.api.errors import ScenarioError
from ..core.schema.params import validate
from . import generation, params_ui, props, reference_form, render_lanes, render_references, runtime

_FIELDS = {
    "look": ("prompt", str),
    "capture_source": ("capture_source", str),
    "force_solid": ("force_solid", bool),
    "spark_enabled": ("spark_enabled", bool),
    "first_frame_path": ("first_frame_path", str),
    "use_first_frame": ("use_first_frame", bool),
    "match_timeline": ("match_timeline", bool),
}


def lane_state(scene, lane):
    if lane not in RENDER_LANES:
        raise ValueError("Choose render_image or render_video")
    return scene.scenario.lane_state(lane)


def request(scene, lane, model_id, parameters=None):
    """Use the same prepared form and final body as the native Generate action."""
    state = lane_state(scene, lane)
    if parameters is not None and parameters != {}:
        raise ScenarioError(0, "Configure render_form first; render quotes use its prepared inputs")
    if state.model_id != model_id:
        raise ValueError("The render model changed; configure render_form and estimate again")
    result = generation.build_request(scene, lane, for_estimate=True)
    if result.errors:
        raise ScenarioError(0, "; ".join(result.errors))
    if result.files or result.captures or result.spark:
        raise ScenarioError(0, "Finish render uploads and separate Prompt Spark approval first")
    return result


def _reference_key(scene, lane, ref):
    value = (
        scene.as_pointer(),
        lane,
        lane_state(scene, lane).model_id,
        ref.as_pointer(),
        reference_form.reference_values(ref),
        ref.get(render_references.ROLE, ""),
        ref.get(reference_form._MARKER, ""),
    )
    return hashlib.sha256(json.dumps(value).encode()).hexdigest()


def inspect(scene, lane):
    state = lane_state(scene, lane)
    schema = generation.schema_for(state.model_id)
    styles = render_lanes.style_input(lane, schema) if schema else None
    values, enabled = params_ui.collect_values(state, schema) if schema else ({}, {})
    hidden = render_lanes.hidden_param_names(schema) if schema and lane == "render_image" else ()
    references = []
    for ref in state.references:
        references.append(
            {
                "reference_key": _reference_key(scene, lane, ref),
                "role": ref.get(render_references.ROLE)
                or ("style" if styles and ref.param_name == styles.name else "input"),
                "parameter": ref.param_name,
                "source": ref.source,
                "asset_id": ref.asset_id if ref.source == "ASSET" else "",
                "upload_id": ref.get(reference_form._REQUEST, ""),
                "upload_marked": bool(ref.get(reference_form._MARKER)),
            }
        )
    result = generation.build_request(scene, lane, for_estimate=True)
    return {
        "lane": lane,
        "context_id": runtime.state.job_context_id,
        "model_id": state.model_id,
        **{name: getattr(state, prop) for name, (prop, _) in _FIELDS.items()},
        "parameters": {
            key: value for key, value in values.items() if enabled.get(key) and key not in hidden
        },
        "references": references,
        "errors": result.errors,
        "ready_to_estimate": not (result.errors or result.files or result.captures or result.spark),
        "spark_required": bool(result.spark),
    }


def _parameter(spec, value):
    if spec is None or spec.is_file or spec.is_prompt:
        raise ValueError("Use look or style_assets for prompt and reference inputs")
    if value is None:
        if spec.required_always or spec.ptype == "boolean":
            raise ValueError(f"{spec.name} cannot be disabled")
        return "enabled", False
    if spec.ptype == "number":
        # Blender stores numeric enum identifiers as strings. Accept only an
        # exact declared option, then validate its numeric value as usual.
        if isinstance(value, str) and spec.allowed_values:
            value = next(
                (
                    option
                    for option in spec.allowed_values
                    if type(option) in (int, float) and str(option) == value
                ),
                value,
            )
        valid = type(value) in (int, float) and math.isfinite(value)
        valid = valid and (not spec.is_integer or float(value).is_integer())
        valid = valid and (not spec.is_integer or -(2**31) <= value < 2**31)
        prop = "int_value" if spec.is_integer else "float_value"
    elif spec.ptype == "boolean":
        valid, prop = type(value) is bool, "bool_value"
    elif spec.ptype == "string_array":
        valid = isinstance(value, list) and all(
            isinstance(item, str)
            and item
            and "," not in item
            and (not spec.allowed_values or item in spec.allowed_values)
            for item in value
        )
        prop = "multi_value"
    else:
        valid, prop = spec.ptype == "string" and isinstance(value, str), "str_value"
    if not valid:
        raise ValueError(f"Invalid value for {spec.name}")
    isolated = replace(spec, required_if_defined=(), required_if_not_defined=())
    errors = validate([isolated], {spec.name: value})
    if errors:
        raise ValueError("; ".join(errors))
    if spec.allowed_values and spec.ptype != "string_array":
        if str(value) not in {str(item) for item in spec.allowed_values if str(item)}:
            raise ValueError(f"Invalid option for {spec.name}")
        return "enum_value", str(value)
    if prop == "int_value":
        value = int(value)
    return prop, ",".join(value) if prop == "multi_value" else value


def configure(scene, lane, changes):
    """Preflight edits before touching the current form; never upload or spend."""
    state = lane_state(scene, lane)
    if not isinstance(changes, dict) or set(changes) - {
        *_FIELDS,
        "model_id",
        "parameters",
        "style_assets",
    }:
        raise ValueError("Unknown render setting")
    model_id = changes.get("model_id", state.model_id)
    if not isinstance(model_id, str) or not model_id:
        raise ValueError("Choose a render model")
    generation.ensure_record(model_id)
    schema = generation.schema_for(model_id)
    choices = runtime.enum_items(("models", lane))
    if model_id not in {item[0] for item in choices} or schema is None:
        raise ValueError("Choose a model from list_models for this render lane")
    if state.model_id != model_id and state.references:
        raise ValueError("Remove the old render references explicitly before changing models")
    for name, (_, kind) in _FIELDS.items():
        if name in changes and type(changes[name]) is not kind:
            raise ValueError(f"Invalid {name}")
    if changes.get("capture_source", state.capture_source) not in {"CAMERA", "VIEWPORT"}:
        raise ValueError("capture_source must be CAMERA or VIEWPORT")
    parameters = changes.get("parameters", {})
    if not isinstance(parameters, dict):
        raise ValueError("parameters must be an object")
    if lane == "render_image" and set(parameters) & render_lanes.hidden_param_names(schema):
        raise ValueError("These parameters are not used by Render Image")
    edits = {name: _parameter(schema.by_name(name), value) for name, value in parameters.items()}
    styles = changes.get("style_assets")
    style_spec = None
    old_style_indices = []
    if "style_assets" in changes:
        if (
            not isinstance(styles, list)
            or len(styles) > 15
            or any(not isinstance(item, str) or not item.strip() for item in styles)
        ):
            raise ValueError("style_assets must contain at most 15 nonempty asset ids")
        scene_spec = render_lanes.scene_spec(lane, schema)
        style_spec = render_lanes.style_input(lane, schema)
        if styles and style_spec is None:
            raise ValueError("This model has no style input")
        if style_spec:
            old_style_indices = [
                index
                for index, ref in enumerate(state.references)
                if ref.param_name == style_spec.name and not ref.get(render_references.ROLE)
            ]
            if any(
                state.references[index].get(reference_form._MARKER) for index in old_style_indices
            ):
                raise ValueError("Remove marked style references explicitly before replacing them")
            occupied = sum(
                ref.param_name == style_spec.name and bool(ref.get(render_references.ROLE))
                for ref in state.references
            )
            # Reserve the scene slot even when it has not been uploaded yet.
            if style_spec is scene_spec and not render_references.slot(
                state, render_references.SCENE
            ):
                occupied += 1
            limit = 1 if style_spec.ptype == "file" else style_spec.max_length
            if limit and occupied + len(styles) > limit:
                raise ValueError("Not enough space for these styles and the render snapshot")
    if state.model_id != model_id:
        state.model_id = model_id
    params_ui.sync_params(state, schema, model_id)
    for name, (prop, _) in _FIELDS.items():
        if name in changes:
            setattr(state, prop, changes[name])
    for name, (prop, value) in edits.items():
        item = state.params[name]
        setattr(item, prop, value)
        if prop != "enabled":
            item.enabled = True
    if styles is not None:
        for index in reversed(old_style_indices):
            state.references.remove(index)
        for asset in styles:
            ref = state.references.add()
            ref.param_name, ref.source, ref.asset_id = style_spec.name, "ASSET", asset
    props.mark_estimate_dirty(state)
    return inspect(scene, lane)


def remove(scene, lane, key):
    state = lane_state(scene, lane)
    for index, ref in enumerate(state.references):
        if isinstance(key, str) and _reference_key(scene, lane, ref) == key:
            state.references.remove(index)
            props.mark_estimate_dirty(state)
            return inspect(scene, lane)
    raise ValueError("The reference changed; inspect render_form before removing it")


def execute(context, args):
    runtime.sync_catalog_context()
    lane = args["lane"]
    lane_state(context.scene, lane)
    action = args.get("action", "inspect")
    if action == "configure":
        return configure(context.scene, lane, args.get("settings", {}))
    if action == "remove":
        return remove(context.scene, lane, args.get("reference_key"))
    if action == "prepare":
        role = args.get("role")
        if role not in {render_references.SCENE, render_references.FIRST_FRAME}:
            raise ValueError("Choose the scene or first_frame role")
        render_references.prepare(context, lane, role)
    elif action != "inspect":
        raise ValueError("Choose inspect, configure, prepare or remove")
    return inspect(context.scene, lane)
