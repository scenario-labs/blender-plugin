---
{
  "type": "Evidence",
  "id": "docs-known-limitations.mcp-result-previews",
  "title": "Local MCP preview and envelope limits",
  "evidence": {
    "path": "docs/KNOWN_LIMITATIONS.md",
    "scope": "mcp-result-previews",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed that inspect_result_previews returns envelope levels and still metadata, never an image or player launch, and that background Blender leaves image stills in the decode state until the scheduler's 120-second expiry fails them. Installed-ZIP native tests (tests/blender/test_mcp_result_previews.py) ran on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 with a synthetic SDK transport, an offline storage stub and the real offline audio decoder; no live Scenario preview, other operating system, desktop interaction or MCP client session is claimed.",
    "sources": {
      "scenario/mcp/tools_scenario.py": "405d28882eed0ab8182b11bf993fcece60a18b61061bb08225661c7f39117a09",
      "scenario/core/jobs/preview_scheduler.py": "bcb363aecc64c5478e08e0accbca4083b811cd172a2b1c3f03557029aca426eb",
      "scenario/blender/result_previews.py": "2431b148a91e5cd035ac1d6ed670eef638dad931f8c1f7fb57c7f0f750a121a8",
      "tests/blender/test_mcp_result_previews.py": "a9c6cc703f94828264aea23b087ac91d67e38546bf6f82d5f93993dcb95a142b"
    }
  }
}
---

# Local MCP preview and envelope limits

Evidence for [the canonical guide](../../KNOWN_LIMITATIONS.md).
