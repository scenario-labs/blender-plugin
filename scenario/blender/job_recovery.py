# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Explicit shared-job recovery controls; drawing never changes stored jobs."""

import bpy
from bpy.props import (
    BoolProperty,
    EnumProperty,
    FloatProperty,
    FloatVectorProperty,
    IntProperty,
    StringProperty,
)

from ..core.api.errors import ScenarioError
from ..core.jobs.playback import PLAYBACK_TYPES
from ..core.scene.mesh_edit_policy import task_label
from ..core.scene.panorama import WORLD_MEDIA_TYPES, describe_world_media
from ..core.scene.placement import MAX_TARGET_SIZE_M, MIN_TARGET_SIZE_M
from ..core.ui import saved_job_actions
from . import render_lanes, result_media, review_previews, runtime
from .media_application import MEDIA_TYPES
from .mesh_result_application import MeshResultApplicationError

# Saved media types offered per application; describe() owns no media policy.
RESULT_TYPES = saved_job_actions.ResultTypes(
    media={media_type: value[0] for media_type, value in MEDIA_TYPES.items()},
    world=WORLD_MEDIA_TYPES,
    playback={media_type: value[0] for media_type, value in PLAYBACK_TYPES.items()},
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


# Shown before marking an unconfirmed request reviewed for this session.
REVIEW_MESSAGE = (
    "Scenario may have started this request. Check your Scenario history first: "
    "an identical request sent now could be charged twice."
)


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
        if self.action == "mark_reviewed":
            return context.window_manager.invoke_confirm(
                self,
                event,
                title="Mark unconfirmed request reviewed?",
                message=REVIEW_MESSAGE,
                confirm_text="Mark reviewed",
            )
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
            else "Marked reviewed for this session; an identical request can be sent again"
            if self.action == "mark_reviewed"
            else "Looking in cloud history; nothing is submitted"
            if self.action == "find_cloud_job"
            else "Stopping the download; Resume download starts it again"
            if self.action == "stop_download"
            else "Recovery requested; no new generation was submitted"
        )
        return {"FINISHED"}


# Shown before linking one listed cloud job to an unconfirmed request.
LINK_MESSAGES = (
    "Scenario cannot tell which job this request created.",
    "Link only a job you recognize as this request.",
    "Linking cannot be undone and sends no new generation.",
    "Results still wait for your review before changing the scene.",
)
LINK_WIDTH = 520
# Blender keeps only references to dynamic enum strings; hold them here.
_LINK_ITEMS = []


def link_candidates(request_id):
    """The cloud candidates ModelJobs projected for this saved job; reads memory only."""
    owner = runtime.state.model_jobs
    view = owner.views.get(request_id) if owner is not None else None
    return tuple(view.meta.get("cloud_candidates", ())) if view is not None else ()


def _link_items(self, context):
    items = [("NONE", "Choose one job", "Nothing is linked until you choose a job")]
    for candidate in link_candidates(self.request_id):
        title, detail = saved_job_actions.candidate_text(candidate)
        items.append((candidate["job_id"], title, detail))
    _LINK_ITEMS[:] = items
    return _LINK_ITEMS


