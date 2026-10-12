# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""The "Trained models" section of the Image and Render Image forms (#97).

Drawn under the Model section by the sidebar, Studio and Render Image alike:
each chosen LoRA with its strength field, bounded by the range the current
base declares; a composition with its own LoRAs read-only; the reason a choice
cannot run; Add (the picker's Trained chip); and the project default row with
Use, Save and Clear. Drawing reads state only; the operators below change it
on the main thread and invalidate the price.
"""

import bpy
from bpy.props import IntProperty, StringProperty

from ..core.api import catalog, model_filter, trained_offers
from ..core.api.errors import ScenarioError
from . import runtime, trained_defaults, trained_models

CONCEPT_LINES = 6  # composition LoRAs listed before "and N more"


def _draw_wrapped(layout, text, icon):
    from .panels import draw_wrapped

    draw_wrapped(layout, text, icon)


def _strength_text(lane_state, slot):
    strength = trained_models.base_strength(lane_state.model_id)
    low, high = (strength.minimum, strength.maximum) if strength else (slot.fmin, slot.fmax)
    return f"Strength ({low:g} to {high:g})"


def _draw_lora(col, lane_state, lane, index, slot):
    if slot.has_scale:
        col.prop(slot, "scale", text=_strength_text(lane_state, slot))
        return
    base = trained_models.base_slot(lane_state.model_id)
    if base is not None and base.scale_default is not None:  # what the request sends now
        col.label(
            text=f"Strength: the base model's default ({base.scale_default:g})", icon="BLANK1"
        )
    if trained_models.base_strength(lane_state.model_id) is not None:
        op = col.operator("scenario.trained_set_strength", text="Set strength", icon="ADD")
        op.lane, op.index = lane, index


def _draw_concepts(col, slot):
    record = runtime.state.trained_records.get(slot.model_id)
    concepts = trained_offers.concepts(record) if record is not None else []
    if not concepts:
        return
    muted = col.column(align=True)
    muted.enabled = False
    count = len(concepts)
    muted.label(text=f"Combines {count} LoRA{'s' if count != 1 else ''}:", icon="BLANK1")
    for model_id, scale in concepts[:CONCEPT_LINES]:
        known = runtime.state.trained_records.get(model_id)
        name = known.name if known is not None and known.name else model_id
        strength = f" (strength {scale:g})" if scale is not None else ""
        muted.label(text=f"{name}{strength}", icon="BLANK1")
    if count > CONCEPT_LINES:
        muted.label(text=f"and {count - CONCEPT_LINES} more", icon="BLANK1")


def draw_default(layout, lane, view):
    """The project default row: what is saved and Use, Save and Clear (read-only)."""
    if not view.loaded:
        return
    col = layout.column(align=True)
    if view.error:
        _draw_wrapped(col, trained_defaults.UNREADABLE.format(reason=view.error), "ERROR")
    elif view.default is None:
        col.label(text="No project default for this form", icon="UNPINNED")
    else:
        _draw_wrapped(col, f"Project default: {view.label}", "PINNED")
        if view.status:
            _draw_wrapped(col, view.status, "ERROR" if view.unavailable else "TIME")
        elif view.in_use:
            col.label(text="This form uses the project default", icon="CHECKMARK")
    row = col.row(align=True)
    use = row.row(align=True)
    use.enabled = view.default is not None and not view.in_use and not view.unavailable
    use.operator("scenario.trained_default_apply", text="Use").lane = lane
    save = row.row(align=True)
    save.enabled = view.can_save
    op = save.operator("scenario.trained_default_save", text="Save")
    op.lane, op.context_id, op.revision = lane, view.context, view.revision
    clear = row.row(align=True)
    clear.enabled = view.default is not None and not view.error
    op = clear.operator("scenario.trained_default_clear", text="Clear")
    op.lane, op.context_id, op.revision = lane, view.context, view.revision


def draw(layout, lane_state, lane):
    """The form's trained models, their strengths and the project default (read-only)."""
    chosen = len(lane_state.trained)
    if lane not in trained_models.LANES and not chosen:
        return
    box = layout.box()
    box.label(text="Trained models", icon="SHADERFX")
    col = box.column(align=True)
    for index, slot in enumerate(lane_state.trained):
        row = col.row(align=True)
        name = trained_models.slot_name(slot)
        if slot.kind == catalog.TRAINED_COMPOSITION:
            row.label(text=f"{name} (composition)", icon="GROUP")
        else:
            row.label(text=name, icon="SHADERFX")
        op = row.operator("scenario.trained_remove", text="", icon="X")
        op.lane, op.index = lane, index
        if slot.kind == catalog.TRAINED_LORA:
            _draw_lora(col, lane_state, lane, index, slot)
        elif slot.kind == catalog.TRAINED_COMPOSITION:
            _draw_concepts(col, slot)
    reason = trained_models.selection_error(lane_state)
    if reason:
        _draw_wrapped(box, reason, "TIME" if reason == trained_models.LOADING else "ERROR")
    view = trained_defaults.view(lane_state, lane, reason)  # one route check per draw
    if lane in trained_models.LANES:
        op = box.operator("scenario.pick_model", text="Add LoRA or composition", icon="ADD")
        op.lane, op.category = lane, model_filter.TRAINED_CATEGORY
        draw_default(box, lane, view)
    if chosen or view.default is not None:
        box.label(text=trained_models.EXPERIMENTAL, icon="EXPERIMENTAL")


# -- operators ------------------------------------------------------------------------------
def _lane_state(context, lane):
    scene = getattr(context, "scene", None)
    return scene.scenario.lane_state(lane) if scene is not None else None


class SCENARIO_OT_trained_set_strength(bpy.types.Operator):
    bl_idname = "scenario.trained_set_strength"
    bl_label = "Set strength"
    bl_description = (
        "Give this LoRA a strength within the base model's range, starting at its visible "
        "start value; the price is requested again"
    )
    bl_options = {"INTERNAL"}
    lane: StringProperty(default="image")
    index: IntProperty(default=-1)

    def execute(self, context):
        lane_state = _lane_state(context, self.lane)
        if lane_state is None:
            return {"CANCELLED"}
        try:
            trained_models.set_strength(lane_state, self.index)
        except ScenarioError as err:
            self.report({"WARNING"}, err.reason)
            return {"CANCELLED"}
        return {"FINISHED"}


class SCENARIO_OT_trained_default_apply(bpy.types.Operator):
    bl_idname = "scenario.trained_default_apply"
    bl_label = "Use project default"
    bl_description = (
        "Replace this form's base model and LoRAs or composition with the project default "
        "of these credentials and project; the price is requested again"
    )
    bl_options = {"INTERNAL"}
    lane: StringProperty(default="image")

    def execute(self, context):
        lane_state = _lane_state(context, self.lane)
        if lane_state is None:
            return {"CANCELLED"}
        try:
            text = trained_defaults.use(lane_state, self.lane)
        except ScenarioError as err:
            self.report({"WARNING"}, err.reason)
            return {"CANCELLED"}
        self.report({"INFO"}, f"Project default: {text}")
        return {"FINISHED"}


class _ReviewedDefault:
    """Save and Clear carry the lane, selection and revision the user saw in the drawn row."""

    def _reviewed(self):
        cache = trained_defaults.cached()
        if cache is None or cache.context != self.context_id or self.revision < 0:
            return None
        return trained_defaults.saved(cache, self.lane)


class SCENARIO_OT_trained_default_save(_ReviewedDefault, bpy.types.Operator):
    bl_idname = "scenario.trained_default_save"
    bl_label = "Save as project default"
    bl_description = (
        "Save this form's base model and LoRAs or composition as the default of these "
        "credentials and project; nothing is priced or sent"
    )
    bl_options = {"INTERNAL"}
    lane: StringProperty(default="image")
    context_id: StringProperty(options={"SKIP_SAVE"})
    revision: IntProperty(default=-1, options={"SKIP_SAVE"})

    def invoke(self, context, event):
        current = self._reviewed()
        if current is None:
            return self.execute(context)
        return context.window_manager.invoke_confirm(
            self,
            event,
            title="Replace the project default?",
            message=f"Replaces {trained_defaults.label(current)} for these credentials and project",
            confirm_text="Replace default",
        )

    def execute(self, context):
        lane_state = _lane_state(context, self.lane)
        if lane_state is None:
            return {"CANCELLED"}
        try:
            trained_defaults.save(lane_state, self.lane, self.context_id, self.revision)
        except ScenarioError as err:
            self.report({"WARNING"}, err.reason)
            return {"CANCELLED"}
        self.report({"INFO"}, "Project default saved; no price was requested")
        return {"FINISHED"}


class SCENARIO_OT_trained_default_clear(_ReviewedDefault, bpy.types.Operator):
    bl_idname = "scenario.trained_default_clear"
    bl_label = "Clear project default"
    bl_description = (
        "Forget this form's project default for these credentials and project; the form "
        "keeps its current choice"
    )
    bl_options = {"INTERNAL"}
    lane: StringProperty(default="image")
    context_id: StringProperty(options={"SKIP_SAVE"})
    revision: IntProperty(default=-1, options={"SKIP_SAVE"})

    def invoke(self, context, event):
        current = self._reviewed()
        message = (
            f"Forgets {trained_defaults.label(current)} for these credentials and project"
            if current is not None
            else "Forgets this form's project default"
        )
        return context.window_manager.invoke_confirm(
            self,
            event,
            title="Clear the project default?",
            message=message,
            confirm_text="Clear default",
        )

    def execute(self, context):
        try:
            trained_defaults.clear(self.lane, self.context_id, self.revision)
        except ScenarioError as err:
            self.report({"WARNING"}, err.reason)
            return {"CANCELLED"}
        self.report({"INFO"}, "Project default cleared")
        return {"FINISHED"}


CLASSES = (
    SCENARIO_OT_trained_set_strength,
    SCENARIO_OT_trained_default_apply,
    SCENARIO_OT_trained_default_save,
    SCENARIO_OT_trained_default_clear,
)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(CLASSES):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass  # already unregistered (a partial registration or tests swapping the module)
