---
{
  "type": "Evidence",
  "id": "release-acceptance.mcp-result-previews",
  "title": "Issue 189 status after MCP preview inspection",
  "evidence": {
    "path": "docs/maintenance/release-acceptance.md",
    "scope": "mcp-result-previews",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed that local MCP inspect_result_previews reads the same preview states and envelopes as the native controls. The #189 row's desktop sentence belongs to the saved-media-playback topic: partial private passes opened a saved video in the system and animation players and drew a waveform at UI scale 1.0 on macOS arm64 Blender 5.1.2, and Play audio, desktop Cancel and Retry, the measured wrapping, other platforms and UI scales and native listening remain unrecorded. Installed-ZIP native tests (tests/blender/test_mcp_result_previews.py) ran on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 with a synthetic SDK transport, an offline storage stub and the real offline audio decoder; no live Scenario preview, other operating system, desktop interaction or MCP client session is claimed. Re-checked after the restack onto the roughness caption fix: the installed test file gained a roughness caption test, and for this restack the native suite ran on macOS arm64 Blender 5.1.2 only. The other claims are unchanged. Re-checked on 2026-10-12 after the restack merged this PR's MCP sentence into that reconciled row: the MCP claim is unchanged, and no desktop evidence covers the MCP tool. Re-checked on 2026-10-12 after the rebase onto main at 4bd0061d, not a full re-review: since the previous review main changed tools_scenario.py (three Film review and four asset organization tools, and other tools' workflow cost, Film composition, first-frame handoff, reference upload, inference-only cancellation, saved original, history row kind and cloud history changes); none of these changes touch inspect_result_previews, its specification or the scheduler wait it uses, so the claims above still hold and these sources' fingerprints are the rebased files'; the review date and base revision are unchanged.",
    "sources": {
      "scenario/mcp/tools_scenario.py": "cfaa4ac4eb6fbb35bcfac4fd42d76670e7dccd9c37f74ac6a9cf84e7752c767f",
      "tests/blender/test_mcp_result_previews.py": "fb487164da1d7fd93dd841506421fee96e85bfc62e6234b56f817e85a1436dea"
    }
  }
}
---

# Issue 189 status after MCP preview inspection

Evidence for [the canonical guide](../../maintenance/release-acceptance.md).
