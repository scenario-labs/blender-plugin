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
    "limits": "Reviewed inspect_result_previews: its arguments and bounds (asset_id, envelope, action inspect, retry or cancel, bins 8 to 256, wait 0 to 60 seconds), context token, revision and previewable-state checks, default selection through the preview controller's tile_targets with more_results, still and envelope rendition fields, envelope levels folded by audio_waveform.fold, the bounded wait through the scheduler watch with a final main-thread read only in an unchanged context, the read-only annotation and the absence of any player tool, plus the generated table and the hosted mapping row. Installed-ZIP native tests (tests/blender/test_mcp_result_previews.py) ran on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 with a synthetic SDK transport, an offline storage stub and the real offline audio decoder; no live Scenario preview, other operating system, desktop interaction or MCP client session is claimed.",
    "sources": {
      "scenario/mcp/tools_scenario.py": "2544f304b15c2c828f7ccf8d17531851719473225d098e22ca9cc226e61918db",
      "scenario/blender/result_previews.py": "2d13cfe3e7c1c89fe7ee4717c2c36432c1d01a35f1e5cd2d0f8a284f87c48ae7",
      "scenario/core/jobs/preview_scheduler.py": "13eec9d2ff9cca03c5d39d16c54083db01ffed4fa4f075c6ceea4c0bb09b0dda",
      "scenario/core/audio_waveform.py": "c5d5715f6d8cd44a18fbff58ec8e0b17dfd045958b2a5c26b1d34b4e2a24400f",
      "tests/blender/test_mcp_result_previews.py": "4e4ee27ccf5c27b2faf3ca0151edefa8dec93ab4ac85f398fc59fdd1316e0cd9",
      "tests/blender/test_mcp_contracts.py": "63aa8a57c1ef5add122c833d053c408e5d858901f486588a9cc49bf59b4ea0e7",
      "tests/unit/test_mcp_descriptions.py": "24eba70eb9d2be0824aba42cd426420c7bc4d41e2bd0531d3716276e2bf61835"
    }
  }
}
---

# Local MCP saved result previews

Evidence for [the canonical guide](../../MCP.md).
