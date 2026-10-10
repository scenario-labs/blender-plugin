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
    "limits": "Reviewed the scheduler's quiet, watch and unwatch (offline counts as quiet, at most eight open watches, signals set by pump and released by close and release, owner-thread checks), audio_waveform.fold, and the MCP tool's use of request, retry, cancel and status snapshots without paths, decode requests, URLs or image bytes, plus the controller's forget_failures on retry. Unit tests cover the watch with a second thread, its bound and release and the fold. Installed-ZIP native tests (tests/blender/test_mcp_result_previews.py) ran on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 with a synthetic SDK transport, an offline storage stub and the real offline audio decoder; no live Scenario preview, other operating system, desktop interaction or MCP client session is claimed. Re-checked after the restack: quiet and watch now accept a renditions filter, the MCP tool watches the requested renditions only, a retry deferred behind an in-flight batch reads queued and is never quiet, and an unsupported still has no source. Unit tests cover the filtered watch and the adapted review probe. Re-checked against the scheduler's cancel rule: a cancel after a retry deferred behind an in-flight batch keeps local renditions failed, so an envelope wait after it ends at once; scheduler unit tests cover that order.",
    "sources": {
      "scenario/mcp/tools_scenario.py": "405d28882eed0ab8182b11bf993fcece60a18b61061bb08225661c7f39117a09",
      "scenario/core/jobs/preview_scheduler.py": "bcb363aecc64c5478e08e0accbca4083b811cd172a2b1c3f03557029aca426eb",
      "scenario/core/audio_waveform.py": "c5d5715f6d8cd44a18fbff58ec8e0b17dfd045958b2a5c26b1d34b4e2a24400f",
      "scenario/blender/result_previews.py": "2431b148a91e5cd035ac1d6ed670eef638dad931f8c1f7fb57c7f0f750a121a8",
      "tests/blender/test_mcp_result_previews.py": "a9c6cc703f94828264aea23b087ac91d67e38546bf6f82d5f93993dcb95a142b",
      "tests/unit/test_preview_scheduler.py": "12b477b6a61d888b4c3a92b69174d80c1ca539fcc7b3c650e2679c55847ff013",
      "tests/unit/test_audio_waveform.py": "4b642b36929e25e8d1a8da2d56d9d28c2096ee68f5cc4ccb5095791e358aee45"
    }
  }
}
---

# Local MCP inspection of the preview scheduler

Evidence for [the canonical guide](../../RESULT_PREVIEWS.md).
