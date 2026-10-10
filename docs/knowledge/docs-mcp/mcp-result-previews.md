---
{
  "type": "Evidence",
  "id": "docs-mcp.mcp-result-previews",
  "title": "Local MCP saved result previews",
  "evidence": {
    "path": "docs/MCP.md",
    "scope": "mcp-result-previews",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed inspect_result_previews: its arguments and bounds (asset_id, envelope, action inspect, retry or cancel, bins 8 to 256, wait 0 to 60 seconds), context token, revision and previewable-state checks, default selection through the preview controller's tile_targets with more_results, still and envelope rendition fields, envelope levels folded by audio_waveform.fold, the bounded wait through the scheduler watch with a final main-thread read only in an unchanged context, the read-only annotation and the absence of any player tool, plus the generated table and the hosted mapping row. Installed-ZIP native tests (tests/blender/test_mcp_result_previews.py) ran on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 with a synthetic SDK transport, an offline storage stub and the real offline audio decoder; no live Scenario preview, other operating system, desktop interaction or MCP client session is claimed. Re-checked after the restack onto the shared preview decode: the wait now watches only the requested renditions, the envelope with envelope true and otherwise the stills, so an envelope wait returns while a Scenario still keeps polling, and in_progress still reports any returned rendition; a still of a result with no preview kind has no source; a retry deferred behind an in-flight batch reads queued at once through the #359 fix, so a wait after it is not reported finished early. A unit test adapted from a review probe fails with that fix reverted, and the two new installed assertions fail with the scoped wait or the source rule reverted. Re-checked against the scheduler's cancel rule: action cancel after a retry deferred behind an in-flight batch keeps the local renditions failed until a later retry, as the tool documentation states; scheduler unit tests cover that order. Re-checked after the restack onto the roughness caption fix: caption() now reads ROLE_LABEL from core.jobs.result_previews, which labels every role in result_metadata.TEXTURE_ROLES, so inspect_result_previews reports a roughness map as Roughness (N), the same caption as its tile. A new installed test checks that caption and fails on the previous head without the fix; for this restack the native suite ran on macOS arm64 Blender 5.1.2 only. The other claims are unchanged.",
    "sources": {
      "scenario/mcp/tools_scenario.py": "405d28882eed0ab8182b11bf993fcece60a18b61061bb08225661c7f39117a09",
      "scenario/blender/result_previews.py": "8c9a836b6322c2ecd24506d68b46186b8addf3a2de3acec12569df07e6ab44d9",
      "scenario/core/jobs/preview_scheduler.py": "bcb363aecc64c5478e08e0accbca4083b811cd172a2b1c3f03557029aca426eb",
      "scenario/core/audio_waveform.py": "c5d5715f6d8cd44a18fbff58ec8e0b17dfd045958b2a5c26b1d34b4e2a24400f",
      "tests/blender/test_mcp_result_previews.py": "fb487164da1d7fd93dd841506421fee96e85bfc62e6234b56f817e85a1436dea",
      "tests/blender/test_mcp_contracts.py": "63aa8a57c1ef5add122c833d053c408e5d858901f486588a9cc49bf59b4ea0e7",
      "tests/unit/test_mcp_descriptions.py": "24eba70eb9d2be0824aba42cd426420c7bc4d41e2bd0531d3716276e2bf61835",
      "tests/unit/test_preview_scheduler.py": "12b477b6a61d888b4c3a92b69174d80c1ca539fcc7b3c650e2679c55847ff013"
    }
  }
}
---

# Local MCP saved result previews

Evidence for [the canonical guide](../../MCP.md).
