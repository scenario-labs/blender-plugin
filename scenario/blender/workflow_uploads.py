# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Explicit local-file and capture uploads into loaded workflow file inputs."""

import hashlib
import json
import os
import uuid
from dataclasses import dataclass
from pathlib import Path

import bpy
from bpy.props import EnumProperty, StringProperty

from ..core.api.errors import ScenarioError
from ..core.jobs.upload_store import UploadState
from ..core.schema.forms import is_file_field
from . import reference_form, runtime, workflow_controls, workflow_references

_MARKER = workflow_controls.UPLOAD_MARKER
_REQUEST = workflow_controls.UPLOAD_REQUEST
_KINDS = frozenset({"image", "audio", "video", "3d"})
# Capacity is checked with this placeholder before any upload starts; delivery
# validates the actual imported asset ID again.
_PROBE = "scenario-upload-capacity-probe"
_SOURCES = (
    ("FILE", "File", "Upload the chosen local file"),
    ("VIEWPORT", "Viewport", "Upload a still of the 3D viewport"),
    ("CAMERA", "Camera view", "Upload a still through the scene camera"),
    ("RENDER", "Render result", "Upload the current render result"),
    ("VIEWPORT_CLIP", "Viewport clip", "Upload a viewport clip of the preview or scene range"),
    ("CAMERA_CLIP", "Camera clip", "Upload a camera clip of the preview or scene range"),
    ("MESH", "Selected mesh", "Upload the selected meshes as one GLB"),
)
_LABELS = {source: label for source, label, _ in _SOURCES}
# Why a stopped upload that never reached Scenario released its input, by the
# state of its saved record (None: staging failed before any record was saved).
_NOTHING_SENT = {
    None: "The file could not be staged and nothing was uploaded; choose it again",
    UploadState.PREPARED: "The upload stopped before sending; nothing was uploaded",
    UploadState.CANCELED: "Preparation was canceled; nothing was uploaded",
}
_CAPTURES = {
    "image": (("VIEWPORT", "VIEW3D"), ("CAMERA", "CAMERA_DATA"), ("RENDER", "RENDER_RESULT")),
    "video": (("VIEWPORT_CLIP", "VIEW3D"), ("CAMERA_CLIP", "CAMERA_DATA")),
    "3d": (("MESH", "MESH_DATA"),),
}


def _field(form, name):
    try:
        schema = json.loads(form.schema_json or "{}")
    except ValueError:
        return None
    fields = schema.get("parameters") if isinstance(schema, dict) else None
    if not isinstance(fields, list):
        return None
    return next((x for x in fields if isinstance(x, dict) and x.get("name") == name), None)


def _allowed(field):
    allowed = field.get("allowedValues", field.get("allowed_values", field.get("enum")))
    return isinstance(allowed, list) and bool(allowed)


def _field_kind(field):
    if not isinstance(field, dict) or not is_file_field(field):
        return None
    kind = str(field.get("kind") or "image").lower()
    return kind if kind in _KINDS else None


def input_kind(form, name):
    """Return an uploadable kind from the saved schema, or None for other inputs."""
    return _field_kind(_field(form, name))


def _values(item):
    """The input's value fields; edits to them reject a late upload result."""
    return (
        item.text,
        item.enabled,
        item.options,
        item.choice if item.options else "",
        item.asset_scope,
        item.asset_value,
    )


def _digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def destination(scene, name):
    """Identify one unchanged workflow input for saved-upload dialogs."""
    form = scene.scenario_workflow
    item = form.inputs.get(name)
    value = (
        scene.as_pointer(),
        form.workflow_id,
        form.loaded_id,
        _digest(form.schema_json),
        name,
        _values(item) if item is not None else None,
        str(item.get(_MARKER, "")) if item is not None else None,
    )
    return _digest(json.dumps(value))


