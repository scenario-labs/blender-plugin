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
      "scenario/mcp/tools_scenario.py": "2544f304b15c2c828f7ccf8d17531851719473225d098e22ca9cc226e61918db",
      "scenario/core/jobs/preview_scheduler.py": "13eec9d2ff9cca03c5d39d16c54083db01ffed4fa4f075c6ceea4c0bb09b0dda",
      "tests/blender/test_mcp_result_previews.py": "4e4ee27ccf5c27b2faf3ca0151edefa8dec93ab4ac85f398fc59fdd1316e0cd9"
    }
  }
}
---

# Agent-requested preview reads

Evidence for [the canonical guide](../../PRIVACY.md).
