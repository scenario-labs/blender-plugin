# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Explicit Image reference upload controls with guarded main-thread attachment."""

import hashlib
import json
import textwrap
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path

import bpy
from bpy.app.handlers import persistent
from bpy.props import EnumProperty, IntProperty, StringProperty

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


def _form_snapshot(lane):
    # The pump may publish a request ID while staging finishes. It is progress
    # metadata, not a change to the selected source, scope or upload identity.
    return tuple(
        (
            ref.as_pointer(),
            reference_values(ref),
            ref.get(_MARKER),
            ref.get(_SCOPE),
            ref.get(_ASSET),
        )
        for ref in lane.references
    )


@dataclass(frozen=True)
class AttachmentApproval:
    identifier: str
    record: object
    origin: object
    scene: object
    scene_name: str
    model_id: str
    model_label: str
    param_name: str
    input_label: str
    reference: object
    reference_label: str
    form: tuple


def _owner(context_id):
    owner = runtime.ensure_reference_uploads()
    if runtime.state.job_context_id != context_id:
        raise ScenarioError(0, "The connection changed; inspect saved uploads again")
    return owner


def prepare_attachment(context, context_id, request_id, revision, index, param_name):
    from . import generation

    owner = _owner(context_id)
    if len(owner.attachments) >= 128:
        raise ScenarioError(0, "Close an existing attachment confirmation before opening another")
    record = owner.session.inspect_upload(request_id)
    if (
        record is None
        or record.revision != revision
        or record.state != UploadState.IMPORTED
        or record.intent.kind != "image"
    ):
        raise ScenarioError(0, "Choose a current imported image upload")
    lane = context.scene.scenario.lane_state("image")
    ref = None
    if index >= 0:
        if index >= len(lane.references):
            raise ScenarioError(0, "The selected reference no longer exists")
        ref = lane.references[index]
        param_name = ref.param_name
    schema = generation.schema_for(lane.model_id)
    spec = schema.by_name(param_name) if schema is not None else None
    if spec is None or not spec.is_file or (spec.kind or "image").lower() != "image":
        raise ScenarioError(0, "Choose an image input for this saved upload")
    matching = [item for item in lane.references if item.param_name == param_name]
    if ref is None and spec.ptype == "file" and matching:
        if len(matching) != 1:
            raise ScenarioError(0, "Choose the specific reference slot to replace")
        ref = matching[0]
    if ref is None and spec.max_length and len(matching) >= spec.max_length:
        raise ScenarioError(0, "This input is full; choose a reference slot to replace")
    bpy.context.view_layer.update()
    approval = AttachmentApproval(
        uuid.uuid4().hex,
        record,
        owner.session.capture(context.scene),
        context.scene,
        context.scene.name,
        lane.model_id,
        runtime.state.records[lane.model_id].name,
        param_name,
        spec.label,
        ref,
        (ref.label or Path(ref.filepath).name or ref.source)
        if ref is not None
        else "New reference",
        _form_snapshot(lane),
    )
    owner.attachments[approval.identifier] = approval
    return owner, approval


