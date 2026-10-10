# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Explicit shared-job recovery controls; drawing never changes stored jobs."""

import bpy
from bpy.props import BoolProperty, EnumProperty, FloatVectorProperty, IntProperty, StringProperty

from ..core.api.errors import ScenarioError
from ..core.scene.panorama import WORLD_MEDIA_TYPES, describe_world_media
from ..core.ui import saved_job_actions
from . import runtime
from .media_application import MEDIA_TYPES
from .model_application import MODEL_MEDIA_TYPE

# Saved media types offered per application; describe() owns no media policy.
RESULT_TYPES = saved_job_actions.ResultTypes(
    model=MODEL_MEDIA_TYPE,
    media={media_type: value[0] for media_type, value in MEDIA_TYPES.items()},
    world=WORLD_MEDIA_TYPES,
)


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


def cancel_prepared_message(request_id):
    """Describe a local discard; reading the saved intent never changes it."""
    message = "Cancel this unsent request locally; nothing is sent to Scenario."
    store = runtime.state.job_store
    try:
        record = store.get(request_id) if store is not None else None
    except Exception:
        record = None
    if record is not None and record.intent.film_task is not None:
        # A canceled record still reserves its Film task identity.
        message += " A Film task stays reserved; use a new take name to try again."
    return message


class SCENARIO_OT_recover_job(bpy.types.Operator):
    bl_idname = "scenario.recover_job"
    bl_label = "Recover saved job"
    bl_description = "Perform the selected recovery action without submitting a new generation"

    context_id: StringProperty(options={"HIDDEN"})
    request_id: StringProperty(options={"HIDDEN"})
    expected_revision: IntProperty(min=0, options={"HIDDEN"})
    action: EnumProperty(
        items=[
            (key, saved_job_actions.LABELS[key], saved_job_actions.LABELS[key])
            for key in saved_job_actions.RECOVERY_ACTIONS
        ]
    )

    def invoke(self, context, event):
        if self.action == "cancel_prepared":
            return context.window_manager.invoke_confirm(
                self,
                event,
                title="Cancel prepared job?",
                message=cancel_prepared_message(self.request_id),
                confirm_text="Discard unsent job",
            )
        if self.action == "cancel":
            return context.window_manager.invoke_confirm(self, event)
        return self.execute(context)

    def execute(self, context):
        try:
            if self.action == "cancel_prepared":
                # The same revision- and context-guarded command as MCP cancel_prepared_job.
                runtime.cancel_prepared_job(
                    self.context_id, self.request_id, self.expected_revision
                )
            else:
                runtime.control_model_job(
                    self.context_id, self.request_id, self.expected_revision, self.action
                )
        except ScenarioError as error:
            self.report({"ERROR"}, error.reason)
            return {"CANCELLED"}
        except Exception:
            self.report({"ERROR"}, "Recovery did not complete; inspect the saved job again")
            return {"CANCELLED"}
        runtime.set_message(
            "Prepared job canceled; nothing was sent to Scenario"
            if self.action == "cancel_prepared"
            else "Recovery requested; no new generation was submitted"
        )
        return {"FINISHED"}


class SCENARIO_OT_read_saved_blockout(bpy.types.Operator):
    bl_idname = "scenario.read_saved_blockout"
    bl_label = "Read saved Blockout plan"
    bl_description = "Read the complete saved plan for destination review without generating again"
    context_id: StringProperty(options={"HIDDEN"})
    request_id: StringProperty(options={"HIDDEN"})
    expected_revision: IntProperty(min=0, options={"HIDDEN"})

    def execute(self, context):
        try:
            runtime.blockout_recovery(self.context_id).prepare(
                self.request_id, self.expected_revision, context.scene
            )
        except Exception:
            self.report({"ERROR"}, "Could not read the saved plan; inspect the job and connection")
            return {"CANCELLED"}
        runtime.set_message("Reading the saved plan; review its destination before using it")
        return {"FINISHED"}


