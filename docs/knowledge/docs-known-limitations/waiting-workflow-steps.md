---
{
  "type": "Evidence",
  "id": "docs-known-limitations.waiting-workflow-steps",
  "title": "Waiting workflow step limits",
  "description": "Rejecting a waiting step is the only workflow stop; nested steps, loop-fed selections, previews and live behavior remain limited.",
  "evidence": {
    "path": "docs/KNOWN_LIMITATIONS.md",
    "scope": "waiting-workflow-steps",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed that ModelJobs.control refuses cancel on a running workflow job with WorkflowCancelUnavailable and that rejection through ModelJobs.decide is the only stop; that pending_steps reads top-level flow nodes only; that a selection feeding a ForEach loop, a nested workflow or an unlisted node type is blocked to reject only; that steps carry asset IDs or text and no preview is loaded; and that the native dialog draws at most 12 wrapped lines per text candidate. No live or paid request was made: the service's handling of repeated or concurrent decisions, rejection inside a ForEach iteration, omitting projectId for API-key decisions and the charge after an approval or selection are not live-verified. No screenshot or physical desktop input, focus, DPI or IME evidence of the review rows or dialog was collected; it is pending for an unlocked desktop session. Re-reviewed on 2026-10-10 after the review dialog's decision cells became an even split and its minimum width 540; the claims here are unchanged, and only the fingerprints of scenario/blender/workflow_steps.py and tests/blender/test_workflow_steps.py were refreshed. Re-reviewed on 2026-10-10 for step links: the entry now says that any selection in a workflow with a loop can only be rejected when the links between its steps cannot be read from the job or the workflow definition, and that an approval then warns about incomplete review assets; the parser, MCP and installed tests listed here cover it.",
    "sources": {
      "scenario/blender/model_jobs.py": "73a4be3cee977332eae60bc44a51a99923d4305cab49fdaeb637d042c8b14b27",
      "scenario/blender/workflow_steps.py": "2184f484dcfa32b373aa5bd28e1f1fdb9d5452d4e1aaefd74cbae14073d311a1",
      "scenario/core/jobs/workflow_nodes.py": "81a15c7f5bc51c74dd94d8abe1f5e1d44d9db12fdea35d79fb2c967f3e65f261",
      "scenario/mcp/tools_scenario.py": "4d6426a08cbef8d9ac3c62392002eaa33367b2c1c6313dbd6d777136631522ef",
      "tests/unit/test_workflow_nodes.py": "6556b51d3750e58c0be73596829e52f4ca448121504cab0c3900831ab1c1aacd",
      "tests/blender/test_workflow_steps.py": "98302e99e25f675fc7bab8564be2fc06d431664d70105fd04b250fcf9b07a30f",
      "tests/blender/test_workflow_commands.py": "447c9446dc4791b4b27567e18d922a42d5f80db52b32ae8dc2fd8f7b75f1cbda",
      "tests/unit/test_workflow_step_links.py": "3dbf4b8351072c6be1ada09a7a92e11ba0a273e3c307b339a274f3779af8ef61"
    }
  }
}
---

# Waiting workflow step limits

Evidence for [the canonical document](../../KNOWN_LIMITATIONS.md).