@dataclass
class WorkflowUpload:
    """Main-thread delivery authority for one upload into one workflow input."""

    scene: object
    workflow_id: str
    schema_sha256: str
    input_name: str
    kind: str
    values: tuple
    ticket: object = None
    error: str = ""
    attached: bool = False

    def item(self):
        return self.scene.scenario_workflow.inputs.get(self.input_name)

    def current(self, token):
        try:
            form = self.scene.scenario_workflow
            item = form.inputs.get(self.input_name)
            return (
                form.loaded_id == form.workflow_id == self.workflow_id
                and _digest(form.schema_json) == self.schema_sha256
                and item is not None
                and input_kind(form, self.input_name) == self.kind
                and item.get(_MARKER) == token
                and _values(item) == self.values
            )
        except (ReferenceError, RuntimeError):
            return False


def _binding(owner, scene, item):
    """Copied ID properties do not transfer ownership of an in-flight upload."""
    if owner is None:
        return None
    binding = owner.workflow_forms.get(item.get(_MARKER))
    try:
        if binding is not None and binding.scene == scene and binding.input_name == item.name:
            return binding
    except (ReferenceError, RuntimeError):
        return None
    return None


def _live(owner, scene, item):
    """Whether an in-memory delivery can still attach this input's upload."""
    binding = _binding(owner, scene, item)
    return (
        binding is not None
        and not binding.error
        and not (binding.ticket is not None and binding.ticket.error)
    )


def _release(owner, token, binding):
    if binding.error:
        owner.form_errors.append(binding.error)
    owner.workflow_forms.pop(token, None)


def _drop_binding(owner, scene, name, token):
    binding = owner.workflow_forms.get(token)
    try:
        if binding is not None and binding.scene == scene and binding.input_name == name:
            owner.workflow_forms.pop(token, None)
    except (ReferenceError, RuntimeError):
        owner.workflow_forms.pop(token, None)


def release(scene, name, token):
    """Stop delivering an admitted upload; its saved record remains inspectable."""
    owner = runtime.state.reference_uploads
    if owner is not None:
        _drop_binding(owner, scene, name, token)


def _remember(owner, scene, item, message):
    """Explain on the freed input, while it keeps these values, why nothing was sent.

    Undo and redo invalidate Python scene references but keep the scene's session
    UID, so the note follows history until another upload targets the input. Each
    input keeps only its latest note; notes on other inputs never evict it. The
    loaded workflow and schema are recorded too, so a same-named input of another
    workflow never shows it.
    """
    key = (scene.session_uid, item.name)
    owner.workflow_notices[key] = (_values(item), _workflow(scene), message)


def _workflow(scene):
    form = scene.scenario_workflow
    return form.loaded_id, _digest(form.schema_json)


def _forget(owner, scene, name):
    """Retire the note of an input once a newer upload may have been admitted."""
    owner.workflow_notices.pop((scene.session_uid, name), None)


def _notice(owner, scene, item):
    if owner is None:
        return ""
    values, workflow, message = owner.workflow_notices.get(
        (scene.session_uid, item.name), (None, None, "")
    )
    if values != _values(item) or workflow != _workflow(scene):
        return ""
    return message


def release_canceled(owner, record):
    """Free inputs still waiting for a canceled preparation; keep their values.

    Called on the main thread after explicit cancellation. A canceled record never
    sent anything. The marker is matched through this connection's ticket for its
    token, or through the saved request link when undo or a restart dropped it.
    """
    if record is None or record.state != UploadState.CANCELED:
        return
    request_id = record.intent.request_id
    for scene in tuple(bpy.data.scenes):
        for item in scene.scenario_workflow.inputs:
            token = item.get(_MARKER)
            if not token:
                continue
            ticket = owner.workflow_tickets.get(token)
            if ticket is not None:
                linked = ticket.record.intent.request_id if ticket.record is not None else None
            else:
                linked = item.get(_REQUEST)
            if linked != request_id:
                continue
            del item[_MARKER]
            if item.get(_REQUEST) == request_id:
                del item[_REQUEST]
            _drop_binding(owner, scene, item.name, token)
            owner.form_errors.append(_NOTHING_SENT[UploadState.CANCELED])
            _remember(owner, scene, item, _NOTHING_SENT[UploadState.CANCELED])


