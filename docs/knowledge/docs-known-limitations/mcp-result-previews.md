---
{
  "type": "Evidence",
  "id": "docs-known-limitations.mcp-result-previews",
  "title": "Local MCP preview and envelope limits",
  "evidence": {
    "path": "docs/KNOWN_LIMITATIONS.md",
    "scope": "mcp-result-previews",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-11",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed that inspect_result_previews returns envelope levels and still metadata, never an image or player launch, and that background Blender leaves image stills in the decode state until the scheduler's 120-second expiry fails them. Installed-ZIP native tests (tests/blender/test_mcp_result_previews.py) ran on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 with a synthetic SDK transport, an offline storage stub and the real offline audio decoder; no live Scenario preview, other operating system, desktop interaction or MCP client session is claimed. Re-checked after the restack onto the roughness caption fix: caption() now reads ROLE_LABEL from core.jobs.result_previews, which labels every role in result_metadata.TEXTURE_ROLES, so inspect_result_previews reports a roughness map as Roughness (N), the same caption as its tile. A new installed test checks that caption and fails on the previous head without the fix; for this restack the native suite ran on macOS arm64 Blender 5.1.2 only. The other claims are unchanged. Re-checked after the restack onto the number-first tile captions: the parent's tiles keep the role or kind label and the number apart and draw the number first, as (3) Albedo, while Tile.caption keeps Albedo (3) for status lines; here a shared _label helper feeds both tile_targets and caption(), so inspect_result_previews still reports the caption status lines and saved-job controls use, such as Roughness (N), with the tile's number. For this restack the native suite ran on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1. The other claims are unchanged.",
    "sources": {
      "scenario/mcp/tools_scenario.py": "405d28882eed0ab8182b11bf993fcece60a18b61061bb08225661c7f39117a09",
      "scenario/core/jobs/preview_scheduler.py": "bcb363aecc64c5478e08e0accbca4083b811cd172a2b1c3f03557029aca426eb",
      "scenario/blender/result_previews.py": "00f36ef0541ad89df08f67980812b4fa377f2f1d0278b5194d84469d7efc34cd",
      "tests/blender/test_mcp_result_previews.py": "fb487164da1d7fd93dd841506421fee96e85bfc62e6234b56f817e85a1436dea"
    }
  }
}
---

# Local MCP preview and envelope limits

Evidence for [the canonical guide](../../KNOWN_LIMITATIONS.md).
