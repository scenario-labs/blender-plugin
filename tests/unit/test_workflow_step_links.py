# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Step links of waiting workflow steps: the job flow, its workflow definition, fail closed.

The job flows below follow the shape a live `jobs.retrieve` returned for
private test workflows (IDs replaced): `custom-model`, `for-each` and
`user-approval` nodes carry no `dependsOn` or `inputs`, only `user-selection`
nodes list their inputs, and ForEach copies are `<template>__iter__<n>` nodes
without `loopNodeId` or `iterationIndex`. The definitions follow the
`workflows.retrieve` flow model: `inputs` with `ref`, `dependsOn` and
`loopBodyNodeIds`.
"""

import copy

import pytest

from scenario.core.jobs import workflow_nodes as nodes
from scenario.core.jobs.workflow_nodes import BLOCKED, StepError, definition_links, pending_steps

SIGNED = "https://cdn.example.invalid/asset?X-Signature=private-signature"
CREATED = "2026-10-10T10:56:00.366Z"
EDITED = "2026-10-10T10:23:21.000Z"
BG, PAD, GRID = "model_bg", "model_pad", "model_grid"


def ref(target, name=None):
    value = {"node": target}
    if name is not None:
        value["name"] = name
    return value


def produced(identifier, model, *assets, status="success"):
    return {
        "id": identifier,
        "type": "custom-model",
        "status": status,
        "modelId": model,
        "jobId": f"job_{identifier}",
        "assets": [{"assetId": asset, "url": SIGNED} for asset in assets],
    }


def job(*flow, created=CREATED, workflow="workflow"):
    return {
        "jobId": "remote",
        "jobType": "workflow",
        "status": "in-progress",
        "createdAt": created,
        "metadata": {"workflowId": workflow, "flow": list(flow)},
    }


def definition(*flow, updated=EDITED, identifier="workflow"):
    return {
        "id": identifier,
        "name": "Fixture workflow",
        "status": "ready",
        "updatedAt": updated,
        "thumbnail": {"assetId": "asset_thumb", "url": SIGNED},
        "flow": list(flow),
    }


def select_node(source, status="processing", identifier="select1"):
    return {
        "id": identifier,
        "type": "user-selection",
        "status": status,
        "items": ["asset_in1", "asset_in2", "asset_in3"],
        "inputs": [
            {"name": "images", "type": "file_array", "min": 2, "max": 2, "ref": source},
        ],
    }


# Selection over three workflow inputs feeding a ForEach background removal.
INTO_LOOP_JOB = (
    select_node(ref("workflow", "images1")),
    {"id": "loop1", "type": "for-each", "status": "pending"},
    {"id": "cutout1", "type": "custom-model", "status": "pending", "modelId": BG},
)
INTO_LOOP = definition(
    {
        "id": "select1",
        "type": "user-selection",
        "inputs": [
            {
                "name": "images",
                "type": "file_array",
                "min": 2,
                "max": 2,
                "ref": ref("workflow", "images1"),
            }
        ],
    },
    {
        "id": "loop1",
        "type": "for-each",
        "loopBodyNodeIds": ["cutout1"],
        "inputs": [{"name": "image0", "type": "file_array", "ref": ref("select1")}],
    },
    {
        "id": "cutout1",
        "type": "custom-model",
        "modelId": BG,
        "includeOutputsInWorkflowJob": True,
        "inputs": [{"name": "image", "type": "file", "ref": ref("loop1", "image0")}],
    },
)

# ForEach background removal over three inputs, then a selection feeding a grid.
AFTER_LOOP_JOB = (
    {"id": "loop1", "type": "for-each", "status": "success", "output": {"total": 3}},
    {"id": "cutout1", "type": "custom-model", "status": "skipped", "modelId": BG},
    produced("cutout1__iter__0", BG, "asset_cut0"),
    produced("cutout1__iter__1", BG, "asset_cut1"),
    produced("cutout1__iter__2", BG, "asset_cut2"),
    select_node(ref("loop1")),
    {"id": "grid1", "type": "custom-model", "status": "pending", "modelId": GRID},
)
AFTER_LOOP = definition(
    {
        "id": "loop1",
        "type": "for-each",
        "loopBodyNodeIds": ["cutout1"],
        "inputs": [{"name": "image0", "type": "file_array", "ref": ref("workflow", "images1")}],
    },
    {
        "id": "cutout1",
        "type": "custom-model",
        "modelId": BG,
        "inputs": [{"name": "image", "type": "file", "ref": ref("loop1", "image0")}],
    },
    {
        "id": "select1",
        "type": "user-selection",
        "inputs": [
            {"name": "images", "type": "file_array", "min": 2, "max": 2, "ref": ref("loop1")}
        ],
    },
    {
        "id": "grid1",
        "type": "custom-model",
        "modelId": GRID,
        "inputs": [{"name": "images", "type": "file_array", "ref": ref("select1")}],
    },
)

# Background removal, an approval gate, then a padding remover.
APPROVAL_JOB = (
    {"id": "approval1", "type": "user-approval", "status": "processing"},
    produced("cutout1", BG, "asset_cut"),
    {"id": "trim1", "type": "custom-model", "status": "pending", "modelId": PAD},
)
APPROVAL = definition(
    {
        "id": "cutout1",
        "type": "custom-model",
        "modelId": BG,
        "inputs": [{"name": "image", "type": "file", "ref": ref("workflow", "image1")}],
    },
    {"id": "approval1", "type": "user-approval", "dependsOn": ["cutout1"]},
    {
        "id": "trim1",
        "type": "custom-model",
        "modelId": PAD,
        "dependsOn": ["approval1"],
        "inputs": [{"name": "image", "type": "file", "ref": ref("cutout1")}],
    },
)


def only(flow, workflow=None, **options):
    links = None if workflow is None else definition_links(workflow, workflow_id="workflow")
    (step,) = pending_steps(
        job(*flow, **options), remote_job_id="remote", workflow_id="workflow", links=links
    )
    return step


def test_a_selection_feeding_a_loop_is_blocked_when_the_job_flow_omits_links():
    # The live defect: no link said that the loop reads the selection.
    step = only(INTO_LOOP_JOB)
    assert step.blocked == "unverified" and step.actions == ("reject",)
    assert not step.links_complete
    with pytest.raises(StepError) as error:
        nodes.validate_decision(step, "select", [0, 2])
    assert str(error.value) == BLOCKED["unverified"]
    assert "could not read how this workflow's steps connect" in str(error.value)
    assert nodes.validate_decision(step, "reject") is None


def test_the_definition_proves_that_the_selection_feeds_the_loop():
    step = only(INTO_LOOP_JOB, INTO_LOOP)
    assert step.blocked == "loop" and step.actions == ("reject",)
    assert step.links_complete
    with pytest.raises(StepError, match="ForEach loop"):
        nodes.validate_decision(step, "select", [0, 2])


def test_a_selection_after_a_loop_is_offered_only_with_the_definition():
    assert only(AFTER_LOOP_JOB).blocked == "unverified"
    step = only(AFTER_LOOP_JOB, AFTER_LOOP)
    assert step.blocked == "" and step.actions == ("select", "reject")
    assert step.links_complete
    assert nodes.validate_decision(step, "select", [0, 2]) == (0, 2)


def test_an_approval_lists_its_dependency_assets_from_the_definition():
    blind = only(APPROVAL_JOB)
    assert (blind.depends_on, blind.review_asset_ids, blind.links_complete) == ((), (), False)
    # Without a loop, an approval is still offered; only its review is incomplete.
    assert blind.actions == ("approve", "reject")
    step = only(APPROVAL_JOB, APPROVAL)
    assert step.depends_on == ("cutout1",)
    assert step.review_asset_ids == ("asset_cut",) and step.review_asset_total == 1
    assert step.links_complete and step.actions == ("approve", "reject")
    assert "https" not in repr(step) and "https" not in repr(step.summary())


def test_links_change_the_review_id():
    assert only(APPROVAL_JOB).review_id != only(APPROVAL_JOB, APPROVAL).review_id


def test_flows_without_a_loop_keep_offering_selection_when_links_are_missing():
    flow = (
        {"id": "split1", "type": "transform", "status": "success"},
        {
            "id": "select1",
            "type": "user-selection",
            "status": "processing",
            "items": ["a red cube", "a blue sphere", "a green cone"],
            "inputs": [
                {"name": "texts", "type": "string_array", "min": 1, "max": 1, "ref": ref("split1")}
            ],
        },
        {"id": "prompt1", "type": "transform", "status": "pending"},
        {"id": "image1", "type": "custom-model", "status": "pending", "modelId": "model_txt"},
    )
    step = only(flow)
    assert step.blocked == "" and step.actions == ("select", "reject")
    assert not step.links_complete


def loop_approval_job():
    return (
        {"id": "loop1", "type": "for-each", "status": "processing"},
        {"id": "cutout1", "type": "custom-model", "status": "skipped", "modelId": BG},
        {"id": "check1", "type": "user-approval", "status": "skipped"},
        produced("cutout1__iter__0", BG, "asset_cut0"),
        produced("cutout1__iter__1", BG, "asset_cut1"),
        {"id": "check1__iter__0", "type": "user-approval", "status": "success"},
        {"id": "check1__iter__1", "type": "user-approval", "status": "processing"},
    )


LOOP_APPROVAL = definition(
    {
        "id": "loop1",
        "type": "for-each",
        "loopBodyNodeIds": ["cutout1", "check1"],
        "inputs": [{"name": "image0", "type": "file_array", "ref": ref("workflow", "images1")}],
    },
    {
        "id": "cutout1",
        "type": "custom-model",
        "modelId": BG,
        "inputs": [{"name": "image", "type": "file", "ref": ref("loop1", "image0")}],
    },
    {"id": "check1", "type": "user-approval", "dependsOn": ["cutout1"]},
)


def test_an_approval_inside_a_loop_reviews_its_own_iteration():
    step = only(loop_approval_job(), LOOP_APPROVAL)
    assert step.node_id == "check1__iter__1"
    assert step.depends_on == ("cutout1__iter__1",)
    assert step.review_asset_ids == ("asset_cut1",)
    assert step.links_complete


@pytest.mark.parametrize(
    "change",
    [
        "edited_after_the_job",
        "undated_job",
        "another_workflow",
        "missing_node",
        "extra_node",
        "type_changed",
        "selection_ref_changed",
        "unknown_copy",
        "copy_of_a_node_outside_loops",
    ],
)
def test_a_definition_that_does_not_describe_the_job_is_not_trusted(change):
    flow = copy.deepcopy(list(AFTER_LOOP_JOB))
    workflow = copy.deepcopy(AFTER_LOOP)
    options = {}
    if change == "edited_after_the_job":
        workflow["updatedAt"] = "2026-10-10T10:56:00.367Z"
    elif change == "undated_job":
        options["created"] = None
    elif change == "another_workflow":
        workflow["id"] = "another"
    elif change == "missing_node":
        flow = [item for item in flow if item["id"] != "grid1"]
    elif change == "extra_node":
        flow.append({"id": "loop9", "type": "for-each", "status": "pending"})
    elif change == "type_changed":
        flow[-1]["type"] = "transform"
    elif change == "selection_ref_changed":
        flow[5]["inputs"][0]["ref"] = ref("workflow", "images1")
    elif change == "unknown_copy":
        flow.append(produced("cutout1__copy__3", BG, "asset_cut3"))
    elif change == "copy_of_a_node_outside_loops":
        flow.append(produced("grid1__iter__0", GRID, "asset_grid"))
    if change == "another_workflow":
        links = definition_links(workflow, workflow_id="another")
    else:
        links = definition_links(workflow, workflow_id="workflow")
    (step,) = pending_steps(
        job(*flow, **options), remote_job_id="remote", workflow_id="workflow", links=links
    )
    assert step.blocked == "unverified" and step.actions == ("reject",)
    assert not step.links_complete


def test_a_definition_edited_before_the_job_is_trusted():
    workflow = copy.deepcopy(AFTER_LOOP)
    workflow["updatedAt"] = CREATED
    assert only(AFTER_LOOP_JOB, workflow).blocked == ""


def test_definition_links_drop_values_and_urls():
    links = definition_links(APPROVAL, workflow_id="workflow")
    assert "https" not in repr(links) and "Signature" not in repr(links)
    assert "asset_thumb" not in repr(links) and BG not in repr(links)
    assert links.workflow_id == "workflow" and links.updated_at == EDITED


@pytest.mark.parametrize(
    "workflow",
    [
        None,
        [],
        definition(identifier="another"),
        {**APPROVAL, "flow": None},
        {**APPROVAL, "flow": []},
        {**APPROVAL, "flow": "unreadable"},
        {**APPROVAL, "flow": [{"id": "a", "type": "transform"}] * 2049},
        {**APPROVAL, "updatedAt": None},
        {**APPROVAL, "updatedAt": "yesterday"},
        {**APPROVAL, "updatedAt": "2026-10-10T10:23:21"},
        definition({"id": "a"}),
        definition({"id": 1, "type": "transform"}),
        definition({"id": "a", "type": "transform"}, {"id": "a", "type": "transform"}),
        definition({"id": "a", "type": "transform", "inputs": [{"ref": "a"}]}),
        definition({"id": "a", "type": "transform", "dependsOn": "b"}),
        definition({"id": "a", "type": "for-each", "loopBodyNodeIds": "b"}),
    ],
)
def test_unreadable_definitions_raise(workflow):
    with pytest.raises(StepError):
        definition_links(workflow, workflow_id="workflow")


def test_waiting_detects_processing_steps_without_raising():
    assert nodes.waiting(job(*INTO_LOOP_JOB))
    assert not nodes.waiting(job(*AFTER_LOOP_JOB[:5]))
    for value in (
        None,
        {},
        {"metadata": "x"},
        {"metadata": {"flow": "x"}},
        {"metadata": {"flow": [1]}},
    ):
        assert not nodes.waiting(value)