def apply_attachment(context_id, identifier):
    owner = _owner(context_id)
    approval = owner.attachments.pop(identifier, None)
    if approval is None:
        raise ScenarioError(0, "Review this saved upload and destination again")
    if owner.session.inspect_upload(approval.record.intent.request_id) != approval.record:
        raise ScenarioError(0, "The saved upload changed; review it again")
    owner.session.validate_destination(approval.origin)
    lane = approval.scene.scenario.lane_state("image")
    if lane.model_id != approval.model_id or _form_snapshot(lane) != approval.form:
        raise ScenarioError(0, "The model or references changed; review the destination again")
    ref = approval.reference
    added = ref is None
    if added:
        ref = lane.references.add()
    marker_keys = (_MARKER, _SCOPE, _REQUEST, _ASSET)
    previous = (
        reference_values(ref),
        ref.label,
        {key: ref[key] for key in marker_keys if key in ref},
    )
    try:
        if added:
            ref.param_name = approval.param_name
        old_marker = ref.get(_MARKER)
        ref[_MARKER] = uuid.uuid4().hex
        ref[_SCOPE] = scope_key(owner.session.scope)
        ref[_REQUEST] = approval.record.intent.request_id
        ref[_ASSET] = approval.record.asset_id
        ref.asset_id = approval.record.asset_id
        ref.source = "ASSET"
        ref.label = approval.record.intent.file_name + " (uploaded snapshot)"
        props.mark_estimate_dirty(lane)
        if old_marker in owner.forms:
            owner.forms[old_marker].attached = True
    except Exception:
        if added:
            lane.references.remove(len(lane.references) - 1)
        else:
            values, ref.label, markers = previous
            ref.param_name, ref.source, ref.filepath, ref.asset_id = values
            for key in marker_keys:
                if key in ref:
                    del ref[key]
            for key, value in markers.items():
                ref[key] = value
        raise
    return ref


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
    from .reference_uploads import UploadNotStarted, capture_upload

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
    if ref.source == "FILE" and not ref.filepath:
        raise ScenarioError(0, "Choose an image file first")
    token = uuid.uuid4().hex
    ref[_MARKER] = token
    ref[_SCOPE] = scope_key(owner.session.scope)
    binding = FormUpload(context.scene, ref, lane.model_id, reference_values(ref))
    owner.forms[token] = binding
    props.mark_estimate_dirty(lane)
    try:
        if ref.source == "FILE":
            binding.ticket = owner.start(context.scene, bpy.path.abspath(ref.filepath))
        else:
            binding.ticket = capture_upload(context, source=ref.source, camera=ref.asset_id or None)
    except UploadNotStarted:
        # The typed result proves no task was admitted. Keep uncertain or
        # asynchronous failures marked, even when their receipt is missing.
        del owner.forms[token]
        del ref[_MARKER]
        del ref[_SCOPE]
        raise
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
        if binding.scene != bpy.context.scene:
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
        op = layout.operator("scenario.inspect_uploads", text="Use saved upload", icon="VIEWZOOM")
        op.index = index
        return
    if ref.source == "ASSET":
        op = layout.operator("scenario.inspect_uploads", text="Inspect uploads", icon="VIEWZOOM")
        op.index = index
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
    op = row.operator("scenario.inspect_uploads", text="Inspect uploads", icon="VIEWZOOM")
    op.index = index


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
    bl_description = "Inspect saved uploads and choose an explicit recovery or attachment action"
    index: IntProperty(default=-1)
    param_name: StringProperty()
    page: IntProperty(default=0, min=0)

    def invoke(self, context, event):
        try:
            self._owner = runtime.ensure_reference_uploads()
            self._context_id = runtime.state.job_context_id
            self._records = self._owner.inspect_saved()
            self._errors = tuple(
                binding.error for binding in self._owner.forms.values() if binding.error
            )
        except Exception:
            self.report({"ERROR"}, "Could not inspect uploads; preserve local storage for recovery")
            return {"CANCELLED"}
        return context.window_manager.invoke_props_dialog(self, width=560)

    def draw(self, context):
        layout = self.layout
        for error in getattr(self, "_errors", ()):
            for line in textwrap.wrap(error, 70):
                layout.label(text=line, icon="ERROR")
        owner = getattr(self, "_owner", None)
        valid = (
            owner is not None and owner is runtime.state.reference_uploads and owner.session.active
        )
        if not valid:
            layout.label(text="The connection changed; close and reopen this view", icon="ERROR")
        records = getattr(self, "_records", ())
        if not records:
            layout.label(text="No saved uploads for this connection")
        navigation = layout.row(align=True)
        for label, page in (
            ("Previous", self.page - 1),
            ("Reload", self.page),
            ("Next", self.page + 1),
        ):
            row = navigation.row(align=True)
            row.enabled = valid and page >= 0 and (page == 0 or page * 6 < len(records))
            op = row.operator("scenario.inspect_uploads", text=label)
            op.page, op.index, op.param_name = max(0, page), self.index, self.param_name
        for snapshot in records[self.page * 6 : (self.page + 1) * 6]:
            record = owner.saved.get(snapshot.intent.request_id, snapshot) if valid else snapshot
            box = layout.box()
            for line in textwrap.wrap(
                f"{record.intent.file_name}: {record.state.value.replace('_', ' ')}", 65
            ):
                box.label(text=line)
            box.label(text=f"Request: {record.intent.request_id}")
            busy = valid and record.intent.request_id in owner._recovering
            if busy:
                box.label(text="Recovery in progress", icon="TIME")
            error = owner.recovery_errors.get(record.intent.request_id) if valid else None
            if error:
                box.label(text=error, icon="ERROR")
            row = box.row(align=True)
            row.enabled = valid and not busy
            actions = []
            if record.state == UploadState.PREPARED:
                actions.append(("cancel_prepared", "Cancel preparation"))
            elif record.state in {UploadState.IMPORTED, UploadState.FAILED, UploadState.CANCELED}:
                actions.append(("cleanup", "Clean staged copy"))
            elif record.upload_id:
                actions.append(("refresh", "Refresh status"))
            for action, label in actions:
                op = row.operator("scenario.recover_upload", text=label)
                op.context_id, op.request_id = self._context_id, record.intent.request_id
                op.expected_revision, op.action = record.revision, action
            if (
                record.state == UploadState.IMPORTED
                and record.intent.kind == "image"
                and (self.index >= 0 or self.param_name)
            ):
                op = row.operator(
                    "scenario.attach_saved_upload", text="Use this image", icon="IMAGE_DATA"
                )
                op.context_id, op.request_id = self._context_id, record.intent.request_id
                op.expected_revision, op.index, op.param_name = (
                    record.revision,
                    self.index,
                    self.param_name,
                )
        layout.label(text="Uncertain uploads are preserved; recovery never resends their bytes.")

    def execute(self, context):
        return {"FINISHED"}