class SCENARIO_OT_use_saved_blockout(bpy.types.Operator):
    bl_idname = "scenario.use_saved_blockout"
    bl_label = "Use saved Blockout plan"
    bl_description = "Replace only the reviewed scene's stored plan without generating or building"
    bl_options = {"REGISTER", "UNDO"}
    context_id: StringProperty(options={"HIDDEN"})
    review_id: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    scene_name: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    element_count: IntProperty(options={"HIDDEN", "SKIP_SAVE"})
    group_count: IntProperty(options={"HIDDEN", "SKIP_SAVE"})
    replaces_plan: BoolProperty(options={"HIDDEN", "SKIP_SAVE"})

    def invoke(self, context, event):
        try:
            recovery = runtime.blockout_recovery(self.context_id)
            summary = recovery.status(self.review_id)
            if summary["state"] != "ready":
                raise ValueError("The plan is not ready")
            self._recovery = recovery
            self.scene_name = summary["scene"]
            self.element_count, self.group_count = summary["elements"], summary["groups"]
            self.replaces_plan = summary["replaces_plan"]
        except Exception:
            self.report({"ERROR"}, "Read and review the saved plan again")
            return {"CANCELLED"}
        return context.window_manager.invoke_props_dialog(self, width=480)

    def draw(self, context):
        layout = self.layout
        layout.label(text=f"Scene: {self.scene_name}", icon="SCENE_DATA")
        layout.label(text=f"Plan: {self.element_count} elements in {self.group_count} groups")
        if self.replaces_plan:
            layout.label(text="Replace this scene's existing stored plan.", icon="ERROR")
        layout.label(text="Keep existing geometry unchanged; no new generation.")
        layout.label(text="Choose Build plan separately to update geometry.")
        layout.label(text="Use Blender Undo to restore the previous plan.")

    def cancel(self, context):
        recovery = getattr(self, "_recovery", None)
        if recovery is not None:
            recovery.discard(self.review_id)

    def execute(self, context):
        try:
            runtime.blockout_recovery(self.context_id).apply(self.review_id)
        except Exception:
            self.report({"ERROR"}, "The saved plan or destination changed; review it again")
            return {"CANCELLED"}
        runtime.set_message("Saved plan ready; choose Build plan to update geometry")
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
    is_reuse: BoolProperty(options={"HIDDEN", "SKIP_SAVE"})

    def invoke(self, context, event):
        try:
            jobs, approval = runtime.prepare_image_application(
                self.context_id, self.request_id, self.expected_revision, context.scene
            )
            self._jobs = jobs
            self.is_reuse = approval.record.state.value == "applied" and not getattr(
                approval, "restore", False
            )
            self.application_id = approval.identifier
            self.scene_name = approval.scene_name
        except Exception:
            self.report({"ERROR"}, "Could not prepare the image import; inspect saved jobs again")
            return {"CANCELLED"}
        return context.window_manager.invoke_props_dialog(self, width=440)

    def draw(self, context):
        self.layout.label(text=f"Scene: {self.scene_name}", icon="SCENE_DATA")
        if self.is_reuse:
            self.layout.label(text="Use saved results again; no new generation.", icon="INFO")
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
    is_reuse: BoolProperty(options={"HIDDEN", "SKIP_SAVE"})
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
            self.is_reuse = approval.record.state.value == "applied" and not getattr(
                approval, "restore", False
            )
            self.application_id, self.scene_name = approval.identifier, approval.scene_name
            self.destination_frame, self.media_kind = approval.frame, approval.kind
        except Exception:
            self.report({"ERROR"}, "Could not prepare media insertion; inspect the saved result")
            return {"CANCELLED"}
        return context.window_manager.invoke_props_dialog(self, width=480)

    def draw(self, context):
        self.layout.label(text=f"Scene: {self.scene_name}", icon="SCENE_DATA")
        if self.is_reuse:
            self.layout.label(text="Use saved results again; no new generation.", icon="INFO")
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
    bl_label = "Import saved model"
    bl_description = "Review one saved GLB model and its scene/cursor destination"

    context_id: StringProperty(options={"HIDDEN"})
    request_id: StringProperty(options={"HIDDEN"})
    expected_revision: IntProperty(min=0, options={"HIDDEN"})
    asset_id: StringProperty(options={"HIDDEN"})
    application_id: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    scene_name: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    is_reuse: BoolProperty(options={"HIDDEN", "SKIP_SAVE"})
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
            self.is_reuse = approval.record.state.value == "applied" and not getattr(
                approval, "restore", False
            )
            self.application_id, self.scene_name = approval.identifier, approval.scene_name
            self.destination_cursor = approval.cursor
        except Exception:
            self.report({"ERROR"}, "Could not prepare model import; inspect the saved result")
            return {"CANCELLED"}
        return context.window_manager.invoke_props_dialog(self, width=480)

    def draw(self, context):
        self.layout.label(text=f"Scene: {self.scene_name}", icon="SCENE_DATA")
        if self.is_reuse:
            self.layout.label(text="Use saved results again; no new generation.", icon="INFO")
        position = ", ".join(f"{value:.3f}" for value in self.destination_cursor)
        self.layout.label(text=f"Place model bottom at cursor: {position}")
        self.layout.label(text="Import one GLB into a new group; pack its textures.")
        self.layout.label(text="Keep existing objects and selection unchanged.")
        self.layout.label(text="Use scene FPS; keep timeline range and current frame.")
        self.layout.label(text="Keep rigs and animation clips; external-file GLBs are unsupported.")

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


