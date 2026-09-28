# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""MCP tools that talk to Scenario through the add-on: catalog, cost, generate, results into the scene."""

import json
import time

import bpy

from ..blender import generation, runtime
from ..core.api.catalog import GENERATION_LANES as LANES
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
    lane = args.get("lane") or "image"
    if lane not in LANES:
        raise ValueError(f"lane must be one of {LANES}")
    jobs = runtime.ensure_model_jobs()
    ticket = jobs.quote(bpy.context.scene, record.id, body, lane=lane)

    def finish_model(_):
        if runtime.ensure_model_jobs() is not jobs:
            raise ScenarioError(0, "The estimate context changed; estimate again")
        quote = jobs.finish_quote(ticket)
        return {
            "model_id": record.id,
            "lane": lane,
            "quote_id": ticket.identifier,
            "cu_cost": float(quote.cost),
            "cu_cost_exact": str(quote.cost),
            "details": json.loads(quote.response_json).get("costDetails") or {},
        }

    return DeferredTool(ticket.task.result, finish_model)


def estimate_prompt(args):
    """Quote the current native prompt field through the shared prompt facade."""
    jobs = runtime.ensure_prompt_jobs()
    item = jobs.quote(bpy.context.scene, args.get("lane", "image"), args["action"])

    def finish(_):
        if runtime.ensure_prompt_jobs() is not jobs:
            raise ScenarioError(0, "The prompt context changed")
        jobs.poll()
        if item.phase != "READY":
            raise ScenarioError(0, item.error or "The prompt price is unavailable")
        return {
            "quote_id": item.identifier,
            "action": item.action,
            "lane": item.lane,
            "cu_cost_exact": item.cost,
        }

    return DeferredTool(item.task.result, finish)


def approve_prompt(args):
    jobs = runtime.ensure_prompt_jobs()
    item = jobs.approve(args["quote_id"], bpy.context.scene, approved_cost=args["approved_cost"])
    return {
        "request_id": item.request_id,
        "state": item.phase.lower(),
        "note": "One prompt submission queued; do not repeat it. The unchanged original field receives the result.",
    }


def read_prompt_result(args):
    session = runtime.ensure_job_session()
    if args.get("context_id") != runtime.state.job_context_id:
        raise ScenarioError(0, "The saved-job context changed; list local jobs again")
    task = session.read_prompt_results(
        args["request_id"], expected_revision=args["expected_revision"]
    )

    def finish(_):
        if runtime.ensure_job_session() is not session:
            raise ScenarioError(0, "The saved-job context changed")
        outcomes = session.drain(task=task)
        if not outcomes:
            raise ScenarioError(0, "The prompt result completion is unavailable")
        if outcomes[0].error is not None:
            raise outcomes[0].error
        result = outcomes[0].result
        # Read-only recovery can inspect an old origin. It never applies to the
        # current field or turns a restart into new spending authorization.
        return {"request_id": result.record.intent.request_id, "prompts": list(result.prompts)}

    return DeferredTool(task.result, finish)


def list_local_jobs(args):
    context_id, items = runtime.local_job_recovery()
    return {
        "context_id": context_id,
        "jobs": [
            {
                "request_id": item.record.intent.request_id,
                "revision": item.record.revision,
                "state": item.record.state.value,
                "action": item.action.value,
                "operation": item.record.intent.operation,
                "target_id": item.record.intent.target_id,
                "cu_cost_exact": item.record.intent.quote_cost,
                "remote_job_id": item.record.remote_job_id,
            }
            for item in items
        ],
    }


def cancel_prepared_job(args):
    context_id, request_id = args.get("context_id"), args.get("request_id")
    revision = args.get("expected_revision")
    if not isinstance(context_id, str) or not context_id or not isinstance(request_id, str):
        raise ValueError("Use the context_id and request_id returned by list_local_jobs")
    if type(revision) is not int or revision < 0:
        raise ValueError("expected_revision must be a nonnegative integer")
    record = runtime.cancel_prepared_job(context_id, request_id, revision)
    return {"request_id": request_id, "revision": record.revision, "state": record.state.value}


