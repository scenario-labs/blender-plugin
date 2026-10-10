---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.waiting-workflow-steps",
  "title": "Waiting workflow steps in the runtime map",
  "description": "Shared polling projects waiting workflow steps and one decision path serves UI and MCP.",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "scope": "waiting-workflow-steps",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed that the Active workflow commands and Native workflow controls paragraphs match the shared projection in ModelJobs, the coordinator decision command, runtime.read_workflow_steps and decide_workflow_step, the local MCP workflow_job_steps and decide_workflow_step tools and the native review dialog and Workflows section in workflow_steps that call the same entry, that rejection is the only workflow cancellation and that cancel_remote stays model-only; no endpoint cancels a running workflow step. No live or paid request was made: the service's handling of repeated or concurrent decisions, rejection inside a ForEach iteration, omitting projectId for API-key decisions and the charge after an approval or selection are not live-verified. No screenshot or physical desktop input, focus, DPI or IME evidence of the review rows or dialog was collected; it is pending for an unlocked desktop session. Re-reviewed on 2026-10-10 after the review dialog's decision cells became an even split and its minimum width 540; the claims here are unchanged, and only the fingerprints of scenario/blender/workflow_steps.py and tests/blender/test_workflow_steps.py were refreshed. Re-reviewed on 2026-10-10 after the projection began reading step links from the workflow definition; the runtime map paragraph remains accurate and is unchanged. Re-reviewed on 2026-10-12 after the parser's linear deduplication and full-dependency review asset count; the runtime map paragraph remains accurate and is unchanged.",
    "sources": {
      "scenario/blender/model_jobs.py": "73a4be3cee977332eae60bc44a51a99923d4305cab49fdaeb637d042c8b14b27",
      "scenario/blender/runtime.py": "bd150ee52a66ca16520617cd1c1d67336862c165db3a8c62ca7b2861c9e37148",
      "scenario/blender/workflow_steps.py": "e48ff16971de14b0d350a304a7475af19bf428df642dd199cd72181a2042222c",
      "scenario/blender/workflow_controls.py": "4de1c7929e512739c96b15f6229f708fd9153fd358f24e9a383647d3117ef8ee",
      "scenario/core/jobs/coordinator.py": "4c7a7242c8f295650cd548bddd1db0bfe197da487998f2897de03a78830a4882",
      "scenario/core/jobs/workflow_nodes.py": "66318468f9afbe9cadeb46faef90baabbded456def4a339bc214073d4e29c720",
      "scenario/mcp/tools_scenario.py": "4d6426a08cbef8d9ac3c62392002eaa33367b2c1c6313dbd6d777136631522ef",
      "tests/blender/test_workflow_commands.py": "447c9446dc4791b4b27567e18d922a42d5f80db52b32ae8dc2fd8f7b75f1cbda",
      "tests/blender/test_workflow_steps.py": "77cdf3ee05fc38f0a99de909b751a50bb6188af72938a339efa0b9bf27baf189",
      "tests/unit/test_workflow_decisions.py": "bed926329df85c217701d8bc0141d5645d98cf5d32ee9372de4644404a9cac2d"
    }
  }
}
---

# Waiting workflow steps in the runtime map

Evidence for [the canonical document](../../architecture/runtime.md).
