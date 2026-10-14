---
{
  "type": "Evidence",
  "id": "security",
  "title": "SECURITY.md evidence",
  "evidence": {
    "path": "SECURITY.md",
    "coverage": "policy",
    "reviewed_at": "2026-10-14",
    "reviewed_revision": "7d3e55cc9ac64e68899fe1adb80a545688701ca9",
    "limits": "Policy reviewed against the MCP server, preferences, credential selection, Python guard and Scorecard workflow. It certifies no implementation; repository security settings, the advisory form and the published Scorecard result were not checked.",
    "sources": [
      ".github/workflows/scorecard.yml",
      "scenario/blender/mcp_service.py",
      "scenario/blender_manifest.toml",
      "scenario/core/config.py",
      "scenario/mcp/sandbox.py",
      "scenario/mcp/server.py",
      "scenario/mcp/stdio_shim.py",
      "scenario/mcp/tools_blender.py",
      "scenario/prefs.py"
    ]
  }
}
---

Evidence for [the canonical document](../../SECURITY.md).
