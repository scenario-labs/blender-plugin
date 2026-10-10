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
    "limits": "Reviewed that the Active workflow commands paragraph matches the shared projection in ModelJobs, the coordinator decision command, runtime.read_workflow_steps and decide_workflow_step and the local MCP workflow_job_steps and decide_workflow_step tools that call them, that rejection is the only workflow cancellation and that cancel_remote stays model-only. No live or paid request was made: the service's handling of repeated or concurrent decisions, rejection inside a ForEach iteration, omitting projectId for API-key decisions and the charge after an approval or selection are not live-verified. Native decision controls and running-step cancellation remain absent. Re-reviewed on 2026-10-10 after the parser also blocked selections read by node types the API reference does not list, and again on 2026-10-10 after the MCP tools were added. Re-reviewed on 2026-10-10 after the workflow cancel explanation was limited to a running workflow job; the runtime map paragraph is unchanged by it. Re-reviewed on 2026-10-10 after the projection began reading step links from the workflow definition; the runtime map paragraph remains accurate and is unchanged. Re-reviewed on 2026-10-12 after the parser's linear deduplication and full-dependency review asset count; the runtime map paragraph remains accurate and is unchanged.",
    "sources": {
      "scenario/blender/model_jobs.py": "cb37cac5833fb7f5c96b2e4e23b41f75e11ba75f1dc75854b2db986733e3b7cf",
      "scenario/blender/runtime.py": "bd150ee52a66ca16520617cd1c1d67336862c165db3a8c62ca7b2861c9e37148",
      "scenario/core/jobs/coordinator.py": "4c7a7242c8f295650cd548bddd1db0bfe197da487998f2897de03a78830a4882",
      "scenario/core/jobs/workflow_nodes.py": "66318468f9afbe9cadeb46faef90baabbded456def4a339bc214073d4e29c720",
      "tests/blender/test_workflow_commands.py": "ef1a5fe27ed2cfceff78f876a76c7fad00b1a35f1f22d6c9d85e34005ef06e09",
      "tests/unit/test_workflow_decisions.py": "bed926329df85c217701d8bc0141d5645d98cf5d32ee9372de4644404a9cac2d",
      "scenario/mcp/tools_scenario.py": "773411b23643e7e1610476625ad5ffbfe0ee4a4ba63fa57500d99cb2467bec0d"
    }
  }
}
---

# Waiting workflow steps in the runtime map

Evidence for [the canonical document](../../architecture/runtime.md).
