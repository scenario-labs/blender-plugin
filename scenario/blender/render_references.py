# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Explicit render input slots backed by the shared typed upload lifecycle."""

from ..core.api.errors import ScenarioError
from . import generation, props, reference_form, render_lanes

ROLE = reference_form.RENDER_ROLE
SCENE = "scene"
FIRST_FRAME = "first_frame"


def first_frame_enabled(lane):
    return bool(lane.use_first_frame and lane.first_frame_path)


def active_references(lane):
    """Order snapshots before style references; a disabled first frame is omitted."""
    references = [
        ref for ref in lane.references if ref.get(ROLE) != FIRST_FRAME or first_frame_enabled(lane)
    ]
    return sorted(references, key=lambda ref: {SCENE: 0, FIRST_FRAME: 1}.get(ref.get(ROLE), 2))


def slot(lane, role):
    return [(index, ref) for index, ref in enumerate(lane.references) if ref.get(ROLE) == role]


def target(lane_name, schema, role):
    if role == SCENE:
        return render_lanes.scene_spec(lane_name, schema)
    if role == FIRST_FRAME and lane_name == "render_video":
        return render_lanes.first_frame_spec(schema) or render_lanes.style_spec(schema)
    return None


def require_uploaded(lane_name, lane, schema, role):
    matches = slot(lane, role)
    label = "scene capture" if role == SCENE else "first frame"
    spec = target(lane_name, schema, role)
    if spec is None:
        raise ScenarioError(0, f"This model has no input for the {label}")
    if len(matches) != 1:
        raise ScenarioError(0, f"Prepare one {label} reference before requesting a price")
    if (
        spec.ptype == "file"
        and sum(ref.param_name == spec.name for ref in active_references(lane)) != 1
    ):
        raise ScenarioError(0, f"Keep only one reference in the {label} input")
    _, ref = matches[0]
    if ref.param_name != spec.name:
        raise ScenarioError(0, f"The model input changed; prepare the {label} again")
    if role == FIRST_FRAME and ref.filepath != lane.first_frame_path:
        raise ScenarioError(0, "The first frame changed; remove its old reference and upload again")
    if ref.source != "ASSET" or not ref.asset_id:
        raise ScenarioError(0, f"Finish uploading the {label} before requesting a price")
    return ref


def prepare(context, lane_name, role):
    if lane_name not in {"render_image", "render_video"}:
        raise ScenarioError(0, "Choose Render Image or Render Video")
    lane = context.scene.scenario.lane_state(lane_name)
    schema = generation.schema_for(lane.model_id)
    if schema is None:
        raise ScenarioError(0, "Load the selected model before preparing references")
    spec = target(lane_name, schema, role)
    if spec is None:
        raise ScenarioError(0, "Choose a model with a matching render input")
    if slot(lane, role):
        raise ScenarioError(0, "Inspect or remove the existing reference before preparing another")
    if role == FIRST_FRAME and not first_frame_enabled(lane):
        raise ScenarioError(0, "Choose and enable a first-frame image before uploading")
    existing = sum(ref.param_name == spec.name for ref in lane.references)
    limit = 1 if spec.ptype == "file" else spec.max_length
    if limit and existing >= limit:
        raise ScenarioError(
            0, "This input is full; remove a reference before preparing this snapshot"
        )
    index = len(lane.references)
    ref = lane.references.add()
    ref.param_name = spec.name
    ref[ROLE] = role
    if role == SCENE:
        ref.source = render_lanes.capture_source(lane, lane_name)
        ref.label = "Scene capture: " + (
            "camera" if lane.capture_source == "CAMERA" else "viewport"
        )
    else:
        ref.source, ref.filepath, ref.label = "FILE", lane.first_frame_path, "First frame"
    props.mark_estimate_dirty(lane)
    try:
        return reference_form.start(context, index, lane_name=lane_name)
    except Exception:
        if not ref.get(reference_form._MARKER):
            lane.references.remove(index)
        raise  # Admitted or uncertain uploads retain their marked slot.


def draw_slot(layout, lane_name, lane, schema, role):
    from . import panels

    matches = slot(lane, role)
    if matches:
        for index, ref in matches:
            panels.draw_reference_row(layout, lane, index, ref)
        if role == FIRST_FRAME and any(ref.filepath != lane.first_frame_path for _, ref in matches):
            layout.label(
                text="First frame changed: remove its old reference and upload again", icon="ERROR"
            )
        return
    row = layout.row()
    row.enabled = target(lane_name, schema, role) is not None
    op = row.operator(
        "scenario.prepare_render_reference",
        text="Capture and upload scene" if role == SCENE else "Upload first frame",
        icon="EXPORT",
    )
    op.lane, op.role = lane_name, role
