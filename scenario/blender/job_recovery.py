# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Explicit shared-job recovery controls; drawing never changes stored jobs."""

import bpy
from bpy.props import EnumProperty, IntProperty, StringProperty

from ..core.api.errors import ScenarioError
from . import runtime

LABELS = {
    "refresh": "Refresh status",
    "resume": "Resume download",
    "cancel": "Cancel generation",
    "recover_download": "Check interrupted download",
    "retry_receipt": "Save import receipt",
}


class SCENARIO_OT_inspect_saved_jobs(bpy.types.Operator):
    bl_idname = "scenario.inspect_saved_jobs"
    bl_label = "Inspect saved jobs"
    bl_description = "Show this connection's saved jobs without resubmitting or applying results"

    def execute(self, context):
        try:
            runtime.inspect_model_jobs()
        except Exception:
            self.report({"ERROR"}, "Could not inspect saved jobs; preserve storage for recovery")
            return {"CANCELLED"}
        return {"FINISHED"}


class SCENARIO_OT_recover_job(bpy.types.Operator):
    bl_idname = "scenario.recover_job"
    bl_label = "Recover saved job"
    bl_description = "Perform the selected recovery action without submitting a new generation"

    context_id: StringProperty(options={"HIDDEN"})
    request_id: StringProperty(options={"HIDDEN"})
    expected_revision: IntProperty(min=0, options={"HIDDEN"})
    action: EnumProperty(items=[(key, label, label) for key, label in LABELS.items()])

    def invoke(self, context, event):
        if self.action == "cancel":
            return context.window_manager.invoke_confirm(self, event)
        return self.execute(context)

    def execute(self, context):
        try:
            runtime.control_model_job(
                self.context_id, self.request_id, self.expected_revision, self.action
            )
        except ScenarioError as error:
            self.report({"ERROR"}, error.reason)
            return {"CANCELLED"}
        except Exception:
            self.report({"ERROR"}, "Recovery did not complete; inspect the saved job again")
            return {"CANCELLED"}
        runtime.set_message("Recovery requested; no new generation was submitted")
        return {"FINISHED"}


def draw_controls(layout, record):
    if not record.meta.get("shared_job"):
        return
    for action in record.meta.get("recovery_actions", ()):
        operator = layout.operator("scenario.recover_job", text=LABELS[action])
        operator.context_id = runtime.state.job_context_id
        operator.request_id = record.local_id
        operator.expected_revision = record.meta["saved_revision"]
        operator.action = action
    if record.meta.get("saved_state") in ("ready", "apply_failed"):
        layout.label(text="Downloaded result awaits application review", icon="INFO")


CLASSES = (SCENARIO_OT_inspect_saved_jobs, SCENARIO_OT_recover_job)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