def stop_waiting(scene, name, token):
    """Release a stopped upload's marker; the values and saved upload are kept."""
    item = scene.scenario_workflow.inputs.get(name)
    if item is None or not token or item.get(_MARKER) != token:
        raise ScenarioError(0, "The input changed; review it again")
    owner = runtime.state.reference_uploads
    if _live(owner, scene, item):
        raise ScenarioError(0, "The upload is still running; wait for it or clear the input")
    for key in (_MARKER, _REQUEST):
        if key in item:
            del item[key]
    if owner is not None:
        _drop_binding(owner, scene, name, token)
    return item


@dataclass(frozen=True)
class UploadReview:
    """What the artist confirmed before any local content is sent."""

    scene: object
    input_name: str
    source: str
    filepath: str
    signature: str
    kind: str
    message: str
    # The connection and scope that receive the content; start() requires both.
    context_id: str = ""
    scope: str = ""


def review(context, name, source):
    """Validate one proposed upload without marking the input or starting work."""
    owner = runtime.ensure_reference_uploads()
    if not runtime.online():
        raise ScenarioError(0, "Allow Online Access before uploading a reference")
    form = context.scene.scenario_workflow
    if not form.loaded_id or form.loaded_id != form.workflow_id or not form.schema_json:
        raise ScenarioError(0, "Load the selected workflow's inputs first")
    item = form.inputs.get(name)
    if item is None or item.kind not in {"file", "file_array"}:
        raise ScenarioError(0, "Choose a workflow file input")
    if item.get(_MARKER):
        raise ScenarioError(
            0,
            "This input already has an upload; inspect its saved progress"
            if _live(owner, context.scene, item)
            else "This input has a saved upload; inspect it or stop waiting for it",
        )
    kind = input_kind(form, name)
    if kind is None:
        raise ScenarioError(
            0, "Upload supports image, audio, video and 3D inputs; use Library or an asset ID"
        )
    if item.options or _allowed(_field(form, name)):
        raise ScenarioError(0, "This input accepts only its listed asset IDs")
    if source not in reference_form._upload_sources(kind):
        raise ScenarioError(0, "Choose a local file or a supported snapshot for this input")
    filepath = item.upload_path if source == "FILE" else ""
    if source == "FILE":
        if not filepath:
            raise ScenarioError(0, f"Choose a file for this {kind} input first")
        # Refuse before marking: a missing file would otherwise fail only in
        # the worker, after the marker already blocks pricing.
        resolved = bpy.path.abspath(filepath)
        if not Path(resolved).is_file() or not os.access(resolved, os.R_OK):
            raise ScenarioError(0, f"Choose an existing, readable {kind} file")
    try:
        workflow_references._proposed(form, item, _PROBE, kind, scope(owner))
    except ValueError as error:
        raise ScenarioError(0, str(error)) from None
    if len(owner.forms) + len(owner.workflow_forms) >= 128:
        raise ScenarioError(0, "Reference upload capacity reached; inspect existing uploads")
    content = Path(filepath).name if filepath else _LABELS[source].lower()
    message = (
        f"Upload {content} to Scenario for {item.label} in {form.title or 'this workflow'}?"
        " Uploading does not generate; the workflow needs a fresh price."
    )
    return UploadReview(
        context.scene,
        name,
        source,
        filepath,
        workflow_controls.signature(form),
        kind,
        message,
        str(runtime.state.job_context_id or ""),
        scope(owner),
    )


def scope(owner):
    return reference_form.scope_key(owner.session.scope)


