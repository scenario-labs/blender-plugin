# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Bind render look preparation to explicitly uploaded image snapshots."""

import json

from ..core.api.errors import ScenarioError
from ..core.scene.render_prompt import SPARK_BRIEF
from . import generation, reference_form, render_references


def parameters(scene, lane_name):
    lane = scene.scenario.lane_state(lane_name)
    schema = generation.schema_for(lane.model_id)
    if schema is None:
        raise ScenarioError(0, "Load the render model before preparing its look")
    references = render_references.active_references(lane)
    if error := reference_form.scope_error(lane, references=references):
        raise ScenarioError(0, error)
    scene_ref = render_references.require_uploaded(lane_name, lane, schema, render_references.SCENE)
    if lane_name == "render_video":
        if not render_references.first_frame_enabled(lane):
            raise ScenarioError(0, "Upload and enable a first frame for video Prompt Spark")
        first = render_references.require_uploaded(
            lane_name, lane, schema, render_references.FIRST_FRAME
        )
        brief = (
            "Image 1 is the approved first frame of a 3D animation. Describe its materials, "
            "lighting, atmosphere, colour palette and rendering style for the whole clip. "
            "Describe only the look, never add, remove or move objects or change the camera."
        )
    else:
        first, brief = scene_ref, SPARK_BRIEF
    images = [first.asset_id]
    identity = []
    for ref in references:
        spec = schema.by_name(ref.param_name)
        if spec is None or not spec.is_file:
            raise ScenarioError(0, "The render reference input changed; review its attachments")
        if ref.source != "ASSET" or not ref.asset_id:
            raise ScenarioError(0, "Finish uploading render references before preparing the look")
        identity.append((ref.param_name, ref.asset_id, ref.get(render_references.ROLE, "")))
        if ref != first and (spec.kind or "image") == "image":
            images.append(ref.asset_id)
    if len(images) > 15:
        raise ScenarioError(0, "Prompt Spark accepts at most 15 image references")
    if len(images) > 1:
        brief += (
            " Other images are style references only: borrow their materials, palette and "
            "lighting, never their objects, text or composition."
        )
    if lane.prompt.strip():
        brief += " Refine this requested look while preserving its intent: " + lane.prompt
    payload = {
        "mode": "contextual-v2",
        "modelId": lane.model_id,
        "prompt": brief,
        "images": images,
        "numResults": 1,
    }
    key = json.dumps(
        {
            "payload": payload,
            "references": identity,
            "spark_enabled": lane.spark_enabled,
            "first_frame_enabled": render_references.first_frame_enabled(lane),
            "first_frame_path": lane.first_frame_path,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return payload, key


def request_price(scene, lane_name):
    """Automatic preparation only requests a price; submission still needs approval."""
    from . import runtime

    if lane_name not in {"render_image", "render_video"}:
        raise ScenarioError(0, "Automatic look preparation belongs to a render lane")
    lane = scene.scenario.lane_state(lane_name)
    if lane.prompt.strip() or not lane.spark_enabled:
        raise ScenarioError(0, "Only an empty render look with Spark enabled needs preparation")
    jobs = runtime.ensure_prompt_jobs()
    current = jobs.current(scene, lane_name)
    if current is None or current.phase == "DONE":
        jobs.quote(scene, lane_name, "GENERATE")
    elif current.phase == "ERROR":
        raise ScenarioError(0, "Inspect the Prompt Spark job or click New to request a fresh price")
