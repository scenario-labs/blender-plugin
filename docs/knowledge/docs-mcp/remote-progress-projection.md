---
{
  "type": "Evidence",
  "id": "docs-mcp.remote-progress-projection",
  "title": "Flat job_status progress fields",
  "description": "MCP job_status and wait_for_job remote projection fields.",
  "evidence": {
    "path": "docs/MCP.md",
    "scope": "remote-progress-projection",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Reviewed ModelJobs.status, which adds lane, remote_status, progress, remote_observed_at and remote_stale from the in-memory binding and view projection, and delivery_active from the same _delivering predicate that wait() uses, and the job_status and wait_for_job descriptions in tools_scenario.py, including the measured-status rule and the expired-wait rule. Installed tests cover UI and MCP parity, null fields for restarted and terminal jobs, delivery_active true while remote and false after terminal delivery or restart, lane null for a workflow submission, an explicit refresh after restart and wait timeout parity with job_status; tools/gen_mcp_docs.py --check passes. Installed native tests on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 cover these claims. No desktop interaction, screenshot, other operating system or live provider progress is claimed. No live agent client is claimed.",
    "sources": {
      "scenario/mcp/tools_scenario.py": "3b75c077ed05ddddf882e251c46064c6d61bb61611c516e8dc7491fb11988e13",
      "scenario/blender/model_jobs.py": "7278524fcd4cac373ce186782e741cc58b5a18e0a8ddca17d4c6cd1045fc52a6",
      "scenario/core/jobs/progress.py": "bf8bea9be0d1ba3c6ca7c2495fecf61eb67481ffb7499d1e30633cc154871af5",
      "tests/blender/test_model_generation.py": "e0f1b143a429bee22f5715ce420ff0d364916efc11bc94b630e8ad067a466f10",
      "tests/blender/test_workflow_commands.py": "74086c3122b3c83103e08072be6669e510ac1026a1da6cbb6f0eeaa1c0f49338"
    }
  }
}
---

# Flat job_status progress fields

Evidence for [the canonical document](../../MCP.md).