def start(context, reviewed):
    """Mark the input, then upload once through the shared reference lifecycle."""
    from .reference_uploads import UploadNotStarted, capture_upload

    if context.scene != reviewed.scene:
        raise ScenarioError(0, "Review the upload from its original scene")
    current = review(context, reviewed.input_name, reviewed.source)
    if (current.context_id, current.scope) != (reviewed.context_id, reviewed.scope):
        raise ScenarioError(0, "The connection changed; review the upload again")
    if (current.signature, current.filepath) != (reviewed.signature, reviewed.filepath):
        raise ScenarioError(0, "The workflow input changed; review the upload again")
    owner = runtime.ensure_reference_uploads()
    form = context.scene.scenario_workflow
    item = form.inputs[reviewed.input_name]
    token = uuid.uuid4().hex
    # Mark before capturing the origin so a second click cannot start another upload.
    item[_MARKER] = token
    binding = WorkflowUpload(
        context.scene,
        form.workflow_id,
        _digest(form.schema_json),
        item.name,
        current.kind,
        _values(item),
    )
    owner.workflow_forms[token] = binding
    try:
        if reviewed.source == "FILE":
            binding.ticket = owner.start(
                context.scene, bpy.path.abspath(reviewed.filepath), kind=current.kind
            )
        else:
            binding.ticket = capture_upload(context, source=reviewed.source)
    except UploadNotStarted:
        # The typed result proves no task was admitted; the input may be retried
        # and keeps any note about its earlier upload.
        del owner.workflow_forms[token]
        del item[_MARKER]
        raise
    except Exception:
        # Work may have been admitted, so an earlier note no longer applies.
        _forget(owner, context.scene, item.name)
        binding.error = "Upload did not start; inspect progress before choosing another reference"
        _release(owner, token, binding)
        raise ScenarioError(0, binding.error) from None
    # An earlier note described another upload; this one reports its own outcome.
    _forget(owner, context.scene, item.name)
    owner.workflow_tickets[token] = binding.ticket
    return binding


def deliver(owner):
    """Called only by the maintenance pump; never mutate properties during drawing."""
    for token, binding in tuple(owner.workflow_forms.items()):
        _deliver_binding(owner, token, binding)
        if binding.attached or binding.error:
            _release(owner, token, binding)


def _clear_own_marker(binding, token, record):
    """Remove only this upload's marker and request link; return the freed input."""
    try:
        item = binding.item()
        if item is None or item.get(_MARKER) != token:
            return None
        del item[_MARKER]
        if record is not None and item.get(_REQUEST) == record.intent.request_id:
            del item[_REQUEST]
        return item
    except (ReferenceError, RuntimeError):
        return None


def _deliver_binding(owner, token, binding):
    ticket = binding.ticket
    if binding.attached or binding.error or ticket is None:
        return
    record = ticket.record
    if ticket.sent_nothing:
        # ReferenceUploads proves this stopped upload never reached Scenario (failed
        # staging, an admission refused while still prepared, or cancellation), so
        # release this upload's own marker and keep existing values for a retry.
        binding.error = _NOTHING_SENT[record.state if record is not None else None]
        item = _clear_own_marker(binding, token, record)
        if item is not None:
            _remember(owner, binding.scene, item, binding.error)
        return
    if not binding.current(token):
        binding.error = "The scene, workflow or input changed; the upload was not attached"
        return
    item = binding.item()
    if record is not None and item.get(_REQUEST) != record.intent.request_id:
        # Link the marker to its saved record at first observation, even when the
        # upload then stops, so cancelling that record can still free the input.
        item[_REQUEST] = record.intent.request_id
    if ticket.error:
        binding.error = ticket.error
        return
    if record is not None and record.state in {UploadState.FAILED, UploadState.CANCELED}:
        binding.error = "Upload finished without an asset; inspect saved progress"
        return
    if binding.scene != bpy.context.scene:
        return  # Transient timer context pauses attachment.
    if record is None or record.state != UploadState.IMPORTED:
        return
    try:
        owner.session.validate_destination(record.intent.origin)
    except Exception:
        binding.error = "The scene changed; inspect the saved upload before attaching it"
        return
    try:
        workflow_references.bind_asset(
            binding.scene.scenario_workflow, item, record.asset_id, binding.kind, scope(owner)
        )
    except Exception:
        binding.error = "The workflow input cannot accept this upload; inspect the saved upload"
        return
    del item[_MARKER]
    binding.attached = True


@dataclass(frozen=True, eq=False)
class SavedWorkflowUpload:
    """Single-use approval to attach one imported saved upload to one input."""

    identifier: str
    record: object
    reference: object
    lane_name: str = reference_form.WORKFLOW_LANE

    @property
    def origin(self):
        return self.reference.origin


