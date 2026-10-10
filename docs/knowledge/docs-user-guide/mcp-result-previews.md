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
    "limits": "Reviewed that connected agents read the same preview states and audio waveforms as the Jobs and Generations tiles and the Waveform control through inspect_result_previews, and that no MCP tool opens a player. Installed-ZIP native tests (tests/blender/test_mcp_result_previews.py) ran on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 with a synthetic SDK transport, an offline storage stub and the real offline audio decoder; no live Scenario preview, other operating system, desktop interaction or MCP client session is claimed. Re-checked after the restack onto the roughness caption fix: caption() now reads ROLE_LABEL from core.jobs.result_previews, which labels every role in result_metadata.TEXTURE_ROLES, so inspect_result_previews reports a roughness map as Roughness (N), the same caption as its tile. A new installed test checks that caption and fails on the previous head without the fix; for this restack the native suite ran on macOS arm64 Blender 5.1.2 only. The other claims are unchanged.",
    "sources": {
      "scenario/mcp/tools_scenario.py": "405d28882eed0ab8182b11bf993fcece60a18b61061bb08225661c7f39117a09",
      "scenario/blender/result_previews.py": "8c9a836b6322c2ecd24506d68b46186b8addf3a2de3acec12569df07e6ab44d9",
      "tests/blender/test_mcp_result_previews.py": "fb487164da1d7fd93dd841506421fee96e85bfc62e6234b56f817e85a1436dea"
    }
  }
}
---

# Agent access to previews and waveforms

Evidence for [the canonical guide](../../USER_GUIDE.md).
