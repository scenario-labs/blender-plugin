---
{
  "type": "Evidence",
  "id": "docs-user-guide.mcp-result-previews",
  "title": "Agent access to previews and waveforms",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "mcp-result-previews",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed that connected agents read the same preview states and audio waveforms as the Jobs and Generations tiles and the Waveform control through inspect_result_previews, and that no MCP tool opens a player. Installed-ZIP native tests (tests/blender/test_mcp_result_previews.py) ran on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 with a synthetic SDK transport, an offline storage stub and the real offline audio decoder; no live Scenario preview, other operating system, desktop interaction or MCP client session is claimed.",
    "sources": {
      "scenario/mcp/tools_scenario.py": "2544f304b15c2c828f7ccf8d17531851719473225d098e22ca9cc226e61918db",
      "scenario/blender/result_previews.py": "2d13cfe3e7c1c89fe7ee4717c2c36432c1d01a35f1e5cd2d0f8a284f87c48ae7",
      "tests/blender/test_mcp_result_previews.py": "4e4ee27ccf5c27b2faf3ca0151edefa8dec93ab4ac85f398fc59fdd1316e0cd9"
    }
  }
}
---

# Agent access to previews and waveforms

Evidence for [the canonical guide](../../USER_GUIDE.md).
