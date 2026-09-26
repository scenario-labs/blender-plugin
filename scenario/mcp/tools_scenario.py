# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""MCP tools that talk to Scenario through the add-on: catalog, cost, generate, results into the scene."""

import json
import time

import bpy

from ..blender import generation, runtime
from ..core.api.catalog import GENERATION_LANES as LANES
from ..core.api.catalog import LANE_KIND as KIND
from ..core.api.errors import ScenarioError
from ..core.schema.params import build_body, validate
from .protocol import DeferredTool, ToolSpec


def _catalog_ready():
    generation.process_catalog_events()
    if not runtime.state.catalog_loaded:
        generation.request_catalog()
        raise RuntimeError("The model catalog is still loading; call again in a few seconds")


def list_models(args):
    _catalog_ready()
    lane = args.get("lane") or "image"
    if lane not in LANES:
        raise ValueError(f"lane must be one of {LANES}")
    query = (args.get("query") or "").lower()
    records = runtime.state.lane_models.get(lane, [])
    if lane == "3d":
        everything = list(runtime.state.records.values())
        records = generation.three_d_models("TEXT", everything) + generation.three_d_models(
            "IMAGE", everything
        )
    out, seen = [], set()
    for rec in records:
        if rec.id in seen:
            continue
        seen.add(rec.id)
        if query and query not in (rec.name + " " + rec.short_description + " " + rec.id).lower():
            continue
        out.append(
            {
                "id": rec.id,
                "name": rec.name,
                "description": rec.short_description,
                "capabilities": list(rec.capabilities),
            }
        )
    return {"lane": lane, "models": out[:40]}


def model_schema(args):
    record = generation.ensure_record(args["model_id"])
    schema = generation.schema_for(record.id)
    params = []
    for spec in schema.specs:
        item = {
            "name": spec.name,
            "type": spec.ptype,
            "label": spec.label,
            "required": spec.required_always,
            "cost_impact": spec.cost_impact,
        }
        if spec.default is not None:
            item["default"] = spec.default
        if spec.allowed_values:
            item["allowed_values"] = list(spec.allowed_values)
        if spec.min is not None or spec.max is not None:
            item["range"] = [spec.min, spec.max]
        if spec.is_file:
            item["file_kind"] = spec.kind or "image"
            item["note"] = (
                "pass a Scenario asset id (capture_reference creates one from the viewport)"
            )
        if spec.description:
            item["description"] = spec.description
        params.append(item)
    return {
        "model_id": record.id,
        "name": record.name,
        "prompt_parameter": schema.prompt_name,
        "parameters": params,
    }


def _body_for(model_id, parameters):
    record = generation.ensure_record(model_id)
    schema = generation.schema_for(record.id)
    parameters = dict(parameters or {})
    files = {}
    for spec in schema.specs:
        if spec.is_file and spec.name in parameters:
            value = parameters.pop(spec.name)
            files[spec.name] = list(value) if isinstance(value, list) else [value]
    body = build_body(schema.specs, parameters, files)
    errors = validate(schema.specs, body, schema.one_of)
    if errors:
        raise ValueError("; ".join(errors))
    return record, body


def estimate_cost(args):
    record, body = _body_for(args["model_id"], args.get("parameters"))
    catalog = runtime.ensure_catalog()

    def finish(quote):
        runtime.sync_catalog_context()
        if catalog is not runtime.state.catalog:
            raise ScenarioError(0, "The selected catalog connection changed")
        return {
            "model_id": record.id,
            "cu_cost": float(quote.cost),
            "cu_cost_exact": str(quote.cost),
            "details": json.loads(quote.response_json).get("costDetails") or {},
        }

    return DeferredTool(lambda: catalog.estimate(record.id, body), finish)


