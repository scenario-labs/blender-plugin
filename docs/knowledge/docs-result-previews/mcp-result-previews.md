---
{
  "type": "Evidence",
  "id": "docs-result-previews.mcp-result-previews",
  "title": "Local MCP inspection of the preview scheduler",
  "evidence": {
    "path": "docs/RESULT_PREVIEWS.md",
    "scope": "mcp-result-previews",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-11",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the scheduler's quiet, watch and unwatch (offline counts as quiet, at most eight open watches, signals set by pump and released by close and release, owner-thread checks), audio_waveform.fold, and the MCP tool's use of request, retry, cancel and status snapshots without paths, decode requests, URLs or image bytes, plus the controller's forget_failures on retry. Unit tests cover the watch with a second thread, its bound and release and the fold. Installed-ZIP native tests (tests/blender/test_mcp_result_previews.py) ran on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 with a synthetic SDK transport, an offline storage stub and the real offline audio decoder; no live Scenario preview, other operating system, desktop interaction or MCP client session is claimed. Re-checked after the restack: quiet and watch now accept a renditions filter, the MCP tool watches the requested renditions only, a retry deferred behind an in-flight batch reads queued and is never quiet, and an unsupported still has no source. Unit tests cover the filtered watch and the adapted review probe. Re-checked against the scheduler's cancel rule: a cancel after a retry deferred behind an in-flight batch keeps local renditions failed, so an envelope wait after it ends at once; scheduler unit tests cover that order. Re-checked after the restack onto the roughness caption fix: caption() now reads ROLE_LABEL from core.jobs.result_previews, which labels every role in result_metadata.TEXTURE_ROLES, so inspect_result_previews reports a roughness map as Roughness (N), the same caption as its tile. A new installed test checks that caption and fails on the previous head without the fix; for this restack the native suite ran on macOS arm64 Blender 5.1.2 only. The other claims are unchanged. Re-checked after the restack onto the number-first tile captions: the parent's tiles keep the role or kind label and the number apart and draw the number first, as (3) Albedo, while Tile.caption keeps Albedo (3) for status lines; here a shared _label helper feeds both tile_targets and caption(), so inspect_result_previews still reports the caption status lines and saved-job controls use, such as Roughness (N), with the tile's number. For this restack the native suite ran on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1. The other claims are unchanged.",
    "sources": {
      "scenario/mcp/tools_scenario.py": "405d28882eed0ab8182b11bf993fcece60a18b61061bb08225661c7f39117a09",
      "scenario/core/jobs/preview_scheduler.py": "bcb363aecc64c5478e08e0accbca4083b811cd172a2b1c3f03557029aca426eb",
      "scenario/core/audio_waveform.py": "c5d5715f6d8cd44a18fbff58ec8e0b17dfd045958b2a5c26b1d34b4e2a24400f",
      "scenario/blender/result_previews.py": "00f36ef0541ad89df08f67980812b4fa377f2f1d0278b5194d84469d7efc34cd",
      "tests/blender/test_mcp_result_previews.py": "fb487164da1d7fd93dd841506421fee96e85bfc62e6234b56f817e85a1436dea",
      "tests/unit/test_preview_scheduler.py": "12b477b6a61d888b4c3a92b69174d80c1ca539fcc7b3c650e2679c55847ff013",
      "tests/unit/test_audio_waveform.py": "4b642b36929e25e8d1a8da2d56d9d28c2096ee68f5cc4ccb5095791e358aee45"
    }
  }
}
---

# Local MCP inspection of the preview scheduler

Evidence for [the canonical guide](../../RESULT_PREVIEWS.md).
