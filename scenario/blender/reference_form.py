# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Explicit Image reference upload controls with guarded main-thread attachment."""

import hashlib
import json
import textwrap
import uuid
from dataclasses import asdict, dataclass

import bpy
from bpy.props import IntProperty

from ..core.api.errors import ScenarioError
from ..core.jobs.upload_store import UploadState
from . import props, runtime

_MARKER = "_scenario_reference_upload"
_SCOPE = "_scenario_reference_scope"
_REQUEST = "_scenario_reference_request"
_ASSET = "_scenario_reference_asset"


def scope_key(scope):
    return hashlib.sha256(json.dumps(asdict(scope), sort_keys=True).encode()).hexdigest()


def reference_values(ref):
    return ref.param_name, ref.source, ref.filepath, ref.asset_id


@dataclass
class FormUpload:
    scene: object
    reference: object
    model_id: str
    values: tuple
    ticket: object = None
    error: str = ""
    attached: bool = False

    def current(self, token):
        try:
            if self.scene != bpy.context.scene:
                return False
            lane = self.scene.scenario.lane_state("image")
            return (
                lane.model_id == self.model_id
                and any(ref == self.reference for ref in lane.references)
                and self.reference.get(_MARKER) == token
                and reference_values(self.reference) == self.values
            )
        except (ReferenceError, RuntimeError):
            return False


def start(context, index):
    from . import generation
    from .reference_uploads import capture_upload

    owner = runtime.ensure_reference_uploads()
    lane = context.scene.scenario.lane_state("image")
    if not 0 <= index < len(lane.references):
        raise ScenarioError(0, "Select a reference to upload")
    ref = lane.references[index]
    if ref.get(_MARKER):
        raise ScenarioError(0, "This reference already has an upload; inspect its saved progress")
    schema = generation.schema_for(lane.model_id)
    spec = schema.by_name(ref.param_name) if schema is not None else None
    if spec is None or not spec.is_file or (spec.kind or "image").lower() != "image":
        raise ScenarioError(0, "Choose an image input before uploading")
    if ref.source not in {"FILE", "VIEWPORT", "CAMERA", "RENDER"}:
        raise ScenarioError(0, "Choose a local image, viewport, camera or render result")
    token = uuid.uuid4().hex
    ref[_MARKER] = token
    ref[_SCOPE] = scope_key(owner.session.scope)
    binding = FormUpload(context.scene, ref, lane.model_id, reference_values(ref))
    owner.forms[token] = binding
    props.mark_estimate_dirty(lane)
    try:
        if ref.source == "FILE":
            if not ref.filepath:
                raise ScenarioError(0, "Choose an image file first")
            binding.ticket = owner.start(context.scene, bpy.path.abspath(ref.filepath))
        else:
            binding.ticket = capture_upload(context, source=ref.source, camera=ref.asset_id or None)
    except Exception:
        binding.error = "Upload did not start; inspect progress before choosing another reference"
        raise ScenarioError(0, binding.error) from None
    return binding


def deliver(owner):
    """Called only by the maintenance pump; never mutate properties during drawing."""
    for token, binding in tuple(owner.forms.items()):
        ticket = binding.ticket
        if binding.attached or binding.error or ticket is None:
            continue
        if not binding.current(token):
            binding.error = "The scene, model or reference changed; the upload was not attached"
            continue
        if ticket.record is not None:
            binding.reference[_REQUEST] = ticket.record.intent.request_id
        if ticket.error:
            binding.error = ticket.error
            continue
        if ticket.record is None or ticket.record.state != UploadState.IMPORTED:
            continue
        try:
            owner.session.validate_destination(ticket.record.intent.origin)
        except Exception:
            binding.error = "The scene changed; inspect the saved upload before attaching it"
            continue
        ref = binding.reference
        ref.asset_id = ticket.record.asset_id
        ref[_ASSET] = ticket.record.asset_id
        ref.source = "ASSET"
        ref.label = (ref.label or "Reference") + " (uploaded snapshot)"
        binding.attached = True
        props.mark_estimate_dirty(binding.scene.scenario.lane_state("image"))