class SCENARIO_OT_apply_saved_world(bpy.types.Operator):
    bl_idname = "scenario.apply_saved_world"
    bl_label = "Review scene World"
    bl_description = "Confirm one saved panorama or restore the previous World in this session"

    context_id: StringProperty(options={"HIDDEN"})
    request_id: StringProperty(options={"HIDDEN"})
    expected_revision: IntProperty(min=0, options={"HIDDEN"})
    asset_id: StringProperty(options={"HIDDEN"})
    purpose: EnumProperty(
        items=[("world", "Set World", ""), ("restore_world", "Restore World", "")]
    )
    application_id: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    scene_name: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    is_reuse: BoolProperty(options={"HIDDEN", "SKIP_SAVE"})
    world_name: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    media_label: StringProperty(options={"HIDDEN", "SKIP_SAVE"})

    def invoke(self, context, event):
        try:
            jobs, approval = runtime.prepare_world_application(
                self.context_id,
                self.request_id,
                self.expected_revision,
                context.scene,
                self.asset_id,
                restore=self.purpose == "restore_world",
            )
            self._jobs = jobs
            self.is_reuse = approval.record.state.value == "applied" and not getattr(
                approval, "restore", False
            )
            self.application_id, self.scene_name = approval.identifier, approval.scene_name
            self.world_name = approval.previous.name if approval.previous else "None"
            self.media_label = describe_world_media(approval.media_type)
        except Exception:
            self.report({"ERROR"}, "Could not prepare the World change; inspect saved jobs")
            return {"CANCELLED"}
        return context.window_manager.invoke_props_dialog(self, width=520)

    def draw(self, context):
        self.layout.label(text=f"Scene: {self.scene_name}", icon="SCENE_DATA")
        if self.is_reuse:
            self.layout.label(text="Use saved results again; no new generation.", icon="INFO")
        self.layout.label(text=f"Current World: {self.world_name}")
        if self.purpose == "restore_world":
            self.layout.label(text="Restore the original World kept by this session.")
            self.layout.label(text="Changed World or image data prevents restoration.")
        else:
            self.layout.label(text=f"Selected: {self.media_label}")
            self.layout.label(text="Use this 2:1 image as an equirectangular environment.")
            self.layout.label(text="Pack the panorama and keep the original World unchanged.")
            self.layout.label(text="PNG/JPEG are LDR; EXR may not be HDR or seamless.")
            self.layout.label(text="Restore remains available in this session while unchanged.")

    def cancel(self, context):
        jobs = getattr(self, "_jobs", None)
        if jobs is not None:
            jobs.discard_image_application(self.application_id)

    def execute(self, context):
        try:
            runtime.apply_saved_result(self.context_id, self.application_id)
        except Exception:
            self.report({"ERROR"}, "World change was not started; review the destination again")
            return {"CANCELLED"}
        runtime.set_message(
            "World restoration finished"
            if self.purpose == "restore_world"
            else "Verifying the saved panorama for the approved scene"
        )
        return {"FINISHED"}


