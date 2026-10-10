---
{
  "type": "Evidence",
  "id": "docs-privacy.mcp-result-previews",
  "title": "Agent-requested preview reads",
  "evidence": {
    "path": "docs/PRIVACY.md",
    "scope": "mcp-result-previews",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed that inspect_result_previews requests stills through the same scheduler, so Scenario stills read asset metadata and download preview images only while Online Access allows, for any downloaded saved job an agent names, while image stills and envelopes use local files only. Installed-ZIP native tests (tests/blender/test_mcp_result_previews.py) ran on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 with a synthetic SDK transport, an offline storage stub and the real offline audio decoder; no live Scenario preview, other operating system, desktop interaction or MCP client session is claimed.",
    "sources": {
      "scenario/mcp/tools_scenario.py": "405d28882eed0ab8182b11bf993fcece60a18b61061bb08225661c7f39117a09",
      "scenario/core/jobs/preview_scheduler.py": "c2c820b2de38d7b22fdcd21c2654eea88a672877fd7a9f14f07a4631022aca54",
      "tests/blender/test_mcp_result_previews.py": "a9c6cc703f94828264aea23b087ac91d67e38546bf6f82d5f93993dcb95a142b"
    }
  }
}
---

# Agent-requested preview reads

Evidence for [the canonical guide](../../PRIVACY.md).