def generate(args):
    import os

    if os.environ.get("SCENARIO_GUI_PROBE") == "1":
        raise PermissionError("Generation is disabled while an automated GUI probe runs")
    lane = args.get("lane") or "image"
    if lane not in LANES:
        raise ValueError(f"lane must be one of {LANES}")
    runtime.ensure_model_jobs().require_quote(args.get("quote_id"))
    record, body = _body_for(args["model_id"], args.get("parameters"))
    meta = {
        "prompt": str(body.get("prompt") or ""),
        "model_name": record.name,
        "source": "mcp",
        "target_objects": [o.name for o in bpy.context.selected_objects if o.type == "MESH"],
    }
    jobs = runtime.ensure_model_jobs()
    rec = jobs.submit(
        args.get("quote_id"),
        bpy.context.scene,
        record.id,
        body,
        lane=lane,
        approved_cost=args.get("approved_cost"),
        meta=meta,
    )
    runtime.state.jobs_view.insert(0, rec)
    return {
        "local_id": rec.local_id,
        "status": rec.status,
        "lane": lane,
        "model_id": record.id,
        "note": "Submission is saved. Poll job_status for remote progress and verified downloads. "
        + (
            "Image jobs import supported images only into their unchanged original scene. "
            if lane == "image"
            else "Results remain saved for explicit application; this lane does not import automatically. "
        )
        + "Paused or restarted jobs require explicit recovery; never repeat an uncertain request.",
    }


def _job_ref(args):
    """Prefer the platform spelling while retaining the original local alias."""
    ref = args.get("job_id") or args.get("id")
    if not isinstance(ref, str) or not ref.strip():
        raise ValueError(
            "Provide job_id (or id): the local_id returned by generate or a Scenario job id"
        )
    return ref


def _local_registry():
    manager = runtime.state.manager
    return (
        manager.registry
        if manager is not None
        else runtime.JobRegistry(runtime.paths().registry_file).load()
    )


def _find(local_or_job_id):
    for rec in _local_registry().all():
        if rec.local_id == local_or_job_id or rec.job_id == local_or_job_id:
            if runtime.state.manager is None and not rec.is_terminal:
                # Active prototype waits still need the manager-owned mutable record.
                return runtime.ensure_manager().registry.by_local_id(rec.local_id)
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


def _saved_status(reference):
    # Cold local imports must not require credentials or resume a job engine.
    if any(reference in (record.local_id, record.job_id) for record in _local_registry().all()):
        return None
    return runtime.ensure_model_jobs().status(reference)


def job_status(args):
    reference = _job_ref(args)
    saved = _saved_status(reference)
    return saved if saved is not None else _status(_find(reference))


def recover_local_job(args):
    jobs, task = runtime.control_model_job(
        args["context_id"], args["request_id"], args["expected_revision"], args["action"]
    )
    if task is None:
        return jobs.status(args["request_id"])
    return _finish_recovery(jobs, task, args["request_id"])


def prepare_result_application(args):
    purpose = args.get("purpose", "import")
    if purpose in {"world", "restore_world"}:
        _, approval = runtime.prepare_world_application(
            args["context_id"],
            args["request_id"],
            args["expected_revision"],
            bpy.context.scene,
            args.get("asset_id"),
            restore=purpose == "restore_world",
        )
        return {
            "context_id": args["context_id"],
            "application_id": approval.identifier,
            "request_id": approval.record.intent.request_id,
            "revision": approval.record.revision,
            "scene": approval.scene_name,
            "asset_id": approval.asset_id,
            "kind": "world",
            "purpose": purpose,
            "previous_world": approval.previous.name if approval.previous else None,
            "note": "Approve restoring this session's original World; changed owned World/image data prevents restoration."
            if approval.restore
            else "Approve replacing this scene's World with one packed equirectangular panorama. "
            "Only supported 2:1 PNG/EXR bytes qualify; PNG is LDR and EXR is not proof of actual HDR range. "
            "The original World stays untouched and this session can restore it while unchanged. Nothing has been applied.",
        }
    if purpose != "import":
        raise ValueError("Choose import, world or restore_world")
    if args.get("asset_id"):
        _, approval = runtime.prepare_asset_application(
            args["context_id"],
            args["request_id"],
            args["expected_revision"],
            bpy.context.scene,
            args["asset_id"],
        )
        if approval.kind == "model":
            return {
                "context_id": args["context_id"],
                "application_id": approval.identifier,
                "request_id": approval.record.intent.request_id,
                "revision": approval.record.revision,
                "scene": approval.scene_name,
                "asset_id": approval.asset_id,
                "kind": "model",
                "cursor": list(approval.cursor),
                "note": "Approve importing this one static embedded GLB into a new group with its bottom at the cursor. "
                "Existing objects and selection stay unchanged. Rigged/animated or externally referenced GLBs are unsupported. "
                "Nothing has been imported; changed destinations require review again.",
            }
        return {
            "context_id": args["context_id"],
            "application_id": approval.identifier,
            "request_id": approval.record.intent.request_id,
            "revision": approval.record.revision,
            "scene": approval.scene_name,
            "asset_id": approval.asset_id,
            "kind": approval.kind,
            "frame": approval.frame,
            "note": "Approve inserting this one media asset at this scene/frame on an unused channel. "
            "Scene timing stays unchanged; video insertion omits embedded audio. "
            "Media stays in a local file that must remain available. Nothing has been inserted.",
        }
    _, approval = runtime.prepare_image_application(
        args["context_id"], args["request_id"], args["expected_revision"], bpy.context.scene
    )
    return {
        "context_id": args["context_id"],
        "application_id": approval.identifier,
        "request_id": approval.record.intent.request_id,
        "revision": approval.record.revision,
        "scene": approval.scene_name,
        "images": [item.asset.name for item in approval.record.results],
        "note": "Ask the user to approve importing and packing these images into this file. "
        "The approval becomes invalid if the destination changes. No images have been imported.",
    }


