# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Waiting workflow approval and selection steps projected from retrieved jobs."""

import ast
import copy
import json
from pathlib import Path

import pytest

from scenario.core.jobs import workflow_nodes as nodes
from scenario.core.jobs.workflow_nodes import BLOCKED, StepError, pending_steps

ROOT = Path(__file__).resolve().parents[2]
SIGNED = "https://cdn.example.invalid/asset?X-Signature=private-signature"


def job(*flow, workflow="workflow", **fields):
    return {
        "jobId": "remote",
        "jobType": "workflow",
        "status": "in-progress",
        "metadata": {"workflowId": workflow, "flow": list(flow)},
        **fields,
    }


def node(identifier, kind="model", status="success", **fields):
    return {"id": identifier, "type": kind, "status": status, **fields}


def produced(identifier, *assets):
    return node(identifier, assets=[{"assetId": asset, "url": SIGNED} for asset in assets])


def approval(identifier="approve", status="processing", **fields):
    return node(identifier, "user-approval", status, **fields)


def selection(
    identifier="pick", items=("asset_a", "asset_b", "asset_c"), kind="file_array", **array
):
    return node(
        identifier,
        "user-selection",
        "processing",
        items=list(items),
        inputs=[{"name": "choices", "type": kind, **array}],
    )


def steps(*flow, **options):
    return pending_steps(job(*flow, **options), remote_job_id="remote", workflow_id="workflow")


def only(*flow):
    (step,) = steps(*flow)
    return step


def test_approval_reviews_its_dependencies_assets_without_urls():
    step = only(
        produced("render", "asset_a", "asset_b"),
        produced("other", "asset_z"),
        approval(dependsOn=["render", "missing"]),
    )
    assert (step.node_id, step.node_type) == ("approve", "user-approval")
    assert step.depends_on == ("render", "missing")
    assert step.review_asset_ids == ("asset_a", "asset_b") and step.review_asset_total == 2
    assert step.actions == ("approve", "reject") and step.blocked == ""
    assert (step.items, step.item_kind, step.minimum, step.maximum) == ((), None, None, None)
    report = json.dumps(step.summary())
    assert "https" not in repr(step) and "https" not in report and "Signature" not in report


def test_review_assets_are_unique_valid_and_bounded():
    many = [f"asset_{index}" for index in range(60)]
    step = only(
        produced("first", *many[:30], "asset_0"),
        node("second", assets=[*({"assetId": a, "url": SIGNED} for a in many[30:]), "bad", {}]),
        node("third", assets=[{"assetId": "not/an id"}, {"assetId": 7}]),
        approval(dependsOn=["first", "second", "third"]),
    )
    assert step.review_asset_ids == tuple(many[:50])
    assert step.review_asset_total == 60


@pytest.mark.parametrize(
    "kind,items,expected",
    [
        ("file_array", ("asset_a", "asset_b"), "asset"),
        ("string_array", ("A red cup", "Ein blauer Becher ☕"), "text"),
    ],
)
def test_selection_candidates_and_default_bounds(kind, items, expected):
    step = only(selection(items=items, kind=kind))
    assert step.items == items and step.item_kind == expected
    assert (step.minimum, step.maximum) == (1, 100)
    assert step.actions == ("select", "reject") and step.blocked == ""


def test_declared_bounds_and_integral_floats_are_kept():
    step = only(selection(min=2.0, max=3))
    assert (step.minimum, step.maximum) == (2, 3)
    assert step.summary()["min"] == 2 and step.summary()["max"] == 3


@pytest.mark.parametrize(
    "change",
    [
        {"min": 0},
        {"min": 3, "max": 2},
        {"max": 101},
        {"min": 1.5},
        {"max": True},
        {"min": "1"},
        {"min": 4},  # more than the three candidates
        {"items": []},
        {"items": [f"asset_{index}" for index in range(51)]},
        {"items": ["asset_a", 7]},
        {"items": ["not an id"]},
        {"items": "asset_a"},
        {"kind": "string_array", "items": ["x" * 4097]},
        {"kind": "string_array", "items": ["\ud800"]},
        {"kind": "file"},
        {"inputs": [{"name": "a", "type": "file_array"}, {"name": "b", "type": "string_array"}]},
        {"inputs": "unreadable"},
    ],
)
def test_unreadable_selections_offer_only_rejection(change):
    change = dict(change)
    options = {key: change.pop(key) for key in ("kind", "min", "max") if key in change}
    array = {key: value for key, value in options.items() if key in ("min", "max")}
    value = selection(kind=options.get("kind", "file_array"), **array)
    value.update(change)
    step = only(value)
    assert step.blocked == "unsupported" and step.actions == ("reject",)
    with pytest.raises(StepError, match="cannot be reviewed here"):
        nodes.validate_decision(step, "select", [0])
    assert nodes.validate_decision(step, "reject") is None


