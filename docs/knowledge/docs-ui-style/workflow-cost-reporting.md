---
{
  "type": "Evidence",
  "id": "docs-ui-style.workflow-cost-reporting",
  "title": "Workflow loop quote warnings and History workflow totals",
  "description": "Nonblocking one-pass loop quote warnings and documented job and workflow totals in History.",
  "evidence": {
    "path": "docs/UI_STYLE.md",
    "scope": "workflow-cost-reporting",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-11",
    "base_revision": "72723f02a97a7226b1c697c31d8124b77ac92c86",
    "limits": "Source review of loop detection from the retrieved workflow definition in the shared adapter: a node counts as a loop when its type is for-each or it carries loopBodyNodeIds, count, loopNodeId or iterationIndex, and the count is 0 only when every node has a known non-loop type (the SDK 2.2.0 WorkflowFlow.type values other than for-each and workflow, plus user-selection) or the flow is empty and the record says hasFlow false. A missing or malformed flow; an empty flow, unless the record says hasFlow false (the SDK documents hasFlow as present even when flow is not, so an empty list alone does not prove an empty workflow); a nested workflow step or any node carrying a workflowId; or a node whose type is missing, not a string or unknown is unknown coverage and warns; a unit test fails when the installed SDK type list changes. Also reviewed: the nonblocking native Generate (from N CU) label and warning, the session result row's from N CU for a workflow job not proven loop-free (including recovered jobs, whose saved record keeps no loop count), and the MCP loop_steps, quote_may_understate and cost_warning fields on estimate_workflow, run_workflow and job_status for saved workflow jobs, where a count this session did not record is unknown. The exact quoted string remains the approval value, and job_status cu_cost_exact remains the approved quote, not the final charge. History rows report billing.cuCost plus cuCostDetails add-ons; workflow runs sum their step charges from metadata.flow job IDs and step workflowJobId, read missing steps on the history worker through jobs.retrieve, at most 24 per page across two passes (whole runs with the fewest missing steps first, so a run that does not fit gets no reads, then the missing steps of nested runs the first pass found, never retrying an identifier), and report cost unavailable instead of 0; step rows say they are included in the run's total once known. Malformed billing on a listed row makes only that row's cost unavailable (MCP cost_unavailable true), while malformed metadata still fails the page; drawing performs no reads. Unit and installed synthetic tests cover detection including each malformed definition, an empty flow with and without hasFlow false, a workflowId on a known node type, the SDK type list, flags, labels, job_status before and after restart, single submission, sums, missing or malformed steps, malformed listed billing, read selection across runs, the nested read pass and its shared cap, cycles, nesting and draw-time reads. Free read-only job list/retrieve calls in a test account's default scope confirmed a workflow job's own cuCost of 0, step add-ons in cuCostDetails and step identity fields, and that a completed three-iteration ForEach run charged its loop step once per iteration; no paid, dry-run or generation request was made for this review. The user-selection node type and the public catalog's node types come from a separate free read-only review of live workflow job flows and public workflow definitions, which this review did not repeat. A separate free read-only gate review, also not repeated here, reported that 164 public workflow list rows and 12 retrieved public definitions had a non-empty flow with hasFlow true and that no node other than a workflow node carried workflowId. Live nested workflow pricing, deleted step jobs, screenshots, physical input and live loop runs were not observed. Rechecked after rebasing onto main 72723f02a97a7226b1c697c31d8124b77ac92c86: workflow runs keep kind workflow while model rows use the merged history kind derivation, and the cited claims still hold. The exact ZIP with SHA-256 7af89ad621347c91ff58a29a56422afc43c8317f26f467d6d886dc2d3a3a102d ran 1,302 installed tests on macOS arm64 Blender 5.1.2 only: every workflow cost test passed, 2 Windows-only tests were skipped, and one unrelated saved-job action test failed exactly as it does on that main commit. This does not establish #65 or #68 acceptance.",
    "sources": {
      "docs/UI_STYLE.md": "8585814c6207d7ca0b8cd5d77963a098ace196a7c6a8d58ee75f59cc181b4d8a",
      "scenario/core/api/sdk_adapter.py": "e7b4d5c2fd2aedf63b7c11f0fac6cbae63c9170e9dcd65151dc633468b00fe11",
      "scenario/core/ui/costs.py": "07f305f86ad6d9acdb0667fcdb2625ca9e9d803bcbb0b7cf7c33b60cca609539",
      "scenario/core/history.py": "278d2c17c8bfd2652fa9b99d35576904df573be0ab7ea9ed7c71e9cb81b29628",
      "scenario/core/api/sdk_catalog.py": "84323d8e4ca6cbddcc4285a96711d235d5bf19f18d2c2e9a4207dc897a1da96f",
      "scenario/core/jobs/manager.py": "e222802758731753852f46dc4c6d6c14ef56d9ab2b3602b98a5fa7ef291e5ad8",
      "scenario/blender/history.py": "6c5bb388396846cb1b01ac0a885081a4af7df3f78a9f443ccdc53f88f9709d93",
      "scenario/blender/model_jobs.py": "93b6286cc811275e1fd9d8050b83c7f339041338674657a312f20cf52711b611",
      "scenario/blender/panels.py": "c4e06b19be47de3d69d622b485b532f437d3d0b556dd5358c60ab9217490183f",
      "scenario/blender/workflow_controls.py": "437f27cf870fc8383f6002fbabf31718e79bdec0e5f461ccfcd3232e3391d09b",
      "scenario/mcp/tools_scenario.py": "84e4bb8b41471b3d7c07f959fd4d552b3ea5832dd677128cd16003d0fb8ae936",
      "tests/unit/test_sdk_adapter.py": "52b6e339b58562fc3d6d2eb335ec20f8df846b8c3736801b7f1bc3aa1982c124",
      "tests/unit/test_cu_display.py": "84fa9a0f5d5957e34c5132febc5b6b2d49c645cc62810faf4ed09a5d5829de7f",
      "tests/unit/test_history.py": "38cbc0c2848e327cadaef8a922bfbda4487e136abfceaa9e7db19ed46d47b01d",
      "tests/unit/test_sdk_history.py": "c9149184d9096435aa50db0a9080dc456bb4220e0e49d691559605131db6397c",
      "tests/blender/test_workflow_commands.py": "a3ee61153c9566029402cb3806dcaec8a4235244c19f6896aeee6edf4c9ada38",
      "tests/blender/test_workflow_controls.py": "762715381d5b8be1c227e8de7130d3680b41b494772d9e538b1859a34a0a937d",
      "tests/blender/test_sdk_history.py": "e7726946ac6f3015636fabda3f05c39a35770ce3e619a451a179f656f1570828"
    }
  }
}
---

# Workflow loop quote warnings and History workflow totals

Evidence for [the canonical guide](../../UI_STYLE.md).