def apply_result_application(args):
    jobs, request_id, task = runtime.apply_saved_result(args["context_id"], args["application_id"])
    return jobs.status(request_id) if task is None else _finish_recovery(jobs, task, request_id)


def _finish_recovery(jobs, task, request_id):

    def run():
        try:
            task.result()
        except Exception:
            pass  # The owned completion supplies sanitized state/error on the main thread.

    def finish(_):
        runtime.sync_catalog_context()
        if runtime.state.model_jobs is not jobs or not jobs.session.active:
            raise ScenarioError(0, "The job context changed during recovery; inspect it again")
        return jobs.status(request_id)

    return DeferredTool(run, finish)


def wait_for_job(args):
    ref = _job_ref(args)
    timeout = args.get("timeout", 170)
    if (
        isinstance(timeout, bool)
        or not isinstance(timeout, (int, float))
        or not 0 <= timeout <= 170
    ):
        raise ValueError("timeout must be a finite number from 0 to 170 seconds")
    saved = _saved_status(ref)
    if saved is not None:
        jobs = runtime.state.model_jobs
        server = runtime.state.mcp
        if timeout == 0 or saved["local_id"] not in jobs.views:
            return saved

        def finish_shared(_):
            runtime.sync_catalog_context()
            if (
                runtime.state.model_jobs is not jobs
                or not jobs.session.active
                or (server is not None and (runtime.state.mcp is not server or not server.running))
            ):
                raise ScenarioError(0, "The job context changed while waiting; inspect it again")
            return jobs.status(saved["local_id"])

        return DeferredTool(
            lambda: jobs.wait(
                saved["local_id"],
                timeout,
                stopped=lambda: server is not None and not server.running,
            ),
            finish_shared,
        )
    rec = _find(ref)
    if rec.is_terminal:
        return _status(rec)
    if timeout == 0:
        return dict(_status(rec), note="still running, call again")
    manager, state = runtime.state.manager, runtime.state
    credentials = runtime.credentials()
    server = state.mcp
    deadline = time.monotonic() + timeout

    def run():
        # Only captured Python objects are read here, never Blender state or bpy.
        while not rec.is_terminal:
            if manager._stop.is_set() or (server is not None and not server.running):
                raise RuntimeError("The job wait stopped; generation was not cancelled")
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            manager._stop.wait(min(0.1, remaining))

    def finish(_):
        if (
            runtime.state is not state
            or runtime.state.manager is not manager
            or runtime.credentials() != credentials
            or manager._stop.is_set()
            or (server is not None and (state.mcp is not server or not server.running))
            or manager.registry.by_local_id(rec.local_id) is not rec
        ):
            raise RuntimeError("The job context changed while waiting; query its status again")
        result = _status(rec)
        if not rec.is_terminal:
            result["note"] = "still running, call again"
        return result

    return DeferredTool(run, finish)


