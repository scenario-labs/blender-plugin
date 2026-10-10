---
{
  "type": "Evidence",
  "id": "release-acceptance.mcp-result-previews",
  "title": "Issue 189 status after MCP preview inspection",
  "evidence": {
    "path": "docs/maintenance/release-acceptance.md",
    "scope": "mcp-result-previews",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed that local MCP inspect_result_previews reads the same preview states and envelopes as the native controls. Desktop interaction, an opened player and native listening remain unrecorded. Installed-ZIP native tests (tests/blender/test_mcp_result_previews.py) ran on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 with a synthetic SDK transport, an offline storage stub and the real offline audio decoder; no live Scenario preview, other operating system, desktop interaction or MCP client session is claimed. Re-checked after the restack onto the roughness caption fix: the installed test file gained a roughness caption test, and for this restack the native suite ran on macOS arm64 Blender 5.1.2 only. The other claims are unchanged.",
    "sources": {
      "scenario/mcp/tools_scenario.py": "405d28882eed0ab8182b11bf993fcece60a18b61061bb08225661c7f39117a09",
      "tests/blender/test_mcp_result_previews.py": "fb487164da1d7fd93dd841506421fee96e85bfc62e6234b56f817e85a1436dea"
    }
  }
}
---

# Issue 189 status after MCP preview inspection

Evidence for [the canonical guide](../../maintenance/release-acceptance.md).
