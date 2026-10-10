---
{
  "type": "Evidence",
  "id": "docs-user-guide.waiting-workflow-steps",
  "title": "Waiting workflow steps in Jobs",
  "description": "A waiting workflow shows a status row; native decisions are not available, while a connected agent can read and decide the step through the local MCP.",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "waiting-workflow-steps",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the review_step status descriptor, its Jobs drawing through job_recovery.draw_controls, the 15 second refresh while a step waits, and the local MCP workflow_job_steps and decide_workflow_step tools with their descriptions and server instructions, which ask the agent for the user's explicit choice; the server cannot verify that a person approved a decision. Installed tests check the descriptor label on a projected view and the MCP tools with synthetic SDK responses; no screenshot, physical desktop interaction or live agent client was exercised. No live or paid request was made: the service's handling of repeated or concurrent decisions, rejection inside a ForEach iteration, omitting projectId for API-key decisions and the charge after an approval or selection are not live-verified. Re-reviewed on 2026-10-10 after the MCP tools were added.",
    "sources": {
      "scenario/core/ui/saved_job_actions.py": "751b2d03f53d0439121dc4528f3fb8b1c683f9368a692b12b5c90cf50b51240e",
      "scenario/blender/job_recovery.py": "da8df6bde6c9a0613565ea0563e7f1211086448d75e9419414f9c738038bda63",
      "scenario/blender/model_jobs.py": "0541e5fdad595a51693e30270c3e187d631bfb279f6089fb188aac810b5cac7f",
      "tests/blender/test_workflow_commands.py": "601e3ea00167217427fe3185e37fec40ddc522bec339524b530dbfaac00f004e",
      "tests/unit/test_saved_job_actions.py": "b5888fd4d1efce167fc71464bb8080b4c0b48cdf72ede9d7029fb73377e6f01a",
      "scenario/mcp/tools_scenario.py": "c8abbc16e7360a0335b2b77ec64dbba6ea9a05002cfeb279121070f54ff533ab",
      "scenario/mcp/protocol.py": "ee30be5866bbee06918c1145e7e770e90275a4c059c5610d83e6c768a719df7a"
    }
  }
}
---

# Waiting workflow steps in Jobs

Evidence for [the canonical document](../../USER_GUIDE.md).