def prepare_saved(context, context_id, request_id, revision, name, *, destination_key=""):
    owner = reference_form._owner(context_id)
    if destination_key and destination_key != destination(context.scene, name):
        raise ScenarioError(0, "The destination changed; open saved uploads from the form again")
    if len(owner.attachments) >= 128:
        raise ScenarioError(0, "Close an existing attachment confirmation before opening another")
    record = owner.session.inspect_upload(request_id)
    if (
        record is None
        or record.revision != revision
        or record.state != UploadState.IMPORTED
        or record.intent.kind not in _KINDS
    ):
        raise ScenarioError(0, "Choose a current imported reference upload")
    form = context.scene.scenario_workflow
    if input_kind(form, name) != record.intent.kind:
        raise ScenarioError(0, "Choose a matching input type for this saved upload")
    if _allowed(_field(form, name)):
        raise ScenarioError(0, "This input accepts only its listed asset IDs")
    try:
        choices = workflow_references.choices(
            context,
            owner.session,
            record.asset_id,
            record.intent.file_name,
            record.intent.kind,
            param_name=name,
            replace_upload=True,
        )
    except ValueError as error:
        raise ScenarioError(0, str(error)) from None
    approval = SavedWorkflowUpload(uuid.uuid4().hex, record, choices[0])
    owner.attachments[approval.identifier] = approval
    return owner, approval


def apply_saved(owner, approval):
    """Attach after reference_form consumed the approval and rechecked its record/origin."""
    reference = approval.reference
    item = reference.scene.scenario_workflow.inputs.get(reference.param_name)
    token = item.get(_MARKER) if item is not None else None
    try:
        item = workflow_references.attach(reference, owner.session)
    except ValueError as error:
        raise ScenarioError(0, str(error)) from None
    if token:
        del item[_MARKER]
        release(reference.scene, reference.param_name, token)
    item[_REQUEST] = approval.record.intent.request_id
    return item


def summary(approval):
    reference = approval.reference
    return (
        f"Scene: {reference.scene_name}",
        f"Workflow: {reference.workflow_label}",
        f"Input: {reference.input_label}",
        f"File: {approval.record.intent.file_name}",
        "Add this uploaded asset to the input.",
        "The workflow then requires a fresh price and approval.",
    )


def draw(layout, scene, item, field):
    """Read-only upload controls for one workflow file input."""
    owner = runtime.state.reference_uploads
    if item.get(_MARKER):
        binding = _binding(owner, scene, item)
        live = _live(owner, scene, item)
        row = layout.row(align=True)
        if binding is None:
            row.label(text="Saved upload: inspect before continuing", icon="INFO")
        elif not live:
            row.label(text="Upload needs review", icon="ERROR")
        else:
            row.label(text="Uploading reference…", icon="TIME")
        op = row.operator("scenario.inspect_uploads", text="Inspect uploads", icon="VIEWZOOM")
        op.lane, op.param_name = reference_form.WORKFLOW_LANE, item.name
        if not live:
            # Nothing can attach automatically any more; free the input explicitly.
            op = row.operator("scenario.release_workflow_upload", text="Stop waiting", icon="X")
            op.input_name = item.name
        return
    notice = _notice(owner, scene, item)
    if notice:
        layout.label(text=notice, icon="INFO")
    # The caller passes the parsed field; reparse the schema only on a mismatch.
    if not isinstance(field, dict) or field.get("name") != item.name:
        field = _field(scene.scenario_workflow, item.name) or {}
    kind = _field_kind(field)
    if kind is None or item.options or _allowed(field):
        layout.label(text="Choose Library > Workflow, or enter an uploaded asset ID")
        return
    layout.label(text="Upload a file or snapshot, use Library, or enter an asset ID")
    row = layout.row(align=True)
    row.prop(item, "upload_path")
    op = row.operator("scenario.upload_workflow_input", text="Upload file", icon="EXPORT")
    op.input_name, op.source = item.name, "FILE"
    captures = _CAPTURES.get(kind, ())
    if captures:
        row = layout.row(align=True)
        for source, icon in captures:
            op = row.operator("scenario.upload_workflow_input", text=_LABELS[source], icon=icon)
            op.input_name, op.source = item.name, source
    op = layout.operator("scenario.inspect_uploads", text="Use saved upload", icon="VIEWZOOM")
    op.lane, op.param_name = reference_form.WORKFLOW_LANE, item.name