class SCENARIO_OT_apply_saved_material(bpy.types.Operator):
    bl_idname = "scenario.apply_saved_material"
    bl_label = "Apply saved material"
    bl_description = (
        "Review a saved texture set for the active mesh material slot without generating again"
    )

    context_id: StringProperty(options={"HIDDEN"})
    request_id: StringProperty(options={"HIDDEN"})
    expected_revision: IntProperty(min=0, options={"HIDDEN"})
    application_id: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    scene_name: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    is_reuse: BoolProperty(options={"HIDDEN", "SKIP_SAVE"})
    target_name: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    slot: IntProperty(options={"HIDDEN", "SKIP_SAVE"})
    roles: StringProperty(options={"HIDDEN", "SKIP_SAVE"})

    def invoke(self, context, event):
        try:
            jobs, approval = runtime.prepare_material_application(
                self.context_id,
                self.request_id,
                self.expected_revision,
                context.scene,
                context.view_layer.objects.active,
            )
            self._jobs = jobs
            self.is_reuse = approval.record.state.value == "applied" and not getattr(
                approval, "restore", False
            )
            self.application_id, self.scene_name = approval.identifier, approval.scene_name
            self.target_name, self.slot = approval.target_name, approval.target.active + 1
            self.roles = ", ".join(approval.roles)
        except Exception:
            self.report(
                {"ERROR"}, "Choose a local single-user UV mesh and inspect saved texture maps"
            )
            return {"CANCELLED"}
        return context.window_manager.invoke_props_dialog(self, width=540)

    def draw(self, context):
        self.layout.label(text=f"Scene: {self.scene_name}", icon="SCENE_DATA")
        if self.is_reuse:
            self.layout.label(text="Use saved results again; no new generation.", icon="INFO")
        self.layout.label(text=f"Mesh: {self.target_name}, material slot {self.slot}")
        self.layout.label(text=f"Maps: {self.roles}")
        self.layout.label(text="Create a packed material using this mesh's active UV map.")
        self.layout.label(text="Replace this slot only; existing materials remain unchanged.")
        self.layout.label(text="Height uses bump; AO/edge maps remain available for wiring.")
        self.layout.label(text="Normal maps use Blender tangent space. No global undo entry.")

    def cancel(self, context):
        jobs = getattr(self, "_jobs", None)
        if jobs is not None:
            jobs.discard_image_application(self.application_id)

    def execute(self, context):
        try:
            runtime.apply_saved_result(self.context_id, self.application_id)
        except Exception:
            self.report({"ERROR"}, "Material assignment was not started; review the destination")
            return {"CANCELLED"}
        runtime.set_message("Verifying saved maps for the approved material slot")
        return {"FINISHED"}


