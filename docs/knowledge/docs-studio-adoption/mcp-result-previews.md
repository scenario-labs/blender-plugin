---
{
  "type": "Evidence",
  "id": "docs-studio-adoption.mcp-result-previews",
  "title": "Preview MCP parity in the adoption table",
  "evidence": {
    "path": "docs/STUDIO_ADOPTION.md",
    "scope": "mcp-result-previews",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed that local MCP inspect_result_previews reads the same scheduler states, still metadata and envelopes as the native preview tiles and Waveform control; the compact composer surface and live and desktop acceptance remain unclaimed. Installed-ZIP native tests (tests/blender/test_mcp_result_previews.py) ran on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 with a synthetic SDK transport, an offline storage stub and the real offline audio decoder; no live Scenario preview, other operating system, desktop interaction or MCP client session is claimed.",
    "sources": {
      "scenario/mcp/tools_scenario.py": "2544f304b15c2c828f7ccf8d17531851719473225d098e22ca9cc226e61918db",
      "scenario/blender/result_previews.py": "2d13cfe3e7c1c89fe7ee4717c2c36432c1d01a35f1e5cd2d0f8a284f87c48ae7",
      "tests/blender/test_mcp_result_previews.py": "4e4ee27ccf5c27b2faf3ca0151edefa8dec93ab4ac85f398fc59fdd1316e0cd9"
    }
  }
}
---

# Preview MCP parity in the adoption table

Evidence for [the canonical guide](../../STUDIO_ADOPTION.md).
