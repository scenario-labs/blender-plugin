# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""The in-place edit a saved Edit 3D job's review starts from. No bpy.

A job's Edit 3D task is the one it was submitted with when that task lists the
job's model, otherwise the model's only task. A model that serves two tasks
(Rodin Bang retextures and splits into parts) has no task of its own. The task
picks the default saved mesh-edit policy; ANIMATE, an unknown model and an
ambiguous one keep REMESH, which the review reports as not derived from the job.
The default only starts a review: an explicit choice always replaces it.
"""

from dataclasses import dataclass

from ..api.catalog import EDIT3D_TASKS

# Edit 3D tasks whose results a saved mesh edit applies in place, by policy.
TASK_POLICIES = {
    "REMESH": "REMESH",
    "RETEXTURE": "RETEXTURE",
    "UV": "UV",
    "RIG": "RIG",
    "PARTS": "PARTS",
}
FALLBACK_POLICY = "REMESH"


@dataclass(frozen=True)
class DefaultPolicy:
    """The starting policy, and the job's Edit 3D task when one is known."""

    policy: str
    task: str | None = None
    # Whether the policy follows the task; False keeps the fallback.
    derived: bool = False


def model_tasks(model_id):
    """The Edit 3D tasks that list this model, in catalog order."""
    return tuple(task for task, _label, _description, models in EDIT3D_TASKS if model_id in models)


def task_label(task):
    """The task's display name, such as Retexture or UV Unwrap."""
    return next((label for task_id, label, _d, _m in EDIT3D_TASKS if task_id == task), task)


def job_task(model_id, submitted_task=None):
    """The submitted task when it lists the model, else the model's only task, else None."""
    tasks = model_tasks(model_id)
    if submitted_task in tasks:
        return submitted_task
    return tasks[0] if len(tasks) == 1 else None


def default_policy(model_id, submitted_task=None):
    """The policy a saved mesh-edit review starts from for this job."""
    task = job_task(model_id, submitted_task)
    policy = TASK_POLICIES.get(task)
    if policy is None:
        return DefaultPolicy(FALLBACK_POLICY, task)
    return DefaultPolicy(policy, task, derived=True)
