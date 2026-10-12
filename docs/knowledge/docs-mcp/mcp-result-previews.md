---
{
  "type": "Evidence",
  "id": "docs-mcp.mcp-result-previews",
  "title": "Local MCP saved result previews",
  "evidence": {
    "path": "docs/MCP.md",
    "scope": "mcp-result-previews",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed inspect_result_previews: its arguments and bounds (asset_id, envelope, action inspect, retry or cancel, bins 8 to 256, wait 0 to 60 seconds), context token, revision and previewable-state checks, default selection through the preview controller's tile_targets with more_results, still and envelope rendition fields, envelope levels folded by audio_waveform.fold, the bounded wait through the scheduler watch with a final main-thread read only in an unchanged context, the read-only annotation and the absence of any player tool, plus the generated table and the hosted mapping row. Installed-ZIP native tests (tests/blender/test_mcp_result_previews.py) ran on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 with a synthetic SDK transport, an offline storage stub and the real offline audio decoder; no live Scenario preview, other operating system, desktop interaction or MCP client session is claimed. Re-checked after the restack onto the shared preview decode: the wait now watches only the requested renditions, the envelope with envelope true and otherwise the stills, so an envelope wait returns while a Scenario still keeps polling, and in_progress still reports any returned rendition; a still of a result with no preview kind has no source; a retry deferred behind an in-flight batch reads queued at once through the #359 fix, so a wait after it is not reported finished early. A unit test adapted from a review probe fails with that fix reverted, and the two new installed assertions fail with the scoped wait or the source rule reverted. Re-checked against the scheduler's cancel rule: action cancel after a retry deferred behind an in-flight batch keeps the local renditions failed until a later retry, as the tool documentation states; scheduler unit tests cover that order. Re-checked after the restack onto the roughness caption fix: caption() now reads ROLE_LABEL from core.jobs.result_previews, which labels every role in result_metadata.TEXTURE_ROLES, so inspect_result_previews reports a roughness map as Roughness (N), the same caption as its tile. A new installed test checks that caption and fails on the previous head without the fix; for this restack the native suite ran on macOS arm64 Blender 5.1.2 only. The other claims are unchanged. Re-checked after the restack onto the number-first tile captions: the parent's tiles keep the role or kind label and the number apart and draw the number first, as (3) Albedo, while Tile.caption keeps Albedo (3) for status lines; here a shared _label helper feeds both tile_targets and caption(), so inspect_result_previews still reports the caption status lines and saved-job controls use, such as Roughness (N), with the tile's number. MCP.md now adds that the tile itself draws the number first, (2) Audio. For this restack the native suite ran on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1. The other claims are unchanged. Re-checked after the restack onto the measured status wrapping: the parent's draw now wraps status, error and Retry lines by the width Blender's interface font measures and joins a caption's words with a no-break space in those drawn lines; Tile.caption, tile_targets and caption() are unchanged, so inspect_result_previews still reports captions such as Roughness (N) with ordinary spaces, reading as the drawn line does. For this restack the native suite ran on macOS arm64 Blender 5.1.2 only. The other claims are unchanged. Re-checked on 2026-10-12 after the rebase onto main at 4bd0061d, not a full re-review: since the previous review main changed tools_scenario.py (three Film review and four asset organization tools, and other tools' workflow cost, Film composition, first-frame handoff, reference upload, inference-only cancellation, saved original, history row kind and cloud history changes), test_mcp_contracts.py (Film review and asset organization tool names, so the listed tool count is now 76 with this tool), test_mcp_descriptions.py (description tests for its new tools and the history kind list) and test_preview_scheduler.py (a still whose transfer declares no length, polled again); none of these changes touch inspect_result_previews, its specification or the scheduler wait it uses, so the claims above still hold and these sources' fingerprints are the rebased files'; the review date and base revision are unchanged.",
    "sources": {
      "scenario/mcp/tools_scenario.py": "cfaa4ac4eb6fbb35bcfac4fd42d76670e7dccd9c37f74ac6a9cf84e7752c767f",
      "scenario/blender/result_previews.py": "55ca1225160d31ca176e6548428acbda0cfd552a23c473874b4cdbad6482ddff",
      "scenario/core/jobs/preview_scheduler.py": "bcb363aecc64c5478e08e0accbca4083b811cd172a2b1c3f03557029aca426eb",
      "scenario/core/audio_waveform.py": "c5d5715f6d8cd44a18fbff58ec8e0b17dfd045958b2a5c26b1d34b4e2a24400f",
      "tests/blender/test_mcp_result_previews.py": "fb487164da1d7fd93dd841506421fee96e85bfc62e6234b56f817e85a1436dea",
      "tests/blender/test_mcp_contracts.py": "2de740493640e18cc41640c7b37a3ce5119f46fa7fe5b12c29f6ed61329738af",
      "tests/unit/test_mcp_descriptions.py": "d3ba66e2c75710879bff259b2c1f71581f105c3289151c73b9a1e675bf3c1d03",
      "tests/unit/test_preview_scheduler.py": "38e88b470da184a27e45b20a0018a69d06108722f2510eae0959a47418a43c7d"
    }
  }
}
---

# Local MCP saved result previews

Evidence for [the canonical guide](../../MCP.md).