def generate(args):
    import os

    if os.environ.get("SCENARIO_GUI_PROBE") == "1":
        raise PermissionError("Generation is disabled while an automated GUI probe runs")
    lane = args.get("lane") or "image"
    if lane not in LANES:
        raise ValueError(f"lane must be one of {LANES}")
    record, body = _body_for(args["model_id"], args.get("parameters"))
    manager = runtime.ensure_manager()
    meta = {
        "prompt": str(body.get("prompt") or ""),
        "model_name": record.name,
        "source": "mcp",
        "target_objects": [o.name for o in bpy.context.selected_objects if o.type == "MESH"],
    }
    rec = manager.submit(lane, KIND[lane], record.id, body, meta=meta)
    runtime.state.jobs_view.insert(0, rec)
    return {
        "local_id": rec.local_id,
        "status": rec.status,
        "lane": lane,
        "model_id": record.id,
        "note": "Poll job_status or wait_for_job; on success the result lands in the scene automatically (image datablock, material on the selection, 3D at the cursor, video file).",
    }


def _job_ref(args):
    """Prefer the platform spelling while retaining the original local alias."""
    ref = args.get("job_id") or args.get("id")
    if not isinstance(ref, str) or not ref.strip():
        raise ValueError(
            "Provide job_id (or id): the local_id returned by generate or a Scenario job id"
        )
    return ref


def _find(local_or_job_id):
    manager = runtime.ensure_manager()
    for rec in manager.registry.all():
        if rec.local_id == local_or_job_id or rec.job_id == local_or_job_id:
            return rec
    raise ValueError(f"Unknown job {local_or_job_id}")


def _status(rec):
    return {
        "local_id": rec.local_id,
        "job_id": rec.job_id,
        "status": rec.status,
        "progress": rec.progress,
        "cu_cost": rec.cu_cost,
        "files": list(rec.files),
        "error": rec.error,
        "kind": rec.kind,
    }


def job_status(args):
    return _status(_find(_job_ref(args)))


def wait_for_job(args):
    ref = _job_ref(args)
    deadline = time.time() + float(args.get("timeout", 170))
    while time.time() < deadline:
        rec = _find(ref)
        if rec.is_terminal:
            return _status(rec)
        time.sleep(1.5)
    return dict(_status(_find(ref)), note="still running, call again")


def import_result(args):
    from ..blender import handlers

    rec = _find(_job_ref(args))
    if not rec.files:
        raise ValueError("This job has no downloaded files yet")
    rec.meta["target_objects"] = [o.name for o in bpy.context.selected_objects if o.type == "MESH"]
    handlers.dispatch(("job_done", rec))
    return {"applied": rec.kind, "files": list(rec.files)}


def capture_reference(args):
    from ..blender import capture
    from ..core.api import assets

    source = args.get("source") or "VIEWPORT"
    path = capture.new_capture_path("mcp_ref", "png")
    capture.capture_still(bpy.context, path, source=source, width=1280, height=720)
    asset_id = assets.upload_file(runtime.make_client(), path, kind="image")
    return {"asset_id": asset_id, "path": path}


def list_generations(args):
    from ..blender import history

    refresh = args.get("refresh", False)
    if not isinstance(refresh, bool):
        raise ValueError("refresh must be a boolean")
    generation.process_catalog_events()
    if refresh:
        history.refresh()
        return {"generations": [], "note": "history requested, call again without refresh"}
    if runtime.state.history_error:
        raise RuntimeError(f"{runtime.state.history_error}; retry with refresh=true")
    if not runtime.state.history_loaded:
        if not runtime.state.history_loading:
            history.refresh()
        return {"generations": [], "note": "history requested, call again in a few seconds"}
    limit = int(args.get("limit", 20))
    result = {
        "generations": [
            {
                "job_id": e.job_id,
                "kind": e.kind,
                "model_id": e.model_id,
                "prompt": e.prompt,
                "status": e.status,
                "cu_cost": e.cu_cost,
                "local_files": e.local_files,
            }
            for e in runtime.state.history[:limit]
        ]
    }
    if runtime.state.history_loading:
        result["note"] = "showing loaded history while refresh is pending; call again"
    return result