def import_result(args):
    from ..blender import handlers

    reference = _job_ref(args)
    if _saved_status(reference) is not None:
        raise ValueError(
            "Use prepare_result_application for saved PNG/EXR images; "
            "other saved result types do not yet support scene application"
        )
    rec = _find(reference)
    if not rec.files:
        raise ValueError("This job has no downloaded files yet")
    rec.meta["target_objects"] = [o.name for o in bpy.context.selected_objects if o.type == "MESH"]
    handlers.dispatch(("job_done", rec))
    return {"applied": rec.kind, "files": list(rec.files)}


def capture_reference(args):
    from ..blender.reference_uploads import capture_upload

    ticket = capture_upload(bpy.context, source=args.get("source") or "VIEWPORT")
    return _reference_response(ticket.identifier)


def upload_reference(args):
    path = args.get("path")
    if not isinstance(path, str) or not path:
        raise ValueError("Choose a local reference path to upload")
    owner = runtime.ensure_reference_uploads()
    ticket = owner.start(bpy.context.scene, bpy.path.abspath(path), kind=args.get("kind", "image"))
    return _reference_response(ticket.identifier)


def _reference_response(identifier):
    return {
        "context_id": runtime.state.job_context_id,
        **runtime.ensure_reference_uploads().status(identifier),
        "note": "Poll reference_upload_status; use its imported asset_id in estimate_cost. "
        "Do not restart an uncertain upload. Uploading does not generate or approve spending.",
    }


def _upload_context(args):
    owner = runtime.ensure_reference_uploads()
    if args.get("context_id") != runtime.state.job_context_id:
        raise ScenarioError(0, "The upload context changed; list saved uploads again")
    return owner


def reference_upload_status(args):
    owner = _upload_context(args)
    return {"context_id": runtime.state.job_context_id, **owner.status(args["reference_id"])}


def list_reference_uploads(args):
    owner = runtime.ensure_reference_uploads()
    return {
        "context_id": runtime.state.job_context_id,
        "uploads": [
            {
                "request_id": item.record.intent.request_id,
                "revision": item.record.revision,
                "state": item.record.state.value,
                "action": item.action.value,
                "asset_id": item.record.asset_id,
                "upload_id": item.record.upload_id,
                "kind": item.record.intent.kind,
                "content_type": item.record.intent.content_type,
            }
            for item in owner.session.upload_recovery_plan()
        ],
    }


