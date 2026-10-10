---
{
  "type": "Evidence",
  "id": "docs-blender-job-context.mcp-result-previews",
  "title": "Local MCP use of the preview scheduler",
  "evidence": {
    "path": "docs/BLENDER_JOB_CONTEXT.md",
    "scope": "mcp-result-previews",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the MCP tool's checks (context token, saved revision, previewable state), its requests, retry with the controller's forget_failures and cancel, and the watch that pump sets, deactivate releases through the scheduler's close, and the final main-thread read in an unchanged context and session. Installed-ZIP native tests (tests/blender/test_mcp_result_previews.py) ran on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 with a synthetic SDK transport, an offline storage stub and the real offline audio decoder; no live Scenario preview, other operating system, desktop interaction or MCP client session is claimed.",
    "sources": {
      "scenario/mcp/tools_scenario.py": "405d28882eed0ab8182b11bf993fcece60a18b61061bb08225661c7f39117a09",
      "scenario/core/jobs/preview_scheduler.py": "c2c820b2de38d7b22fdcd21c2654eea88a672877fd7a9f14f07a4631022aca54",
      "scenario/blender/result_previews.py": "2431b148a91e5cd035ac1d6ed670eef638dad931f8c1f7fb57c7f0f750a121a8",
      "scenario/blender/job_session.py": "fb42ae76844e48b22a7ef48d3cc408370392ce7be3d78cb4f3e587ea9d5c2c47",
      "tests/blender/test_mcp_result_previews.py": "a9c6cc703f94828264aea23b087ac91d67e38546bf6f82d5f93993dcb95a142b"
    }
  }
}
---

# Local MCP use of the preview scheduler

Evidence for [the canonical guide](../../BLENDER_JOB_CONTEXT.md).