class SCENARIO_OT_apply_saved_mesh(bpy.types.Operator):
    bl_idname = "scenario.apply_saved_mesh"
    bl_label = "Apply saved mesh edit"
    bl_description = "Review one saved result before replacing the captured mesh"
    context_id: StringProperty(options={"HIDDEN"})
    request_id: StringProperty(options={"HIDDEN"})
    expected_revision: IntProperty(min=0, options={"HIDDEN"})
    asset_id: StringProperty(options={"HIDDEN"})
    original_source: BoolProperty(options={"HIDDEN", "SKIP_SAVE"})
    application_id: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    scene_name: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    target_name: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    is_reuse: BoolProperty(options={"HIDDEN", "SKIP_SAVE"})
    review_error: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    local_placement_required: BoolProperty(options={"HIDDEN", "SKIP_SAVE"})
    policy: EnumProperty(
        name="Edit",
        items=(
            ("REMESH", "Replace geometry", "Adopt result geometry, UVs and mesh materials"),
            ("UV", "Replace active UVs", "Require exactly matching indexed topology and positions"),
            (
                "RETEXTURE",
                "Replace textures",
                "Preserve geometry; adopt result UVs and materials with exactly matching topology and positions",
            ),
            (
                "PARTS",
                "Replace with parts",
                "Keep the source as an empty mesh parent; adopt every mesh in the selected GLB as a part",
            ),
            (
                "RIG",
                "Attach rig",
                "Preserve source mesh data; attach weights and a compatible returned rig",
            ),
        ),
        default="REMESH",
        options={"SKIP_SAVE"},
    )
    placement: EnumProperty(
        name="Result coordinates",
        items=(
            ("WORLD", "Scene coordinates", "Preserve imported result positions in the scene"),
            (
                "LOCAL",
                "Object local coordinates",
                "Use imported positions in the source object's local axes",
            ),
        ),
        default="WORLD",
        options={"SKIP_SAVE"},
    )
    keep_original: BoolProperty(name="Keep original", default=True, options={"SKIP_SAVE"})

    def invoke(self, context, event):
        try:
            context.view_layer.update()
            source = context.view_layer.objects.active
            jobs, approval = runtime.prepare_mesh_application(
                self.context_id,
                self.request_id,
                self.expected_revision,
                context.scene,
                source,
                self.asset_id,
                policy=self.policy,
                placement=self.placement,
                keep_original=self.keep_original,
                original_source=self.original_source,
                review_placement=True,
            )
            self._jobs = jobs
            self.application_id = approval.identifier
            self.placement = approval.placement
            self.local_placement_required = approval.target.obj.matrix_world.determinant() <= 0
            self.scene_name, self.target_name = approval.scene_name, approval.target_name
            self.is_reuse = approval.record.state.value == "applied"
            self.review_error = ""
        except Exception:
            self.report(
                {"ERROR"},
                (
                    "Captured source changed or is unavailable; review a destination with Apply mesh edit"
                    if self.original_source
                    else "Choose one local mesh in Object Mode and inspect the saved GLB"
                ),
            )
            return {"CANCELLED"}
        return context.window_manager.invoke_props_dialog(self, width=580)

    def _sync_options(self):
        approval = runtime.revise_mesh_application(
            self.context_id,
            self.application_id,
            policy=self.policy,
            placement=self.placement,
            keep_original=self.keep_original,
        )
        self.application_id = approval.identifier
        self.review_error = ""

    def check(self, context):
        if not self.application_id:
            return False
        try:
            self._sync_options()
        except Exception:
            self.review_error = "Target or options changed; cancel and review again"
        return True

    def draw(self, context):
        layout = self.layout
        layout.label(text=f"Scene: {self.scene_name}", icon="SCENE_DATA")
        layout.label(text=f"Mesh: {self.target_name}", icon="MESH_DATA")
        layout.label(text=f"Saved result: {self.asset_id}")
        if self.original_source:
            layout.label(text="Use the unchanged source captured for this generation.", icon="INFO")
        if self.is_reuse:
            layout.label(text="Use saved results again; no new generation.", icon="INFO")
        layout.prop(self, "policy")
        layout.prop(self, "placement")
        if self.local_placement_required:
            layout.label(text="Mirrored or zero-scale source: use object local coordinates.")
        layout.prop(self, "keep_original")
        if self.policy == "REMESH":
            layout.label(text="Replace this mesh's geometry, UVs and mesh materials.")
        elif self.policy == "RIG":
            layout.label(text="Attach bone weights and rig; preserve geometry, UVs and materials.")
            layout.label(text="Matching geometry required. No morphs or mesh animation.")
            layout.label(
                text="Keep rig clips. Move the source and new rig group together afterward."
            )
        elif self.policy == "PARTS":
            layout.label(text="Replace source geometry with an empty mesh parent and named parts.")
            layout.label(text="Treat every mesh in this GLB as a part, not an alternate variant.")
        elif self.policy == "RETEXTURE":
            layout.label(text="Replace all UV layers and mesh materials; preserve geometry.")
            layout.label(text="Indexed topology and positions must match exactly.")
        else:
            layout.label(text="Replace active UVs only; topology and positions must match exactly.")
        layout.label(text="Keep the source object's name, transforms, parenting and collections.")
        layout.label(
            text="One static GLB, 2 to 128 parts. No automatic fitting or scale adjustment."
            if self.policy == "PARTS"
            else "One GLB mesh and rig. No automatic fitting or scale adjustment."
            if self.policy == "RIG"
            else "One static GLB mesh only. No automatic fitting or scale adjustment."
        )
        layout.label(text="Keep original makes an unselected copy. Undo follows Blender settings.")
        layout.label(
            text="Undo/redo changes the scene only; saved jobs and spending stay recorded."
        )
        if self.review_error:
            layout.label(text=self.review_error, icon="ERROR")

    def cancel(self, context):
        jobs = getattr(self, "_jobs", None)
        if jobs is not None:
            jobs.discard_image_application(self.application_id)

    def execute(self, context):
        try:
            self._sync_options()
            runtime.apply_saved_result(self.context_id, self.application_id)
        except Exception:
            self.cancel(context)
            self.report(
                {"ERROR"}, "Mesh edit was not started; review the captured target and options"
            )
            return {"CANCELLED"}
        runtime.set_message("Mesh edit approved; inspect the saved job for its result")
        return {"FINISHED"}


def _refusal(context_id, error):
    """A first-frame refusal in native words; the facade's context reason names MCP steps."""
    if context_id != runtime.state.job_context_id:
        return "The connection changed; inspect saved jobs again"
    return error.reason