def recover_reference_upload(args):
    owner = _upload_context(args)
    command = owner.recover(args["request_id"], args["expected_revision"], args.get("action"))

    def finish(_):
        runtime.sync_catalog_context()
        if runtime.state.reference_uploads is not owner or not owner.session.active:
            raise ScenarioError(0, "The upload context changed during recovery")
        record = owner.recovery_result(command)
        return {
            "request_id": record.intent.request_id,
            "state": record.state.value,
            "revision": record.revision,
            "asset_id": record.asset_id,
            "kind": record.intent.kind,
            "content_type": record.intent.content_type,
        }

    if command.task is None:
        return finish(None)

    def run():
        try:
            command.task.result()
        except Exception:
            # finish() checks the owned completion and reports recovery failure
            # on the main thread; this worker only waits for the task to finish.
            pass

    return DeferredTool(run, finish)


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
        "upload_reference",
        (
            "Upload an explicitly chosen image, audio, video or 3D file through the shared durable upload session.\n"
            "Args:\n  - path: required string, local file path selected by the user.\n"
            "  - kind: optional string, image (default), audio, video or 3d; must match the file extension.\n"
            "Returns: context_id, reference_id, staging/upload state, request_id when persisted, kind and content_type after staging, and note.\n"
            'Example: {"path": "/chosen/reference.png"}.\n'
            "This sends the selected file to Scenario without conversion or sidecar discovery. Call only for an authorized upload; it does not generate or approve spending. Poll reference_upload_status until imported, then quote with asset_id. Do not repeat an uncertain upload.\n"
            "Platform equivalent: upload_asset then upload_asset_complete."
        ),
        _schema(
            {
                "path": {"type": "string"},
                "kind": {
                    "type": "string",
                    "enum": ["image", "audio", "video", "3d"],
                    "default": "image",
                },
            },
            ["path"],
        ),
        upload_reference,
    ),
    ToolSpec(
        "reference_upload_status",
        (
            "Read a reference upload's progress while the shared session advances its already authorized work.\n"
            "Args:\n  - context_id: required string, context from upload_reference or capture_reference.\n"
            "  - reference_id: required string, the returned session-owned upload handle.\n"
            "Returns: reference_id, request_id, revision, state, asset_id, kind, content_type, error and pending. Kind and content_type are null until staging completes.\n"
            'Example: {"context_id": "from-upload", "reference_id": "from-upload"}.\n'
            "Use asset_id only after state imported. A changed context rejects old handles; use list_reference_uploads after restart. This does not create or replay uploads.\n"
            "Platform equivalent: upload status retrieval."
        ),
        _schema(
            {"context_id": {"type": "string"}, "reference_id": {"type": "string"}},
            ["context_id", "reference_id"],
        ),
        reference_upload_status,
        {"readOnlyHint": True},
    ),
    ToolSpec(
        "list_reference_uploads",
        (
            "Inspect saved uploads under the selected credential scope, including after restart.\n"
            "Args: none.\n"
            "Returns: context_id and uploads with request_id, revision, state, suggested action, upload_id, asset_id, kind and content_type.\n"
            "Example: {}.\n"
            "Inspection makes no network request, sends no bytes and never resumes uncertain initialization or parts. Use recover_reference_upload for explicit known-upload reads or local cleanup.\n"
            "Platform equivalent: none; this inspects local durable upload history."
        ),
        _schema({}),
        list_reference_uploads,
        {"readOnlyHint": True},
    ),
    ToolSpec(
        "recover_reference_upload",
        (
            "Explicitly inspect a known remote upload, cancel unclaimed preparation, or clean its finished private source copy.\n"
            "Args:\n  - context_id: required string, context from list_reference_uploads.\n"
            "  - request_id: required string, saved local upload identity.\n"
            "  - expected_revision: required nonnegative integer, observed saved revision.\n"
            "  - action: required string, refresh, cancel_prepared or cleanup.\n"
            "Returns: request_id, state, revision, asset_id, kind and content_type.\n"
            'Example: {"context_id": "from-list", "request_id": "from-list", "expected_revision": 2, "action": "refresh"}.\n'
            "Refresh sends only a status read. Cleanup accepts only finished records and never deletes the original user file. No action repeats initialization, PUT or finalization.\n"
            "Platform equivalent: upload retrieval or local source cleanup."
        ),
        _schema(
            {
                "context_id": {"type": "string"},
                "request_id": {"type": "string"},
                "expected_revision": {"type": "integer", "minimum": 0},
                "action": {"type": "string", "enum": ["refresh", "cancel_prepared", "cleanup"]},
            },
            ["context_id", "request_id", "expected_revision", "action"],
        ),
        recover_reference_upload,
        {"destructiveHint": True},
    ),
    ToolSpec(
        "prepare_result_application",
        (
            "Prepare explicit saved image/media/model import, panorama World replacement, or session-local World restoration.\n"
            "Args:\n"
            "  - context_id: required string, current context from list_local_jobs.\n"
            "  - request_id: required string, saved local job identity.\n"
            "  - expected_revision: required nonnegative integer, observed saved revision.\n"
            "  - purpose: import (default), world, or restore_world; World replacement requires asset_id.\n"
            "  - asset_id: optional saved asset ID; required for one MP4/WebM video, MP3/WAV/OGG audio strip or static embedded GLB model. Omit for PNG/EXR image import.\n"
            "Returns: context_id, application_id, request_id, revision, scene, images or asset_id/kind/frame or cursor, and note.\n"
            'Example: {"context_id": "from-list", "request_id": "from-list", "expected_revision": 8}.\n'
            "Show the destination, selected assets and media frame, model cursor or World operation before apply_result_application. This makes no network request, spends no credits and imports nothing. Imports and World replacement require ready or confirmed rolled-back results; restoration requires this session's completed World application.\n"
            "Platform equivalent: none; this captures a local Blender destination."
        ),
        _schema(
            {
                "context_id": {"type": "string"},
                "request_id": {"type": "string"},
                "expected_revision": {"type": "integer", "minimum": 0},
                "asset_id": {"type": "string"},
                "purpose": {"type": "string", "enum": ["import", "world", "restore_world"]},
            },
            ["context_id", "request_id", "expected_revision"],
        ),
        prepare_result_application,
        {"readOnlyHint": True},
    ),
    ToolSpec(
        "apply_result_application",
        (
            "Apply or restore saved results after the user approves the prepared destination and operation.\n"
            "Args:\n"
            "  - context_id: required string, context from prepare_result_application.\n"
            "  - application_id: required string, single-use approval handle from prepare_result_application.\n"
            "Returns: saved job status, revision, images, imported object names and any delivery error.\n"
            'Example: {"context_id": "from-prepare", "application_id": "from-prepare"}.\n'
            "Call only after explicit destination approval. Verification runs off the main thread; application rechecks the captured scene/file revision and media frame or model cursor. Media uses a persistent private file; video omits embedded audio and scene timing is unchanged. Changed contexts or records require fresh review. World replacement or restoration changes only the approved scene World with guarded owned-data cleanup. This performs no generation, downloads, existing-object/material replacement or file save. Never repeat an uncertain import; inspect the saved job.\n"
            "Platform equivalent: none; this applies saved results locally in Blender."
        ),
        _schema(
            {"context_id": {"type": "string"}, "application_id": {"type": "string"}},
            ["context_id", "application_id"],
        ),
        apply_result_application,
        {"destructiveHint": True},
    ),
    ToolSpec(
        "recover_local_job",
        (
            "Explicitly recover a saved job without repeating generation or importing into another scene.\n"
            "Args:\n"
            "  - context_id: required string from list_local_jobs.\n"
            "  - request_id: required local job identity.\n"
            "  - expected_revision: required observed integer revision.\n"
            "  - action: refresh, resume, cancel, recover_download or retry_receipt.\n"
            "Returns: saved status, revision, available actions and delivery error if any.\n"
            'Example: {"context_id":"from-list","request_id":"from-list","expected_revision":2,"action":"resume"}.\n'
            "Refresh reads once; resume polls and downloads without automatic import. Cancel requests known model-job cancellation and observes its actual outcome. recover_download verifies interrupted local receipts without network calls. retry_receipt saves an already completed import without repeating it and requires the same live owner. Stale contexts/revisions and uncertain submissions are rejected.\n"
            "Platform equivalent: jobs.retrieve, jobs.trigger_action and assets.retrieve through the shared SDK, plus local receipt recovery."
        ),
        _schema(
            {
                "context_id": {"type": "string"},
                "request_id": {"type": "string"},
                "expected_revision": {"type": "integer", "minimum": 0},
                "action": {
                    "type": "string",
                    "enum": ["refresh", "resume", "cancel", "recover_download", "retry_receipt"],
                },
            },
            ["context_id", "request_id", "expected_revision", "action"],
        ),
        recover_local_job,
        {"destructiveHint": True},
    ),
    ToolSpec(
        "list_local_jobs",
        (
            "Inspect durable local jobs for the selected API-key pair without network requests.\n"
            "Args: none.\n"
            "Returns: context_id and jobs[] with request_id, revision, state, action, operation, target_id, cu_cost_exact and remote_job_id.\n"
            "Example: {}.\n"
            "Saved costs are informational, not spending approval. Unknown submissions require reconciliation, never automatic retry.\n"
            "Prototype generate/job_status records are separate and are not imported here. No remote job polling or result application occurs.\n"
            "Platform equivalent: none; this is local recovery inspection."
        ),
        _schema({}),
        list_local_jobs,
        {"readOnlyHint": True},
    ),
    ToolSpec(
        "cancel_prepared_job",
        (
            "Cancel an unsubmitted durable local intent without contacting Scenario.\n"
            "Args:\n"
            "  - context_id: required string, current context returned by list_local_jobs.\n"
            "  - request_id: required string, local durable request identity.\n"
            "  - expected_revision: required nonnegative integer, observed record revision.\n"
            "Returns: request_id, revision and state (canceled).\n"
            'Example: {"context_id": "from-list", "request_id": "from-list", "expected_revision": 0}.\n'
            "Only prepared jobs can be canceled here. Claimed, uncertain, remote and changed-context jobs are rejected; this does not cancel a remote generation.\n"
            "Platform equivalent: none; this changes only local durable state."
        ),
        _schema(
            {
                "context_id": {"type": "string"},
                "request_id": {"type": "string"},
                "expected_revision": {"type": "integer", "minimum": 0},
            },
            ["context_id", "request_id", "expected_revision"],
        ),
        cancel_prepared_job,
        {"destructiveHint": True},
    ),
    ToolSpec(
        "estimate_prompt",
        'Get the exact server price for New, Rewrite or Translate on the current scene\'s native prompt field. This does not generate or change text. Args: lane and action (GENERATE, REWRITE, TRANSLATE). Returns: quote_id and cu_cost_exact. Obtain explicit approval of that exact cost before approve_prompt. The current field text/model must remain unchanged.\nExample: {"lane": "image", "action": "REWRITE"}.\nPlatform equivalent: prompt_spark for prompt generation; translation uses SDK generate.translate.',
        _schema(
            {
                "lane": {"type": "string", "enum": list(LANES)},
                "action": {"type": "string", "enum": ["GENERATE", "REWRITE", "TRANSLATE"]},
            },
            ["action"],
        ),
        estimate_prompt,
        {"readOnlyHint": True},
    ),
    ToolSpec(
        "approve_prompt",
        'Spend the explicitly approved exact price once for a quote from estimate_prompt. Args: quote_id and approved_cost (the unchanged decimal string). Returns: request_id and queued state. Queues one durable submission; never retry an uncertain outcome. The shared runtime updates only the unchanged original prompt field. Inspect list_local_jobs for recovery.\nExample: {"quote_id": "saved-quote", "approved_cost": "1.25"}.\nPlatform equivalent: prompt_spark after separate local approval.',
        _schema(
            {"quote_id": {"type": "string"}, "approved_cost": {"type": "string"}},
            ["quote_id", "approved_cost"],
        ),
        approve_prompt,
        {"destructiveHint": True},
    ),
    ToolSpec(
        "read_prompt_result",
        'Read full text from a saved successful prompt or translation job without generating, spending or applying it. Args: context_id, request_id and expected_revision from list_local_jobs; refresh a known remote job\'s status first if necessary. Returns: prompts; old scene origins are readable but are never silently applied to the current scene.\nExample: {"context_id": "current-context", "request_id": "saved-request", "expected_revision": 3}.\nPlatform equivalent: job_get and asset_get without generation.',
        _schema(
            {
                "context_id": {"type": "string"},
                "request_id": {"type": "string"},
                "expected_revision": {"type": "integer", "minimum": 0},
            },
            ["context_id", "request_id", "expected_revision"],
        ),
        read_prompt_result,
        {"readOnlyHint": True},
    ),
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
            "  - lane: optional generation lane, default image. Every lane issues a single-use quote_id.\n"
            "Returns: model_id, lane, cu_cost, cu_cost_exact (decimal string), details and quote_id bound to the lane, model, inputs, scene and credential context.\n"
            'Example: {"model_id": "model_example", "parameters": {"prompt": "a wooden crate"}}.\n'
            "Call before generate and show the cost to the user; an estimate does not authorize spending.\n"
            "Platform equivalent: model_run with dry_run."
        ),
        _schema(
            {
                "model_id": {"type": "string"},
                "parameters": {"type": "object"},
                "lane": {"type": "string", "enum": list(LANES)},
            },
            ["model_id"],
        ),
        estimate_cost,
        {"readOnlyHint": True},
    ),  # touches bpy (prefs, catalog): must run on the main thread
    ToolSpec(
        "generate",
        (
            "Submit a generation that spends the user's credits. Every model lane uses durable shared jobs.\n"
            "Args:\n"
            "  - lane: required string; image, video, 3d, material, audio, render_image, render_video or edit3d.\n"
            "  - model_id: required string, the exact model to run.\n"
            "  - parameters: optional object, model parameters; file inputs take Scenario asset ids.\n"
            "  - quote_id: required, from estimate_cost with the same lane, model, inputs and scene.\n"
            "  - approved_cost: required, the exact cu_cost_exact string explicitly approved by the user.\n"
            "Returns: local_id, status, lane, model_id and note. All model jobs poll and download through the shared session. Only the Image lane imports verified PNG/EXR images automatically into the unchanged origin. Other lanes stop at saved ready results; their scene application remains separate. Render lanes take explicit model inputs without UI capture or Prompt Spark preparation.\n"
            'Example: {"lane": "image", "model_id": "model_example", "parameters": {"prompt": "a wooden crate"}, "quote_id": "quote_from_estimate", "approved_cost": "1.25"}.\n'
            "Do not call before estimate_cost and explicit spending approval. Do not repeat a timed-out submission. Use prepare_result_application for saved PNG/EXR imports; import_result is for prototype records only.\n"
            "Platform equivalent: model_run."
        ),
        _schema(
            {
                "lane": {"type": "string", "enum": list(LANES)},
                "quote_id": {"type": "string"},
                "approved_cost": {"type": "string"},
                "model_id": {"type": "string"},
                "parameters": {
                    "type": "object",
                    "description": "Model parameters; file parameters take Scenario asset ids",
                },
            },
            ["lane", "model_id", "quote_id", "approved_cost"],
        ),
        generate,
    ),
    ToolSpec(
        "job_status",
        (
            "Read one local generation's status and cost without spending credits. Active model jobs advance through shared remote polling and verified downloads; restarted jobs remain inspection-only.\n"
            "Args:\n"
            "  - job_id: optional string, a Scenario job id or the local_id returned by generate.\n"
            "  - id: optional string, compatibility alias; provide job_id or id. job_id takes precedence if both are supplied.\n"
            "Returns: local_id, job_id, status, cu_cost, files, error and kind. Shared jobs also return revision, cu_cost_exact, results (asset_id, name, media_type, size, downloaded), actions and images. Recovered jobs report kind=model; result media types remain available. Unknown jobs raise ValueError.\n"
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
            "Wait for a generation while Blender remains responsive. Shared jobs return when delivery finishes, pauses for review, or the wait expires. Restarted jobs remain inspection-only until explicitly resumed.\n"
            "Args:\n"
            "  - job_id: optional string, a Scenario job id or local_id returned by generate.\n"
            "  - id: optional string, compatibility alias; provide job_id or id. job_id takes precedence.\n"
            "  - timeout: optional finite number of seconds from 0 to 170, default 170.\n"
            "Returns: local_id, job_id, status, progress, cu_cost, files, error and kind; on timeout, also note: still running, call again.\n"
            'Example: {"job_id": "job_example", "timeout": 30}.\n'
            "Prefer job_status for a quick check. Waiting runs off the main thread; it does not cancel, retry or submit generation. Context changes require a fresh status query.\n"
            "Platform equivalent: jobs_wait."
        ),
        _schema({**_JOB_REF, "timeout": {"type": "number", "minimum": 0, "maximum": 170}}),
        wait_for_job,
        {"readOnlyHint": True},
    ),  # touches bpy (paths, manager): main thread
    ToolSpec(
        "import_result",
        (
            "Apply a downloaded prototype generation again to the current Blender scene and selection.\n"
            "Args:\n"
            "  - job_id: optional string, a Scenario job id or local_id returned by generate.\n"
            "  - id: optional string, compatibility alias; provide job_id or id. job_id takes precedence.\n"
            "Returns: applied (result kind), files. Raises ValueError if no downloaded files exist.\n"
            'Example: {"job_id": "job_example"}.\n'
            "Do not use for the initial automatic application. Use only for prototype records when the user wants another copy or to apply a material to the current mesh selection. Shared jobs reject this tool; use prepare_result_application for saved PNG/EXR images or a selected MP4/WebM video or MP3/WAV/OGG sound asset. Static embedded GLB import uses the same asset approval. In-place editing and material application remain separate.\n"
            "No platform equivalent."
        ),
        _schema({**_JOB_REF}),
        import_result,
    ),
    ToolSpec(
        "capture_reference",
        (
            "Capture a viewport/camera still or clip, or export selected meshes, and upload the snapshot as a Scenario reference asset.\n"
            "Args:\n"
            "  - source: optional string, VIEWPORT (default), CAMERA, VIEWPORT_CLIP, CAMERA_CLIP or MESH.\n"
            "Returns: context_id and reference_id; poll reference_upload_status until imported to obtain asset_id for a model file parameter. Captures use private temporary storage cleaned after staging.\n"
            'Example: {"source": "CAMERA"}.\n'
            "Stills/clips use 1280x720 and require an interactive Blender window with a 3D viewport. Clips use the preview range when enabled, otherwise the scene frame range, without audio or implicit duration padding. MESH exports the selected meshes as one GLB and also works in background mode. This sends scene content to Scenario; use it only for an authorized reference upload.\n"
            "Platform equivalent: upload_asset then upload_asset_complete."
        ),
        _schema(
            {
                "source": {
                    "type": "string",
                    "enum": ["VIEWPORT", "CAMERA", "VIEWPORT_CLIP", "CAMERA_CLIP", "MESH"],
                }
            }
        ),
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