def test_oversized_text_items_are_not_projected():
    step = only(selection(kind="string_array", items=["ok", "x" * 4097]))
    assert step.items == () and step.blocked == "unsupported"


def test_loop_iteration_copies_are_separate_steps():
    first, second = steps(
        approval("check#0", iterationIndex=0, loopNodeId="loop"),
        approval("check#1", iterationIndex=1.0, loopNodeId="loop"),
    )
    assert (first.iteration_index, second.iteration_index) == (0, 1)
    assert first.loop_node_id == second.loop_node_id == "loop"
    assert first.review_id != second.review_id


def test_only_processing_approval_and_selection_nodes_wait():
    assert (
        steps(
            approval(status="pending"),
            approval("done", status="success"),
            approval("rejected", status="rejected"),
            node("future", "user-review", "processing"),
            node("model", "model", "processing"),
        )
        == ()
    )


@pytest.mark.parametrize(
    "value",
    [
        None,
        [],
        {"jobId": "another", "jobType": "workflow"},
        {"jobId": "remote", "jobType": "custom"},
        {"jobId": "remote"},
        job(workflow="another-workflow"),
        {**job(), "metadata": {"input": {"workflowId": "another-workflow"}, "flow": []}},
        {**job(), "metadata": "unreadable"},
        {**job(), "metadata": {"flow": {"id": "a"}}},
        {**job(), "metadata": {"flow": [node("a")] * 2049}},
        job("not a node"),
        job({"id": 1, "type": "model", "status": "success"}),
        job({"id": "a", "type": "model"}),
    ],
)
def test_malformed_or_other_jobs_raise(value):
    with pytest.raises(StepError):
        pending_steps(value, remote_job_id="remote", workflow_id="workflow")


def test_jobs_without_metadata_or_flow_have_no_steps():
    for value in (
        {"jobId": "remote", "jobType": "workflow"},
        {"jobId": "remote", "jobType": "workflow", "metadata": {"workflowId": "workflow"}},
    ):
        assert pending_steps(value, remote_job_id="remote", workflow_id="workflow") == ()


@pytest.mark.parametrize(
    "downstream",
    [
        # Direct array input of a ForEach loop.
        [node("loop", "for-each", "pending", inputs=[{"name": "a", "ref": {"node": "pick"}}])],
        # Through an intermediate node.
        [
            node("t", "transform", "pending", inputs=[{"name": "a", "ref": {"node": "pick"}}]),
            node("loop", "for-each", "pending", inputs=[{"name": "a", "ref": {"node": "t"}}]),
        ],
        # A control dependency, a conditional reference and a nested input.
        [node("loop", "for-each", "pending", dependsOn=["pick"])],
        [
            node(
                "loop",
                "for-each",
                "pending",
                inputs=[{"name": "a", "ref": {"conditional": ["pick"]}}],
            )
        ],
        [
            node(
                "m",
                "model",
                "pending",
                inputs=[
                    {"name": "a", "type": "inputs_array", "items": [[{"ref": {"node": "pick"}}]]}
                ],
            ),
            node("loop", "for-each", "pending", dependsOn=["m"]),
        ],
        # A nested workflow may loop over the items without showing it here.
        [node("inner", "workflow", "pending", inputs=[{"name": "a", "ref": {"node": "pick"}}])],
    ],
)
def test_selections_feeding_a_loop_are_blocked_but_can_be_rejected(downstream):
    step = only(selection(), *downstream)
    assert step.blocked == "loop" and step.actions == ("reject",)
    with pytest.raises(StepError) as error:
        nodes.validate_decision(step, "select", [0])
    assert str(error.value) == BLOCKED["loop"]
    assert nodes.validate_decision(step, "reject") is None


def test_loops_that_do_not_read_the_selection_do_not_block_it():
    step = only(
        node("loop", "for-each", "success", inputs=[{"name": "a", "ref": {"node": "workflow"}}]),
        selection(inputs=[{"name": "c", "type": "file_array", "ref": {"node": "loop"}}]),
        node("after", "model", "pending", inputs=[{"name": "a", "ref": {"node": "pick"}}]),
    )
    assert step.blocked == "" and step.actions == ("select", "reject")


def test_unreadable_references_block_selections_only_when_a_loop_exists():
    unreadable = node("odd", "model", "pending", inputs=[{"name": "a", "ref": "pick"}])
    assert only(selection(), unreadable).blocked == ""
    looped = only(selection(), unreadable, node("loop", "for-each", "pending"))
    assert looped.blocked == "loop"


@pytest.mark.parametrize("identifier", [" padded", "line\nbreak", "bidi‮", "x" * 1025, ""])
def test_unsendable_node_ids_offer_no_decision(identifier):
    step = only(approval(identifier))
    assert step.blocked == "unidentified" and step.actions == ()
    with pytest.raises(StepError, match="node ID is unreadable or not unique"):
        nodes.validate_decision(step, "reject")


