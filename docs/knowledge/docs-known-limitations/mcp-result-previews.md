---
{
  "type": "Evidence",
  "id": "docs-known-limitations.mcp-result-previews",
  "title": "Local MCP preview and envelope limits",
  "evidence": {
    "path": "docs/KNOWN_LIMITATIONS.md",
    "scope": "mcp-result-previews",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed that inspect_result_previews returns envelope levels and still metadata, never an image or player launch, and that background Blender leaves image stills in the decode state until the scheduler's 120-second expiry fails them. Installed-ZIP native tests (tests/blender/test_mcp_result_previews.py) ran on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 with a synthetic SDK transport, an offline storage stub and the real offline audio decoder; no live Scenario preview, other operating system, desktop interaction or MCP client session is claimed.",
    "sources": {
      "scenario/mcp/tools_scenario.py": "2544f304b15c2c828f7ccf8d17531851719473225d098e22ca9cc226e61918db",
      "scenario/core/jobs/preview_scheduler.py": "13eec9d2ff9cca03c5d39d16c54083db01ffed4fa4f075c6ceea4c0bb09b0dda",
      "scenario/blender/result_previews.py": "2d13cfe3e7c1c89fe7ee4717c2c36432c1d01a35f1e5cd2d0f8a284f87c48ae7",
      "tests/blender/test_mcp_result_previews.py": "4e4ee27ccf5c27b2faf3ca0151edefa8dec93ab4ac85f398fc59fdd1316e0cd9"
    }
  }
}
---

# Local MCP preview and envelope limits

Evidence for [the canonical guide](../../KNOWN_LIMITATIONS.md).
