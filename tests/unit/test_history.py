# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
from decimal import Decimal
from types import SimpleNamespace

import pytest

from scenario.core import history
from scenario.core.jobs.records import JobRecord


def test_entries_merge_cloud_jobs_with_local_files():
    local = JobRecord.new(lane="image", kind="image", model_id="model_g", body={})
    local.job_id, local.status, local.files = "job_a", "success", ["/out/a.png"]
    jobs = [
        {
            "jobId": "job_a",
            "jobType": "custom",
            "status": "success",
            "createdAt": "2026-08-28T07:37:09.434Z",
            "billing": {"cuCost": 6},
            "metadata": {
                "input": {"modelId": "model_g", "prompt": "teapot"},
                "assetIds": ["asset_1"],
            },
        },
        {
            "jobId": "job_b",
            "jobType": "upload",
            "status": "success",
            "createdAt": "2026-08-28T07:40:00.000Z",
            "metadata": {"input": {}},
        },
        {
            "jobId": "job_c",
            "jobType": "custom",
            "status": "failure",
            "createdAt": "2026-08-28T08:00:00.000Z",
            "metadata": {"input": {"modelId": "model_m", "prompt": "x"}, "assetIds": []},
        },
    ]
    entries = history.entries_from_jobs(jobs, [local], kinds={"model_m": "3d"})
    assert [e.job_id for e in entries] == ["job_c", "job_a"]
    a = entries[1]
    assert (
        a.local_files == ["/out/a.png"]
        and a.prompt == "teapot"
        and a.cu_cost == 6.0
        and a.kind == "image"
    )
    assert entries[0].kind == "3d" and entries[0].status == "failure"


def test_prompt_asset_ids_are_hidden_until_resolved():
    jobs = [
        {
            "jobId": "job_p",
            "jobType": "custom",
            "status": "success",
            "createdAt": "2026-08-28T09:00:00.000Z",
            "metadata": {
                "input": {"modelId": "model_g", "prompt": "asset_Lq9G6auxQxXpiWiahw6K5nc6"},
                "assetIds": ["a"],
            },
        }
    ]
    assert history.prompt_asset_ids(jobs) == ["asset_Lq9G6auxQxXpiWiahw6K5nc6"]
    assert history.entries_from_jobs(jobs, [])[0].prompt == ""
    history.resolve_prompts(jobs, {"asset_Lq9G6auxQxXpiWiahw6K5nc6": "mossy stone wall"})
    assert history.entries_from_jobs(jobs, [])[0].prompt == "mossy stone wall"
    assert history.prompt_asset_ids(jobs) == []


def test_scoped_jobs_hide_legacy_files_and_preserve_ambiguous_request_ids():
    local = JobRecord.new(lane="image", kind="image", model_id="old-model", body={})
    local.job_id, local.files = "job_saved", ["unverified.png"]
    local.meta["prompt"] = "old account text"
    shared = [
        SimpleNamespace(remote_job_id="job_saved", intent=SimpleNamespace(request_id=identity))
        for identity in ("saved-one", "saved-two")
    ]
    jobs = [
        {
            "jobId": "job_saved",
            "jobType": "custom",
            "status": "success",
            "metadata": {"input": {"modelId": "current-model", "prompt": "asset_prompt"}},
        }
    ]
    entry = history.entries_from_jobs(jobs, [local], shared_records=shared)[0]
    assert entry.local_request_ids == ("saved-one", "saved-two")
    assert entry.local_files == []
    assert entry.prompt == ""
    assert entry.model_id == "current-model"


def billing(main, quality_gate=None):
    value = {"cuCost": main, "cuDiscount": 0}
    if quality_gate is not None:
        value["cuCostDetails"] = {"quality-gate": quality_gate}
    return value


def step(identifier, parent, main, quality_gate=1.75, *, status="success"):
    return {
        "jobId": identifier,
        "jobType": "custom",
        "status": status,
        "createdAt": "2026-10-10T10:56:40.000Z",
        "billing": billing(main, quality_gate),
        "metadata": {
            "input": {"modelId": "model_step", "prompt": "step"},
            "workflowId": "workflow_fixture",
            "workflowJobId": parent,
            "assetIds": [],
        },
    }


def workflow_run(identifier, children, *, status="success", own=0):
    nodes = [{"id": "loop", "type": "for-each", "status": "success"}]
    nodes += [
        {"id": f"node-{child}", "type": "custom-model", "status": "success", "jobId": child}
        for child in children
    ]
    nodes.append({"id": "template", "type": "custom-model", "status": "skipped"})
    return {
        "jobId": identifier,
        "jobType": "workflow",
        "status": status,
        "createdAt": "2026-10-10T10:56:34.000Z",
        "billing": billing(own),
        "metadata": {
            "input": {"prompt": "a loop"},
            "workflowId": "workflow_fixture",
            "flow": nodes,
            "assetIds": ["asset_out"],
        },
    }


def test_job_cost_adds_documented_add_on_details():
    assert history.job_cost({"billing": billing(16, 1.75)}) == Decimal("17.75")
    assert history.job_cost({"billing": billing(6)}) == Decimal("6")
    assert history.job_cost({"billing": {"cuCost": 0, "cuCostDetails": {"x": None}}}) == 0
    # Numeric strings were accepted before add-ons were counted; keep them.
    assert history.job_cost({"billing": {"cuCost": "1", "cuCostDetails": {"q": "1.75"}}}) == 2.75
    for value in ({}, {"billing": None}, {"billing": {"cuCost": None}}):
        assert history.job_cost(value) is None, value
    for value in (
        {"billing": {"cuCost": True}},
        {"billing": {"cuCost": "invalid"}},
        {"billing": {"cuCost": float("nan")}},
        {"billing": {"cuCost": 1, "cuCostDetails": []}},
        {"billing": {"cuCost": 1, "cuCostDetails": {"quality-gate": "x"}}},
    ):
        with pytest.raises(ValueError):
            history.job_cost(value)
    jobs = [step("job_step", None, 1)]
    jobs[0]["metadata"].pop("workflowJobId")
    [entry] = history.entries_from_jobs(jobs, [])
    assert entry.cu_cost == 2.75 and not entry.cost_unavailable


