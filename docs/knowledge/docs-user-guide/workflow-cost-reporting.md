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
    "reviewed_at": "2026-10-11",
    "base_revision": "1d86f53d3489b23f2447be69cb589140e2f3ba64",
    "limits": "Source review of loop detection from the retrieved workflow definition in the shared adapter: a node counts as a loop when its type is for-each or it carries loopBodyNodeIds, count, loopNodeId or iterationIndex, and the count is 0 only when every node has a known non-loop type (the SDK 2.2.0 WorkflowFlow.type values other than for-each and workflow, plus user-selection) or the flow is empty and the record says hasFlow false. A missing or malformed flow; an empty flow, unless the record says hasFlow false (the SDK documents hasFlow as present even when flow is not, so an empty list alone does not prove an empty workflow); a nested workflow step or any node carrying a workflowId; or a node whose type is missing, not a string or unknown is unknown coverage and warns; a unit test fails when the installed SDK type list changes. Also reviewed: the nonblocking native Generate (from N CU) label and warning, the session result row's from N CU for a workflow job not proven loop-free (including recovered jobs, whose saved record keeps no loop count), and the MCP loop_steps, quote_may_understate and cost_warning fields on estimate_workflow, run_workflow and job_status for saved workflow jobs, where a count this session did not record is unknown. The exact quoted string remains the approval value, and job_status cu_cost_exact remains the approved quote, not the final charge. History rows report billing.cuCost plus cuCostDetails add-ons; workflow runs sum their step charges from metadata.flow job IDs and step workflowJobId, read missing steps on the history worker through jobs.retrieve, at most 24 per page across two passes (whole runs with the fewest missing steps first, so a run that does not fit gets no reads, then the missing steps of nested runs the first pass found, never retrying an identifier), and report cost unavailable instead of 0; step rows say they are included in the run's total once known. Malformed billing on a listed row makes only that row's cost unavailable (MCP cost_unavailable true), while malformed metadata still fails the page; drawing performs no reads. Unit and installed synthetic tests cover detection including each malformed definition, an empty flow with and without hasFlow false, a workflowId on a known node type, the SDK type list, flags, labels, job_status before and after restart, single submission, sums, missing or malformed steps, malformed listed billing, read selection across runs, the nested read pass and its shared cap, cycles, nesting and draw-time reads. Free read-only job list/retrieve calls in a test account's default scope confirmed a workflow job's own cuCost of 0, step add-ons in cuCostDetails and step identity fields, and that a completed three-iteration ForEach run charged its loop step once per iteration; no paid, dry-run or generation request was made for this review. The user-selection node type and the public catalog's node types come from a separate free read-only review of live workflow job flows and public workflow definitions, which this review did not repeat. A separate free read-only gate review, also not repeated here, reported that 164 public workflow list rows and 12 retrieved public definitions had a non-empty flow with hasFlow true and that no node other than a workflow node carried workflowId. Live nested workflow pricing, deleted step jobs, screenshots, physical input and live loop runs were not observed. Rechecked after rebasing onto main 1d86f53d3489b23f2447be69cb589140e2f3ba64, which merged the shared prepare_workflow, Load older paging, workflow step decisions, workflow input uploads and result previews: the workflow quote prepares its payload through the merged prepare_workflow and still counts loop nodes from the same retrieved record; workflow runs keep kind workflow while model rows use the merged history kind derivation; because this branch lists workflow runs as rows, the guides and the panel comment now name only uploads and mesh preview renders as unlisted, and the merged empty-page installed test uses those two job types. A finished run whose nested run is still running stays unpriced, and malformed own billing on a running workflow row reports cost unavailable; unit tests cover both. The cited claims still hold. The exact ZIP with SHA-256 f8eacb168515ef3fd49bfeb51939d85844d156569663433c4f6147a7c1c00050 ran 1,376 installed tests on macOS arm64 Blender 5.1.2 only: every workflow cost test and the merged empty-page test passed, 2 Windows-only tests were skipped, and one saved-job action test that this branch does not touch (key remote, expecting Cancel generation) failed; that failure is tracked separately. This does not establish #65 or #68 acceptance. On 2026-10-12 the model_jobs.py and tools_scenario.py fingerprints were refreshed after saved model package import added import units to ModelJobs and job_status; the workflow quote notice and loop fields are unchanged, as are these statements and the review date. On 2026-10-12 the same fingerprints were refreshed again after saved splat import added splat options and counts; the workflow quote notice and loop fields are unchanged.",
    "sources": {
      "docs/USER_GUIDE.md": "adcf7061c10c259a0ff01601263ba08d0f2f0bbdc7fa42ba125eb101c38ddade",
      "scenario/core/api/sdk_adapter.py": "0add4688710b00326fc31381d028e42cd9b5415f84bd168f45b5a8434a48aa19",
      "scenario/core/ui/costs.py": "07f305f86ad6d9acdb0667fcdb2625ca9e9d803bcbb0b7cf7c33b60cca609539",
      "scenario/core/history.py": "fddd9193d7e18ff9eada121663c8b8cab0b18c87f2b59e5b9361ecc0a5cc074f",
      "scenario/core/api/sdk_catalog.py": "84323d8e4ca6cbddcc4285a96711d235d5bf19f18d2c2e9a4207dc897a1da96f",
      "scenario/core/jobs/manager.py": "e222802758731753852f46dc4c6d6c14ef56d9ab2b3602b98a5fa7ef291e5ad8",
      "scenario/blender/history.py": "62dcbb6a32a55fc43a3621d8b0a58d034b12f72a0c53ba912f551ef07c6f64e4",
      "scenario/blender/model_jobs.py": "2c9fa1c05bc714b8051035d0b70dcb46279abed08c82075404b88947c6019670",
      "scenario/blender/panels.py": "5df6d90cb57b0f832c9079e3e016b3989f33f45cea41513809a61d568a8a44bb",
      "scenario/blender/workflow_controls.py": "0e238d355e65f1f1e1ecb06a634e5d60c2a7753d8e781a8a2c9d725e49d23c17",
      "scenario/mcp/tools_scenario.py": "26239ef10a085bf4d1120ea4abc555c97c44fe47061d2cf916fdcea8b16e6adf",
      "tests/unit/test_sdk_adapter.py": "4c6e88a329c958878b64a1aee6828b38c1e6a964930dadf35d27377b5f04ed96",
      "tests/unit/test_cu_display.py": "84fa9a0f5d5957e34c5132febc5b6b2d49c645cc62810faf4ed09a5d5829de7f",
      "tests/unit/test_history.py": "c8cf5f209e744f23c9dd9bd180fee5885894b6db60ec94b1d0234d8c39fd97b1",
      "tests/unit/test_sdk_history.py": "c9149184d9096435aa50db0a9080dc456bb4220e0e49d691559605131db6397c",
      "tests/blender/test_workflow_commands.py": "5874f33c44088afd56b4318915dd4a95f23fa346465518be38db03bc9a33975f",
      "tests/blender/test_workflow_controls.py": "762715381d5b8be1c227e8de7130d3680b41b494772d9e538b1859a34a0a937d",
      "tests/blender/test_sdk_history.py": "1a74c1bde95091e8aea233ac5e67d333ddf10688722e2e4fdc403dcbf1c4a261"
    }
  }
}
---

# Workflow loop quote warnings and History workflow totals

Evidence for [the canonical guide](../../USER_GUIDE.md).
