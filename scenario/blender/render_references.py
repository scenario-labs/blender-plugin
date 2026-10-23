# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Explicit render input slots backed by the shared typed upload lifecycle."""

from ..core.api.errors import ScenarioError
from . import generation, props, reference_form, render_lanes, runtime

ROLE = reference_form.RENDER_ROLE
SCENE = "scene"
FIRST_FRAME = "first_frame"
# The price waits for these; each says what to do or what is under way, in one line.
CAPTURE_SCENE = "Capture the scene to see the price"
NEEDS_FIRST_FRAME = "Upload the first frame to see the price"
UPLOADING_SCENE = "Uploading the scene capture; the price follows"
UPLOADING_FIRST_FRAME = "Uploading the first frame; the price follows"
UPLOADING = "uploading"
READY = "ready"
REVIEW = "review"
ALL = "all"  # the operator's role for the whole form: the scene, with the first frame it uses


def first_frame_enabled(lane):
    """A chosen local file, or a first-frame slot that already holds a Scenario asset."""
    return bool(lane.use_first_frame and (lane.first_frame_path or asset_first_frame(lane)))


def asset_first_frame(lane):
    """A role-tagged first frame with an asset but no local file, such as a saved result.

    Such a slot keeps no path in the blend. Choosing a local file afterwards
    makes `require_uploaded` ask for the old slot's removal, as for any change.
    """
    return any(
        ref.source == "ASSET" and ref.asset_id and not ref.filepath
        for _, ref in slot(lane, FIRST_FRAME)
    )


def active_references(lane):
    """Order snapshots before style references; a disabled first frame is omitted."""
    references = [
        ref for ref in lane.references if ref.get(ROLE) != FIRST_FRAME or first_frame_enabled(lane)
    ]
    return sorted(references, key=lambda ref: {SCENE: 0, FIRST_FRAME: 1}.get(ref.get(ROLE), 2))


def slot(lane, role):
    return [(index, ref) for index, ref in enumerate(lane.references) if ref.get(ROLE) == role]


def slot_state(lane, role):
    """The slot's upload, read-only: None without one, READY once an asset is attached,
    UPLOADING while this session's upload runs, REVIEW when it stopped or belongs to a saved upload."""
    matches = slot(lane, role)
    if not matches:
        return None
    ref = matches[0][1]
    if ref.source == "ASSET" and ref.asset_id:
        return READY
    binding = reference_form._binding(runtime.state.reference_uploads, ref)
    if binding is None or binding.error or (binding.ticket is not None and binding.ticket.error):
        return REVIEW
    return UPLOADING


def uploading_note(lane):
    """What an upload under way for this form says in place of a price, or ""; read-only."""
    if slot_state(lane, SCENE) == UPLOADING:
        return UPLOADING_SCENE
    if slot_state(lane, FIRST_FRAME) == UPLOADING and first_frame_enabled(lane):
        return UPLOADING_FIRST_FRAME
    return ""


def chip(lane):
    """The composer's capture chip for a render form: (label, wait), read-only.

    `wait` says why a click does nothing now (offline, no credentials, an upload running or in
    need of review), else "". An uploaded capture is offered again as Recapture.
    """
    state = slot_state(lane, SCENE)
    label = "Recapture" if state == READY else "Capture"
    if not runtime.online():
        return label, "Allow Online Access to capture the scene"
    if not runtime.credentials().valid:
        return label, "Set up credentials to capture the scene"
    if note := uploading_note(lane):
        return "Uploading...", note
    if state == REVIEW or (slot_state(lane, FIRST_FRAME) == REVIEW and first_frame_enabled(lane)):
        return label, "An upload needs review: open Settings to inspect it"
    return label, ""


def target(lane_name, schema, role):
    if role == SCENE:
        return render_lanes.scene_spec(lane_name, schema)
    if role == FIRST_FRAME and lane_name == "render_video":
        return render_lanes.first_frame_target(schema)
    return None


