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
    "reviewed_at": "2026-10-13",
    "base_revision": "a0a0c9259535a483acff2f3d52a9e161449ececc",
    "limits": "Source review of the current guide's workflow cost claims: Generate (from N CU) for a workflow that loops, priced for one pass (Run a workflow); the workflow case of the from N CU bullet (Costs); and, in Generations, add-on fees, a workflow's total of its steps or Cost unavailable, and listed steps that must not be added again. sdk_adapter.workflow_loop_steps counts for-each nodes and nodes carrying loopBodyNodeIds, count, loopNodeId or iterationIndex, and returns 0 only when every node has a known non-loop type; a missing, malformed or unexplained empty flow, a nested workflow or workflowId, or an unknown node type is unknown coverage, which also shows from N CU with the warning that loop steps could not be checked (costs.workflow_loop_warning). workflow_controls draws the nonblocking from label and warning and repeats the warning in the confirmation. This session's results show the approved quote (model_jobs, panels.result_cost_label), as from N CU unless the quote was proven loop-free, including recovered jobs whose saved record keeps no loop count. Only cloud history rows read billing: history.job_cost adds cuCostDetails add-ons to billing.cuCost; workflow_cost sums a finished run's own charge and its steps, nested runs to a bounded depth; sdk_catalog.history_page reads up to 24 missing steps per page on the history worker (manager) in two passes; an unread step, a cycle or a nested run still running gives Cost unavailable (panels.history_cost_label), never 0; a running run shows its status; listed step rows say they are included in the run's total once known; malformed billing makes only that row's cost unavailable. Offline unit tests in test_history.py, test_sdk_history.py, test_cu_display.py, test_sdk_adapter.py and test_forms.py passed (337 tests). Installed tests in tests/blender/test_workflow_controls.py, test_workflow_commands.py (its fixture) and test_sdk_history.py were read, not run. Free read-only job reads recorded by the 2026-10-11 review, not repeated, confirmed a workflow job's own cuCost of 0, step add-ons in cuCostDetails, step identity fields, and a three-iteration ForEach run that charged its loop step once per iteration; the known non-loop node types and public workflow flow shapes come from earlier free read-only reviews. scenario/mcp/tools_scenario.py was removed as a source: this guide no longer describes the MCP loop and cost fields, whose evidence belongs to docs/MCP.md. Not verified: whether a quote includes add-on fees, live loop runs, live nested workflow pricing, deleted step jobs, screenshots, physical input, other operating systems and DPI. No paid, dry-run or live service call was made for this review. 2026-10-13 gallery note: refreshed after the guide gained an explorations gallery; the gallery doesn't touch the sections this topic covers, and its claims were not re-reviewed.",
    "sources": {
      "docs/USER_GUIDE.md": "5a627dd3a18d30092ce168797c91e1e971c4bd5f27d955f55fb91a10eb7e338d",
      "scenario/core/api/sdk_adapter.py": "0add4688710b00326fc31381d028e42cd9b5415f84bd168f45b5a8434a48aa19",
      "scenario/core/ui/costs.py": "07f305f86ad6d9acdb0667fcdb2625ca9e9d803bcbb0b7cf7c33b60cca609539",
      "scenario/core/history.py": "fddd9193d7e18ff9eada121663c8b8cab0b18c87f2b59e5b9361ecc0a5cc074f",
      "scenario/core/api/sdk_catalog.py": "84323d8e4ca6cbddcc4285a96711d235d5bf19f18d2c2e9a4207dc897a1da96f",
      "scenario/core/jobs/manager.py": "ea9d222ffe50ad1df9257e8e89350f78f4f9eecdcd70016e00b809ab71803a91",
      "scenario/blender/history.py": "62dcbb6a32a55fc43a3621d8b0a58d034b12f72a0c53ba912f551ef07c6f64e4",
      "scenario/blender/model_jobs.py": "956e032cbe134fc57a3f0aa2e996a1f06388b80f8f0561b16bd703763995240e",
      "scenario/blender/panels.py": "ed89c44a0d327f3a9de13d62f6bb44116e9ff88defdabc01e805900ee45c3d67",
      "scenario/blender/workflow_controls.py": "8b515b7c19fb0c6b4bc797a612a6158dac0bbecffb2a8254d259cb1a4ae956fd",
      "tests/unit/test_sdk_adapter.py": "4c6e88a329c958878b64a1aee6828b38c1e6a964930dadf35d27377b5f04ed96",
      "tests/unit/test_cu_display.py": "84fa9a0f5d5957e34c5132febc5b6b2d49c645cc62810faf4ed09a5d5829de7f",
      "tests/unit/test_history.py": "c8cf5f209e744f23c9dd9bd180fee5885894b6db60ec94b1d0234d8c39fd97b1",
      "tests/unit/test_sdk_history.py": "c9149184d9096435aa50db0a9080dc456bb4220e0e49d691559605131db6397c",
      "tests/blender/test_workflow_commands.py": "636c2e5a69c4a7a2e4a4aceff171d939af8bddb46a57d77d297fe661bbd1e312",
      "tests/blender/test_workflow_controls.py": "9128647ac6f788430919835a8d2d057bd7c426075b586a3c51c929fde8149578",
      "tests/blender/test_sdk_history.py": "1a74c1bde95091e8aea233ac5e67d333ddf10688722e2e4fdc403dcbf1c4a261"
    }
  }
}
---

# Workflow loop quote warnings and History workflow totals

Evidence for [the canonical guide](../../USER_GUIDE.md).
