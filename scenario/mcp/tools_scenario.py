# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""MCP tools that talk to Scenario through the add-on: catalog, cost, generate, results into the scene."""

import json
from dataclasses import asdict

import bpy

from ..blender import generation, runtime
from ..core.api.catalog import GENERATION_LANES as LANES
from ..core.api.errors import ScenarioError
from ..core.api.library import asset_summary as _asset_summary
from ..core.scene.panorama import describe_world_media
from ..core.schema.params import build_body, validate
from ..core.ui import capability_status
from ..core.ui.costs import workflow_quote_notice
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
                "capability_status": capability_status.model_status(rec.capabilities),
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


def _generation_input(args, lane):
    if lane in {"render_image", "render_video"}:
        from ..blender import render_commands

        runtime.sync_catalog_context()
        request = render_commands.request(
            bpy.context.scene, lane, args["model_id"], args.get("parameters")
        )
        return generation.ensure_record(request.model_id), request.body, request
    record, body = _body_for(args["model_id"], args.get("parameters"))
    return record, body, None


def render_form(args):
    from ..blender import render_commands

    return render_commands.execute(bpy.context, args)


def estimate_cost(args):
    lane = args.get("lane") or "image"
    if lane not in LANES:
        raise ValueError(f"lane must be one of {LANES}")
    record, body, render_request = _generation_input(args, lane)
    jobs = runtime.ensure_model_jobs()
    ticket = jobs.quote(bpy.context.scene, record.id, body, lane=lane)

    def finish_model(_):
        if runtime.ensure_model_jobs() is not jobs:
            raise ScenarioError(0, "The estimate context changed; estimate again")
        quote = jobs.finish_quote(ticket)
        if render_request is not None:
            try:
                _, current, _ = _generation_input(args, lane)
                if current != body:
                    raise ScenarioError(0, "The render form changed; estimate again")
            except Exception:
                jobs.quotes.pop(ticket.identifier, None)
                raise
        return {
            "model_id": record.id,
            "lane": lane,
            "quote_id": ticket.identifier,
            "cu_cost": float(quote.cost),
            "cu_cost_exact": str(quote.cost),
            "mesh_sources": [asdict(source) for source in ticket.quote.mesh_sources],
            "details": json.loads(quote.response_json).get("costDetails") or {},
        }

    return DeferredTool(ticket.task.result, finish_model)


def _wait_workflow(task):
    try:
        task.result()
    except Exception:
        # Deliver the owned completion on the main thread, including errors.
        pass


def _asset_library(args, *, search=False):
    options = {"public": args.get("public", False)}
    if search:
        options.update(
            query=args["query"], limit=args.get("limit", 40), offset=args.get("offset", 0)
        )
    else:
        options.update(
            page_size=args.get("page_size", 40),
            pagination_token=args.get("pagination_token"),
            collection_id=args.get("collection_id"),
        )
    session = runtime.ensure_job_session()
    task = session.asset_library(bpy.context.scene, **options)

    def finish(_):
        if runtime.ensure_job_session() is not session:
            raise ScenarioError(0, "The asset library context changed; read it again")
        outcomes = session.drain(task=task)
        if not outcomes:
            raise ScenarioError(0, "The asset library is still loading")
        page = session.deliver(outcomes[0], lambda value, *_: value)
        return {**page, "assets": [_asset_summary(row) for row in page["assets"]]}

    return DeferredTool(lambda: _wait_workflow(task), finish)


def list_assets(args):
    return _asset_library(args)


def search_assets(args):
    return _asset_library(args, search=True)


def _workflow_metadata(args, *, detail=False):
    privacy = args.get("privacy", "private")
    if privacy not in {"private", "public"}:
        raise ValueError("Choose private or public workflows")
    offset, limit = args.get("offset", 0), args.get("limit", 40)
    query = args.get("query", "")
    if (
        type(offset) is not int
        or offset < 0
        or type(limit) is not int
        or not 1 <= limit <= 40
        or not isinstance(query, str)
    ):
        raise ValueError("Use a nonnegative offset, limit from 1 to 40 and text query")
    session = runtime.ensure_job_session()
    task = session.workflow_metadata(
        bpy.context.scene, identifier=args["workflow_id"] if detail else None, privacy=privacy
    )

    def finish(_):
        if runtime.ensure_job_session() is not session:
            raise ScenarioError(0, "The workflow context changed; inspect again")
        outcomes = session.drain(task=task)
        if not outcomes:
            raise ScenarioError(0, "Workflow metadata is still loading")
        result = session.deliver(outcomes[0], lambda value, *_: value)
        if detail:
            fields = result.get("inputs_definition")
            if fields is None:
                fields = result.get("inputs")
            return {
                "workflow_id": result["id"],
                "name": result.get("name", ""),
                "description": result.get("description", ""),
                "inputs": fields,
            }
        rows = [
            {
                "id": row["id"],
                "name": row.get("name", ""),
                "description": row.get("description", ""),
            }
            for row in result
        ]
        rows = [
            row
            for row in rows
            if query.lower() in " ".join(str(value) for value in row.values()).lower()
        ]
        end = offset + limit
        return {
            "privacy": privacy,
            "workflows": rows[offset:end],
            "total": len(rows),
            "next_offset": end if end < len(rows) else None,
        }

    return DeferredTool(lambda: _wait_workflow(task), finish)


def list_workflows(args):
    return _workflow_metadata(args)


def workflow_schema(args):
    return _workflow_metadata(args, detail=True)


def estimate_workflow(args):
    jobs = runtime.ensure_model_jobs()
    ticket = jobs.quote_workflow(bpy.context.scene, args["workflow_id"], args.get("parameters", {}))

    def finish(_):
        if runtime.ensure_model_jobs() is not jobs:
            raise ScenarioError(0, "The workflow context changed; estimate again")
        estimate = jobs.finish_quote(ticket)
        return {
            "workflow_id": ticket.model_id,
            "quote_id": ticket.identifier,
            "parameters": json.loads(ticket.inputs),
            "payload": estimate.payload,
            "cu_cost_exact": str(estimate.cost),
            "mesh_sources": [asdict(source) for source in ticket.quote.mesh_sources],
            **workflow_quote_notice(estimate.loop_steps),
        }

    return DeferredTool(lambda: _wait_workflow(ticket.task), finish)


def run_workflow(args):
    jobs = runtime.ensure_model_jobs()
    view = jobs.submit_workflow(
        args["quote_id"],
        bpy.context.scene,
        args["workflow_id"],
        args.get("parameters", {}),
        approved_cost=args["approved_cost"],
    )
    return {
        "local_id": view.local_id,
        "state": view.status,
        # A missing count is unknown coverage, never proof that there is no loop.
        **workflow_quote_notice(view.meta.get("workflow_loop_steps")),
        "note": "One workflow submission saved. Inspect job_status; never repeat uncertain work. Results require explicit application. General workflow cancellation is unavailable. job_status cu_cost_exact stays the approved quote, not the final charge.",
    }


def discard_workflow_estimate(args):
    runtime.ensure_model_jobs().discard_workflow_quote(args["quote_id"])
    return {"discarded": True}


def film_recipe(args):
    from ..blender import film_jobs

    action = args.get("action", "inspect")
    scene = bpy.context.scene
    if action == "inspect":
        owner = runtime.ensure_film_jobs()
        return {"context_id": runtime.state.job_context_id, **owner.inspect(scene)}
    if action == "load":
        plan = film_jobs.load_recipe(scene, args["recipe"])
    elif action == "new_production":
        import uuid

        _, plan = film_jobs.recipe(scene)
        scene.scenario_film.production_id = uuid.uuid4().hex
    else:
        raise ValueError("Choose inspect, load or new_production")
    return {
        "production_id": scene.scenario_film.production_id,
        "title": plan["title"],
        "tasks": plan["tasks"],
        "shots": [{"shot_id": shot["id"], "title": shot["title"]} for shot in plan["shots"]],
    }


def _film_owner(args):
    owner = runtime.ensure_film_jobs()
    if args["production_id"] != bpy.context.scene.scenario_film.production_id:
        raise ScenarioError(0, "The Film production changed; inspect the recipe again")
    return owner


def estimate_film_task(args):
    owner = _film_owner(args)
    scene = bpy.context.scene
    item = owner.quote(scene, args["task_id"])

    def finish(_):
        if runtime.ensure_film_jobs() is not owner or bpy.context.scene != scene:
            raise ScenarioError(
                0, "The Film context changed; return to its scene and inspect the recipe"
            )
        owner.finish(item, scene)
        return owner.quote_details(item, scene)

    return DeferredTool(item.task.result, finish)


