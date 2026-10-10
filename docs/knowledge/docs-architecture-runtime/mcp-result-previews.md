---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.mcp-result-previews",
  "title": "Result previews row with local MCP inspection",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "scope": "mcp-result-previews",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the MCP tool's main-thread use of the session scheduler for the tile results or one named result, envelope requests, retry and cancel, and its off-main-thread wait through the scheduler watch. Clip display, live thumbnail coverage and desktop acceptance stay open. Installed-ZIP native tests (tests/blender/test_mcp_result_previews.py) ran on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 with a synthetic SDK transport, an offline storage stub and the real offline audio decoder; no live Scenario preview, other operating system, desktop interaction or MCP client session is claimed.",
    "sources": {
      "scenario/mcp/tools_scenario.py": "2544f304b15c2c828f7ccf8d17531851719473225d098e22ca9cc226e61918db",
      "scenario/core/jobs/preview_scheduler.py": "13eec9d2ff9cca03c5d39d16c54083db01ffed4fa4f075c6ceea4c0bb09b0dda",
      "scenario/blender/result_previews.py": "2d13cfe3e7c1c89fe7ee4717c2c36432c1d01a35f1e5cd2d0f8a284f87c48ae7",
      "tests/blender/test_mcp_result_previews.py": "4e4ee27ccf5c27b2faf3ca0151edefa8dec93ab4ac85f398fc59fdd1316e0cd9"
    }
  }
}
---

# Result previews row with local MCP inspection

Evidence for [the canonical guide](../../architecture/runtime.md).
