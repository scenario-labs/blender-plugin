---
{
  "type": "Evidence",
  "id": "docs-mcp.waiting-workflow-steps",
  "title": "Waiting workflow steps in MCP job status",
  "description": "job_status and wait_for_job report sanitized waiting steps that the MCP step tools read and decide.",
  "evidence": {
    "path": "docs/MCP.md",
    "scope": "waiting-workflow-steps",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the job_status and wait_for_job descriptions and the regenerated tool table against ModelJobs.status, _advancing and the parser summary: awaiting_decision, pending_steps without URLs, decision_error, blocked values, the review_step action that recover_local_job rejects, and the immediate wait return. Installed tests read these fields through the real job_status and wait_for_job tools. No live or paid request was made: the service's handling of repeated or concurrent decisions, rejection inside a ForEach iteration, omitting projectId for API-key decisions and the charge after an approval or selection are not live-verified. Re-reviewed on 2026-10-10 for the blocked loop value, which also covers a selection read by a node type the API reference does not list, and again on 2026-10-10 after the workflow_job_steps and decide_workflow_step tools were added: the job_status description and this paragraph now point to them instead of saying no MCP tool sends a decision; those tools have their own workflow-step-decision-tools topic. A live agent client was not exercised. Re-reviewed on 2026-10-10 after the workflow cancel explanation was limited to a running workflow job; the job_status and wait_for_job fields and this paragraph are unchanged by it. Re-reviewed on 2026-10-10 for the native review controls and dialog: ModelJobs.status, _advancing and the review_step action that job_status reports are unchanged, ModelJobs only gained the memory-only step_view and waiting_step, and the unit test of the review_step status row still holds; only the fingerprints of scenario/blender/model_jobs.py and tests/unit/test_saved_job_actions.py were refreshed. Re-reviewed on 2026-10-10 for step links: the job_status description and this document now list links_complete and the unverified blocked value (links between the workflow's steps unreadable in a flow with a loop, so only reject), and say that links come from the job and, while a step waits, from the workflow definition read once per waiting period. Installed tests read blocked unverified and loop, links_complete and definition-linked review assets through the real job_status tool. Fingerprints refreshed on 2026-10-10 after the workflow_job_steps description and its installed tests gained the step-link fields; this topic's job_status and wait_for_job claims were re-checked and are unchanged. Re-reviewed on 2026-10-12 after the parser began counting review assets from every dependency while still listing at most 64 in depends_on; the job_status description and this document (up to 50 review asset IDs with their total) remain accurate and are unchanged.",
    "sources": {
      "scenario/mcp/tools_scenario.py": "4d6426a08cbef8d9ac3c62392002eaa33367b2c1c6313dbd6d777136631522ef",
      "scenario/blender/model_jobs.py": "73a4be3cee977332eae60bc44a51a99923d4305cab49fdaeb637d042c8b14b27",
      "scenario/core/jobs/workflow_nodes.py": "66318468f9afbe9cadeb46faef90baabbded456def4a339bc214073d4e29c720",
      "tests/blender/test_workflow_commands.py": "447c9446dc4791b4b27567e18d922a42d5f80db52b32ae8dc2fd8f7b75f1cbda",
      "tests/unit/test_saved_job_actions.py": "ac7679b2665509d333855b3c7f26bed297c856a26391a200aa800444f9f16379",
      "tests/unit/test_workflow_step_links.py": "3dbf4b8351072c6be1ada09a7a92e11ba0a273e3c307b339a274f3779af8ef61"
    }
  }
}
---

# Waiting workflow steps in MCP job status

Evidence for [the canonical document](../../MCP.md).
