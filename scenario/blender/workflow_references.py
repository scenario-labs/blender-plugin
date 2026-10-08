# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Scoped, confirmed Library references for saved workflow forms."""

import json
from dataclasses import dataclass

import bpy
from bpy.props import StringProperty

from ..core.schema.forms import append_file_reference
from . import reference_form, workflow_controls


@dataclass(frozen=True, eq=False)
class WorkflowReferenceApproval:
    asset_id: str
    label: str
    kind: str
    scene: object
    scene_name: str
    origin: object
    workflow_id: str
    workflow_label: str
    param_name: str
    input_label: str
    signature: str
    value: str
    scope: str


def _value(item):
    return None if not item.text.strip() else workflow_controls.input_value(item)


def _check_binding(item, scope):
    if item.asset_scope and (
        item.asset_scope != scope or item.asset_value != workflow_controls._json(_value(item))
    ):
        raise ValueError("The reference connection or value changed; clear it and choose again")


def choices(context, session, asset_id, label, kind):
    form = context.scene.scenario_workflow
    if not form.loaded_id or form.loaded_id != form.workflow_id or not form.schema_json:
        raise ValueError("Load a workflow in Workflows before choosing a reference")
    schema = json.loads(form.schema_json)
    scope = reference_form.scope_key(session.scope)
    bpy.context.view_layer.update()
    origin = session.capture(context.scene)
    signature = workflow_controls.signature(form)
    result = []
    for item in form.inputs:
        if item.kind not in {"file", "file_array"}:
            continue
        try:
            _check_binding(item, scope)
            value = append_file_reference(schema, item.name, asset_id, kind, _value(item))
        except ValueError:
            continue
        result.append(
            WorkflowReferenceApproval(
                asset_id,
                label,
                kind,
                context.scene,
                context.scene.name,
                origin,
                form.workflow_id,
                form.title,
                item.name,
                item.label,
                signature,
                value if item.kind == "file" else workflow_controls._json(value),
                scope,
            )
        )
    if not result:
        raise ValueError(
            "No matching workflow input; clear an occupied input or choose a matching asset"
        )
    return result


def attach(approval, session):
    """Called only after Library consumes its issued identity and validates origin."""
    form = approval.scene.scenario_workflow
    if (
        workflow_controls.signature(form) != approval.signature
        or reference_form.scope_key(session.scope) != approval.scope
    ):
        raise ValueError("The workflow inputs changed; review the reference again")
    item = form.inputs.get(approval.param_name)
    if item is None:
        raise ValueError("The workflow input is unavailable")
    _check_binding(item, approval.scope)
    value = append_file_reference(
        json.loads(form.schema_json), item.name, approval.asset_id, approval.kind, _value(item)
    )
    text = value if item.kind == "file" else workflow_controls._json(value)
    if text != approval.value:
        raise ValueError("The proposed reference value changed; review it again")
    previous = item.text, item.enabled, item.asset_scope, item.asset_value
    try:
        item.text, item.enabled = text, True
        item.asset_scope = approval.scope
        item.asset_value = workflow_controls._json(value)
    except Exception:
        item.text, item.enabled, item.asset_scope, item.asset_value = previous
        raise
    return item


class SCENARIO_OT_clear_workflow_reference(bpy.types.Operator):
    bl_idname = "scenario.clear_workflow_reference"
    bl_label = "Clear workflow reference"
    bl_description = "Confirm clearing this workflow file input and its saved reference binding"
    input_name: StringProperty(options={"HIDDEN", "SKIP_SAVE"})

    def invoke(self, context, event):
        form = context.scene.scenario_workflow
        item = form.inputs.get(self.input_name)
        if item is None or item.kind not in {"file", "file_array"}:
            return {"CANCELLED"}
        self._scene = context.scene
        self._signature = workflow_controls.signature(form)
        self._input_name = self.input_name
        return context.window_manager.invoke_confirm(
            self,
            event,
            message=(
                "Clear "
                + item.label
                + " from "
                + (form.title or "this workflow")
                + "? Unchecked inputs use workflow defaults."
            ),
        )

    def execute(self, context):
        scene = getattr(self, "_scene", None)
        if scene is None or scene != context.scene:
            self.report({"WARNING"}, "Review the original workflow input first")
            return {"CANCELLED"}
        form = scene.scenario_workflow
        if (
            self.input_name != self._input_name
            or workflow_controls.signature(form) != self._signature
        ):
            self.report({"WARNING"}, "The workflow form changed; review it again")
            return {"CANCELLED"}
        item = form.inputs.get(self._input_name)
        item.text = "" if item.kind == "file" else "[]"
        item.enabled = False
        item.asset_scope = item.asset_value = ""
        self._scene = None
        return {"FINISHED"}


def register():
    bpy.utils.register_class(SCENARIO_OT_clear_workflow_reference)


def unregister():
    bpy.utils.unregister_class(SCENARIO_OT_clear_workflow_reference)
