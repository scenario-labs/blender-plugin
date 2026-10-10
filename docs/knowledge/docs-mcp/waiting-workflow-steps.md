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
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the job_status and wait_for_job descriptions and the regenerated tool table against ModelJobs.status, _advancing and the parser summary: awaiting_decision, pending_steps without URLs, decision_error, blocked values, the review_step action that recover_local_job rejects, and the immediate wait return. Installed tests read these fields through the real job_status and wait_for_job tools. No live or paid request was made: the service's handling of repeated or concurrent decisions, rejection inside a ForEach iteration, omitting projectId for API-key decisions and the charge after an approval or selection are not live-verified. No MCP tool sends a decision yet; a live agent client was not exercised. Re-reviewed on 2026-10-10 for the blocked loop value, which now also covers a selection read by a node type the API reference does not list, in both the job_status description and this document.",
    "sources": {
      "scenario/mcp/tools_scenario.py": "522485dc8bbbfe99d71ee24d51753b0a4831ccfd7c271b8b02eb616e2578a7be",
      "scenario/blender/model_jobs.py": "14737547ccaf27acb7efed4a937314f8808b54afa52ef7b8e21e2c0d9e0f4d24",
      "scenario/core/jobs/workflow_nodes.py": "24a72b8fdeffe9ff9540d5fd57fff10ece53559bbc5ab571880c00298f537a51",
      "tests/blender/test_workflow_commands.py": "c801ddf916034704b16fe25384ef9ee319b3c1c81f4ec4ede5577b2f7ce84776",
      "tests/unit/test_saved_job_actions.py": "b5888fd4d1efce167fc71464bb8080b4c0b48cdf72ede9d7029fb73377e6f01a"
    }
  }
}
---

# Waiting workflow steps in MCP job status

Evidence for [the canonical document](../../MCP.md).
