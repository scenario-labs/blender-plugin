---
{
  "type": "Evidence",
  "id": "docs-privacy.asset-organization",
  "title": "Agent collection and tag changes in privacy disclosures",
  "description": "What the local MCP organization tools send to Scenario and how their account changes are approved.",
  "evidence": {
    "path": "docs/PRIVACY.md",
    "scope": "asset-organization",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed only the two organization sentences: a connected agent can change collection membership and tags or create a collection, sending the chosen asset IDs, tags and collection names through the shared SDK adapter, and a separate review and apply call precedes an immediate, credit-free account metadata change that Blender Undo does not reverse. A bounded resend after an already-member add refusal sends only a subset of the same reviewed asset IDs, so the sentences stay accurate. Installed synthetic tests confirm request bodies and that no request is sent while online access is off. This is not a legal-policy audit, and it does not establish that an agent obtained the user's permission. No live collection, tag or bulk request was made from this repository; the observed already-member 400 and one-transaction add, service name uniqueness, DELETE body survival, tag normalization and live limits remain unverified here.",
    "sources": {
      "docs/PRIVACY.md": "e7530d29a98b1e8bd8e08b2f4d6f601a566564c53e646084da7419521a47e52f",
      "scenario/mcp/tools_scenario.py": "f4e87186806f93466220ef04f7c2530f0532ded790d4a8754a2a5b81183db08a",
      "scenario/core/jobs/organization.py": "69ad48086ff2b763c565a22bce2bf60e142afbc10e757c56d938daf2198fbeba",
      "scenario/core/api/sdk_adapter.py": "43eb582d077677e2975c21e13cd3164b319c96f14a36988c6b9f04ca56124121",
      "tests/blender/test_asset_organization.py": "b00e136dfcf7667b1d93bb54b3efc84c1643380e88e8524ea12238edb6e793d5"
    }
  }
}
---

# Agent collection and tag changes

Evidence for [the canonical guide](../../PRIVACY.md#the-local-mcp-server).