class SCENARIO_OT_link_cloud_job(bpy.types.Operator):
    bl_idname = "scenario.link_cloud_job"
    bl_label = "Choose cloud job"
    bl_description = (
        "Link one listed cloud job to this unconfirmed request after review; nothing is submitted"
    )

    context_id: StringProperty(options={"HIDDEN"})
    request_id: StringProperty(options={"HIDDEN"})
    expected_revision: IntProperty(min=0, options={"HIDDEN"})
    job_id: EnumProperty(name="Cloud job", items=_link_items, options={"SKIP_SAVE"})

    def invoke(self, context, event):
        owner = runtime.state.model_jobs
        view = owner.views.get(self.request_id) if owner is not None else None
        if (
            not link_candidates(self.request_id)
            or self.context_id != runtime.state.job_context_id
            or view.meta.get("saved_revision") != self.expected_revision
        ):
            self.report({"ERROR"}, "The cloud candidates changed; find them again")
            return {"CANCELLED"}
        return context.window_manager.invoke_props_dialog(
            self, width=LINK_WIDTH, title="Link a cloud job?", confirm_text="Link this job"
        )

    def draw(self, context):
        layout = self.layout
        for line in LINK_MESSAGES:
            layout.label(text=line)
        column = layout.column(align=True)
        for candidate in link_candidates(self.request_id):
            title, detail = saved_job_actions.candidate_text(candidate)
            box = column.box()
            box.prop_enum(self, "job_id", candidate["job_id"], text=title)
            box.label(text=detail)

    def execute(self, context):
        if self.job_id == "NONE":
            self.report({"ERROR"}, "Choose one cloud job first; nothing was linked")
            return {"CANCELLED"}
        try:
            runtime.link_cloud_job(
                self.context_id, self.request_id, self.expected_revision, self.job_id
            )
        except ScenarioError as error:
            self.report({"ERROR"}, error.reason)
            return {"CANCELLED"}
        except Exception:
            self.report({"ERROR"}, "Could not link the cloud job; inspect the saved job again")
            return {"CANCELLED"}
        runtime.set_message("Checking the chosen cloud job; nothing new is submitted")
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
        layout.label(text="Choose Build blockout separately to update geometry.")
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
        runtime.set_message("Saved plan ready; choose Build blockout to update geometry")
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


def _kept(count):
    """The review line naming the camera backgrounds that stay."""
    if count == 0:
        return "The camera has no other background."
    noun = "background" if count == 1 else "backgrounds"
    return f"Keep its {count} existing {noun} unchanged."


class SCENARIO_OT_set_saved_camera_background(bpy.types.Operator):
    bl_idname = "scenario.set_saved_camera_background"
    bl_label = "Set as camera background"
    bl_description = "Review one saved image or video as another background of the scene camera"

    context_id: StringProperty(options={"HIDDEN"})
    request_id: StringProperty(options={"HIDDEN"})
    expected_revision: IntProperty(min=0, options={"HIDDEN"})
    asset_id: StringProperty(options={"HIDDEN"})
    application_id: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    scene_name: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    is_reuse: BoolProperty(options={"HIDDEN", "SKIP_SAVE"})
    camera_name: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    media_kind: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    destination_frame: IntProperty(options={"HIDDEN", "SKIP_SAVE"})
    backgrounds: IntProperty(options={"HIDDEN", "SKIP_SAVE"})

    def invoke(self, context, event):
        try:
            jobs, approval = runtime.prepare_landing_application(
                self.context_id,
                self.request_id,
                self.expected_revision,
                context.scene,
                self.asset_id,
                purpose="camera_background",
            )
        except ScenarioError as error:
            # A refusal names its cause, such as a scene without a camera.
            self.report({"ERROR"}, f"No background added: {_refusal(self.context_id, error)}")
            return {"CANCELLED"}
        except Exception:
            self.report({"ERROR"}, "Could not prepare the background; inspect the saved result")
            return {"CANCELLED"}
        self._jobs = jobs
        self.is_reuse = approval.record.state.value == "applied"
        self.application_id, self.scene_name = approval.identifier, approval.scene_name
        self.camera_name, self.media_kind = approval.camera_name, approval.kind
        self.destination_frame = approval.frame or 0
        self.backgrounds = approval.backgrounds
        return context.window_manager.invoke_props_dialog(self, width=480)

    def draw(self, context):
        layout = self.layout
        layout.label(text=f"Scene: {self.scene_name}", icon="SCENE_DATA")
        if self.is_reuse:
            layout.label(text="Use saved results again; no new generation.", icon="INFO")
        layout.label(text=f"Camera: {self.camera_name}", icon="CAMERA_DATA")
        layout.label(text=f"Add this saved {self.media_kind} as one more background.")
        layout.label(text=_kept(self.backgrounds))
        if self.media_kind == "video":
            layout.label(text=f"Start the clip at frame {self.destination_frame}.")
            layout.label(text="Video stays in a local file needed by this blend.")
        else:
            layout.label(text="Pack the image into the blend file.")
        for line in BACKGROUND_REVIEW:
            layout.label(text=line)

    def cancel(self, context):
        jobs = getattr(self, "_jobs", None)
        if jobs is not None:
            jobs.discard_image_application(self.application_id)

    def execute(self, context):
        try:
            runtime.apply_saved_result(self.context_id, self.application_id)
        except ScenarioError as error:
            self.cancel(context)
            self.report({"ERROR"}, f"No background added: {_refusal(self.context_id, error)}")
            return {"CANCELLED"}
        except Exception:
            self.cancel(context)
            self.report({"ERROR"}, "No background added; review the scene camera again")
            return {"CANCELLED"}
        runtime.set_message("Verifying the saved result for the approved camera")
        return {"FINISHED"}


