---
{
  "type": "Evidence",
  "id": "docs-user-guide.workflow-cost-reporting",
  "title": "Workflow loop quote warnings and History workflow totals",
  "description": "Nonblocking one-pass loop quote warnings and documented job and workflow totals in History.",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "workflow-cost-reporting",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Source review of loop detection from the retrieved workflow definition in the shared adapter: a node counts as a loop when its type is for-each or it carries loopBodyNodeIds, count, loopNodeId or iterationIndex, and the count is 0 only when every node has a known non-loop type (the SDK 2.2.0 WorkflowFlow.type values other than for-each and workflow, plus user-selection) or the flow is empty and the record says hasFlow false. A missing or malformed flow; an empty flow, unless the record says hasFlow false (the SDK documents hasFlow as present even when flow is not, so an empty list alone does not prove an empty workflow); a nested workflow step or any node carrying a workflowId; or a node whose type is missing, not a string or unknown is unknown coverage and warns; a unit test fails when the installed SDK type list changes. Also reviewed: the nonblocking native Generate (from N CU) label and warning, the session result row's from N CU for a workflow job not proven loop-free (including recovered jobs, whose saved record keeps no loop count), and the MCP loop_steps, quote_may_understate and cost_warning fields on estimate_workflow, run_workflow and job_status for saved workflow jobs, where a count this session did not record is unknown. The exact quoted string remains the approval value, and job_status cu_cost_exact remains the approved quote, not the final charge. History rows report billing.cuCost plus cuCostDetails add-ons; workflow runs sum their step charges from metadata.flow job IDs and step workflowJobId, read missing steps on the history worker through jobs.retrieve (24 per page) and report cost unavailable instead of 0; step rows say they are included in the run's total once known. Malformed billing on a listed row still fails the page; drawing performs no reads. Unit and installed synthetic tests cover detection including each malformed definition, an empty flow with and without hasFlow false, a workflowId on a known node type, the SDK type list, flags, labels, job_status before and after restart, single submission, sums, missing or malformed steps, cycles, nesting and draw-time reads. Free read-only job list/retrieve calls in a test account's default scope confirmed a workflow job's own cuCost of 0, step add-ons in cuCostDetails and step identity fields, and that a completed three-iteration ForEach run charged its loop step once per iteration; no paid, dry-run or generation request was made for this review. The user-selection node type and the public catalog's node types come from a separate free read-only review of live workflow job flows and public workflow definitions, which this review did not repeat. A separate free read-only gate review, also not repeated here, reported that 164 public workflow list rows and 12 retrieved public definitions had a non-empty flow with hasFlow true and that no node other than a workflow node carried workflowId. Nested workflow pricing, deleted step jobs, screenshots, physical input and live loop runs were not observed. The exact ZIP with SHA-256 a085410c11a4c6f4b4623014918aa1fcf1c6d66f17f424f8674e75467fd81711 passes 1,210 installed tests (2 Windows-only skips) on macOS arm64 Blender 5.1.2 only. This does not establish #65 or #68 acceptance.",
    "sources": {
      "docs/USER_GUIDE.md": "0716a36e62d2717db02429fa06dd3be27ba6a960fc904daca3c40081d9e14e34",
      "scenario/core/api/sdk_adapter.py": "fa768d6f42163f647cc1d6955b9bae044c4067a6ddf56a8663922bb89d558f0b",
      "scenario/core/ui/costs.py": "07f305f86ad6d9acdb0667fcdb2625ca9e9d803bcbb0b7cf7c33b60cca609539",
      "scenario/core/history.py": "e1af45a8502893026c4e28e2c154fe5cbb730fa07f24610616a95963aa24368e",
      "scenario/core/api/sdk_catalog.py": "3cf31246efc31cd46c9dcd7fbf726512ea4b1eecd42cc0e2881e3d2166f6f4df",
      "scenario/core/jobs/manager.py": "e222802758731753852f46dc4c6d6c14ef56d9ab2b3602b98a5fa7ef291e5ad8",
      "scenario/blender/history.py": "2dee6ead2c4ef24754cce15acf0971b72eb1ce59dd1cbf2eb1f90963023da6b7",
      "scenario/blender/model_jobs.py": "90636aea146e195553522fc01610bdfeb32fefedffd8b937a9c186972282982e",
      "scenario/blender/panels.py": "aa22d499e89d24c10d0d80177ce41f65db373d67fa25e7e3f830545b14f97023",
      "scenario/blender/workflow_controls.py": "437f27cf870fc8383f6002fbabf31718e79bdec0e5f461ccfcd3232e3391d09b",
      "scenario/mcp/tools_scenario.py": "2d0c840e13e6007a88f5c543110439d05f892b581885d05119993b7d7d7f4ad1",
      "tests/unit/test_sdk_adapter.py": "52b6e339b58562fc3d6d2eb335ec20f8df846b8c3736801b7f1bc3aa1982c124",
      "tests/unit/test_cu_display.py": "84fa9a0f5d5957e34c5132febc5b6b2d49c645cc62810faf4ed09a5d5829de7f",
      "tests/unit/test_history.py": "bd37632ac5d4ed4a6167157a70e47924fff95413e898fb5c99daa0d7f212ef5a",
      "tests/unit/test_sdk_history.py": "9f26ae998cfcb5f09534ff9c383f66e00a5cf777c63d31862ef5d396090e947f",
      "tests/blender/test_workflow_commands.py": "a3ee61153c9566029402cb3806dcaec8a4235244c19f6896aeee6edf4c9ada38",
      "tests/blender/test_workflow_controls.py": "762715381d5b8be1c227e8de7130d3680b41b494772d9e538b1859a34a0a937d",
      "tests/blender/test_sdk_history.py": "478342315ad0d0771edcbcbea94cfcb49956aa9943b35a492c25a2621cf35693"
    }
  }
}
---

# Workflow loop quote warnings and History workflow totals

Evidence for [the canonical guide](../../USER_GUIDE.md).
