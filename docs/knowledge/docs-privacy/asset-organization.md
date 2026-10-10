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
    "limits": "Reviewed only the two organization sentences: a connected agent can change collection membership and tags or create a collection, sending the chosen asset IDs, tags and collection names through the shared SDK adapter, and a separate review and apply call precedes an immediate, credit-free account metadata change that Blender Undo does not reverse. Installed synthetic tests confirm request bodies and that no request is sent while online access is off. This is not a legal-policy audit, and it does not establish that an agent obtained the user's permission. No live collection, tag or bulk request was made; service name uniqueness, re-adding a member, DELETE body survival, tag normalization and live limits remain unverified.",
    "sources": {
      "docs/PRIVACY.md": "e7530d29a98b1e8bd8e08b2f4d6f601a566564c53e646084da7419521a47e52f",
      "scenario/mcp/tools_scenario.py": "79d6bfc51b06fba53b870739220068822ae4df0aac3c45d4d68b755794d34356",
      "scenario/core/jobs/organization.py": "7f69ce28e4c54e3c2b819cc76735d001671de6bcfcb12145b2cd90b059e8b84d",
      "scenario/core/api/sdk_adapter.py": "8741ed98d0d4ace8a4d1c21a65aaf79f85eeabf69023477d23fa028f4911bb95",
      "tests/blender/test_asset_organization.py": "bf758ad6d9dd86af04b173e4e4eec85ffc9f708e7be4205bae9039201d593269"
    }
  }
}
---

# Agent collection and tag changes

Evidence for [the canonical guide](../../PRIVACY.md#the-local-mcp-server).