class SCENARIO_OT_recover_upload(bpy.types.Operator):
    bl_idname = "scenario.recover_upload"
    bl_label = "Recover reference upload"
    bl_description = (
        "Refresh saved progress, cancel unclaimed preparation or remove its finished staged copy"
    )
    context_id: StringProperty(options={"HIDDEN"})
    request_id: StringProperty(options={"HIDDEN"})
    expected_revision: IntProperty(min=0, options={"HIDDEN"})
    action: EnumProperty(
        items=[
            ("refresh", "Refresh status", "Read known remote progress"),
            ("cancel_prepared", "Cancel preparation", "Cancel only an unclaimed local preparation"),
            ("cleanup", "Clean staged copy", "Delete only a verified finished private copy"),
        ]
    )

    def invoke(self, context, event):
        if self.action in {"cancel_prepared", "cleanup"}:
            return context.window_manager.invoke_confirm(self, event)
        return self.execute(context)

    def execute(self, context):
        try:
            _owner(self.context_id).recover(self.request_id, self.expected_revision, self.action)
        except Exception:
            self.report({"ERROR"}, "Recovery did not start; inspect the current saved state")
            return {"CANCELLED"}
        runtime.set_message("Recovery requested; the original file is preserved")
        return {"FINISHED"}


class SCENARIO_OT_attach_saved_upload(bpy.types.Operator):
    bl_idname = "scenario.attach_saved_upload"
    bl_label = "Use saved upload"
    bl_description = (
        "Review this imported image and the selected form destination before attaching it"
    )
    bl_options = {"UNDO"}
    context_id: StringProperty(options={"HIDDEN"})
    request_id: StringProperty(options={"HIDDEN"})
    expected_revision: IntProperty(min=0, options={"HIDDEN"})
    index: IntProperty(default=-1, options={"HIDDEN"})
    param_name: StringProperty(options={"HIDDEN"})
    approval_id: StringProperty(options={"HIDDEN", "SKIP_SAVE"})

    def invoke(self, context, event):
        try:
            self._owner, self._approval = prepare_attachment(
                context,
                self.context_id,
                self.request_id,
                self.expected_revision,
                self.index,
                self.param_name,
            )
            self.approval_id = self._approval.identifier
        except Exception:
            self.report(
                {"ERROR"},
                "Could not prepare attachment; inspect the upload and selected input again",
            )
            return {"CANCELLED"}
        return context.window_manager.invoke_props_dialog(self, width=500)

    def draw(self, context):
        approval = self._approval
        for text in (
            f"Scene: {approval.scene_name}",
            f"Model: {approval.model_label}",
            f"Input: {approval.input_label}",
            f"Reference: {approval.reference_label}",
            f"Image: {approval.record.intent.file_name}",
        ):
            for line in textwrap.wrap(text, 65):
                self.layout.label(text=line)
        self.layout.label(
            text="Replace the selected reference."
            if approval.reference is not None
            else "Add this image as a new reference."
        )
        self.layout.label(text="The next generation requires a fresh price and approval.")

    def cancel(self, context):
        owner = getattr(self, "_owner", None)
        if owner is not None:
            owner.attachments.pop(self.approval_id, None)

    def execute(self, context):
        try:
            apply_attachment(self.context_id, self.approval_id)
        except Exception:
            self.report(
                {"ERROR"},
                "Attachment was not completed; review the saved image and destination again",
            )
            return {"CANCELLED"}
        return {"FINISHED"}


CLASSES = (
    SCENARIO_OT_upload_image_reference,
    SCENARIO_OT_inspect_uploads,
    SCENARIO_OT_recover_upload,
    SCENARIO_OT_attach_saved_upload,
)


@persistent
def _history_post(_):
    # Undo restores RNA, not these Python bindings or consumed approvals. Keep
    # durable uploads and restored duplicate guards, then require fresh review.
    owner = runtime.state.reference_uploads
    if owner is not None:
        owner.forms.clear()
        owner.attachments.clear()


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    for handlers in (bpy.app.handlers.undo_post, bpy.app.handlers.redo_post):
        if _history_post not in handlers:
            handlers.append(_history_post)


def unregister():
    for handlers in (bpy.app.handlers.undo_post, bpy.app.handlers.redo_post):
        if _history_post in handlers:
            handlers.remove(_history_post)
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
