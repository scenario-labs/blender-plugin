---
{
  "type": "Evidence",
  "id": "docs-privacy.local-mcp",
  "title": "docs/PRIVACY.md: local mcp",
  "description": "Repository evidence for the named source family and canonical document.",
  "evidence": {
    "path": "docs/PRIVACY.md",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-13",
    "limits": "Re-reviewed on 2026-10-13 for the local MCP section's start, listener and upload claims: the GUI start with the extension when Allow Online Access is on (registry.register calls mcp_service.start outside background mode), the Agents (MCP) panel's Stop MCP server operator, the explicit headless scenario_blender command, McpServer refusing any bind host other than 127.0.0.1, the Host check and 60-second idle timeout in server.py, the session-generated token, the manifest network permission naming the 127.0.0.1 listener, and the agent upload allowlist in upload_policy.py, reference_uploads.py, tools_scenario.upload_reference and render_commands (files the extension saved or the user chose this session; the Output Folder and every other path refused before reading). MCP generate's require_quote and approved_cost were rechecked in tools_scenario.py. The section's prompt, Blockout, Film, organization and recovery approval sentences were not re-reviewed and keep their earlier evidence. Earlier statements still apply: this note discloses the explicit credential source; there is no live service call or legal-policy audit; native synthetic preference-storage tests verify local persistence. Other PRIVACY.md sections keep their own topics.",
    "sources": {
      "docs/MCP.md": "8675f5b2f7d38f5e534680c97f14a35dd5f530655ca13594c360b595e700df14",
      "scenario/blender/mcp_service.py": "f56b2020dadeef23ae089a5a649bbbb99fa4cba407994ebd8f3d12c1680495b9",
      "scenario/blender/registry.py": "c3a880832b4cf47ce530ecea582a5c73e53c8f346d5a6521b7c023bab31cd9e3",
      "scenario/blender/operators.py": "8881ad17a319551e5cfb3af00937651df50b4584adfa7b4221d506baa2269475",
      "scenario/blender/reference_uploads.py": "688f20c80bffe9ee16c602867ee1c03132e3f174c6bdaf866b0e9472bdca53ba",
      "scenario/blender/render_commands.py": "c49dd046a555163775183ddc51b67a0bc8e72798db9b3ca026e86ae8a9b9680c",
      "scenario/blender_manifest.toml": "d9272c0810c168b1558ce0891fecf062a3974dcbc9bbae1a89777b911a1bfcef",
      "scenario/mcp/server.py": "775c22ecdb8e7aad7fec1044f431564812c60bc49febb7e1f6eb3e14d57fb29a",
      "scenario/mcp/tools_scenario.py": "7f82a77aa9f76e6907f07d5a716e154a44a2a56735326d9cf20dbfbc5d52b007",
      "scenario/mcp/upload_policy.py": "b2eec937e08ca92d659808692294286993fea428708d9b25489b642d80e9102d"
    },
    "scope": "local-mcp",
    "base_revision": "a0a0c9259535a483acff2f3d52a9e161449ececc"
  }
}
---

# docs/PRIVACY.md: local mcp

Evidence for [the canonical document](../../PRIVACY.md).

Source families separate independent maintenance work. The review date, coverage,
source fingerprints and document-wide limitations were preserved during the split.
Grouping sources does not renew the review or attribute every inherited claim to
this subset. Review and narrow this topic's limits when its evidence changes.