class SCENARIO_OT_add_saved_image_plane(bpy.types.Operator):
    bl_idname = "scenario.add_saved_image_plane"
    bl_label = "Add image plane"
    bl_description = "Review one saved image as a new upright plane at the 3D cursor"

    context_id: StringProperty(options={"HIDDEN"})
    request_id: StringProperty(options={"HIDDEN"})
    expected_revision: IntProperty(min=0, options={"HIDDEN"})
    asset_id: StringProperty(options={"HIDDEN"})
    application_id: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    scene_name: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    is_reuse: BoolProperty(options={"HIDDEN", "SKIP_SAVE"})
    destination_cursor: FloatVectorProperty(size=3, options={"HIDDEN", "SKIP_SAVE"})
    review_error: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    unlit: BoolProperty(
        name="Unlit",
        description="Show the image's own colours, unaffected by scene lights",
        options={"SKIP_SAVE"},
    )

    def invoke(self, context, event):
        try:
            jobs, approval = runtime.prepare_landing_application(
                self.context_id,
                self.request_id,
                self.expected_revision,
                context.scene,
                self.asset_id,
                purpose="image_plane",
            )
        except ScenarioError as error:
            self.report({"ERROR"}, f"No image plane added: {_refusal(self.context_id, error)}")
            return {"CANCELLED"}
        except Exception:
            self.report({"ERROR"}, "Could not prepare the image plane; inspect the saved result")
            return {"CANCELLED"}
        self._jobs = jobs
        self.is_reuse = approval.record.state.value == "applied"
        self.application_id, self.scene_name = approval.identifier, approval.scene_name
        self.destination_cursor, self.unlit = approval.cursor, approval.unlit
        self.review_error = ""
        return context.window_manager.invoke_props_dialog(self, width=480)

    def _sync_options(self):
        """Exchange the approval for one with the shown unlit choice."""
        approval = runtime.revise_landing_application(
            self.context_id, self.application_id, unlit=bool(self.unlit)
        )
        self.application_id = approval.identifier
        self.review_error = ""

    def check(self, context):
        if not self.application_id:
            return False
        try:
            self._sync_options()
        except Exception:
            self.review_error = "Destination changed; cancel and review again"
        return True

    def draw(self, context):
        layout = self.layout
        layout.label(text=f"Scene: {self.scene_name}", icon="SCENE_DATA")
        if self.is_reuse:
            layout.label(text="Use saved results again; no new generation.", icon="INFO")
        position = ", ".join(f"{value:.3f}" for value in self.destination_cursor)
        layout.label(text=f"Place plane bottom at cursor: {position}")
        for line in PLANE_REVIEW:
            layout.label(text=line)
        layout.prop(self, "unlit")
        layout.label(text="Files are checked again first; a change stops it.")
        if self.review_error:
            layout.label(text=self.review_error, icon="ERROR")

    def cancel(self, context):
        jobs = getattr(self, "_jobs", None)
        if jobs is not None:
            jobs.discard_image_application(self.application_id)

    def execute(self, context):
        try:
            if self.unlit:
                self._sync_options()
            runtime.apply_saved_result(self.context_id, self.application_id)
        except ScenarioError as error:
            self.cancel(context)
            self.report({"ERROR"}, f"No image plane added: {_refusal(self.context_id, error)}")
            return {"CANCELLED"}
        except Exception:
            self.cancel(context)
            self.report({"ERROR"}, "No image plane added; review its destination again")
            return {"CANCELLED"}
        runtime.set_message("Verifying the saved image for the approved scene and cursor")
        return {"FINISHED"}