class SCENARIO_OT_upload_workflow_input(bpy.types.Operator):
    bl_idname = "scenario.upload_workflow_input"
    bl_label = "Upload workflow input"
    bl_description = (
        "Confirm uploading this file or snapshot to Scenario for one workflow input; "
        "it does not spend credits"
    )
    # The marker gets its own undo step, so undoing later edits keeps the guard.
    bl_options = {"UNDO"}
    input_name: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    source: EnumProperty(items=_SOURCES, default="FILE", options={"HIDDEN", "SKIP_SAVE"})

    @classmethod
    def poll(cls, context):
        from .operators import _network_poll

        return _network_poll(cls, context)

    def invoke(self, context, event):
        try:
            self._review = review(context, self.input_name, self.source)
        except ScenarioError as error:
            self.report({"ERROR"}, error.reason)
            return {"CANCELLED"}
        except Exception:
            self.report({"ERROR"}, "Upload could not be reviewed; check the workflow input")
            return {"CANCELLED"}
        return context.window_manager.invoke_confirm(
            self, event, message=self._review.message, confirm_text="Upload"
        )

    def execute(self, context):
        reviewed = getattr(self, "_review", None)
        self._review = None
        if reviewed is None or reviewed.input_name != self.input_name:
            self.report({"WARNING"}, "Review the workflow input upload first")
            return {"CANCELLED"}
        item = context.scene.scenario_workflow.inputs.get(self.input_name)
        before = item.get(_MARKER) if item is not None else None
        try:
            start(context, reviewed)
        except Exception as error:
            reason = (
                error.reason
                if isinstance(error, ScenarioError)
                else "Upload could not start; inspect saved uploads"
            )
            self.report({"ERROR"}, reason)
            # A failure after admission keeps the new marker. Finishing records its
            # undo step, so undoing a later edit keeps the guard.
            marked = item is not None and item.get(_MARKER) not in {None, before}
            return {"FINISHED"} if marked else {"CANCELLED"}
        return {"FINISHED"}


class SCENARIO_OT_release_workflow_upload(bpy.types.Operator):
    bl_idname = "scenario.release_workflow_upload"
    bl_label = "Stop waiting for upload"
    bl_description = (
        "Stop waiting for this input's stopped upload; its values stay and the upload "
        "stays in saved uploads"
    )
    bl_options = {"UNDO"}
    input_name: StringProperty(options={"HIDDEN", "SKIP_SAVE"})

    def invoke(self, context, event):
        form = context.scene.scenario_workflow
        item = form.inputs.get(self.input_name)
        token = item.get(_MARKER) if item is not None else None
        if not token or _live(runtime.state.reference_uploads, context.scene, item):
            self.report({"ERROR"}, "Only a stopped upload can be released; inspect uploads")
            return {"CANCELLED"}
        self._scene, self._token = context.scene, token
        return context.window_manager.invoke_confirm(
            self,
            event,
            message=(
                f"Stop waiting for the upload into {item.label} in "
                f"{form.title or 'this workflow'}? Its current values stay, and the upload "
                "stays in saved uploads."
            ),
            confirm_text="Stop waiting",
        )

    def execute(self, context):
        scene, token = getattr(self, "_scene", None), getattr(self, "_token", None)
        self._scene = self._token = None
        try:
            if scene is None or context.scene != scene:
                raise ScenarioError(0, "Review the input from its original scene")
            stop_waiting(scene, self.input_name, token)
        except ScenarioError as error:
            self.report({"ERROR"}, error.reason)
            return {"CANCELLED"}
        except Exception:
            self.report({"ERROR"}, "The input was not released; inspect saved uploads")
            return {"CANCELLED"}
        return {"FINISHED"}


_CLASSES = (SCENARIO_OT_upload_workflow_input, SCENARIO_OT_release_workflow_upload)


def register():
    for cls in _CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)
