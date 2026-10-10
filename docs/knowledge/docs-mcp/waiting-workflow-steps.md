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
    "limits": "Reviewed the job_status and wait_for_job descriptions and the regenerated tool table against ModelJobs.status, _advancing and the parser summary: awaiting_decision, pending_steps without URLs, decision_error, blocked values, the review_step action that recover_local_job rejects, and the immediate wait return. Installed tests read these fields through the real job_status and wait_for_job tools. No live or paid request was made: the service's handling of repeated or concurrent decisions, rejection inside a ForEach iteration, omitting projectId for API-key decisions and the charge after an approval or selection are not live-verified. No MCP tool sends a decision yet; a live agent client was not exercised.",
    "sources": {
      "scenario/mcp/tools_scenario.py": "5143389a10f159a48b659d5409b1476c7229b4838185269c007c0dc590259b90",
      "scenario/blender/model_jobs.py": "14737547ccaf27acb7efed4a937314f8808b54afa52ef7b8e21e2c0d9e0f4d24",
      "scenario/core/jobs/workflow_nodes.py": "94a38896e6331e6dc993a5a83ecdb7b740ab5f60897bab73e7f45f4dbcade4d2",
      "tests/blender/test_workflow_commands.py": "c801ddf916034704b16fe25384ef9ee319b3c1c81f4ec4ede5577b2f7ce84776",
      "tests/unit/test_saved_job_actions.py": "b5888fd4d1efce167fc71464bb8080b4c0b48cdf72ede9d7029fb73377e6f01a"
    }
  }
}
---

# Waiting workflow steps in MCP job status

Evidence for [the canonical document](../../MCP.md).