def approve_film_task(args):
    owner = runtime.ensure_film_jobs()
    view = owner.approve(args["quote_id"], bpy.context.scene, approved_cost=args["approved_cost"])
    return {
        "request_id": view.local_id,
        "local_id": view.local_id,
        "state": view.status,
        "note": "One submission saved. Use job_status and explicit recovery/application; never repeat uncertain work.",
    }


def discard_film_estimate(args):
    runtime.ensure_film_jobs().discard(args["quote_id"], bpy.context.scene)
    return {"discarded": True}


def bind_film_upload(args):
    owner = _film_owner(args)
    if args["context_id"] != runtime.state.job_context_id:
        raise ScenarioError(0, "The upload context changed; inspect uploads again")
    scene = bpy.context.scene
    item = owner.bind_upload(
        scene,
        args["task_id"],
        request_id=args["request_id"],
        expected_revision=args["expected_revision"],
    )

    def finish(_):
        if runtime.ensure_film_jobs() is not owner or bpy.context.scene != scene:
            raise ScenarioError(0, "The Film context changed; inspect saved associations")
        owner.finish(item, scene)
        return {
            "production_id": item.binding[0],
            "task_id": item.task_id,
            "upload_request_id": item.request_id,
            "state": "bound",
        }

    return DeferredTool(item.task.result, finish)


def film_shot_sources(args):
    owner = _film_owner(args)
    return {
        "context_id": runtime.state.job_context_id,
        "production_id": args["production_id"],
        "shot_id": args["shot_id"],
        "heroes": owner.session.film_shots.inspect(bpy.context.scene, shot_id=args["shot_id"]),
    }


def prepare_film_shot(args):
    owner = _film_owner(args)
    if args["context_id"] != runtime.state.job_context_id:
        raise ScenarioError(0, "The Film connection changed; inspect the shot's sources again")
    return owner.session.film_shots.prepare(
        bpy.context.scene, shot_id=args["shot_id"], selections=args["selections"]
    )


def film_shot_review(args):
    commands = runtime.ensure_film_jobs().session.film_shots
    action = args.get("action", "status")
    if action == "status":
        commands.poll()
        return commands.status(args["review_id"])
    if action == "discard":
        return commands.discard(args["review_id"])
    if action == "retry_receipts":
        return commands.retry_receipts(args["review_id"])
    if action == "dismiss_uncertain":
        return commands.dismiss_uncertain(args["review_id"], inspected=args.get("inspected"))
    raise ValueError("Choose status, discard, retry_receipts or dismiss_uncertain")


def build_film_shot(args):
    return runtime.ensure_film_jobs().session.film_shots.approve(args["review_id"])


def film_timeline_sources(args):
    owner = _film_owner(args)
    return {
        "context_id": runtime.state.job_context_id,
        **owner.session.film_timeline.inspect(bpy.context.scene),
    }


def prepare_film_timeline(args):
    owner = _film_owner(args)
    if args["context_id"] != runtime.state.job_context_id:
        raise ScenarioError(0, "The Film connection changed; inspect timeline sources again")
    return owner.session.film_timeline.prepare(bpy.context.scene, selections=args["selections"])


def film_timeline_review(args):
    commands = runtime.ensure_film_jobs().session.film_timeline
    action = args.get("action", "status")
    if action == "status":
        return commands.status(args["review_id"])
    if action == "discard":
        return commands.discard(args["review_id"], inspected=args.get("inspected", False))
    raise ValueError("Choose status or discard")


def build_film_timeline(args):
    return runtime.ensure_film_jobs().session.film_timeline.approve(args["review_id"])


def prepare_film_composition(args):
    owner = _film_owner(args).compositions
    if args["context_id"] != runtime.state.job_context_id:
        raise ValueError("The composition connection changed; inspect the recipe again")
    return owner.prepare(
        bpy.context.scene,
        mode=args.get("mode", "final"),
        score_task_id=args.get("score_task_id", "score"),
    )


def film_composition_review(args):
    owner = runtime.ensure_film_jobs().compositions
    action = args.get("action", "status")
    if action == "cancel":
        return owner.cancel(args["review_id"])
    if action == "status":
        owner.poll()
        return owner.status(args["review_id"])
    if action == "discard":
        owner.poll()
        return owner.discard(args["review_id"])
    raise ValueError("Choose status, cancel or discard")


def estimate_film_composition(args):
    owner = runtime.ensure_film_jobs().compositions
    scene = bpy.context.scene
    identifier = args["review_id"]
    owner.estimate(identifier)
    task = owner._get(identifier).task

    def finish(_):
        if runtime.ensure_film_jobs().compositions is not owner or bpy.context.scene != scene:
            raise ScenarioError(0, "The Film context changed; inspect the composition review")
        owner.poll()
        status = owner.status(identifier)
        if status["phase"] != "QUOTED":
            raise ScenarioError(0, status["error"] or "The composition price is unavailable")
        return status

    return DeferredTool(task.result, finish)


def generate_film_composition(args):
    return runtime.ensure_film_jobs().compositions.approve(
        args["review_id"], approved_cost=args["approved_cost"]
    )


def film_capture_sources(args):
    owner = _film_owner(args).session.film_capture
    return {
        "context_id": runtime.state.job_context_id,
        **owner.inspect(bpy.context.scene, shot_id=args["shot_id"]),
    }


def prepare_film_capture(args):
    owner = _film_owner(args).session.film_capture
    if args["context_id"] != runtime.state.job_context_id:
        raise ValueError("The capture connection changed; inspect sources again")
    return owner.prepare(
        bpy.context.scene,
        shot_id=args["shot_id"],
        source_id=args["source_id"],
        kind=args.get("kind", "VIDEO"),
        width=args.get("width", 1280),
        height=args.get("height", 720),
        color_type=args.get("color_type", "MATERIAL"),
    )


def render_film_capture(args):
    return runtime.ensure_film_jobs().session.film_capture.approve(args["review_id"])


def film_capture_review(args):
    owner = runtime.ensure_film_jobs().session.film_capture
    action = args.get("action", "status")
    if action == "status":
        owner.poll()
        return owner.status(args["review_id"])
    if action == "cancel":
        return owner.cancel(args["review_id"])
    if action == "discard":
        return owner.discard(args["review_id"])
    raise ValueError("Choose status, cancel or discard")


def upload_film_capture(args):
    owner = runtime.ensure_film_jobs().session.film_capture
    return {
        "context_id": runtime.state.job_context_id,
        **owner.upload(args["review_id"], runtime.ensure_reference_uploads()),
    }


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


def estimate_blockout(args):
    jobs = runtime.ensure_blockout_jobs()
    item = jobs.quote(bpy.context.scene, args.get("action", "DESIGN"))

    def finish(_):
        if runtime.ensure_blockout_jobs() is not jobs:
            raise ScenarioError(0, "The Blockout context changed")
        jobs.poll()
        if item.phase != "READY":
            raise ScenarioError(0, item.error or "The Blockout price is unavailable")
        return {"quote_id": item.identifier, "action": item.action, "cu_cost_exact": item.cost}

    return DeferredTool(item.task.result, finish)


def approve_blockout(args):
    item = runtime.ensure_blockout_jobs().approve(
        args["quote_id"], bpy.context.scene, approved_cost=args["approved_cost"]
    )
    return {"request_id": item.request_id, "state": item.phase.lower()}


def prepare_blockout_plan(args):
    recovery = runtime.blockout_recovery(args["context_id"])
    review = recovery.prepare(args["request_id"], args["expected_revision"], bpy.context.scene)
    return recovery.status(review.identifier)


def blockout_plan_status(args):
    recovery = runtime.blockout_recovery(args["context_id"])
    recovery.poll()
    if args.get("discard", False):
        review = recovery.reviews.get(args["review_id"])
        if review is not None and review.task is not None:
            raise ScenarioError(0, "Wait for the saved-plan read before discarding its review")
        recovery.discard(args["review_id"])
        return {"state": "discarded"}
    return recovery.status(args["review_id"])


def apply_blockout_plan(args):
    return runtime.blockout_recovery(args["context_id"]).apply(args["review_id"])