class SCENARIO_OT_use_saved_first_frame(bpy.types.Operator):
    bl_idname = "scenario.use_saved_first_frame"
    bl_label = "Use as video first frame"
    bl_description = (
        "Review one saved image as the Render Video first frame without uploading or generating"
    )

    context_id: StringProperty(options={"HIDDEN"})
    request_id: StringProperty(options={"HIDDEN"})
    expected_revision: IntProperty(min=0, options={"HIDDEN"})
    asset_id: StringProperty(options={"HIDDEN"})
    application_id: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    scene_name: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    model_label: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    input_label: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    file_name: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    replaced_file: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    enables_first_frame: BoolProperty(options={"HIDDEN", "SKIP_SAVE"})

    def invoke(self, context, event):
        try:
            jobs, approval = runtime.prepare_first_frame_application(
                self.context_id,
                self.request_id,
                self.expected_revision,
                context.scene,
                self.asset_id,
            )
        except ScenarioError as error:
            # Refusals name what to change: the model, its input or the existing slot.
            self.report({"ERROR"}, _refusal(self.context_id, error))
            return {"CANCELLED"}
        except Exception:
            self.report({"ERROR"}, "Could not review the first frame; inspect the saved job again")
            return {"CANCELLED"}
        self._jobs = jobs
        target = approval.target
        self.application_id, self.scene_name = approval.identifier, approval.scene_name
        self.model_label, self.input_label = target.model_label, target.input_label
        self.file_name = approval.asset.name
        self.replaced_file = bpy.path.basename(target.previous_path)
        self.enables_first_frame = not target.previous_enabled
        return context.window_manager.invoke_props_dialog(
            self, width=520, title="Use as video first frame", confirm_text="Use as first frame"
        )

    def draw(self, context):
        layout = self.layout
        layout.label(text=f"Scene: {self.scene_name}", icon="SCENE_DATA")
        layout.label(text="Form: Render Video")
        layout.label(text=f"Model: {self.model_label}")
        layout.label(text=f"Input: {self.input_label}")
        layout.label(text=f"Image: {self.file_name} (saved result)", icon="IMAGE_DATA")
        layout.label(text="Use the saved Scenario asset; nothing is uploaded.")
        layout.label(text="No new generation; the blend stores no file path.")
        if self.replaced_file:
            layout.label(text=f"Replace the chosen first-frame file: {self.replaced_file}")
        if self.enables_first_frame:
            layout.label(text="Turn on the video first frame.")
        layout.label(text="Invalidate the Render Video and Prompt Spark prices.")
        layout.label(text="Remove the first-frame slot to undo this.")

    def cancel(self, context):
        jobs = getattr(self, "_jobs", None)
        if jobs is not None:
            jobs.discard_image_application(self.application_id)

    def execute(self, context):
        try:
            runtime.apply_saved_result(self.context_id, self.application_id)
        except ScenarioError as error:
            self.report({"ERROR"}, f"First frame was not set: {_refusal(self.context_id, error)}")
            return {"CANCELLED"}
        except Exception:
            self.report({"ERROR"}, "First frame was not set; review the saved image and form again")
            return {"CANCELLED"}
        runtime.set_message("Verifying the saved image for the Render Video first frame")
        return {"FINISHED"}


def result_actions(record):
    """Describe one view's saved-job controls from in-memory state, without I/O."""
    review = None
    if "recover_blockout" in record.meta.get("recovery_actions", ()):
        jobs = runtime.state.blockout_jobs
        review = jobs.recovery.current(record.local_id, bpy.context.scene) if jobs else None
    return saved_job_actions.describe(
        record, runtime.state.job_context_id, RESULT_TYPES, blockout_review=review
    )


def draw_action(layout, item):
    """Draw one descriptor; its operator performs any confirmation or review."""
    if item.operator is None:
        layout.label(text=item.label, icon=item.icon)
        return
    operator = layout.operator(item.operator, text=item.label, icon=item.icon)
    for name, value in item.properties:
        setattr(operator, name, value)


def draw_controls(layout, record):
    for item in result_actions(record):
        draw_action(layout, item)


CLASSES = (
    SCENARIO_OT_inspect_saved_jobs,
    SCENARIO_OT_recover_job,
    SCENARIO_OT_read_saved_blockout,
    SCENARIO_OT_use_saved_blockout,
    SCENARIO_OT_import_saved_images,
    SCENARIO_OT_import_saved_media,
    SCENARIO_OT_import_saved_model,
    SCENARIO_OT_apply_saved_world,
    SCENARIO_OT_apply_saved_material,
    SCENARIO_OT_apply_saved_mesh,
    SCENARIO_OT_use_saved_first_frame,
)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
