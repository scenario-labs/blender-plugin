# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Native review of waiting workflow approval and selection steps.

Jobs rows and the Studio Workflows page draw one review control per waiting
step from the shared saved-job descriptors; drawing reads only the in-memory
projection of `ModelJobs`. The review dialog captures the step when it opens
and sends the person's one decision through `runtime.decide_workflow_step`, the
entry local MCP `decide_workflow_step` also uses. That entry checks the context
token, the saved revision and the step's `review_id` again, and nothing is
retried. Rejecting a waiting step ("Stop workflow") is the only way to stop a
workflow: Scenario has no endpoint that cancels a running step.
"""

import textwrap
from dataclasses import dataclass

import bpy
from bpy.props import BoolProperty, CollectionProperty, EnumProperty, IntProperty, StringProperty

from ..core.api.errors import ScenarioError
from ..core.jobs import workflow_nodes
from ..core.ui import saved_job_actions
from . import job_recovery, runtime

# Dialog text width in characters at the default popup width.
WRAP = 70
# Smallest dialog width: the Generate workflow confirmation's, which wraps at the same width.
MIN_WIDTH = 540
# Lines of one text candidate drawn in the dialog before it is shortened.
ITEM_LINES = 12
CONTINUE_TEXT = (
    "Continuing runs the remaining steps of this job, which spend credits. The charge "
    "after a decision is not verified against the approved price."
)
STOP_TEXT = (
    "Rejecting this step cancels the workflow; completed steps stay charged. If the step "
    "is inside a loop, Scenario may stop only that loop; the refreshed status is "
    "authoritative."
)
BLOCKED_CONTINUE = "Choose Stop workflow to reject this step, or Cancel to keep it waiting."
# An approval whose step links could not all be read; see workflow_nodes.
UNLINKED = (
    "This extension could not read how this workflow's steps connect, so results to "
    "review may be missing here. Check them in Scenario before approving."
)
ONCE_TEXT = (
    "The decision is sent once and never repeated. If its outcome is unknown, wait until "
    "the job is read again before deciding."
)


def workflow_name(workflow_id):
    """A workflow's display name from the loaded catalog or a loaded form, else its ID.

    Reads memory and scene data only, so drawing code may call it.
    """
    owner = runtime.state.workflow_controls
    for record in owner.catalog if owner is not None else ():
        if isinstance(record, dict) and record.get("id") == workflow_id and record.get("name"):
            return str(record["name"])
    for scene in bpy.data.scenes:
        form = scene.scenario_workflow
        if form.loaded_id == workflow_id and form.title:
            return form.title
    return workflow_id


@dataclass(frozen=True)
class StepReview:
    """One waiting step as the dialog showed it, with the job it belongs to."""

    context_id: str
    request_id: str
    revision: int
    job_id: str
    workflow: str
    cost: str | None
    step: workflow_nodes.PendingStep
    error: str = ""

    @property
    def can_continue(self):
        """Whether approving or selecting is offered, as opposed to rejecting only."""
        return any(action in self.step.actions for action in ("approve", "select"))


def prepare(context_id, request_id, expected_revision, node_id, review_id):
    """Capture a current waiting step for review; reads memory and the store only."""
    jobs = runtime.state.model_jobs
    if (
        jobs is None
        or context_id != runtime.state.job_context_id
        or not runtime.catalog_selection_matches()
    ):
        raise ScenarioError(0, "The selected job context changed; inspect saved jobs again")
    record, step = jobs.waiting_step(request_id, expected_revision, node_id)
    if step.review_id != review_id:
        raise ScenarioError(0, "The workflow step changed; review it again")
    if not step.actions:
        raise ScenarioError(0, workflow_nodes.BLOCKED["unidentified"])
    cost = record.intent.quote_cost
    return StepReview(
        context_id=context_id,
        request_id=request_id,
        revision=record.revision,
        job_id=record.remote_job_id,
        workflow=workflow_name(record.intent.target_id),
        cost=None if cost is None else str(cost),
        step=step,
        error=jobs.step_view(request_id).error,
    )


def decision(review, choice, picks=()):
    """Return the action and picks for one dialog choice, or raise ValueError.

    Picks are candidate indices in listed order. Stopping needs the explicit
    `STOP` choice; a blocked selection offers nothing else.
    """
    step = review.step
    if choice == "STOP":
        if "reject" not in step.actions:
            raise ValueError(workflow_nodes.BLOCKED["unidentified"])
        return "reject", None
    if choice != "CONTINUE":
        raise ValueError("Choose a decision")
    if not review.can_continue:
        raise ValueError(BLOCKED_CONTINUE)
    if step.node_type == "user-approval":
        return "approve", None
    return "select", workflow_nodes.validate_selection(step, sorted(picks))


def send(review, action, picks=None):
    """Queue one decision through the shared native and MCP entry; never retried."""
    return runtime.decide_workflow_step(
        review.context_id,
        review.request_id,
        review.revision,
        review.step.node_id,
        review.step.review_id,
        action,
        None if picks is None else list(picks),
    )


def step_title(step):
    """What the step asks for, with its loop index when it has one."""
    if step.node_type == "user-approval":
        text = "Approval step"
    elif step.minimum is None or step.maximum is None or not step.items:
        text = "Selection step with unreadable candidates or limits"
    else:
        upper = min(step.maximum, len(step.items))
        count = str(upper) if step.minimum == upper else f"{step.minimum} to {upper}"
        text = f"Selection step: choose {count} of {len(step.items)}"
    if step.iteration_index is not None:
        text += f" (loop index {step.iteration_index})"
    return text


def _wrapped(layout, text, icon="NONE", width=WRAP):
    for index, line in enumerate(textwrap.wrap(text, width)):
        layout.label(text=line, icon=icon if index == 0 else "NONE")


def _draw_approval(box, step):
    if not step.links_complete:
        _wrapped(box, UNLINKED, "ERROR")
    if not step.review_asset_ids:
        box.label(text="No result assets are listed for this step.")
        return
    box.label(text="Results to review before approving:")
    for asset_id in step.review_asset_ids:
        box.label(text=asset_id, icon="FILE")
    hidden = step.review_asset_total - len(step.review_asset_ids)
    if hidden > 0:
        box.label(text=f"{hidden} more result assets are not listed")
    box.label(text="Open these assets in Scenario to see them.")


def _draw_selection(box, step, candidates, choosable):
    if step.blocked:
        _wrapped(box, workflow_nodes.BLOCKED[step.blocked], "ERROR")
    kind = "asset IDs" if step.item_kind == "asset" else "texts"
    box.label(text=f"Candidates ({kind}), in listed order:")
    if choosable:
        count = sum(1 for item in candidates if item.selected)
        upper = min(step.maximum, len(step.items))
        bounds = str(upper) if step.minimum == upper else f"{step.minimum} to {upper}"
        box.label(
            text=f"Selected {count}; choose {bounds}",
            icon="CHECKMARK" if step.minimum <= count <= upper else "ERROR",
        )
    for index, item in enumerate(candidates):
        text = f"{index + 1}." if step.item_kind == "text" else f"{index + 1}. {item.label}"
        row = box.row()
        if choosable:
            row.prop(item, "selected", text=text)
        else:
            row.label(text=text)
        if step.item_kind == "text":
            column = box.column(align=True)
            lines = textwrap.wrap(item.label, WRAP - 4) or [""]
            for line in lines[:ITEM_LINES]:
                column.label(text=f"    {line}")
            if len(lines) > ITEM_LINES:
                column.label(text=f"    (first {ITEM_LINES} of {len(lines)} lines shown)")


class ScenarioWorkflowStepItem(bpy.types.PropertyGroup):
    """One selection candidate in the review dialog; never saved."""

    label: StringProperty()
    selected: BoolProperty(name="Select", default=False)


class SCENARIO_OT_review_workflow_step(bpy.types.Operator):
    bl_idname = "scenario.review_workflow_step"
    bl_label = "Review workflow step"
    bl_description = (
        "Review a waiting workflow approval or selection, then approve, select or stop the "
        "workflow once"
    )

    context_id: StringProperty(options={"HIDDEN"})
    request_id: StringProperty(options={"HIDDEN"})
    expected_revision: IntProperty(min=0, options={"HIDDEN"})
    node_id: StringProperty(options={"HIDDEN"})
    review_id: StringProperty(options={"HIDDEN"})
    decision: EnumProperty(
        name="Decision",
        items=(
            ("CONTINUE", "Continue", "Approve, or send the selected items, and continue"),
            ("STOP", "Stop workflow", "Reject this step; Scenario stops the workflow"),
        ),
        default="CONTINUE",
        options={"SKIP_SAVE"},
    )
    candidates: CollectionProperty(type=ScenarioWorkflowStepItem, options={"SKIP_SAVE"})

    @classmethod
    def poll(cls, context):
        from .operators import _network_poll

        return _network_poll(cls, context)

    def invoke(self, context, event):
        try:
            review = prepare(
                self.context_id,
                self.request_id,
                self.expected_revision,
                self.node_id,
                self.review_id,
            )
        except ScenarioError as error:
            self.report({"ERROR"}, error.reason)
            return {"CANCELLED"}
        except Exception:
            self.report({"ERROR"}, "Could not review this step; inspect the saved job again")
            return {"CANCELLED"}
        self._review = review
        # Operator properties only, set when the dialog opens, never while drawing.
        self.decision = "CONTINUE"
        self.candidates.clear()
        for value in review.step.items:
            item = self.candidates.add()
            item.label = value
            item.selected = False
        try:
            from .studio import popup_width

            width = popup_width(context)
        except Exception:
            width = 560
        return context.window_manager.invoke_props_dialog(
            self,
            width=max(width, MIN_WIDTH),
            title="Review workflow step",
            confirm_text="Send decision",
        )

    def check(self, context):
        # Redraw for the consequence text of the chosen decision.
        return True

    def draw(self, context):
        layout = self.layout
        review = getattr(self, "_review", None)
        if review is None:
            layout.label(text="Review the workflow step again", icon="ERROR")
            return
        step = review.step
        layout.label(text=f"Workflow: {review.workflow}", icon="NODETREE")
        layout.label(text=f"Job: {review.job_id}")
        layout.label(
            text=f"Approved price: {review.cost} CU"
            if review.cost is not None
            else "Approved price: not recorded"
        )
        layout.label(text=step_title(step), icon="QUESTION")
        layout.label(text=f"Step ID: {step.node_id}")
        if review.error:
            _wrapped(layout, f"Last decision: {review.error}", "ERROR")
        box = layout.box()
        if step.node_type == "user-approval":
            _draw_approval(box, step)
        else:
            _draw_selection(box, step, self.candidates, review.can_continue)
        layout.separator(factor=0.5)
        # One continuous segmented control with equal cells (UI_STYLE "Tabs and
        # segmented choices"); the Select cell alone may be disabled.
        split = layout.split(factor=0.5, align=True)
        go = split.row(align=True)
        go.enabled = review.can_continue
        go.prop_enum(
            self,
            "decision",
            "CONTINUE",
            text="Approve" if step.node_type == "user-approval" else "Select",
        )
        split.prop_enum(self, "decision", "STOP", text="Stop workflow")
        if self.decision == "STOP":
            _wrapped(layout, STOP_TEXT, "ERROR")
        elif review.can_continue:
            _wrapped(layout, CONTINUE_TEXT, "INFO")
            if step.node_type == "user-selection":
                layout.label(text="Selected items are sent in their listed order.")
        else:
            _wrapped(layout, BLOCKED_CONTINUE, "INFO")
        _wrapped(layout, ONCE_TEXT)

    def execute(self, context):
        # Single use: a second execute without a fresh review sends nothing.
        review, self._review = getattr(self, "_review", None), None
        if review is None:
            self.report({"ERROR"}, "Review the workflow step again before deciding")
            return {"CANCELLED"}
        try:
            if len(self.candidates) != len(review.step.items):
                raise ValueError("The candidates changed; review the step again")
            picks = [index for index, item in enumerate(self.candidates) if item.selected]
            action, picks = decision(review, self.decision, picks)
            send(review, action, picks)
        except ScenarioError as error:
            self.report({"ERROR"}, error.reason)
            return {"CANCELLED"}
        except ValueError as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        except Exception:
            self.report({"ERROR"}, "The decision was not sent; inspect the saved job again")
            return {"CANCELLED"}
        runtime.set_message(
            "Sending Stop workflow once; the refreshed job status shows the outcome"
            if action == "reject"
            else "Sending your decision once; follow the job in Jobs"
        )
        return {"FINISHED"}


def pending_views():
    """Workflow views of the current owner with a waiting step or a decision in flight.

    A view stays listed while an automatic refresh is in flight, when its
    controls are hidden, as long as its steps are projected for its saved
    revision. Reads only in-memory views and projections, so drawing code may
    call it.
    """
    jobs = runtime.state.model_jobs
    if jobs is None:
        return ()
    views = []
    for view in runtime.state.jobs_view:
        if view.kind != "workflow" or view.meta.get("saved_state") != "remote":
            continue
        steps = job_recovery.workflow_steps(view)
        if steps is None:
            continue
        projected = bool(steps.steps) and steps.revision == view.meta.get("saved_revision")
        if projected or steps.deciding or "review_step" in view.meta.get("recovery_actions", ()):
            views.append(view)
    return tuple(views)


def draw_pending(layout, context):
    """Studio Workflows section listing waiting steps; reads only, never queues work."""
    views = pending_views()
    if not views:
        return
    box = layout.box()
    box.label(text="Waiting for your decision", icon="QUESTION")
    for view in views:
        column = box.column(align=True)
        column.label(text=workflow_name(view.model_id), icon="NODETREE")
        column.label(text=f"Job: {view.job_id or view.local_id}")
        for item in job_recovery.result_actions(view):
            if (
                item.action == "review_step"
                or item.key.partition(":")[0] in saved_job_actions.DECISION_ROWS
            ):
                job_recovery.draw_action(column, item)


CLASSES = (ScenarioWorkflowStepItem, SCENARIO_OT_review_workflow_step)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