def require_uploaded(lane_name, lane, schema, role):
    matches = slot(lane, role)
    label = "scene capture" if role == SCENE else "first frame"
    spec = target(lane_name, schema, role)
    if spec is None:
        raise ScenarioError(0, f"This model has no input for the {label}")
    if not matches:
        raise ScenarioError(0, CAPTURE_SCENE if role == SCENE else NEEDS_FIRST_FRAME)
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


def _detach(lane, index):
    """Take a slot out of the form, keeping what it takes to put it back."""
    ref = lane.references[index]
    saved = (
        (ref.param_name, ref.source, ref.filepath, ref.asset_id, ref.label),
        {key: ref[key] for key in ref.keys()},
    )
    lane.references.remove(index)
    return saved


def _reattach(lane, saved):
    values, markers = saved
    ref = lane.references.add()
    ref.param_name, ref.source, ref.filepath, ref.asset_id, ref.label = values
    for key, value in markers.items():
        ref[key] = value
    props.mark_estimate_dirty(lane)


def capture_form(context, lane_name):
    """Capture the scene and upload it, with the first frame the form uses, in one action.

    A scene capture already uploaded is replaced, as removing it and capturing again would;
    one still uploading, or one whose upload needs review, is never replaced. Nothing is
    priced or submitted here: each upload that attaches marks the form dirty, and the pump
    prices the shown form once everything it needs is in, so the Generate button shows the
    exact price without another click. Whatever fails before the capture leaves the form as
    it was.
    """
    if lane_name not in {"render_image", "render_video"}:
        raise ScenarioError(0, "Choose Render Image or Render Video")
    lane = context.scene.scenario.lane_state(lane_name)
    schema = generation.schema_for(lane.model_id)
    if schema is None:
        raise ScenarioError(0, "Load the selected model before capturing the scene")
    if target(lane_name, schema, SCENE) is None:
        raise ScenarioError(0, "Choose a model with a matching render input")
    if not runtime.online():
        raise ScenarioError(0, "Allow Online Access before uploading a reference")
    from . import capture

    source = render_lanes.capture_source(lane, lane_name)
    if reason := capture.unavailable_reason(context, source):
        raise ScenarioError(0, reason)
    if slot(lane, SCENE) and slot_state(lane, SCENE) != READY:
        raise ScenarioError(0, "The scene capture has an upload in progress; inspect it first")
    # The first frame goes first: its file uploads on a worker while the capture runs here.
    if lane_name == "render_video" and first_frame_enabled(lane) and lane.first_frame_path:
        if target(lane_name, schema, FIRST_FRAME) is None:
            raise ScenarioError(
                0, "This model has no input for the first frame; turn it off or pick another model"
            )
        frames = slot(lane, FIRST_FRAME)
        if not frames:
            prepare(context, lane_name, FIRST_FRAME)
        elif frames[0][1].filepath != lane.first_frame_path:
            if slot_state(lane, FIRST_FRAME) != READY:
                raise ScenarioError(
                    0, "The first frame has an upload in progress; inspect it first"
                )
            _detach(lane, frames[0][0])  # a changed file replaces the old one, as asked
            prepare(context, lane_name, FIRST_FRAME)
    old = slot(lane, SCENE)  # after the first frame: its slot may have moved this one
    saved = _detach(lane, old[0][0]) if old else None
    try:
        return prepare(context, lane_name, SCENE)
    except Exception:
        if saved is not None and not slot(lane, SCENE):
            _reattach(lane, saved)
        raise


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
        if role == SCENE and slot_state(lane, SCENE) == READY:
            # A new capture of the scene as it is now, replacing this snapshot.
            row = layout.row()
            op = row.operator(
                "scenario.prepare_render_reference", text="Capture again", icon="EXPORT"
            )
            op.lane, op.role = lane_name, ALL
        return
    row = layout.row()
    row.enabled = target(lane_name, schema, role) is not None
    op = row.operator(
        "scenario.prepare_render_reference",
        text="Capture and upload scene" if role == SCENE else "Upload first frame",
        icon="EXPORT",
    )
    op.lane, op.role = lane_name, ALL if role == SCENE else role
