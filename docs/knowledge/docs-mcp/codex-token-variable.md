---
{
  "type": "Evidence",
  "id": "docs-mcp.codex-token-variable",
  "title": "Codex local MCP token variable",
  "evidence": {
    "path": "docs/MCP.md",
    "scope": "codex-token-variable",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Inspected the repository Codex MCP entry, the generated Codex client snippet, headless CLI token resolution and this document's Codex example; all name SCENARIO_BLENDER_TOKEN and the repository entry remains disabled. An offline unit regression compares them. No authenticated Codex connection, dotenv loading (#71), token rotation or native runtime acceptance is claimed.",
    "sources": {
      ".codex/config.toml": "fcc339f393ab5c82ff34039150dfa1cd50587ef462bafcbe9bff947e796b27ae",
      "scenario/blender/mcp_service.py": "f56b2020dadeef23ae089a5a649bbbb99fa4cba407994ebd8f3d12c1680495b9",
      "scenario/mcp/cli.py": "733ec02de0f03a9bfb0a9326a8f94ac32a2b6c33a5c11a09b79694cabd87c156",
      "tests/unit/test_cli_command.py": "c3e4ee60799a2f921583e25f6ac0f354af097862eb19f0dd61d32b0926042681"
    }
  }
}
---

Evidence for [the canonical document](../../MCP.md).
