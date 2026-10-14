# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""The saved mesh-edit policy a review starts from, by the job's Edit 3D task."""

import pytest

from scenario.core.api import catalog
from scenario.core.scene import mesh_edit_policy as policy

ROTATING = "model_rodin-hyper3d-bang"  # listed by RETEXTURE and PARTS


@pytest.mark.parametrize(
    ("model_id", "expected"),
    [
        ("model_tripo-retopology", "REMESH"),
        ("model_meshy-7-retexture", "RETEXTURE"),
        ("model_meshy-uv-unwrap", "UV"),
        ("model_meshy-rigging", "RIG"),
        ("model_tripo-segmentation-v2", "PARTS"),
    ],
)
def test_a_model_with_one_task_starts_from_that_tasks_policy(model_id, expected):
    start = policy.default_policy(model_id)
    assert start == policy.DefaultPolicy(expected, expected, derived=True)


def test_every_applicable_task_names_a_policy_and_animate_depends_on_the_source():
    tasks = {task for task, _label, _description, _models in catalog.EDIT3D_TASKS}
    assert set(policy.TASK_POLICIES) == tasks - {"ANIMATE", "ALL"}
    # The task is known; the caller chooses from the captured source's skin.
    start = policy.default_policy("model_meshy-animation")
    assert start == policy.DefaultPolicy("REMESH", "ANIMATE", derived=False)
    assert policy.default_policy("model_cartwheel-text-to-motion").task == "ANIMATE"


def test_an_animate_job_keeps_a_skinned_rig_and_rigs_any_other_mesh():
    assert policy.animate_policy(True) == "ANIMATE"
    assert policy.animate_policy(False) == "RIG"


def test_an_ambiguous_or_unknown_model_keeps_the_fallback_without_a_task():
    assert policy.model_tasks(ROTATING) == ("RETEXTURE", "PARTS")
    for model_id in (ROTATING, "model_unknown", "workflow-id", None):
        assert policy.default_policy(model_id) == policy.DefaultPolicy("REMESH")


def test_the_submitted_task_wins_only_when_it_lists_the_model():
    assert policy.default_policy(ROTATING, "PARTS") == policy.DefaultPolicy(
        "PARTS", "PARTS", derived=True
    )
    assert policy.default_policy(ROTATING, "RETEXTURE").policy == "RETEXTURE"
    # ALL lists no model, and a task that does not list the model is ignored.
    assert policy.default_policy(ROTATING, "ALL") == policy.DefaultPolicy("REMESH")
    assert policy.default_policy("model_meshy-uv-unwrap", "RIG").policy == "UV"
    assert policy.default_policy("model_unknown", "RIG") == policy.DefaultPolicy("REMESH")


def test_task_labels_are_the_edit_3d_tab_names():
    assert policy.task_label("UV") == "UV Unwrap"
    assert policy.task_label("RIG") == "Rigging"
