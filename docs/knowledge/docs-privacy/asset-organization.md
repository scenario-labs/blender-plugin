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
    "reviewed_at": "2026-10-11",
    "base_revision": "72723f02a97a7226b1c697c31d8124b77ac92c86",
    "limits": "Reviewed only the two organization sentences: a connected agent can change collection membership and tags or create a collection, sending the chosen asset IDs, tags and collection names through the shared SDK adapter, and a separate review and apply call precedes an immediate, credit-free account metadata change that Blender Undo does not reverse. A bounded resend after an already-member add refusal sends only a subset of the same reviewed asset IDs, so the sentences stay accurate. Installed synthetic tests confirm request bodies and that no request is sent while online access is off. This is not a legal-policy audit, and it does not establish that an agent obtained the user's permission. No live collection, tag or bulk request was made from this repository; the observed already-member 400 and one-transaction add, service name uniqueness, DELETE body survival, tag normalization and live limits remain unverified here.",
    "sources": {
      "docs/PRIVACY.md": "ac7ee14eeb7fdfcad8bac9555ada13e3e689167204a77b0336f4eb8e334991d2",
      "scenario/mcp/tools_scenario.py": "6e4a3b38ae75521eea54daed93e2a8612dbf49b33eea8de968d084fd84260c99",
      "scenario/core/jobs/organization.py": "69ad48086ff2b763c565a22bce2bf60e142afbc10e757c56d938daf2198fbeba",
      "scenario/core/api/sdk_adapter.py": "43eb582d077677e2975c21e13cd3164b319c96f14a36988c6b9f04ca56124121",
      "tests/blender/test_asset_organization.py": "b00e136dfcf7667b1d93bb54b3efc84c1643380e88e8524ea12238edb6e793d5"
    }
  }
}
---

# Agent collection and tag changes

Evidence for [the canonical guide](../../PRIVACY.md#the-local-mcp-server).