# Review lines shared by every saved camera background.
BACKGROUND_REVIEW = (
    "Half opacity, behind objects, fitted to the camera frame.",
    "Shown when you look through the camera.",
    "Files are checked again first; a change stops it.",
)
# Review lines of a saved image plane, after its cursor.
PLANE_REVIEW = (
    "Add one 1 m tall plane facing the Front view.",
    "Keep existing objects and selection unchanged.",
    "Use the image's alpha when it has one; pack the image.",
)

# Format-specific review lines for the saved model confirmation.
MODEL_REVIEW = {
    "glb": (
        "Use scene FPS; keep timeline range and current frame.",
        "Keep rigs and animation clips; external-file GLBs are unsupported.",
    ),
    "gltf": (
        "Use scene FPS; keep timeline range and current frame.",
        "Read only this job's saved buffers and images.",
    ),
    "fbx": (
        "Pack embedded textures; external texture files stop the import.",
        "Keep clips at the file's frame rate; keep the scene timeline.",
    ),
    "obj": ("Leave out maps that were not saved with this job.",),
    "ply": ("A PLY without splat data imports as a mesh.",),
    "spz": ("Read SPZ versions 2 and 3; other versions stop unchanged.",),
}
# Formats a worker reads first, with reviewed point limits and saved axes.
SPLAT_REVIEW_FORMATS = frozenset({"spz", "splat", "ply"})
SPLAT_REVIEW = (
    "Show splats as coloured points; Blender has no splat renderer.",
    "Denser files are thinned evenly to the point limit.",
    "Default axes follow the file format; check the result is upright.",
)
# Shown when the review scales the new group to a longest side.
TARGET_SIZE_REVIEW = "Scale the group evenly; its bottom stays at the cursor."
SPLAT_POINT_ITEMS = (
    ("250000", "250,000", "Keep at most 250,000 evenly spaced points"),
    ("500000", "500,000", "Keep at most 500,000 evenly spaced points"),
    ("1000000", "1,000,000", "Keep at most 1,000,000 evenly spaced points"),
    ("2000000", "2,000,000", "Keep at most 2,000,000 evenly spaced points"),
)
SPLAT_AXIS_ITEMS = (
    ("OPENGL", "OpenGL: Y up", "Saved right, up, back; the SPZ format convention"),
    ("OPENCV", "OpenCV: Y down", "Saved right, down, forward; the PLY and .splat convention"),
)


def unit_summary(unit):
    """Describe one import unit's saved files, e.g. "OBJ + MTL + 2 maps"."""
    name = saved_job_actions.MODEL_FORMATS.get(unit.format.value, unit.format.value.upper())
    parts = [name]
    if unit.material is not None:
        parts.append("MTL")
    count = len(unit.textures)
    if count:
        parts.append(f"{count} map" if count == 1 else f"{count} maps")
    if unit.resources:
        count = len(unit.resources)
        parts.append(f"up to {count} saved file" if count == 1 else f"up to {count} saved files")
    return " + ".join(parts)


