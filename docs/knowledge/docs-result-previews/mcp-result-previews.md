---
{
  "type": "Evidence",
  "id": "docs-result-previews.mcp-result-previews",
  "title": "Local MCP inspection of the preview scheduler",
  "evidence": {
    "path": "docs/RESULT_PREVIEWS.md",
    "scope": "mcp-result-previews",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the scheduler's quiet, watch and unwatch (offline counts as quiet, at most eight open watches, signals set by pump and released by close and release, owner-thread checks), audio_waveform.fold, and the MCP tool's use of request, retry, cancel and status snapshots without paths, decode requests, URLs or image bytes, plus the controller's forget_failures on retry. Unit tests cover the watch with a second thread, its bound and release and the fold. Installed-ZIP native tests (tests/blender/test_mcp_result_previews.py) ran on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 with a synthetic SDK transport, an offline storage stub and the real offline audio decoder; no live Scenario preview, other operating system, desktop interaction or MCP client session is claimed.",
    "sources": {
      "scenario/mcp/tools_scenario.py": "2544f304b15c2c828f7ccf8d17531851719473225d098e22ca9cc226e61918db",
      "scenario/core/jobs/preview_scheduler.py": "13eec9d2ff9cca03c5d39d16c54083db01ffed4fa4f075c6ceea4c0bb09b0dda",
      "scenario/core/audio_waveform.py": "c5d5715f6d8cd44a18fbff58ec8e0b17dfd045958b2a5c26b1d34b4e2a24400f",
      "scenario/blender/result_previews.py": "2d13cfe3e7c1c89fe7ee4717c2c36432c1d01a35f1e5cd2d0f8a284f87c48ae7",
      "tests/blender/test_mcp_result_previews.py": "4e4ee27ccf5c27b2faf3ca0151edefa8dec93ab4ac85f398fc59fdd1316e0cd9",
      "tests/unit/test_preview_scheduler.py": "0507863f8efaa5128f54a84c345215e93075648aa8905593da8a82acaa767788",
      "tests/unit/test_audio_waveform.py": "4b642b36929e25e8d1a8da2d56d9d28c2096ee68f5cc4ccb5095791e358aee45"
    }
  }
}
---

# Local MCP inspection of the preview scheduler

Evidence for [the canonical guide](../../RESULT_PREVIEWS.md).
