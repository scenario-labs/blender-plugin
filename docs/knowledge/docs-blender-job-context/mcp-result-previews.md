---
{
  "type": "Evidence",
  "id": "docs-blender-job-context.mcp-result-previews",
  "title": "Local MCP use of the preview scheduler",
  "evidence": {
    "path": "docs/BLENDER_JOB_CONTEXT.md",
    "scope": "mcp-result-previews",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the MCP tool's checks (context token, saved revision, previewable state), its requests, retry with the controller's forget_failures and cancel, and the watch that pump sets, deactivate releases through the scheduler's close, and the final main-thread read in an unchanged context and session. Installed-ZIP native tests (tests/blender/test_mcp_result_previews.py) ran on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 with a synthetic SDK transport, an offline storage stub and the real offline audio decoder; no live Scenario preview, other operating system, desktop interaction or MCP client session is claimed. Re-checked after the restack onto the roughness caption fix: caption() now reads ROLE_LABEL from core.jobs.result_previews, which labels every role in result_metadata.TEXTURE_ROLES, so inspect_result_previews reports a roughness map as Roughness (N), the same caption as its tile. A new installed test checks that caption and fails on the previous head without the fix; for this restack the native suite ran on macOS arm64 Blender 5.1.2 only. The other claims are unchanged. Re-checked after the restack onto the number-first tile captions: the parent's tiles keep the role or kind label and the number apart and draw the number first, as (3) Albedo, while Tile.caption keeps Albedo (3) for status lines; here a shared _label helper feeds both tile_targets and caption(), so inspect_result_previews still reports the caption status lines and saved-job controls use, such as Roughness (N), with the tile's number. For this restack the native suite ran on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1. The other claims are unchanged. Re-checked after the restack onto the measured status wrapping: the parent's draw now wraps status, error and Retry lines by the width Blender's interface font measures and joins a caption's words with a no-break space in those drawn lines; Tile.caption, tile_targets and caption() are unchanged, so inspect_result_previews still reports captions such as Roughness (N) with ordinary spaces, reading as the drawn line does. For this restack the native suite ran on macOS arm64 Blender 5.1.2 only. The other claims are unchanged.",
    "sources": {
      "scenario/mcp/tools_scenario.py": "405d28882eed0ab8182b11bf993fcece60a18b61061bb08225661c7f39117a09",
      "scenario/core/jobs/preview_scheduler.py": "bcb363aecc64c5478e08e0accbca4083b811cd172a2b1c3f03557029aca426eb",
      "scenario/blender/result_previews.py": "55ca1225160d31ca176e6548428acbda0cfd552a23c473874b4cdbad6482ddff",
      "scenario/blender/job_session.py": "fb42ae76844e48b22a7ef48d3cc408370392ce7be3d78cb4f3e587ea9d5c2c47",
      "tests/blender/test_mcp_result_previews.py": "fb487164da1d7fd93dd841506421fee96e85bfc62e6234b56f817e85a1436dea"
    }
  }
}
---

# Local MCP use of the preview scheduler

Evidence for [the canonical guide](../../BLENDER_JOB_CONTEXT.md).