class SCENARIO_OT_import_saved_model(bpy.types.Operator):
    bl_idname = "scenario.import_saved_model"
    bl_label = "Import saved model"
    bl_description = "Review one saved model and its scene/cursor destination"

    context_id: StringProperty(options={"HIDDEN"})
    request_id: StringProperty(options={"HIDDEN"})
    expected_revision: IntProperty(min=0, options={"HIDDEN"})
    asset_id: StringProperty(options={"HIDDEN"})
    application_id: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    scene_name: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    is_reuse: BoolProperty(options={"HIDDEN", "SKIP_SAVE"})
    destination_cursor: FloatVectorProperty(size=3, options={"HIDDEN", "SKIP_SAVE"})
    model_format: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    model_summary: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    is_primary: BoolProperty(options={"HIDDEN", "SKIP_SAVE"})
    is_splat: BoolProperty(options={"HIDDEN", "SKIP_SAVE"})
    review_error: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    splat_points: EnumProperty(
        name="Points", items=SPLAT_POINT_ITEMS, default="1000000", options={"SKIP_SAVE"}
    )
    splat_axes: EnumProperty(
        name="Saved axes", items=SPLAT_AXIS_ITEMS, default="OPENGL", options={"SKIP_SAVE"}
    )
    use_target_size: BoolProperty(
        name="Longest side",
        description="Scale the new group evenly so its longest side has this length",
        options={"SKIP_SAVE"},
    )
    target_size: FloatProperty(
        name="Longest side",
        description="Length of the new group's longest side, in scene units",
        default=1.0,
        min=MIN_TARGET_SIZE_M,
        max=MAX_TARGET_SIZE_M,
        subtype="DISTANCE",
        unit="LENGTH",
        options={"SKIP_SAVE"},
    )

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
            self.model_format = approval.unit.format.value
            self.model_summary = unit_summary(approval.unit)
            self.is_primary = approval.unit.primary
            # The review shows the approval's own defaults for SPZ, PLY and .splat.
            self.is_splat = approval.max_points is not None
            if self.is_splat:
                self.splat_points, self.splat_axes = str(approval.max_points), approval.axes
            self.use_target_size = approval.target_size is not None
            if self.use_target_size:
                self.target_size = approval.target_size
            self.review_error = ""
        except Exception:
            self.report({"ERROR"}, "Could not prepare model import; inspect the saved result")
            return {"CANCELLED"}
        return context.window_manager.invoke_props_dialog(self, width=480)

    def _sync_options(self):
        """Exchange the approval for one with the shown splat options and size."""
        # Rounded to micrometres: the property stores a single-precision float.
        options = {"target_size": round(self.target_size, 6) if self.use_target_size else None}
        if self.is_splat:
            options.update(max_points=int(self.splat_points), axes=self.splat_axes)
        approval = runtime.revise_model_application(self.context_id, self.application_id, **options)
        self.application_id = approval.identifier
        self.review_error = ""

    def check(self, context):
        if not self.application_id:
            return False
        try:
            self._sync_options()
        except Exception:
            self.review_error = "Destination or options changed; cancel and review again"
        return True

    def draw(self, context):
        layout = self.layout
        layout.label(text=f"Scene: {self.scene_name}", icon="SCENE_DATA")
        if self.is_reuse:
            layout.label(text="Use saved results again; no new generation.", icon="INFO")
        choice = "primary result" if self.is_primary else "alternate result"
        layout.label(text=f"Selected: {self.model_summary} ({choice})")
        position = ", ".join(f"{value:.3f}" for value in self.destination_cursor)
        splats_only = self.model_format in ("spz", "splat")
        noun = "splats" if splats_only else "model"
        layout.label(text=f"Place {noun} bottom at cursor: {position}")
        if splats_only:
            layout.label(text="Import into a new group with its own new material.")
        else:
            layout.label(text="Import into a new group; pack its textures.")
        layout.label(text="Keep existing objects and selection unchanged.")
        for line in MODEL_REVIEW.get(self.model_format, ()):
            layout.label(text=line)
        if self.is_splat:
            layout.prop(self, "splat_points")
            layout.prop(self, "splat_axes")
            for line in SPLAT_REVIEW:
                layout.label(text=line)
        row = layout.row(align=True)
        row.prop(self, "use_target_size")
        size = row.row(align=True)
        size.active = self.use_target_size
        size.prop(self, "target_size", text="")
        if self.use_target_size:
            layout.label(text=TARGET_SIZE_REVIEW)
        layout.label(text="Files are checked again first; a change stops the import.")
        if self.review_error:
            layout.label(text=self.review_error, icon="ERROR")

    def cancel(self, context):
        jobs = getattr(self, "_jobs", None)
        if jobs is not None:
            jobs.discard_image_application(self.application_id)

    def execute(self, context):
        try:
            if self.is_splat or self.use_target_size:
                self._sync_options()
            runtime.apply_saved_result(self.context_id, self.application_id)
        except ScenarioError as error:
            # A sanitized refusal, such as a busy local-operation slot, names its cause.
            self.cancel(context)
            self.report(
                {"ERROR"}, f"Model import was not started: {_refusal(self.context_id, error)}"
            )
            return {"CANCELLED"}
        except Exception:
            self.cancel(context)
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
            self.layout.label(text="Adds a new World with the panorama; keeps the current one.")
            self.layout.label(text="PNG/JPEG are LDR; EXR may not be HDR or seamless.")
            self.layout.label(text="Restore brings it back while neither World is changed.")
            self.layout.label(text="Rendered viewport shading shows the new World.")

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