def read_model_text(args):
    session = runtime.ensure_job_session()
    if args.get("context_id") != runtime.state.job_context_id:
        raise ScenarioError(0, "The saved-job context changed; list local jobs again")
    task = session.read_model_text(
        args["request_id"], expected_revision=args["expected_revision"], asset_id=args["asset_id"]
    )

    def finish(_):
        if runtime.ensure_job_session() is not session:
            raise ScenarioError(0, "The text result context changed")
        outcomes = session.drain(task=task)
        if not outcomes:
            raise ScenarioError(0, "The text result completion is unavailable")
        if outcomes[0].error is not None:
            raise outcomes[0].error
        result = outcomes[0].result
        return {
            "request_id": result.record.intent.request_id,
            "asset_id": result.asset_id,
            "text": result.text,
        }

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
                "source": getattr(item.record.intent, "source", "generation"),
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
    ticket = runtime.ensure_model_jobs().require_quote(args.get("quote_id"))
    if ticket.lane != lane:
        raise ScenarioError(0, "The generation lane changed; estimate again")
    record, body, render_request = _generation_input(args, lane)
    meta = {
        "prompt": str(body.get("prompt") or ""),
        "model_name": record.name,
        "source": "mcp",
        "target_objects": [o.name for o in bpy.context.selected_objects if o.type == "MESH"],
    }
    if render_request is not None:
        meta.update(generation.request_meta(bpy.context, lane, render_request))
        meta["source"] = "mcp"
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
    from ..blender import history

    if runtime.credentials().valid:
        matches = history.saved_matches(reference)
        if len(matches) > 1:
            raise ValueError("Several saved jobs match; use a request_id from list_local_jobs")
        if matches:
            status = runtime.ensure_model_jobs().status(matches[0].intent.request_id)
            if status is None:
                raise ValueError("The saved job changed; inspect list_local_jobs again")
            return status
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
    if purpose in {"mesh_edit", "mesh_source"}:
        _, approval = runtime.prepare_mesh_application(
            args["context_id"],
            args["request_id"],
            args["expected_revision"],
            bpy.context.scene,
            bpy.context.view_layer.objects.active,
            args.get("asset_id"),
            policy=args.get("mesh_policy", "REMESH"),
            placement=args.get("mesh_placement", "WORLD"),
            keep_original=args.get("keep_original", True),
            original_source=purpose == "mesh_source",
        )
        return {
            "context_id": args["context_id"],
            "application_id": approval.identifier,
            "request_id": approval.record.intent.request_id,
            "revision": approval.record.revision,
            "reuse": approval.record.state.value == "applied",
            "kind": "mesh_edit",
            "purpose": purpose,
            "scene": approval.scene_name,
            "target": approval.target_name,
            "asset_id": approval.asset_id,
            "mesh_policy": approval.policy,
            "mesh_placement": approval.placement,
            "keep_original": approval.keep_original,
            "result_to_source": [list(row) for row in approval.mapping],
            "note": "Approve applying one saved GLB to this captured mesh. "
            "REMESH replaces geometry, UVs and mesh materials; UV replaces only active UVs "
            "and requires exact indexed topology and positions. RETEXTURE preserves geometry and "
            "non-UV attributes, replacing all UV layers and mesh materials with exact topology/position matching. "
            "PARTS replaces source geometry with an empty mesh parent and 2 to 128 named parts; "
            "every mesh in the selected GLB is treated as a part, not an alternate variant. "
            "RIG preserves source geometry, UVs and materials, attaching compatible bone weights "
            "and one returned rig with its clips. Indexed geometry must match; morphs and mesh "
            "animation are unsupported. Move the source and its new rig group together afterward. "
            "WORLD preserves imported scene "
            "positions; LOCAL treats imported positions as object-local. Neither fits or rescales "
            "the result automatically. Keep original preserves an unselected copy. "
            "No new generation or blend save. Desktop undo follows Blender settings; "
            "undo/redo changes the scene only and never replays spending. Check mesh_edit.undo_available "
            "after application. Provider alignment is not guaranteed.",
        }
    if purpose == "material":
        _, approval = runtime.prepare_material_application(
            args["context_id"],
            args["request_id"],
            args["expected_revision"],
            bpy.context.scene,
            bpy.context.view_layer.objects.active,
        )
        return {
            "context_id": args["context_id"],
            "application_id": approval.identifier,
            "reuse": approval.record.state.value == "applied"
            and not getattr(approval, "restore", False),
            "request_id": approval.record.intent.request_id,
            "revision": approval.record.revision,
            "scene": approval.scene_name,
            "target": approval.target_name,
            "slot": approval.target.active + 1,
            "roles": list(approval.roles),
            "kind": "material",
            "purpose": purpose,
            "note": "Approve one saved texture set for this mesh's active material slot. "
            "Images are packed; old materials and other slots are untouched. "
            "Only a local single-user mesh with UVs in Object Mode is supported. "
            "Normals use Blender tangent space; height uses bump only. AO/edge nodes stay unconnected. "
            "This does not regenerate or save the blend file, and has no global undo transaction.",
        }
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
            "reuse": approval.record.state.value == "applied"
            and not getattr(approval, "restore", False),
            "request_id": approval.record.intent.request_id,
            "revision": approval.record.revision,
            "scene": approval.scene_name,
            "asset_id": approval.asset_id,
            "kind": "world",
            "purpose": purpose,
            "previous_world": approval.previous.name if approval.previous else None,
            "format": None if approval.restore else describe_world_media(approval.media_type),
            "note": "Approve restoring this session's original World; changed owned World/image data prevents restoration."
            if approval.restore
            else "Approve replacing this scene's World with one packed equirectangular panorama. "
            "Only supported 2:1 PNG, JPEG or scanline OpenEXR bytes matching the saved media type qualify; "
            "PNG/JPEG are LDR and EXR is not proof of actual HDR range. "
            "The original World stays untouched and this session can restore it while unchanged. Nothing has been applied.",
        }
    if purpose != "import":
        raise ValueError("Choose import, material, world or restore_world")
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
                "reuse": approval.record.state.value == "applied"
                and not getattr(approval, "restore", False),
                "request_id": approval.record.intent.request_id,
                "revision": approval.record.revision,
                "scene": approval.scene_name,
                "asset_id": approval.asset_id,
                "kind": "model",
                "cursor": list(approval.cursor),
                "note": "Approve importing this one embedded GLB into a new group with its bottom at the cursor. "
                "Existing objects, selection and timeline stay unchanged. Rigs and node animation clips are retained using scene FPS; external-file GLBs are unsupported. "
                "Nothing has been imported; changed destinations require review again.",
            }
        return {
            "context_id": args["context_id"],
            "application_id": approval.identifier,
            "reuse": approval.record.state.value == "applied"
            and not getattr(approval, "restore", False),
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
        "reuse": approval.record.state.value == "applied"
        and not getattr(approval, "restore", False),
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
    result = _status(rec)
    if not rec.is_terminal:
        result["note"] = (
            "Prototype status is a local snapshot; automatic polling is retired. "
            "Use recover_cloud_job in the selected account, then approve its destination."
        )
    return result


def import_result(args):
    reference = _job_ref(args)
    if not runtime.credentials().valid:
        raise ScenarioError(
            0, "Select complete credentials before importing; inspect saved jobs first"
        )
    if _saved_status(reference) is not None:
        raise ValueError(
            "Use prepare_result_application and explicit destination approval for saved results; "
            "use prepare_blockout_plan for saved Blockout text"
        )
    raise ValueError(
        "Use recover_cloud_job with the remote job and model IDs, then explicit destination "
        "approval; cached prototype files cannot authorize application"
    )


def recover_cloud_job(args):
    jobs = runtime.ensure_model_jobs()
    item = jobs.recover_cloud(args["job_id"], args["model_id"], bpy.context.scene)

    def finish(_):
        if runtime.ensure_model_jobs() is not jobs:
            raise ScenarioError(0, "The cloud recovery context changed; inspect saved jobs")
        record = jobs.finish_cloud(item)
        generation.process_model_jobs()
        return {
            "context_id": runtime.state.job_context_id,
            "request_id": record.intent.request_id,
            "job_id": record.remote_job_id,
            "revision": record.revision,
            "state": record.state.value,
            "source": getattr(record.intent, "source", "generation"),
            "note": "Saved for explicit recovery; this read did not download or apply anything",
        }

    def run():
        try:
            item.task.result()
        except Exception:
            pass  # The main-thread finisher reports the owned, sanitized failure.

    return DeferredTool(run, finish)


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
    saved_ids = {}
    for record in history.saved_records():
        if record.remote_job_id:
            saved_ids.setdefault(record.remote_job_id, []).append(record.intent.request_id)
    result = {
        "generations": [
            {
                "job_id": e.job_id,
                "kind": e.kind,
                "model_id": e.model_id,
                "prompt": e.prompt,
                "status": e.status,
                "cu_cost": e.cu_cost,
                "cost_unavailable": e.cost_unavailable,
                "workflow_id": e.workflow_id or None,
                "workflow_job_id": e.workflow_job_id or None,
                "local_files": [],
                "local_request_ids": saved_ids.get(e.job_id, list(e.local_request_ids)),
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
        "list_assets",
        (
            "Read one asset-library page using the selected credentials and optional project scope.\n"
            "Args: public defaults to false (owned assets); page_size is 1 to 100, default 40; pagination_token and collection_id are optional.\n"
            "Returns: asset IDs, names, descriptions, MIME types, generation types, tags, collection IDs and next_pagination_token.\n"
            'Example: {"page_size": 20}.\n'
            "Reuse the same filters with the returned cursor. Ordering can change between reads. No download URLs, file bytes, complete text previews, upload or generation are returned or started.\n"
            "Platform equivalent: SDK assets.list through the shared adapter."
        ),
        _schema(
            {
                "public": {"type": "boolean"},
                "page_size": {"type": "integer", "minimum": 1, "maximum": 100},
                "pagination_token": {"type": "string"},
                "collection_id": {"type": "string"},
            }
        ),
        list_assets,
        {"readOnlyHint": True},
    ),
    ToolSpec(
        "search_assets",
        (
            "Search asset-library metadata through the shared SDK session.\n"
            "Args: query is required nonempty text, at most 4096 characters; public defaults to false; limit is 1 to 100 (default 40), offset is nonnegative (default 0).\n"
            "Returns: reusable asset metadata, estimated_total and next_offset; a total is an estimate, not a stable snapshot.\n"
            'Example: {"query": "ceramic cup", "limit": 20}.\n'
            "Continue with the same query/public selection and returned offset. Signed URLs, indexed text bodies and account identifiers are omitted. No upload, generation, file download or organization write.\n"
            "Platform equivalent: SDK search.asset_search through the shared adapter."
        ),
        _schema(
            {
                "query": {"type": "string", "minLength": 1, "maxLength": 4096},
                "public": {"type": "boolean"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 100},
                "offset": {"type": "integer", "minimum": 0},
            },
            ["query"],
        ),
        search_assets,
        {"readOnlyHint": True},
    ),
    ToolSpec(
        "list_workflows",
        (
            "List workflows in the selected credential/project scope without spending.\n"
            "Args: privacy is private (default) or public; query filters id/name/description; offset defaults to 0 and limit is 1 to 40 (default 40).\n"
            "Returns: workflows, total matching rows and next_offset, or an explicit catalog error.\n"
            'Example: {"privacy": "public", "query": "image", "limit": 20}.\n'
            "Each call reads the bounded complete catalog before local filtering/paging; ordering can change between calls. Context changes reject delivery. No upload or generation.\n"
            "Platform equivalent: workflows_list."
        ),
        _schema(
            {
                "privacy": {"type": "string", "enum": ["private", "public"]},
                "query": {"type": "string"},
                "offset": {"type": "integer", "minimum": 0},
                "limit": {"type": "integer", "minimum": 1, "maximum": 40},
            }
        ),
        list_workflows,
        {"readOnlyHint": True},
    ),
    ToolSpec(
        "workflow_schema",
        (
            "Read a workflow's declared input definitions without spending.\n"
            "Args: workflow_id is required.\n"
            "Returns: workflow_id, name, description and original inputs with conditional/default/file definitions.\n"
            'Example: {"workflow_id": "workflow-example"}.\n'
            "This does not prove every workflow feature is supported; estimate_workflow validates supported input forms with fresh metadata before pricing. Use uploaded Scenario asset IDs for file inputs.\n"
            "Platform equivalent: workflow_get."
        ),
        _schema({"workflow_id": {"type": "string"}}, ["workflow_id"]),
        workflow_schema,
        {"readOnlyHint": True},
    ),
    ToolSpec(
        "estimate_workflow",
        (
            "Request a free exact workflow price bound to the selected scene and connection.\n"
            "Args: workflow_id is required; parameters is an input object (default empty).\n"
            "Returns: quote_id, workflow_id, original parameters, normalized payload, cu_cost_exact, mesh_sources, loop_steps, quote_may_understate and cost_warning. loop_steps counts loop nodes (for-each, or any node carrying a ForEach field) in the workflow definition, or is null when coverage is unknown, including an empty flow not marked hasFlow false; when quote_may_understate is true the price covers one loop pass and the final charge can be higher. Show cost_warning with the price; it does not block approval.\n"
            'Example: {"workflow_id": "workflow-example", "parameters": {"prompt": "a cup"}}.\n'
            "No paid submission or upload. Review the normalized payload and exact price; run_workflow requires the same original parameters and explicit approved_cost. Scene, file, credential or project changes require a fresh estimate.\n"
            "Platform equivalent: dry_run on workflow_run."
        ),
        _schema(
            {"workflow_id": {"type": "string"}, "parameters": {"type": "object"}}, ["workflow_id"]
        ),
        estimate_workflow,
    ),
    ToolSpec(
        "run_workflow",
        (
            "Approve one unchanged workflow estimate and persist its identity before paid dispatch.\n"
            "Args: workflow_id, quote_id and approved_cost are required; parameters must match estimate_workflow's original parameters. approved_cost must be its exact cu_cost_exact string.\n"
            "Returns: local_id, saved state, loop_steps, quote_may_understate, cost_warning and note; use job_status, wait_for_job and explicit result application. job_status cu_cost_exact remains the approved quote, not the final charge.\n"
            'Example: {"workflow_id": "workflow-example", "quote_id": "approved-quote", "parameters": {"prompt": "a cup"}, "approved_cost": "1.25"}.\n'
            "Consumes the quote before persistence. Never repeat an uncertain submission; inspect saved jobs. Closing views does not stop it. No automatic scene import. General workflow cancellation and interactive approval/selection nodes are not supported here.\n"
            "Platform equivalent: workflow_run."
        ),
        _schema(
            {
                "workflow_id": {"type": "string"},
                "parameters": {"type": "object"},
                "quote_id": {"type": "string"},
                "approved_cost": {"type": "string"},
            },
            ["workflow_id", "quote_id", "approved_cost"],
        ),
        run_workflow,
    ),
    ToolSpec(
        "discard_workflow_estimate",
        (
            "Discard one ready unsubmitted workflow approval without changing saved jobs.\n"
            "Args: quote_id is required.\n"
            "Returns: discarded=true.\n"
            'Example: {"quote_id": "unused-workflow-quote"}.\n'
            "This only releases local approval authority; it does not cancel remote work, upload inputs or request another price. Used quotes remain unusable.\n"
            "Platform equivalent: none; local estimate lifecycle."
        ),
        _schema({"quote_id": {"type": "string"}}, ["quote_id"]),
        discard_workflow_estimate,
    ),
    ToolSpec(
        "prepare_film_composition",
        (
            "Inspect saved Film media and prepare a final or previs composition without spending.\n"
            "Args: context_id and production_id are required from film_recipe inspection; mode is final (default) or previs, score_task_id defaults to score.\n"
            "Returns: review_id and PREPARING phase; poll film_composition_review until READY.\n"
            'Example: {"context_id": "current-context", "production_id": "saved-production", "mode": "final"}.\n'
            "Film is experimental. Requires retained upload files or downloaded results and installed ffprobe. Uses the existing selected connection and recipe; no upload, download, scene mutation or generation. Reviews are session-local.\n"
            "Platform equivalent: none; local composition source verification."
        ),
        _schema(
            {
                "context_id": {"type": "string"},
                "production_id": {"type": "string"},
                "mode": {"type": "string", "enum": ["final", "previs"]},
                "score_task_id": {"type": "string"},
            },
            ["context_id", "production_id"],
        ),
        prepare_film_composition,
    ),
    ToolSpec(
        "film_composition_review",
        (
            "Inspect, cancel or discard a session-local Film composition review.\n"
            "Args: review_id is required; action is status (default), cancel or discard.\n"
            "Returns: phase, original scene/production/master, frames/fps, sources/layers, parameters, exact price, saved request_id and sanitized error when available.\n"
            'Example: {"review_id": "current-composition", "action": "status"}.\n'
            "Film is experimental. Cancel stops local inspection or discards a pending price after it finishes. Discard releases only the review after active work ends; media and saved jobs remain. Neither action cancels or repeats a generation. After restart inspect film_recipe and saved jobs.\n"
            "Platform equivalent: none; local composition review lifecycle."
        ),
        _schema(
            {
                "review_id": {"type": "string"},
                "action": {"type": "string", "enum": ["status", "cancel", "discard"]},
            },
            ["review_id"],
        ),
        film_composition_review,
    ),
    ToolSpec(
        "estimate_film_composition",
        (
            "Request the exact server price for one READY verified Film composition.\n"
            "Args: review_id is required from prepare_film_composition.\n"
            "Returns: QUOTED review with exact cu_cost_exact, model parameters and original master identity.\n"
            'Example: {"review_id": "ready-composition"}.\n'
            "Film is experimental. Rechecks saved sources, original recipe, scene and connection. No generation. Review the returned payload and obtain explicit spending approval before generate_film_composition.\n"
            "Platform equivalent: estimate_cost for model_scenario-compose-video."
        ),
        _schema({"review_id": {"type": "string"}}, ["review_id"]),
        estimate_film_composition,
        {"readOnlyHint": True},
    ),
    ToolSpec(
        "generate_film_composition",
        (
            "Approve one exact Film composition price and save its master identity before a single submission.\n"
            "Args: review_id and approved_cost are required strings; approve cu_cost_exact verbatim.\n"
            "Returns: SUBMITTED review with request_id for job_status and saved-job recovery.\n"
            'Example: {"review_id": "quoted-composition", "approved_cost": "0.10000000000000001"}.\n'
            "Film is experimental. Requires explicit approval of the reviewed payload and exact cost. Consumes approval before preparation. On an error or lost response inspect film_recipe and saved jobs; never repeat uncertain submission. Downloads remain saved for separate application; no recipe or scene edit.\n"
            "Platform equivalent: generate with model_scenario-compose-video through the shared model runtime."
        ),
        _schema(
            {"review_id": {"type": "string"}, "approved_cost": {"type": "string"}},
            ["review_id", "approved_cost"],
        ),
        generate_film_composition,
    ),
    ToolSpec(
        "film_capture_sources",
        (
            "Inspect matching local scenes for one Film shot before capture.\n"
            "Args: production_id and shot_id are required strings from film_recipe.\n"
            "Returns: context_id, source_id/scene choices, editorial frames/fps and generated source timing.\n"
            'Example: {"production_id": "saved-production", "shot_id": "shot"}.\n'
            "Film is experimental. Fresh inspection replaces unprepared source handles; prepared reviews keep their identities. No rendering or upload.\n"
            "Platform equivalent: none; local Film capture inspection."
        ),
        _schema(
            {"production_id": {"type": "string"}, "shot_id": {"type": "string"}},
            ["production_id", "shot_id"],
        ),
        film_capture_sources,
        {"readOnlyHint": True},
    ),
    ToolSpec(
        "prepare_film_capture",
        (
            "Prepare a local shot capture for separate render approval.\n"
            "Args: context_id, production_id, shot_id and source_id are required; kind is VIDEO (default) or STILL, width/height default 1280/720, color_type is MATERIAL (default), TEXTURE or OBJECT.\n"
            "Returns: review_id, READY phase, exact source, dimensions, frames and fps.\n"
            'Example: {"context_id": "current-context", "production_id": "saved-production", "shot_id": "shot", "source_id": "current-source", "kind": "STILL"}.\n'
            "Film is experimental. No scene snapshot, render, upload or generation yet. VIDEO requires installed ffmpeg/ffprobe and uses the editorial range without padding; STILL uses its first frame. Ask for approval of the displayed settings before render_film_capture.\n"
            "Platform equivalent: none; local capture settings review."
        ),
        _schema(
            {
                "context_id": {"type": "string"},
                "production_id": {"type": "string"},
                "shot_id": {"type": "string"},
                "source_id": {"type": "string"},
                "kind": {"type": "string", "enum": ["STILL", "VIDEO"]},
                "width": {"type": "integer", "minimum": 64, "maximum": 4096},
                "height": {"type": "integer", "minimum": 64, "maximum": 4096},
                "color_type": {"type": "string", "enum": ["MATERIAL", "TEXTURE", "OBJECT"]},
            },
            ["context_id", "production_id", "shot_id", "source_id"],
        ),
        prepare_film_capture,
    ),
    ToolSpec(
        "render_film_capture",
        (
            "Approve a READY Film capture and start one local render on the shared workers.\n"
            "Args: review_id is required from prepare_film_capture.\n"
            "Returns: capture phase; poll film_capture_review without starting another render.\n"
            'Example: {"review_id": "approved-capture"}.\n'
            "Film is experimental. Requires explicit approval of the source and settings. The snapshot/render is local, preserves the working file and sends no bytes to Scenario. Changed scenes or credentials invalidate approval.\n"
            "Platform equivalent: none; local offline capture."
        ),
        _schema({"review_id": {"type": "string"}}, ["review_id"]),
        render_film_capture,
    ),
    ToolSpec(
        "film_capture_review",
        (
            "Inspect, cancel or discard an owner-local Film capture.\n"
            "Args: review_id is required; action is status (default), cancel or discard.\n"
            "Returns: phase, dimensions/timing, private output path/hash, error and any upload reference_id/request_id.\n"
            'Example: {"review_id": "current-capture", "action": "status"}.\n'
            "Film is experimental. Cancel stops only the local render. Explicit discard deletes its private snapshot/media/logs after active work ends, preserving saved uploads. Captures are session-local and cleaned on session shutdown; no render replays after restart. No upload or generation.\n"
            "Platform equivalent: none; local capture lifecycle."
        ),
        _schema(
            {
                "review_id": {"type": "string"},
                "action": {"type": "string", "enum": ["status", "cancel", "discard"]},
            },
            ["review_id"],
        ),
        film_capture_review,
    ),
    ToolSpec(
        "upload_film_capture",
        (
            "Upload the reviewed bytes of one completed Film capture through the shared upload runtime.\n"
            "Args: review_id is required for a CAPTURED result.\n"
            "Returns: reference_id for reference_upload_status and the original capture metadata.\n"
            'Example: {"review_id": "approved-capture"}.\n'
            "Film is experimental. Requires separate user approval of the captured output and selected connection. Staging verifies its exact content hash before any service request. Never restart an uncertain upload; inspect saved progress. Associate the imported upload with a recipe task separately using bind_film_upload. Does not generate or approve spending.\n"
            "Platform equivalent: shared uploads create/complete, followed by explicit local Film association."
        ),
        _schema({"review_id": {"type": "string"}}, ["review_id"]),
        upload_film_capture,
    ),
    ToolSpec(
        "film_timeline_sources",
        (
            "Inspect matching local scenes for every shot in the current Film recipe.\n"
            "Args: production_id is required from film_recipe.\n"
            "Returns: context_id, production_id, fps, total_frames and shots with source_id/scene choices.\n"
            'Example: {"production_id": "saved-production"}.\n'
            "Film is experimental. Choices are owner-issued live references, not scene names. Fresh inspection replaces previous choices but keeps prepared reviews. Existing scene markers identify recipe compatibility, not generation provenance; the user explicitly selects local scenes. No service call or scene mutation.\n"
            "Platform equivalent: none; local editable timeline planning."
        ),
        _schema({"production_id": {"type": "string"}}, ["production_id"]),
        film_timeline_sources,
        {"readOnlyHint": True},
    ),
    ToolSpec(
        "prepare_film_timeline",
        (
            "Prepare explicit completed shot choices for separate timeline build approval.\n"
            "Args: context_id and production_id from film_timeline_sources; selections maps every shot ID to one returned source_id.\n"
            "Returns: review_id, phase, scene, shot_count, fps, total_frames and error.\n"
            'Example: {"context_id": "current", "production_id": "saved-production", "selections": {"shot-one": "returned-source"}}.\n'
            "Film is experimental. Captures current recipe/destination and unchanged local scenes. No generation, download, render or scene build; build_film_timeline requires separate approval.\n"
            "Platform equivalent: none; local timeline review."
        ),
        _schema(
            {
                "context_id": {"type": "string"},
                "production_id": {"type": "string"},
                "selections": {"type": "object", "additionalProperties": {"type": "string"}},
            },
            ["context_id", "production_id", "selections"],
        ),
        prepare_film_timeline,
    ),
    ToolSpec(
        "film_timeline_review",
        (
            "Inspect or discard an owner-local Film timeline review.\n"
            "Args: review_id is required; action is status (default) or discard; inspected=true is required to dismiss uncertain partial cleanup.\n"
            "Returns: review_id, phase, scene, shot_count, fps, total_frames and error.\n"
            'Example: {"review_id": "returned-review", "action": "status"}.\n'
            "Film is experimental. Never builds, cleans Blender data or changes saved jobs. Handles expire when the session closes. Inspect uncertain local data before starting another review.\n"
            "Platform equivalent: none; local timeline review."
        ),
        _schema(
            {
                "review_id": {"type": "string"},
                "action": {"type": "string", "enum": ["status", "discard"]},
                "inspected": {"type": "boolean"},
            },
            ["review_id"],
        ),
        film_timeline_review,
    ),
    ToolSpec(
        "build_film_timeline",
        (
            "Approve one READY Film timeline review and create a new editable scene-strip sequence.\n"
            "Args: review_id is the required string from prepare_film_timeline.\n"
            "Returns: review_id, phase, scene, shot_count, fps, total_frames and error.\n"
            'Example: {"review_id": "returned-review"}.\n'
            "Film is experimental. Requires explicit build approval. Rechecks chosen scenes and consumes the review before mutation. Preserves the working scene and existing timelines. Strips reference live shot scenes; later edits affect the sequence. No generation, download, render, export, saved-job mutation or native operator Undo entry. Never repeat an uncertain build.\n"
            "Platform equivalent: none; local Blender timeline assembly."
        ),
        _schema({"review_id": {"type": "string"}}, ["review_id"]),
        build_film_timeline,
    ),
    ToolSpec(
        "film_shot_sources",
        (
            "Inspect eligible downloaded hero models for one shot in the current Film recipe.\n"
            "Args: production_id and shot_id are required strings from film_recipe.\n"
            "Returns: context_id, production_id, shot_id and heroes with request_id, revision and GLB asset choices.\n"
            'Example: {"production_id": "saved-production", "shot_id": "shot-one"}.\n'
            "Film is experimental. Reads the selected credential scope only. No verification, download, generation or scene build occurs.\n"
            "Platform equivalent: none; local saved Film model inspection."
        ),
        _schema(
            {"production_id": {"type": "string"}, "shot_id": {"type": "string"}},
            ["production_id", "shot_id"],
        ),
        film_shot_sources,
        {"readOnlyHint": True},
    ),
    ToolSpec(
        "prepare_film_shot",
        (
            "Verify explicit saved hero selections and prepare a shot for separate build approval.\n"
            "Args: context_id, production_id and shot_id are required strings from film_shot_sources; selections is a required object mapping every hero_id to request_id, integer revision and asset_id. Use {} for a no-hero shot.\n"
            "Returns: review_id, shot_id, phase, hero_count, scene, error and recovery flags.\n"
            'Example: {"context_id": "current", "production_id": "saved-production", "shot_id": "shot-one", "selections": {"hero": {"request_id": "saved-job", "revision": 8, "asset_id": "saved-glb"}}}.\n'
            "Film is experimental. Captures the current recipe and scene; verifies local receipts on the shared workers without building, downloading or spending. Poll film_shot_review; a READY review still needs explicit build_film_shot approval.\n"
            "Platform equivalent: none; local Film application preparation."
        ),
        _schema(
            {
                "context_id": {"type": "string"},
                "production_id": {"type": "string"},
                "shot_id": {"type": "string"},
                "selections": {
                    "type": "object",
                    "additionalProperties": {
                        "type": "object",
                        "properties": {
                            "request_id": {"type": "string"},
                            "revision": {"type": "integer", "minimum": 0},
                            "asset_id": {"type": "string"},
                        },
                        "required": ["request_id", "revision", "asset_id"],
                        "additionalProperties": False,
                    },
                },
            },
            ["context_id", "production_id", "shot_id", "selections"],
        ),
        prepare_film_shot,
    ),
    ToolSpec(
        "film_shot_review",
        (
            "Inspect or discard a Film shot review, or retry only its known persistence receipts.\n"
            "Args: review_id is required; action is status (default), discard, retry_receipts or dismiss_uncertain. Dismissal requires inspected=true.\n"
            "Returns: review_id, shot_id, phase, hero_count, scene, error, receipt_retry_available and inspection_required.\n"
            'Example: {"review_id": "returned-review", "action": "status"}.\n'
            "Film is experimental. Status advances pending local verification but never builds. Discard retires unapproved work. Receipt retry never calls the builder. After inspecting the scene and saved jobs, dismissal retires an uncertain review only if no known receipts remain; it never clears durable claims or repeats a build. Review handles do not survive a changed connection or restart.\n"
            "Platform equivalent: none; local review and receipt recovery."
        ),
        _schema(
            {
                "review_id": {"type": "string"},
                "action": {
                    "type": "string",
                    "enum": ["status", "discard", "retry_receipts", "dismiss_uncertain"],
                },
                "inspected": {"type": "boolean"},
            },
            ["review_id"],
        ),
        film_shot_review,
    ),
    ToolSpec(
        "build_film_shot",
        (
            "Approve one READY Film review and build a new shot scene from its verified saved models.\n"
            "Args: review_id is the required string from prepare_film_shot.\n"
            "Returns: review_id, shot_id, phase, hero_count, scene, error and recovery flags.\n"
            'Example: {"review_id": "returned-review"}.\n'
            "Film is experimental. Requires explicit scene-build approval. Rechecks the original recipe/destination, consumes the review and claims every source before mutation. Keeps the working scene selected. No generation or download occurs. Never repeat an uncertain build; use receipt-only recovery when offered.\n"
            "Platform equivalent: none; local Blender shot construction."
        ),
        _schema({"review_id": {"type": "string"}}, ["review_id"]),
        build_film_shot,
    ),
    ToolSpec(
        "film_recipe",
        (
            "Inspect or load the current scene's Film recipe, or explicitly start a new production.\n"
            "Args: action is inspect (default), load or new_production; recipe is a raw Film JSON object required for load.\n"
            "Returns: stable production_id, title, tasks and shots; inspection adds context_id and saved job/upload identities and states, including declared master jobs. A quoted task includes quote_id, model_id, parameters and cu_cost_exact for its existing approval.\n"
            'Example: {"action": "inspect"}.\n'
            "Film is experimental. Load validates before mutation and preserves identity. Save the blend file to retain it. New production deliberately gives the same task names a fresh identity; it does not submit or recover work.\n"
            "After a scene-switch error, return to the original scene and inspect to recover an unchanged quote or saved upload association. Inspection only completes already-admitted preparation; it never reprices, resumes saved jobs or submits. Stale quotes are omitted.\n"
            "Platform equivalent: none; local Film recipe and saved-task inspection."
        ),
        _schema(
            {
                "action": {"type": "string", "enum": ["inspect", "load", "new_production"]},
                "recipe": {"type": "object"},
            }
        ),
        film_recipe,
    ),
    ToolSpec(
        "estimate_film_task",
        (
            "Request the exact server price for one model task in the loaded Film recipe.\n"
            "Args: production_id and task_id are required strings from film_recipe.\n"
            "Returns: quote_id, production_id, task_id, model_id, resolved parameters and cu_cost_exact.\n"
            'Example: {"production_id": "saved-production", "task_id": "shot-one"}.\n'
            "Film is experimental. Uses saved scoped dependencies and the shared SDK model quote; never submits. Existing task identities cannot be spent again. Discard an unused quote before repricing.\n"
            "Platform equivalent: estimate_cost for the recipe model's resolved inputs."
        ),
        _schema(
            {"production_id": {"type": "string"}, "task_id": {"type": "string"}},
            ["production_id", "task_id"],
        ),
        estimate_film_task,
        {"readOnlyHint": True},
    ),
    ToolSpec(
        "approve_film_task",
        (
            "Approve one unchanged Film estimate and save its identity before one paid submission.\n"
            "Args: quote_id and approved_cost are required strings; approve the returned cu_cost_exact verbatim.\n"
            "Returns: request_id/local_id, state and recovery note.\n"
            'Example: {"quote_id": "returned-quote", "approved_cost": "0.10000000000000001"}.\n'
            "Film is experimental. Requires explicit spending approval. Results download through the shared model lifecycle and remain saved for explicit application. Never repeat an uncertain submission.\n"
            "Platform equivalent: generate for the approved Film model task."
        ),
        _schema(
            {"quote_id": {"type": "string"}, "approved_cost": {"type": "string"}},
            ["quote_id", "approved_cost"],
        ),
        approve_film_task,
    ),
    ToolSpec(
        "discard_film_estimate",
        (
            "Release one unsubmitted Film estimate so its task can be repriced.\n"
            "Args: quote_id is the required string from estimate_film_task.\n"
            "Returns: discarded.\n"
            'Example: {"quote_id": "returned-quote"}.\n'
            "Film is experimental. Does not cancel or change saved jobs.\n"
            "Platform equivalent: none; local approval handle."
        ),
        _schema({"quote_id": {"type": "string"}}, ["quote_id"]),
        discard_film_estimate,
    ),
    ToolSpec(
        "bind_film_upload",
        (
            "Associate one imported saved upload with a Film upload task without sending bytes.\n"
            "Args: production_id/task_id identify the loaded Film task; context_id, request_id and integer expected_revision come from list_reference_uploads. All required.\n"
            "Returns: production_id, task_id, upload_request_id and bound state.\n"
            'Example: {"production_id": "saved-production", "task_id": "reference", "context_id": "current", "request_id": "upload", "expected_revision": 4}.\n'
            "Film is experimental. Requires an unchanged imported upload in the selected scope. The association is durable and immutable; choose a new task name for a different source.\n"
            "Platform equivalent: none; local reference to an already imported asset."
        ),
        _schema(
            {
                "production_id": {"type": "string"},
                "task_id": {"type": "string"},
                "context_id": {"type": "string"},
                "request_id": {"type": "string"},
                "expected_revision": {"type": "integer", "minimum": 0},
            },
            ["production_id", "task_id", "context_id", "request_id", "expected_revision"],
        ),
        bind_film_upload,
    ),
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
            "Prepare explicit saved image/media/model import, material assignment, panorama World replacement, or session-local World restoration.\n"
            "Args:\n"
            "  - context_id: required string, current context from list_local_jobs.\n"
            "  - request_id: required string, saved local job identity.\n"
            "  - expected_revision: required nonnegative integer, observed saved revision.\n"
            "  - purpose: import (default), material, world, restore_world, mesh_edit or mesh_source; material uses the active mesh and saved unambiguous texture roles; World replacement requires asset_id.\n"
            "  - asset_id: optional saved asset ID; required for one MP4/WebM video, MP3/WAV/OGG audio strip or embedded GLB model. Omit for PNG/EXR image import.\n"
            "  - mesh_policy: REMESH (default) replaces geometry/UV/materials; UV replaces only active UVs; RETEXTURE preserves geometry/non-UV attributes and replaces all UV layers/materials. UV and RETEXTURE require exact topology/position matching. PARTS replaces source geometry with an empty mesh parent and 2 to 128 named parts from the selected static GLB; every mesh is a part, not an alternate variant. RIG preserves source geometry, UVs and materials and attaches matching weights and one rig with clips; it requires exact indexed geometry and rejects morphs/mesh animation.\n"
            "  - mesh_placement: WORLD (default) preserves imported scene positions; LOCAL uses imported positions in the object's local coordinates. No fitting is inferred.\n"
            "  - keep_original: boolean, default true; preserve an unselected original mesh copy. These mesh options apply to mesh_edit and mesh_source, which require asset_id. mesh_source requires exactly one captured input and its unchanged live export source; it ignores current selection and cannot restore authority after undo/load/restart.\n"
            "Returns: context_id, application_id, request_id, revision, reuse, scene, images or asset_id/kind/frame, cursor or World format, and note.\n"
            'Example: {"context_id": "from-list", "request_id": "from-list", "expected_revision": 8}.\n'
            "Show the destination, selected assets and media frame, model cursor, material target/slot/roles, World operation/format or mesh target/policy/placement/Keep original before apply_result_application. This makes no network request, spends no credits and imports nothing. Ready or confirmed rolled-back results use their original application claim. Completed results require a new local reuse approval; show reuse=true as another application, never another generation. Unfinished reuse blocks another attempt. Restoration applies to this session's most recent World assignment for this job.\n"
            "Platform equivalent: none; this captures a local Blender destination."
        ),
        _schema(
            {
                "context_id": {"type": "string"},
                "request_id": {"type": "string"},
                "expected_revision": {"type": "integer", "minimum": 0},
                "asset_id": {"type": "string"},
                "purpose": {
                    "type": "string",
                    "enum": [
                        "import",
                        "material",
                        "world",
                        "restore_world",
                        "mesh_edit",
                        "mesh_source",
                    ],
                },
                "mesh_policy": {
                    "type": "string",
                    "enum": ["REMESH", "UV", "RETEXTURE", "PARTS", "RIG"],
                },
                "mesh_placement": {"type": "string", "enum": ["WORLD", "LOCAL"]},
                "keep_original": {"type": "boolean"},
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
            "Returns: saved job status, revision, images, imported object names, materials and any delivery error.\n"
            'Example: {"context_id": "from-prepare", "application_id": "from-prepare"}.\n'
            "Call only after explicit destination approval. Verification runs off the main thread; application rechecks the captured scene/file revision and media frame or model cursor. Media uses a persistent private file; video omits embedded audio and scene timing is unchanged. Changed contexts or records require fresh review. World replacement or restoration changes only the approved scene World with guarded owned-data cleanup. Material assignment changes only the approved mesh slot to a new packed material; it preserves old materials and other slots. Mesh edit replaces only the captured target under its prepared policy, placement and Keep original choice. This performs no generation, downloads or file save. Never repeat an uncertain import; inspect the saved job.\n"
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
        "estimate_blockout",
        'Get the exact free estimate for the current scene\'s Blockout description or refinement. This reads the native Blockout fields and current plan; it does not generate or build geometry. Approve the exact returned cu_cost_exact separately. Args: action DESIGN or REFINE. Returns: quote_id, action, cu_cost_exact.\nExample: {"action": "DESIGN"}.\nPlatform equivalent: model_estimate for the Scenario LLM.',
        _schema({"action": {"type": "string", "enum": ["DESIGN", "REFINE"]}}, []),
        estimate_blockout,
        {"readOnlyHint": True},
    ),
    ToolSpec(
        "approve_blockout",
        'Spend the explicitly approved exact cost once for estimate_blockout. Args: quote_id and approved_cost. Inputs, current plan and origin must still match. Returns: request_id and state. The unchanged source scene receives a complete plan; no geometry is built automatically. Inspect list_local_jobs after failure or restart; never repeat an uncertain submission.\nExample: {"quote_id": "saved-quote", "approved_cost": "1.25"}.\nPlatform equivalent: model_generate after exact local approval.',
        _schema(
            {"quote_id": {"type": "string"}, "approved_cost": {"type": "string"}},
            ["quote_id", "approved_cost"],
        ),
        approve_blockout,
    ),
    ToolSpec(
        "prepare_blockout_plan",
        'Read and validate one saved Scenario LLM plan for the current scene without generating or building geometry. Args: context_id, request_id, expected_revision from list_local_jobs. Returns: review_id, state, scene, elements, groups, replaces_plan, error. Poll blockout_plan_status until ready, then review the destination and replacement before apply_blockout_plan.\nExample: {"context_id": "current-context", "request_id": "saved-request", "expected_revision": 3}.\nPlatform equivalent: job_get and asset_get, followed by local destination review.',
        _schema(
            {
                "context_id": {"type": "string"},
                "request_id": {"type": "string"},
                "expected_revision": {"type": "integer", "minimum": 0},
            },
            ["context_id", "request_id", "expected_revision"],
        ),
        prepare_blockout_plan,
        {"readOnlyHint": True},
    ),
    ToolSpec(
        "blockout_plan_status",
        'Inspect a prepared saved-plan review or discard its finished approval handle. Args: context_id, review_id, optional discard. Returns: state, scene, elements, groups, replaces_plan, error; discarded state when requested. Never generates or changes a scene.\nExample: {"context_id": "current-context", "review_id": "saved-review"}.\nPlatform equivalent: local saved-result review.',
        _schema(
            {
                "context_id": {"type": "string"},
                "review_id": {"type": "string"},
                "discard": {"type": "boolean"},
            },
            ["context_id", "review_id"],
        ),
        blockout_plan_status,
        {"readOnlyHint": True},
    ),
    ToolSpec(
        "apply_blockout_plan",
        'Use a ready saved-plan review once, after explicit destination and replacement approval. Args: context_id, review_id from prepare_blockout_plan. Returns: scene, elements, geometry_changed=false. Replaces only the unchanged destination scene stored Blockout plan; use native Build plan separately. Never spends or builds geometry.\nExample: {"context_id": "current-context", "review_id": "saved-review"}.\nPlatform equivalent: local plan application.',
        _schema(
            {"context_id": {"type": "string"}, "review_id": {"type": "string"}},
            ["context_id", "review_id"],
        ),
        apply_blockout_plan,
        {"destructiveHint": True},
    ),
    ToolSpec(
        "read_model_text",
        'Read one explicitly selected complete text asset from a successful saved model job, including after restart. Obtain context_id and revision from list_local_jobs and asset_id from job_status results. Returns: request_id, asset_id and bounded full text. Never spends, parses a plan, applies to the scene or substitutes a truncated preview. Args: context_id, request_id, expected_revision, asset_id.\nExample: {"context_id": "current-context", "request_id": "saved-request", "expected_revision": 3, "asset_id": "asset_text"}.\nPlatform equivalent: job_get and asset_get without generation.',
        _schema(
            {
                "context_id": {"type": "string"},
                "request_id": {"type": "string"},
                "expected_revision": {"type": "integer", "minimum": 0},
                "asset_id": {"type": "string"},
            },
            ["context_id", "request_id", "expected_revision", "asset_id"],
        ),
        read_model_text,
        {"readOnlyHint": True},
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
            "Returns: lane, models[] with id, name, description, capabilities and capability_status (empty, or the experimental note the picker shows). Retry after catalog loading completes.\n"
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
        "render_form",
        (
            "Inspect or prepare the native Render Image/Video form without submitting generation.\n"
            "Args:\n"
            "  - lane: required render_image or render_video.\n"
            "  - action: inspect (default), configure, prepare or remove.\n"
            "  - settings: configure edits model_id, look, capture_source (CAMERA/VIEWPORT), force_solid, spark_enabled, first_frame_path, use_first_frame, match_timeline, scalar parameters and style_assets (replaces unmarked styles). Optional parameters accept null to disable them. Choose a model from list_models. Remove references before changing models.\n"
            "  - role: prepare explicitly captures/uploads scene or uploads the selected first_frame file using the shared reference lifecycle. Repeated preparation refuses an occupied slot.\n"
            "  - reference_key: remove requires the exact key from a fresh inspection; detaches only that reference and does not cancel its saved upload. Inspect uncertain uploads before preparing another.\n"
            "Returns: current settings, references with reference_key/upload_id, preparation errors, ready_to_estimate and spark_required. Uploaded snapshots remain fixed when capture settings or the scene change.\n"
            'Example: {"lane":"render_image","action":"configure","settings":{"look":"copper sculpture","capture_source":"CAMERA"}}.\n'
            "Configure, prepare the scene and optional first frame, then inspect until ready. An empty automatic look needs estimate_prompt(action=GENERATE), separate approve_prompt spending approval and result delivery first. Finally use estimate_cost/generate with this lane/model and no parameters. File uploads and captures are explicit; no Python execution is required.\n"
            "Platform equivalent: upload_create and upload_complete for prepared snapshots; native form editing is local."
        ),
        _schema(
            {
                "lane": {"type": "string", "enum": ["render_image", "render_video"]},
                "action": {"type": "string", "enum": ["inspect", "configure", "prepare", "remove"]},
                "settings": {
                    "type": "object",
                    "properties": {
                        "model_id": {"type": "string"},
                        "look": {"type": "string"},
                        "capture_source": {"type": "string", "enum": ["CAMERA", "VIEWPORT"]},
                        "force_solid": {"type": "boolean"},
                        "spark_enabled": {"type": "boolean"},
                        "first_frame_path": {"type": "string"},
                        "use_first_frame": {"type": "boolean"},
                        "match_timeline": {"type": "boolean"},
                        "parameters": {"type": "object"},
                        "style_assets": {
                            "type": "array",
                            "items": {"type": "string"},
                            "maxItems": 15,
                        },
                    },
                    "additionalProperties": False,
                },
                "role": {"type": "string", "enum": ["scene", "first_frame"]},
                "reference_key": {"type": "string"},
            },
            ["lane"],
        ),
        render_form,
    ),
    ToolSpec(
        "estimate_cost",
        (
            "Get the exact CU cost with a dry run that spends no credits.\n"
            "Args:\n"
            "  - model_id: required string, the model identifier.\n"
            "  - parameters: optional object, model parameters including Scenario asset ids for file inputs. Omit for render lanes: prepare render_form first; pricing uses its native scene prompt and uploaded snapshots.\n"
            "  - lane: optional generation lane, default image. Every lane issues a single-use quote_id.\n"
            "Returns: model_id, lane, cu_cost, cu_cost_exact (decimal string), details, mesh_sources (local captured 3D input provenance) and quote_id bound to the lane, model, inputs, scene and credential context.\n"
            'Example: {"model_id": "model_example", "parameters": {"prompt": "a wooden crate"}}.\n'
            "Call before generate and show the cost to the user; an estimate does not authorize spending. Speech-to-text (audio2txt) and video-to-motion (video23d) models are experimental: they can be estimated and generated and their results stay in saved jobs, but motion and transcription handling is not accepted. prepare_result_application imports a returned GLB or media file by file type only.\n"
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
            "  - parameters: optional object, model parameters; file inputs take Scenario asset ids. Omit for render lanes, which rebuild the current render_form before checking the approved quote.\n"
            "  - quote_id: required, from estimate_cost with the same lane, model, inputs and scene.\n"
            "  - approved_cost: required, the exact cu_cost_exact string explicitly approved by the user.\n"
            "Returns: local_id, status, lane, model_id and note. All model jobs poll and download through the shared session. Only the Image lane imports verified PNG/EXR images automatically into the unchanged origin. Other lanes stop at saved ready results; their scene application remains separate. Render lanes require explicit render_form uploads and separate Prompt Spark approval when enabled with an empty look. No capture, upload or Spark submission occurs during generate.\n"
            'Example: {"lane": "image", "model_id": "model_example", "parameters": {"prompt": "a wooden crate"}, "quote_id": "quote_from_estimate", "approved_cost": "1.25"}.\n'
            "Do not call before estimate_cost and explicit spending approval. Do not repeat a timed-out submission. Use prepare_result_application for saved-result imports. Speech-to-text (audio2txt) and video-to-motion (video23d) models are experimental: their results stay in saved jobs, but motion and transcription handling is not accepted. prepare_result_application imports a returned GLB or media file by file type only.\n"
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
            "Returns: local_id, job_id, status, cu_cost, files, error and kind. Shared jobs also return revision, cu_cost_exact, results (asset_id, name, media_type, size, downloaded), actions, images and mesh_sources. actions name explicit follow-ups that never run automatically: cancel_prepared maps to the cancel_prepared_job tool; refresh, resume, cancel, recover_download and retry_receipt map to recover_local_job. Source records describe uploaded snapshots; they do not authorize finding or replacing an object after restart. Recovered jobs report kind=model; result media types remain available. Saved workflow jobs also return loop_steps, quote_may_understate and cost_warning: cu_cost_exact stays the approved quote, which may cover only one loop pass when quote_may_understate is true; loop_steps is null when this session did not record the definition's loop count. Unknown jobs raise ValueError.\n"
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
            "Wait for a generation while Blender remains responsive. Shared jobs return when delivery finishes, pauses for review, or the wait expires. Restarted shared jobs remain inspection-only until explicitly resumed. Prototype records return a local snapshot immediately with scoped recovery guidance.\n"
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
        "recover_cloud_job",
        (
            "Read one completed cloud model job into the selected credential-scoped saved jobs.\n"
            "Args:\n"
            "  - job_id: required string, the exact remote job ID from list_generations.\n"
            "  - model_id: required string, that row's model ID, verified against the fresh SDK response.\n"
            "Returns: context_id, request_id, job_id, revision, state, source and note. Existing saved records are preserved; repeated reads do not duplicate them. No local quote is invented and this never submits generation, downloads media or changes the scene.\n"
            'Example: {"job_id": "job_example", "model_id": "model_example"}.\n'
            "Inspect list_local_jobs next. Use recover_local_job to resume downloads, then prepare_result_application and explicit destination approval. Failed reads may be retried; uncertain generation submissions must not be repeated.\n"
            "Platform equivalent: job_get followed by local recovery storage."
        ),
        _schema(
            {"job_id": {"type": "string"}, "model_id": {"type": "string"}}, ["job_id", "model_id"]
        ),
        recover_cloud_job,
    ),
    ToolSpec(
        "import_result",
        (
            "Reject direct cached-file import and explain the required saved-result approval flow.\n"
            "Args:\n"
            "  - job_id: optional string, a Scenario job id or local_id returned by generate.\n"
            "  - id: optional string, compatibility alias; provide job_id or id. job_id takes precedence.\n"
            "Returns: an error directing the caller to explicit destination approval; no scene mutation.\n"
            'Example: {"job_id": "job_example"}.\n'
            "Use recover_cloud_job for a completed cloud row that is not yet saved. For saved jobs, use prepare_result_application and approve its exact destination. Cached prototype files cannot authorize application.\n"
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
            "Returns: generations[] with job_id, kind, model_id, prompt, status, cu_cost, cost_unavailable, workflow_id, workflow_job_id, empty local_files and local_request_ids. cu_cost is billing.cuCost plus cuCostDetails add-ons; a workflow run (kind=workflow) reports its own charge plus its steps' charges, or cu_cost null with cost_unavailable true when a step could not be read. Rows with workflow_job_id are steps of that run; its cu_cost, once not null, already includes them. Matching scoped saved jobs expose request IDs; inspect list_local_jobs and use explicit result approval. Use recover_cloud_job for unsaved completed model jobs. The first call may return an empty list and a note while history loads; call again after loading.\n"
            'Example: {"limit": 10}.\n'
            "Prefer job_status for a tracked active generation; this is not a fresh platform-wide history query on every call.\n"
            "Platform equivalent: jobs_list."
        ),
        _schema({"limit": {"type": "integer"}, "refresh": {"type": "boolean"}}),
        list_generations,
        {"readOnlyHint": True},
    ),
)
