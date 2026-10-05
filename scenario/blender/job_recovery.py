# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Explicit shared-job recovery controls; drawing never changes stored jobs."""

import bpy
from bpy.props import EnumProperty, FloatVectorProperty, IntProperty, StringProperty

from ..core.api.errors import ScenarioError
from . import runtime
from .media_application import MEDIA_TYPES
from .model_application import MODEL_MEDIA_TYPE

LABELS = {
    "refresh": "Refresh status",
    "resume": "Resume download",
    "cancel": "Cancel generation",
    "recover_download": "Check interrupted download",
    "retry_receipt": "Save import receipt",
    "import_images": "Import saved images",
    "import_media": "Add media strip",
    "import_model": "Import static model",
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
    action: EnumProperty(
        items=[
            (key, label, label)
            for key, label in LABELS.items()
            if key not in {"import_images", "import_media", "import_model"}
        ]
    )

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


class SCENARIO_OT_import_saved_images(bpy.types.Operator):
    bl_idname = "scenario.import_saved_images"
    bl_label = "Import saved images"
    bl_description = (
        "Review and import verified saved images into this file without generating again"
    )

    context_id: StringProperty(options={"HIDDEN"})
    request_id: StringProperty(options={"HIDDEN"})
    expected_revision: IntProperty(min=0, options={"HIDDEN"})
    application_id: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    scene_name: StringProperty(options={"HIDDEN", "SKIP_SAVE"})

    def invoke(self, context, event):
        try:
            jobs, approval = runtime.prepare_image_application(
                self.context_id, self.request_id, self.expected_revision, context.scene
            )
            self._jobs = jobs
            self.application_id = approval.identifier
            self.scene_name = approval.scene_name
        except Exception:
            self.report({"ERROR"}, "Could not prepare the image import; inspect saved jobs again")
            return {"CANCELLED"}
        return context.window_manager.invoke_props_dialog(self, width=440)

    def draw(self, context):
        self.layout.label(text=f"Scene: {self.scene_name}", icon="SCENE_DATA")
        self.layout.label(text="Import and pack these saved images into the current file.")
        self.layout.label(text="Choose an image in the Image Editor after importing.")

    def cancel(self, context):
        jobs = getattr(self, "_jobs", None)
        if jobs is not None:
            jobs.discard_image_application(self.application_id)

    def execute(self, context):
        try:
            runtime.apply_saved_images(self.context_id, self.application_id)
        except Exception:
            self.report(
                {"ERROR"}, "Import was not started; review the saved images and destination again"
            )
            return {"CANCELLED"}
        runtime.set_message("Verifying saved images for the approved destination")
        return {"FINISHED"}


class SCENARIO_OT_import_saved_media(bpy.types.Operator):
    bl_idname = "scenario.import_saved_media"
    bl_label = "Add saved media strip"
    bl_description = "Review one verified video or sound result and its sequencer destination"

    context_id: StringProperty(options={"HIDDEN"})
    request_id: StringProperty(options={"HIDDEN"})
    expected_revision: IntProperty(min=0, options={"HIDDEN"})
    asset_id: StringProperty(options={"HIDDEN"})
    application_id: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    scene_name: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    destination_frame: IntProperty(options={"HIDDEN", "SKIP_SAVE"})
    media_kind: StringProperty(options={"HIDDEN", "SKIP_SAVE"})

    def invoke(self, context, event):
        try:
            jobs, approval = runtime.prepare_media_application(
                self.context_id,
                self.request_id,
                self.expected_revision,
                context.scene,
                self.asset_id,
            )
            self._jobs = jobs
            self.application_id, self.scene_name = approval.identifier, approval.scene_name
            self.destination_frame, self.media_kind = approval.frame, approval.kind
        except Exception:
            self.report({"ERROR"}, "Could not prepare media insertion; inspect the saved result")
            return {"CANCELLED"}
        return context.window_manager.invoke_props_dialog(self, width=480)

    def draw(self, context):
        self.layout.label(text=f"Scene: {self.scene_name}", icon="SCENE_DATA")
        self.layout.label(text=f"Add one {self.media_kind} strip at frame {self.destination_frame}")
        self.layout.label(text="Use an unused channel; keep scene timing unchanged.")
        if self.media_kind == "video":
            self.layout.label(text="Picture frames only; embedded audio is not added.")
        self.layout.label(text="Media remains in a local file needed by this blend.")

    def cancel(self, context):
        jobs = getattr(self, "_jobs", None)
        if jobs is not None:
            jobs.discard_image_application(self.application_id)

    def execute(self, context):
        try:
            runtime.apply_saved_result(self.context_id, self.application_id)
        except Exception:
            self.report({"ERROR"}, "Media insertion was not started; review its destination again")
            return {"CANCELLED"}
        runtime.set_message("Verifying saved media for the approved scene and frame")
        return {"FINISHED"}


class SCENARIO_OT_import_saved_model(bpy.types.Operator):
    bl_idname = "scenario.import_saved_model"
    bl_label = "Import saved static model"
    bl_description = "Review one saved static GLB model and its scene/cursor destination"

    context_id: StringProperty(options={"HIDDEN"})
    request_id: StringProperty(options={"HIDDEN"})
    expected_revision: IntProperty(min=0, options={"HIDDEN"})
    asset_id: StringProperty(options={"HIDDEN"})
    application_id: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    scene_name: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    destination_cursor: FloatVectorProperty(size=3, options={"HIDDEN", "SKIP_SAVE"})

    def invoke(self, context, event):
        try:
            jobs, approval = runtime.prepare_model_application(
                self.context_id,
                self.request_id,
                self.expected_revision,
                context.scene,
                self.asset_id,
            )
            self._jobs = jobs
            self.application_id, self.scene_name = approval.identifier, approval.scene_name
            self.destination_cursor = approval.cursor
        except Exception:
            self.report({"ERROR"}, "Could not prepare model import; inspect the saved result")
            return {"CANCELLED"}
        return context.window_manager.invoke_props_dialog(self, width=480)

    def draw(self, context):
        self.layout.label(text=f"Scene: {self.scene_name}", icon="SCENE_DATA")
        position = ", ".join(f"{value:.3f}" for value in self.destination_cursor)
        self.layout.label(text=f"Place model bottom at cursor: {position}")
        self.layout.label(text="Import one static GLB into a new group; pack its textures.")
        self.layout.label(text="Keep existing objects and selection unchanged.")
        self.layout.label(text="Rigged, animated and external-file GLBs are not supported.")

    def cancel(self, context):
        jobs = getattr(self, "_jobs", None)
        if jobs is not None:
            jobs.discard_image_application(self.application_id)

    def execute(self, context):
        try:
            runtime.apply_saved_result(self.context_id, self.application_id)
        except Exception:
            self.report({"ERROR"}, "Model import was not started; review its destination again")
            return {"CANCELLED"}
        runtime.set_message("Verifying saved model for the approved scene and cursor")
        return {"FINISHED"}


def draw_controls(layout, record):
    if not record.meta.get("shared_job"):
        return
    for action in record.meta.get("recovery_actions", ()):
        if action == "import_model":
            for index, asset_id in enumerate(record.asset_ids, 1):
                if record.asset_types.get(asset_id) != MODEL_MEDIA_TYPE:
                    continue
                operator = layout.operator(
                    "scenario.import_saved_model", text=f"Import static model ({index})"
                )
                operator.context_id, operator.request_id = (
                    runtime.state.job_context_id,
                    record.local_id,
                )
                operator.expected_revision, operator.asset_id = (
                    record.meta["saved_revision"],
                    asset_id,
                )
            continue
        if action == "import_media":
            for index, asset_id in enumerate(record.asset_ids, 1):
                media = MEDIA_TYPES.get(record.asset_types.get(asset_id))
                if media is None:
                    continue
                operator = layout.operator(
                    "scenario.import_saved_media", text=f"Add {media[0]} strip ({index})"
                )
                operator.context_id, operator.request_id = (
                    runtime.state.job_context_id,
                    record.local_id,
                )
                operator.expected_revision, operator.asset_id = (
                    record.meta["saved_revision"],
                    asset_id,
                )
            continue
        operator = layout.operator(
            "scenario.import_saved_images" if action == "import_images" else "scenario.recover_job",
            text=LABELS[action],
        )
        operator.context_id = runtime.state.job_context_id
        operator.request_id = record.local_id
        operator.expected_revision = record.meta["saved_revision"]
        if action != "import_images":
            operator.action = action
    if record.meta.get("saved_state") in ("ready", "apply_failed"):
        layout.label(text="Downloaded result awaits application review", icon="INFO")


CLASSES = (
    SCENARIO_OT_inspect_saved_jobs,
    SCENARIO_OT_recover_job,
    SCENARIO_OT_import_saved_images,
    SCENARIO_OT_import_saved_media,
    SCENARIO_OT_import_saved_model,
)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