def _draw_animate(layout, review_error):
    # Clips are pose data on the mesh's own rig: coordinates and Keep original
    # do not apply, so the review does not offer them.
    layout.label(text="Add the returned clips to this mesh's rig; keep its mesh and skin.")
    layout.label(text="Bone names, parents and rest pose must match; clips scale to the rig.")
    layout.label(text="The first clip plays; it, the others and the previous action stay in NLA.")
    layout.label(text="The returned character is not added. Timeline settings stay unchanged.")
    layout.label(text="Undo follows Blender settings; saved jobs and spending stay recorded.")
    if review_error:
        layout.label(text=review_error, icon="ERROR")


_FIT_POLICIES = {"REMESH", "UV", "RETEXTURE", "PARTS", "RIG"}
# Several captured sources edited together; the review names this many of them.
_SEVERAL_POLICIES = {"UV", "RETEXTURE", "RIG"}
_NAMED_SOURCES = 4


def _source_names(names):
    """A bounded list of target names for one dialog line."""
    shown = ", ".join(names[:_NAMED_SOURCES])
    hidden = len(names) - _NAMED_SOURCES
    return f"{shown} and {hidden} more" if hidden > 0 else shown


def _mesh_policy_changed(self, _context):
    # A property update, never draw(): mesh edits default to a verified fit;
    # ANIMATE uses no coordinates, and a REMESH that is not the job's own Remesh
    # task starts on scene coordinates. check() then revises the approval.
    if self.policy in _FIT_POLICIES and (self.policy != "REMESH" or self.remesh_task):
        self.placement = "FIT"
    elif self.placement == "FIT":
        self.placement = "LOCAL" if self.local_placement_required else "WORLD"


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
    remesh_task: BoolProperty(options={"HIDDEN", "SKIP_SAVE"})
    # Where the starting policy came from, the result's format and whether it is an alternate.
    policy_note: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    result_format: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    result_role: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    source_rigged: BoolProperty(options={"HIDDEN", "SKIP_SAVE"})
    # How many captured objects the edit applies to together.
    source_count: IntProperty(default=1, options={"HIDDEN", "SKIP_SAVE"})
    policy: EnumProperty(
        name="Edit",
        items=(
            ("REMESH", "Replace geometry", "Adopt result geometry, UVs and mesh materials"),
            ("UV", "Replace active UVs", "Keep geometry; the result must be the same surface"),
            (
                "RETEXTURE",
                "Replace textures",
                "Preserve geometry; adopt result UVs and materials from the same surface",
            ),
            (
                "PARTS",
                "Replace with parts",
                "Keep the source as an empty mesh parent; adopt every mesh in the selected result as a part",
            ),
            (
                "RIG",
                "Attach rig",
                "Preserve source mesh data; attach weights and a compatible returned rig",
            ),
            (
                "ANIMATE",
                "Apply animation",
                "Keep this mesh, its skin and rig; add the returned clips to its armature",
            ),
        ),
        default="REMESH",
        options={"SKIP_SAVE"},
        update=_mesh_policy_changed,
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
            (
                "FIT",
                "Fit and verify",
                "Scale and move the result uniformly only if it then matches the source surface",
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
            # Without an explicit policy the review starts from the job's Edit 3D task.
            explicit = self.properties.is_property_set("policy")
            jobs, approval = runtime.prepare_mesh_application(
                self.context_id,
                self.request_id,
                self.expected_revision,
                context.scene,
                source,
                self.asset_id,
                policy=self.policy if explicit else None,
                # Unset, coordinates follow the policy: a verified fit, except for
                # ANIMATE and a REMESH that is not the job's own Remesh task, which
                # start on scene (or required local) coordinates.
                placement=self.placement if self.properties.is_property_set("placement") else None,
                keep_original=self.keep_original,
                original_source=self.original_source,
                review_placement=True,
            )
            self._jobs = jobs
            self.application_id = approval.identifier
            self.policy, self.placement = approval.policy, approval.placement
            self.remesh_task = approval.remesh_task
            self.policy_note = _policy_note(approval)
            self.result_role = {True: "primary", False: "alternate"}.get(approval.primary, "")
            self.result_format = saved_job_actions.MODEL_FORMATS.get(approval.format, "")
            targets = approval.targets
            self.source_count = len(targets)
            self.source_rigged = any(target.skin is not None for target in targets)
            # Several sources are each placed by their own transform.
            self.local_placement_required = (
                len(targets) == 1 and targets[0].obj.matrix_world.determinant() <= 0
            )
            self.scene_name = approval.scene_name
            self.target_name = _source_names(approval.target_names)
            self.is_reuse = approval.record.state.value == "applied"
            self.review_error = ""
        except MeshResultApplicationError as error:
            # A policy the captured sources cannot take, such as Replace geometry
            # for several objects, names its own reason.
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        except Exception:
            self.report(
                {"ERROR"},
                (
                    "Captured source changed or is unavailable; review a destination with Apply mesh edit"
                    if self.original_source
                    else "Choose one local mesh in Object Mode and inspect the saved result"
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
            several = self.source_count > 1
            if several and self.policy not in _SEVERAL_POLICIES:
                self.review_error = (
                    "Several objects: choose Replace active UVs, Replace textures or Attach rig"
                )
            elif several and self.placement == "LOCAL":
                self.review_error = "Several objects use scene coordinates or Fit and verify"
            elif self.source_rigged and self.policy not in {"RIG", "ANIMATE"}:
                self.review_error = "This mesh has a rig: choose Attach rig or Apply animation"
            elif not self.source_rigged and self.policy == "ANIMATE":
                self.review_error = "Apply animation needs a mesh skinned to an armature"
            else:
                self.review_error = "Target or options changed; cancel and review again"
        return True

    def draw(self, context):
        layout = self.layout
        several = self.source_count > 1
        layout.label(text=f"Scene: {self.scene_name}", icon="SCENE_DATA")
        if several:
            layout.label(text=f"Meshes ({self.source_count}): {self.target_name}", icon="MESH_DATA")
        else:
            layout.label(text=f"Mesh: {self.target_name}", icon="MESH_DATA")
        role = ", ".join(
            part
            for part in (self.result_format, self.result_role and f"{self.result_role} result")
            if part
        )
        layout.label(text=f"Saved result: {self.asset_id}" + (f" ({role})" if role else ""))
        if several:
            layout.label(
                text="Edit every object captured for this generation, or none.", icon="INFO"
            )
        elif self.original_source:
            layout.label(text="Use the unchanged source captured for this generation.", icon="INFO")
        if self.is_reuse:
            layout.label(text="Use saved results again; no new generation.", icon="INFO")
        layout.prop(self, "policy")
        if self.policy_note:
            layout.label(text=self.policy_note)
        if self.policy == "ANIMATE":
            _draw_animate(layout, self.review_error)
            return
        layout.prop(self, "placement")
        if self.local_placement_required:
            layout.label(text="Mirrored or zero-scale source: use object local coordinates.")
        layout.prop(self, "keep_original")
        if self.policy == "REMESH":
            layout.label(text="Replace this mesh's geometry, UVs and mesh materials.")
            layout.label(text="With Fit and verify, several result meshes are joined into one.")
        elif self.policy == "RIG":
            layout.label(text="Attach bone weights and rig; preserve geometry, UVs and materials.")
            if self.source_rigged:
                layout.label(
                    text="Replace this mesh's skin; the old rig stays, and Keep original uses it."
                )
            layout.label(text="The skin must match this surface. No morphs or mesh animation.")
            layout.label(
                text="Keep rig clips. Move the source and new rig group together afterward."
            )
            if several:
                layout.label(text="One returned rig skins every object; its group is in the scene.")
        elif self.policy == "PARTS":
            layout.label(text="Replace source geometry with an empty mesh parent and named parts.")
            layout.label(
                text="Treat each of the result's 2 to 128 meshes as a part, not a variant."
            )
            layout.label(text="Parts made of this surface split it, keeping its or their own UVs;")
            layout.label(text="other parts, such as remeshed ones, are copied from the result.")
        elif self.policy == "RETEXTURE":
            layout.label(text="Replace all UV layers and mesh materials; preserve geometry.")
            layout.label(text="The result must match this surface; triangles and seams are fine.")
        else:
            layout.label(text="Replace active UVs only; the result must match this surface.")
        layout.label(
            text="Keep each object's name, transforms, parenting and collections."
            if several
            else "Keep the source object's name, transforms, parenting and collections."
        )
        layout.label(
            text="Fit and verify scales uniformly, never rotates, and stops on any mismatch."
            if self.placement == "FIT"
            else "No fitting or scale adjustment: positions are used as they are."
            if self.policy in {"REMESH", "PARTS"}
            else "All result meshes form one surface. No fitting or scale adjustment."
        )
        layout.label(
            text="Keep original copies each object, unselected. Undo follows Blender settings."
            if several
            else "Keep original makes an unselected copy. Undo follows Blender settings."
        )
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


def _policy_note(approval):
    """Say whether the review's starting edit follows the job's Edit 3D task."""
    if approval.policy_source == "edit3d_task":
        if approval.edit3d_task == "ANIMATE" and approval.policy == "RIG":
            return "This mesh has no rig, so the Animate result starts on Attach rig."
        return f"Default edit follows this job's {task_label(approval.edit3d_task)} task."
    if approval.policy_source == "rigged_source":
        return "This mesh already has a rig, so the edit starts on Attach rig."
    if approval.policy_source == "default":
        return "Default edit is not from this job's task; check it."
    return ""


def _refusal(context_id, error):
    """A saved-result refusal in native words; the facade's context reason names MCP steps."""
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
    route_reason: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
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
        self.route_reason = target.reason or ""
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
        lines = render_lanes.first_frame_route_lines(self.route_reason, self.input_label)
        if lines:
            # The model cannot pin an exact first frame with the scene clip.
            layout.label(text=lines[0], icon="INFO")
            layout.label(text=lines[1])
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
            # A refusal before consumption, such as a retired connection, discards it too.
            self.cancel(context)
            self.report({"ERROR"}, f"First frame was not set: {_refusal(self.context_id, error)}")
            return {"CANCELLED"}
        except Exception:
            self.cancel(context)
            self.report({"ERROR"}, "First frame was not set; review the saved image and form again")
            return {"CANCELLED"}
        runtime.set_message("Verifying the saved image for the Render Video first frame")
        return {"FINISHED"}


def workflow_steps(record):
    """The owner's in-memory step projection for one of its workflow views, or None."""
    jobs = runtime.state.model_jobs
    if jobs is None or record.kind != "workflow" or jobs.views.get(record.local_id) is not record:
        return None
    return jobs.step_view(record.local_id)


def result_actions(record):
    """Describe one view's saved-job controls from in-memory state, without I/O."""
    review = None
    if "recover_blockout" in record.meta.get("recovery_actions", ()):
        jobs = runtime.state.blockout_jobs
        review = jobs.recovery.current(record.local_id, bpy.context.scene) if jobs else None
    return saved_job_actions.describe(
        record,
        runtime.state.job_context_id,
        RESULT_TYPES,
        blockout_review=review,
        workflow_steps=workflow_steps(record),
        listening=result_media.controller.listening(record.local_id),
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
    """Draw the view's descriptors, review previews and selected waveform from cached state."""
    row_key = row = None
    for item in result_actions(record):
        if not item.row:
            row_key = None
            draw_action(layout, item)
            continue
        if item.row != row_key:
            row_key, row = item.row, layout.row(align=True)
        draw_action(row, item)
    # Waiting workflow steps: Load previews and the review asset icons.
    review_previews.draw_step_previews(layout, record)
    result_media.draw(layout, record)


CLASSES = (
    SCENARIO_OT_inspect_saved_jobs,
    SCENARIO_OT_recover_job,
    SCENARIO_OT_link_cloud_job,
    SCENARIO_OT_read_saved_blockout,
    SCENARIO_OT_use_saved_blockout,
    SCENARIO_OT_import_saved_images,
    SCENARIO_OT_import_saved_media,
    SCENARIO_OT_set_saved_camera_background,
    SCENARIO_OT_add_saved_image_plane,
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
