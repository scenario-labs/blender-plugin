---
{
  "type": "Evidence",
  "id": "docs-privacy.asset-organization",
  "title": "Library and agent collection and tag changes in privacy disclosures",
  "description": "What the native Library and local MCP organization controls send to Scenario and how their account changes are approved.",
  "evidence": {
    "path": "docs/PRIVACY.md",
    "scope": "asset-organization",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-11",
    "base_revision": "7fb15252f747f52db24f7e659f8d5048241f803e",
    "limits": "Reviewed the Studio Library and agent organization sentences: Load collections reads collection names and counts only when chosen; confirming Organize reads the chosen asset's tags and memberships and the target collection or matching names; Apply, after a review, sends that asset ID with the entered tags or collection name; a connected agent can change collection membership and tags or create a collection, sending the chosen asset IDs, tags and collection names through the shared SDK adapter; and a separate review and apply precedes an immediate, credit-free account metadata change that Blender Undo does not reverse. A bounded resend after an already-member add refusal sends only a subset of the same reviewed asset IDs, so the sentences stay accurate. Installed synthetic tests confirm request bodies, that drawing and a cancelled dialog send nothing and that no request is sent while online access is off. This is not a legal-policy audit, and it does not establish that an agent obtained the user's permission. No live collection, tag or bulk request was made from this repository; the observed already-member 400 and one-transaction add, service name uniqueness, DELETE body survival, tag normalization and live limits remain unverified here.",
    "sources": {
      "docs/PRIVACY.md": "3c25bc2f7107bf7efa180a651f302da066997ca49575a36fa36ea8f276e932e3",
      "scenario/mcp/tools_scenario.py": "ac814890e57891397e7f124fb6e12568144ef858e05356028a73e03b03bde94e",
      "scenario/core/jobs/organization.py": "69ad48086ff2b763c565a22bce2bf60e142afbc10e757c56d938daf2198fbeba",
      "scenario/core/api/sdk_adapter.py": "784ac9f7f7c071291086eef894a4bcb3d895e53b8b26a233efea2d119f395765",
      "tests/blender/test_asset_organization.py": "b00e136dfcf7667b1d93bb54b3efc84c1643380e88e8524ea12238edb6e793d5",
      "scenario/blender/library_view.py": "9d64adaa197fc1d212c95b3b256d61ff67acdc9456ef1266c61c3168b2c50f17",
      "scenario/core/ui/library_organization.py": "e583e5b900b4532c25f6fc146c97d4ab3989243a0295ec915546e6b9dadd974f",
      "tests/blender/test_library_organization.py": "69b88b38a3b9d1f487150490e9c4d41ca9886d2b6d884ac1b98fa79cfadcdb03"
    }
  }
}
---

# Library and agent collection and tag changes

Evidence for [the canonical guide](../../PRIVACY.md#what-leaves-your-machine-and-when).