def test_workflow_run_reports_the_sum_of_its_loop_steps():
    children = [step(f"job_{i}", "job_run", 1) for i in range(3)]
    children.append(step("job_last", "job_run", 2))
    jobs = [*children, workflow_run("job_run", [c["jobId"] for c in children])]
    entries = {e.job_id: e for e in history.entries_from_jobs(jobs, [])}
    run = entries["job_run"]
    assert (run.kind, run.model_id, run.workflow_id) == ("workflow", "", "workflow_fixture")
    assert run.cu_cost == 12.0 and not run.cost_unavailable
    assert run.prompt == "a loop" and run.asset_ids == ["asset_out"]
    for child in children:
        entry = entries[child["jobId"]]
        assert entry.workflow_job_id == "job_run"
        assert entry.kind == "image" and entry.model_id == "model_step"
    assert entries["job_0"].cu_cost == 2.75 and entries["job_last"].cu_cost == 3.75


def test_workflow_children_listed_only_by_parent_reference_are_counted():
    run = workflow_run("job_run", ["job_a"])
    jobs = [step("job_a", "job_run", 1), step("job_b", "job_run", 2, None), run]
    [entry] = [e for e in history.entries_from_jobs(jobs, []) if e.kind == "workflow"]
    assert entry.cu_cost == 4.75


def test_missing_or_unpriced_workflow_steps_make_cost_unavailable_not_zero():
    run = workflow_run("job_run", ["job_a", "job_missing"])
    entries = history.entries_from_jobs([step("job_a", "job_run", 1), run], [])
    [entry] = [e for e in entries if e.kind == "workflow"]
    assert entry.cu_cost is None and entry.cost_unavailable
    assert history.missing_workflow_steps([step("job_a", "job_run", 1), run]) == ["job_missing"]
    broken = step("job_missing", "job_run", None)
    entries = history.entries_from_jobs([step("job_a", "job_run", 1), run], [], related=[broken])
    [entry] = [e for e in entries if e.kind == "workflow"]
    assert entry.cu_cost is None and entry.cost_unavailable
    # Related reads complete the total without becoming history rows themselves.
    entries = history.entries_from_jobs(
        [step("job_a", "job_run", 1), run], [], related=[step("job_missing", "job_run", 2)]
    )
    assert [e.job_id for e in entries if e.job_id == "job_missing"] == []
    [entry] = [e for e in entries if e.kind == "workflow"]
    assert entry.cu_cost == 6.5 and not entry.cost_unavailable


def test_running_and_canceled_workflow_runs():
    running = workflow_run("job_run", ["job_a"], status="in-progress")
    entries = history.entries_from_jobs([step("job_a", "job_run", 1), running], [])
    [entry] = [e for e in entries if e.kind == "workflow"]
    assert entry.cu_cost is None and not entry.cost_unavailable
    canceled = workflow_run("job_run", ["job_a"], status="canceled")
    entries = history.entries_from_jobs([step("job_a", "job_run", 1), canceled], [])
    [entry] = [e for e in entries if e.kind == "workflow"]
    assert entry.cu_cost == 2.75 and entry.status == "canceled"
    assert history.missing_workflow_steps([running]) == []


def test_nested_workflow_runs_are_bounded_and_cycles_are_unavailable():
    inner = workflow_run("job_inner", ["job_a"])
    inner["metadata"]["workflowJobId"] = "job_outer"
    outer = workflow_run("job_outer", ["job_inner"])
    jobs = [step("job_a", "job_inner", 1), inner, outer]
    entries = {e.job_id: e for e in history.entries_from_jobs(jobs, [])}
    assert entries["job_outer"].cu_cost == 2.75
    assert entries["job_inner"].workflow_job_id == "job_outer"
    loop = workflow_run("job_x", ["job_y"])
    other = workflow_run("job_y", ["job_x"])
    entries = {e.job_id: e for e in history.entries_from_jobs([loop, other], [])}
    assert entries["job_x"].cost_unavailable and entries["job_x"].cu_cost is None


def test_missing_steps_are_bounded_unique_and_skip_running_runs():
    runs = [workflow_run(f"job_run{i}", [f"job_{i}_{j}" for j in range(10)]) for i in range(5)]
    missing = history.missing_workflow_steps(runs, limit=24)
    assert len(missing) == 24 and len(set(missing)) == 24
    assert missing[:10] == [f"job_0_{j}" for j in range(10)]
    bad = workflow_run("job_bad", ["job_a"])
    bad["metadata"]["flow"] = [{"jobId": "bad/id"}, "node", {"jobId": 3}]
    assert history.missing_workflow_steps([bad]) == []


def test_malformed_listed_run_billing_fails_but_malformed_rows_do_not_break_step_discovery():
    run = workflow_run("job_run", ["job_a"])
    run["billing"] = {"cuCost": "invalid"}
    with pytest.raises(ValueError):
        history.entries_from_jobs([step("job_a", "job_run", 1), run], [])
    rows = [{"jobId": "job_x", "metadata": [1]}, workflow_run("job_run", ["job_a"]), "row"]
    assert history.missing_workflow_steps(rows) == ["job_a"]