def test_repeated_waiting_node_ids_offer_no_decision():
    first, second = steps(approval("same"), approval("same"))
    assert first.actions == second.actions == ()
    assert first.blocked == second.blocked == "unidentified"


def test_review_id_binds_the_projection_and_remote_job_but_not_signed_urls():
    base = job(produced("render", "asset_a"), approval(dependsOn=["render"]))
    (step,) = pending_steps(base, remote_job_id="remote", workflow_id="workflow")
    resigned = copy.deepcopy(base)
    resigned["metadata"]["flow"][0]["assets"][0]["url"] = SIGNED + "-renewed"
    resigned["progress"] = 0.5
    (same,) = pending_steps(resigned, remote_job_id="remote", workflow_id="workflow")
    assert same.review_id == step.review_id
    changed = copy.deepcopy(base)
    changed["metadata"]["flow"][0]["assets"].append({"assetId": "asset_b", "url": SIGNED})
    (other,) = pending_steps(changed, remote_job_id="remote", workflow_id="workflow")
    assert other.review_id != step.review_id
    assert nodes.review_id(step, "another-remote") != step.review_id
    assert len(step.review_id) == 64 and int(step.review_id, 16) >= 0


def test_selection_validation_keeps_order_and_enforces_bounds():
    step = only(selection(min=2, max=3, items=("a1", "a2", "a3", "a4")))
    assert nodes.validate_decision(step, "select", [3, 0]) == (3, 0)
    assert nodes.validate_decision(step, "select", (1, 2, 0)) == (1, 2, 0)
    for picks, message in [
        ([0], "Select 2 to 3 items"),
        ([0, 1, 2, 3], "Select 2 to 3 items"),
        ([0, 0], "at most once"),
        ([0, 4], "listed candidates"),
        ([0, -1], "listed candidates"),
        ([0, True], "integer indices"),
        ([0, 1.0], "integer indices"),
        ("01", "list of indices"),
        (None, "list of indices"),
    ]:
        with pytest.raises(StepError, match=message):
            nodes.validate_decision(step, "select", picks)


def test_selection_upper_bound_follows_the_candidates():
    step = only(selection(min=2, max=10, items=("a1", "a2")))
    with pytest.raises(StepError, match="Select exactly 2 items"):
        nodes.validate_decision(step, "select", [0])
    one = only(selection(items=("a1",)))
    with pytest.raises(StepError, match="Select exactly 1 item$"):
        nodes.validate_decision(one, "select", [])


def test_decisions_must_match_the_step_type():
    approve = only(approval())
    pick = only(selection())
    for step, action in [(approve, "select"), (pick, "approve"), (approve, "cancel"), (pick, 1)]:
        with pytest.raises(StepError, match="decision this workflow step accepts"):
            nodes.validate_decision(step, action, [0] if action == "select" else None)
    with pytest.raises(StepError, match="Only a selection"):
        nodes.validate_decision(approve, "approve", [0])
    with pytest.raises(StepError, match="Only a selection"):
        nodes.validate_decision(pick, "reject", [0])
    assert nodes.validate_decision(approve, "approve") is None


def test_summary_is_json_ready_and_complete():
    step = only(selection(kind="string_array", items=("a", "b")))
    summary = step.summary()
    assert json.loads(json.dumps(summary)) == summary
    assert set(summary) == {
        "node_id",
        "type",
        "iteration_index",
        "loop_node_id",
        "depends_on",
        "review_asset_ids",
        "review_asset_total",
        "items",
        "item_kind",
        "min",
        "max",
        "actions",
        "blocked",
        "review_id",
    }
    assert summary["blocked"] is None and summary["actions"] == ["select", "reject"]


def test_hostile_reference_nesting_is_bounded():
    deep = [{"name": "a", "type": "inputs_array", "items": [[{"name": "b"}] * 1000] * 200}]
    step = only(selection(), node("m", "model", "pending", inputs=deep), node("l", "for-each"))
    # The budget marks the flow unreadable, which keeps the selection blocked.
    assert step.blocked == "loop"


def test_parser_stays_free_of_blender_and_network_modules():
    tree = ast.parse((ROOT / "scenario/core/jobs/workflow_nodes.py").read_text())
    imported = {
        alias.name.split(".")[0]
        for item in ast.walk(tree)
        if isinstance(item, (ast.Import, ast.ImportFrom))
        for alias in item.names
    }
    modules = {
        item.module.split(".")[0]
        for item in ast.walk(tree)
        if isinstance(item, ast.ImportFrom) and item.module
    }
    assert not ({"bpy", "httpx", "scenario_sdk"} & (imported | modules))