def scope_error(lane_state):
    """Persisted uploaded asset IDs may only be quoted in their selected scope."""
    for ref in lane_state.references:
        if ref.source != "ASSET" or not ref.get(_SCOPE):
            continue
        store = runtime.state.job_store
        if (
            store is None
            or ref.get(_SCOPE) != scope_key(store.scope)
            or ref.asset_id != ref.get(_ASSET)
        ):
            return "This uploaded reference belongs to another connection or was edited; choose it again"
    return None


def draw(layout, lane_state, index, ref):
    if props.lane_of(lane_state) != "image":
        return
    marker = ref.get(_MARKER)
    if not marker:
        if ref.source in {"FILE", "VIEWPORT", "CAMERA", "RENDER"}:
            from . import generation

            schema = generation.schema_for(lane_state.model_id)
            spec = schema.by_name(ref.param_name) if schema is not None else None
            if spec is None or (spec.kind or "image").lower() != "image":
                return
            op = layout.operator(
                "scenario.upload_image_reference", text="Upload reference", icon="EXPORT"
            )
            op.index = index
        return
    if ref.source == "ASSET":
        return
    owner = runtime.state.reference_uploads
    binding = owner.forms.get(marker) if owner is not None else None
    row = layout.row(align=True)
    if binding is None:
        row.label(text="Saved upload: inspect before continuing", icon="INFO")
    elif binding.error or (binding.ticket is not None and binding.ticket.error):
        row.label(text="Upload needs review", icon="ERROR")
    else:
        row.label(text="Uploading reference…", icon="TIME")
    row.operator("scenario.inspect_uploads", text="Inspect uploads", icon="VIEWZOOM")


class SCENARIO_OT_upload_image_reference(bpy.types.Operator):
    bl_idname = "scenario.upload_image_reference"
    bl_label = "Upload reference"
    bl_description = "Upload this image snapshot to Scenario before requesting its generation price"
    index: IntProperty(min=0)

    @classmethod
    def poll(cls, context):
        from .operators import _network_poll

        return _network_poll(cls, context)

    def execute(self, context):
        try:
            start(context, self.index)
        except ScenarioError as error:
            self.report({"ERROR"}, error.reason)
            return {"CANCELLED"}
        except Exception:
            self.report({"ERROR"}, "Upload could not start; inspect saved uploads")
            return {"CANCELLED"}
        return {"FINISHED"}


class SCENARIO_OT_inspect_uploads(bpy.types.Operator):
    bl_idname = "scenario.inspect_uploads"
    bl_label = "Saved reference uploads"
    bl_description = "Inspect saved reference uploads without sending bytes or repeating requests"

    def invoke(self, context, event):
        try:
            owner = runtime.ensure_reference_uploads()
            self._records = tuple(item.record for item in owner.session.upload_recovery_plan())
            self._errors = tuple(binding.error for binding in owner.forms.values() if binding.error)
        except Exception:
            self.report({"ERROR"}, "Could not inspect uploads; preserve local storage for recovery")
            return {"CANCELLED"}
        return context.window_manager.invoke_props_dialog(self, width=560)

    def draw(self, context):
        layout = self.layout
        for error in getattr(self, "_errors", ()):
            for line in textwrap.wrap(error, 70):
                layout.label(text=line, icon="ERROR")
        records = getattr(self, "_records", ())
        if not records:
            layout.label(text="No saved uploads for this connection")
        for record in records:
            box = layout.box()
            box.label(text=f"{record.intent.file_name}: {record.state.value.replace('_', ' ')}")
            box.label(text=f"Request: {record.intent.request_id}")
            if record.asset_id:
                op = box.operator(
                    "scenario.copy_text", text="Copy uploaded asset ID", icon="COPYDOWN"
                )
                op.text = record.asset_id
        layout.label(text="Uncertain uploads are preserved and never sent again automatically.")

    def execute(self, context):
        return {"FINISHED"}


CLASSES = (SCENARIO_OT_upload_image_reference, SCENARIO_OT_inspect_uploads)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
