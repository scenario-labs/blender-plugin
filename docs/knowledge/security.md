---
{
  "type": "Evidence",
  "id": "security",
  "title": "SECURITY.md evidence",
  "evidence": {
    "path": "SECURITY.md",
    "coverage": "policy",
    "reviewed_at": "2026-11-04",
    "reviewed_revision": "a316f6a00c2c126d63e349f492fd9340d7ca7e3b",
    "limits": "Policy reviewed against the MCP server, client setup, preferences, credential selection, browser sign-in, Python guard, telemetry relay client and Scorecard workflow. It certifies no implementation; repository security settings, the advisory form and the published Scorecard result were not checked.",
    "sources": [
      ".github/workflows/scorecard.yml",
      "scenario/blender/mcp_service.py",
      "scenario/blender_manifest.toml",
      "scenario/core/api/oauth.py",
      "scenario/core/config.py",
      "scenario/core/telemetry/relay.py",
      "scenario/mcp/client_setup.py",
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