def _schema(props, required=()):
    return {"type": "object", "properties": props, "required": list(required)}


_JOB_REF = {
    "job_id": {
        "type": "string",
        "description": "Scenario job id (job_...) or the local_id returned by generate",
    },
    "id": {"type": "string", "description": "Same as job_id, kept for compatibility"},
}


SPECS = (
    ToolSpec(
        "list_models",
        (
            "List the loaded lane catalog, with curated models first and at most 40 matches.\n"
            "Args:\n"
            "  - lane: optional string, default image; image, video, 3d, material, audio, render_image, render_video or edit3d.\n"
            "  - query: optional string, substring of the model name, description or id.\n"
            "Returns: lane, models[] with id, name, description and capabilities. Retry after catalog loading completes.\n"
            'Example: {"lane": "material", "query": "patina"}.\n'
            "Prefer model_schema before choosing generation parameters; this is not the full platform catalog.\n"
            "Platform equivalent: models_list, recommend."
        ),
        _schema({"lane": {"type": "string", "enum": list(LANES)}, "query": {"type": "string"}}),
        list_models,
        {"readOnlyHint": True},
    ),
    ToolSpec(
        "model_schema",
        (
            "Read the model's current form parameters for this Blender extension.\n"
            "Args:\n"
            "  - model_id: required string, the exact model identifier from list_models.\n"
            "Returns: model_id, name, prompt_parameter, parameters[] with name, type, label, required, default, allowed_values, range, cost_impact and file_kind when present. File parameters take Scenario asset ids.\n"
            'Example: {"model_id": "model_example"}.\n'
            "Prefer this before estimate_cost; do not guess parameter names or supported inputs.\n"
            "Platform equivalent: model_schema_get."
        ),
        _schema({"model_id": {"type": "string"}}, ["model_id"]),
        model_schema,
        {"readOnlyHint": True},
    ),
    ToolSpec(
        "estimate_cost",
        (
            "Get the exact CU cost with a dry run that spends no credits.\n"
            "Args:\n"
            "  - model_id: required string, the model identifier.\n"
            "  - parameters: optional object, model parameters including Scenario asset ids for file inputs.\n"
            "Returns: model_id, cu_cost, cu_cost_exact (decimal string) and details from the server estimate.\n"
            'Example: {"model_id": "model_example", "parameters": {"prompt": "a wooden crate"}}.\n'
            "Call before generate and show the cost to the user; an estimate does not authorize spending.\n"
            "Platform equivalent: model_run with dry_run."
        ),
        _schema({"model_id": {"type": "string"}, "parameters": {"type": "object"}}, ["model_id"]),
        estimate_cost,
        {"readOnlyHint": True},
    ),  # touches bpy (prefs, catalog): must run on the main thread
    ToolSpec(
        "generate",
        (
            "Submit a generation that spends the user's credits and automatically places its result in Blender.\n"
            "Args:\n"
            "  - lane: required string; image, video, 3d, material, audio, render_image, render_video or edit3d.\n"
            "  - model_id: required string, the exact model to run.\n"
            "  - parameters: optional object, model parameters; file inputs take Scenario asset ids.\n"
            "Returns: local_id, status, lane, model_id and note. Poll job_status for the Scenario job_id after acceptance. Results become image datablocks, materials on the captured meshes, 3D objects at the cursor, or video/audio files.\n"
            'Example: {"lane": "image", "model_id": "model_example", "parameters": {"prompt": "a wooden crate"}}.\n'
            "Do not call before estimate_cost and explicit spending approval. Do not repeat a timed-out submission. import_result is only for an intentional additional application.\n"
            "Platform equivalent: model_run."
        ),
        _schema(
            {
                "lane": {"type": "string", "enum": list(LANES)},
                "model_id": {"type": "string"},
                "parameters": {
                    "type": "object",
                    "description": "Model parameters; file parameters take Scenario asset ids",
                },
            },
            ["lane", "model_id"],
        ),
        generate,
    ),
    ToolSpec(
        "job_status",
        (
            "Read one local generation's status, cost and downloaded files without spending credits.\n"
            "Args:\n"
            "  - job_id: optional string, a Scenario job id or the local_id returned by generate.\n"
            "  - id: optional string, compatibility alias; provide job_id or id. job_id takes precedence if both are supplied.\n"
            "Returns: local_id, job_id, status, progress, cu_cost, files, error and kind. Unknown jobs raise ValueError.\n"
            'Example: {"job_id": "job_example"}.\n'
            "Prefer this for one status check; it only knows jobs tracked by this Blender runtime.\n"
            "Platform equivalent: job_get."
        ),
        _schema({**_JOB_REF}),
        job_status,
        {"readOnlyHint": True},
    ),
    ToolSpec(
        "wait_for_job",
        (
            "Wait for one tracked generation using a client-side status loop in Blender.\n"
            "Args:\n"
            "  - job_id: optional string, a Scenario job id or local_id returned by generate.\n"
            "  - id: optional string, compatibility alias; provide job_id or id. job_id takes precedence.\n"
            "  - timeout: optional number of seconds, default 170.\n"
            "Returns: local_id, job_id, status, progress, cu_cost, files, error and kind; on timeout, also note: still running, call again.\n"
            'Example: {"job_id": "job_example", "timeout": 30}.\n'
            "Prefer job_status for a quick check. This blocks Blender's main thread while waiting; it does not wait for multiple jobs or retry generation.\n"
            "Platform equivalent: jobs_wait."
        ),
        _schema({**_JOB_REF, "timeout": {"type": "number"}}),
        wait_for_job,
        {"readOnlyHint": True},
    ),  # touches bpy (paths, manager): main thread
    ToolSpec(
        "import_result",
        (
            "Apply an already downloaded generation again to the current Blender scene and selection.\n"
            "Args:\n"
            "  - job_id: optional string, a Scenario job id or local_id returned by generate.\n"
            "  - id: optional string, compatibility alias; provide job_id or id. job_id takes precedence.\n"
            "Returns: applied (result kind), files. Raises ValueError if no downloaded files exist.\n"
            'Example: {"job_id": "job_example"}.\n'
            "Do not use for the initial automatic application. Use only when the user wants another copy or to apply a material to the current mesh selection.\n"
            "No platform equivalent."
        ),
        _schema({**_JOB_REF}),
        import_result,
    ),
    ToolSpec(
        "capture_reference",
        (
            "Capture a 1280x720 viewport or camera still and upload it as a Scenario reference asset.\n"
            "Args:\n"
            "  - source: optional string, VIEWPORT (default) or CAMERA.\n"
            "Returns: asset_id for a model file parameter, and the local capture path.\n"
            'Example: {"source": "CAMERA"}.\n'
            "Do not use in background mode: capture needs the Blender GUI and a 3D viewport. This sends the captured scene image to Scenario; use it only for an authorized reference upload.\n"
            "Platform equivalent: upload_asset then upload_asset_complete."
        ),
        _schema({"source": {"type": "string", "enum": ["VIEWPORT", "CAMERA"]}}),
        capture_reference,
    ),
    ToolSpec(
        "list_generations",
        (
            "List recent cloud generations using this Blender runtime's loaded history.\n"
            "Args:\n"
            "  - limit: optional integer, default 20, maximum number of rows to return.\n"
            "  - refresh: optional boolean, request a new cloud page or retry a failed read; then poll without refresh.\n"
            "Returns: generations[] with job_id, kind, model_id, prompt, status, cu_cost and local_files. The first call may return an empty list and a note while history loads; call again after loading.\n"
            'Example: {"limit": 10}.\n'
            "Prefer job_status for a tracked active generation; this is not a fresh platform-wide history query on every call.\n"
            "Platform equivalent: jobs_list."
        ),
        _schema({"limit": {"type": "integer"}, "refresh": {"type": "boolean"}}),
        list_generations,
        {"readOnlyHint": True},
    ),
)
