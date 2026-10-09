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
    "limits": "Reviewed ModelJobs.status, which adds lane, remote_status, progress, remote_observed_at and remote_stale from the in-memory binding and view projection, and the job_status and wait_for_job descriptions in tools_scenario.py. Installed tests cover UI and MCP parity, null fields for restarted and terminal jobs, an explicit refresh after restart and wait timeout parity with job_status; tools/gen_mcp_docs.py --check passes. Installed native tests on macOS arm64 Blender 5.1.2 cover these claims. No desktop interaction, screenshot, Blender 5.0/5.2 run, other operating system or live provider progress is claimed. No live agent client is claimed.",
    "sources": {
      "scenario/mcp/tools_scenario.py": "a960c7495ea57658c9813fda4caa64178ead8f02a25530cd4bb5e93ed52cde64",
      "scenario/blender/model_jobs.py": "ef10249154c8842a96da012d07395bf8c1554bc762542cdc27f1539ae1590e85",
      "scenario/core/jobs/progress.py": "286563456f871fb3073ad32932cc3d9b750f12b9d263abef2fe931cbc5568f92",
      "tests/blender/test_model_generation.py": "a7994ea7cf89c4c26b29701682b9cf9e39971e6fef54a031f4394b9ed57e2f66"
    }
  }
}
---

# Flat job_status progress fields

Evidence for [the canonical document](../../MCP.md).
