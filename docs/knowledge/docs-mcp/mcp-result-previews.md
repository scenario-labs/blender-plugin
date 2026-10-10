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
    "limits": "Reviewed inspect_result_previews: its arguments and bounds (asset_id, envelope, action inspect, retry or cancel, bins 8 to 256, wait 0 to 60 seconds), context token, revision and previewable-state checks, default selection through the preview controller's tile_targets with more_results, still and envelope rendition fields, envelope levels folded by audio_waveform.fold, the bounded wait through the scheduler watch with a final main-thread read only in an unchanged context, the read-only annotation and the absence of any player tool, plus the generated table and the hosted mapping row. Installed-ZIP native tests (tests/blender/test_mcp_result_previews.py) ran on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 with a synthetic SDK transport, an offline storage stub and the real offline audio decoder; no live Scenario preview, other operating system, desktop interaction or MCP client session is claimed. Re-checked after the restack onto the shared preview decode: the wait now watches only the requested renditions, the envelope with envelope true and otherwise the stills, so an envelope wait returns while a Scenario still keeps polling, and in_progress still reports any returned rendition; a still of a result with no preview kind has no source; a retry deferred behind an in-flight batch reads queued at once through the #359 fix, so a wait after it is not reported finished early. A unit test adapted from a review probe fails with that fix reverted, and the two new installed assertions fail with the scoped wait or the source rule reverted.",
    "sources": {
      "scenario/mcp/tools_scenario.py": "405d28882eed0ab8182b11bf993fcece60a18b61061bb08225661c7f39117a09",
      "scenario/blender/result_previews.py": "2431b148a91e5cd035ac1d6ed670eef638dad931f8c1f7fb57c7f0f750a121a8",
      "scenario/core/jobs/preview_scheduler.py": "c2c820b2de38d7b22fdcd21c2654eea88a672877fd7a9f14f07a4631022aca54",
      "scenario/core/audio_waveform.py": "c5d5715f6d8cd44a18fbff58ec8e0b17dfd045958b2a5c26b1d34b4e2a24400f",
      "tests/blender/test_mcp_result_previews.py": "a9c6cc703f94828264aea23b087ac91d67e38546bf6f82d5f93993dcb95a142b",
      "tests/blender/test_mcp_contracts.py": "63aa8a57c1ef5add122c833d053c408e5d858901f486588a9cc49bf59b4ea0e7",
      "tests/unit/test_mcp_descriptions.py": "24eba70eb9d2be0824aba42cd426420c7bc4d41e2bd0531d3716276e2bf61835",
      "tests/unit/test_preview_scheduler.py": "81d980faea7c9f61aaa243247f6e81ee564b17502e5811af69308f067f3dd90c"
    }
  }
}
---

# Local MCP saved result previews

Evidence for [the canonical guide](../../MCP.md).
