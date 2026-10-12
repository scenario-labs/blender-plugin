---
{
  "type": "Evidence",
  "id": "docs-mcp.waiting-workflow-steps",
  "title": "Waiting workflow steps in MCP job status",
  "description": "job_status and wait_for_job report sanitized waiting steps; no MCP decision tool yet.",
  "evidence": {
    "path": "docs/MCP.md",
    "scope": "waiting-workflow-steps",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the job_status and wait_for_job descriptions and the regenerated tool table against ModelJobs.status, _advancing and the parser summary: awaiting_decision, pending_steps without URLs, decision_error, blocked values, the review_step action that recover_local_job rejects, and the immediate wait return. Installed tests read these fields through the real job_status and wait_for_job tools. No live or paid request was made: the service's handling of repeated or concurrent decisions, rejection inside a ForEach iteration, omitting projectId for API-key decisions and the charge after an approval or selection are not live-verified. No MCP tool sends a decision yet; a live agent client was not exercised. Re-reviewed on 2026-10-10 for the blocked loop value, which now also covers a selection read by a node type the API reference does not list, in both the job_status description and this document. Re-reviewed on 2026-10-10 for step links: the job_status description and this document now list links_complete and the unverified blocked value (links between the workflow's steps unreadable in a flow with a loop, so only reject), and say that links come from the job and, while a step waits, from the workflow definition read once per waiting period. Installed tests read blocked unverified and loop, links_complete and definition-linked review assets through the real job_status tool. Re-reviewed on 2026-10-12 after the parser began counting review assets from every dependency while still listing at most 64 in depends_on; the job_status description and this document (up to 50 review asset IDs with their total) remain accurate and are unchanged.",
    "sources": {
      "scenario/mcp/tools_scenario.py": "77d057047220b728281f69f2bff9b05debf637ab38772b2cf8e4e51367872d90",
      "scenario/blender/model_jobs.py": "b52d70361f3e6cdd50fb8cc236e2da5aaa9be003252e859f1ba24d3cc7e80798",
      "scenario/core/jobs/workflow_nodes.py": "66318468f9afbe9cadeb46faef90baabbded456def4a339bc214073d4e29c720",
      "tests/blender/test_workflow_commands.py": "e470e6a96fbeda7eab66a6d9fe71c00aa224c7361f833684f76fc94fc5be8282",
      "tests/unit/test_saved_job_actions.py": "b5888fd4d1efce167fc71464bb8080b4c0b48cdf72ede9d7029fb73377e6f01a",
      "tests/unit/test_workflow_step_links.py": "3dbf4b8351072c6be1ada09a7a92e11ba0a273e3c307b339a274f3779af8ef61"
    }
  }
}
---

# Waiting workflow steps in MCP job status

Evidence for [the canonical document](../../MCP.md).
