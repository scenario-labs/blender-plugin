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
    "reviewed_at": "2026-10-12",
    "base_revision": "3acb9625dc28bc74a6b764163ce6a6ca27144528",
    "limits": "Reviewed the Studio Library and agent organization sentences: Load collections reads collection names and counts only when chosen; confirming Organize reads the chosen asset's tags and memberships and the target collection or matching names; Apply, after a review, sends that asset ID with the entered tags or collection name; a connected agent can change collection membership and tags or create a collection, sending the chosen asset IDs, tags and collection names through the shared SDK adapter; and a separate review and apply precedes an immediate, credit-free account metadata change that Blender Undo does not reverse. A bounded resend after an already-member add refusal sends only a subset of the same reviewed asset IDs, so the sentences stay accurate. Installed synthetic tests confirm request bodies, that drawing and a cancelled dialog send nothing and that no request is sent while online access is off. This is not a legal-policy audit, and it does not establish that an agent obtained the user's permission. No live collection or tag write was made from this repository, and a desktop pass on an earlier candidate made reads only; the observed already-member 400 and one-transaction add, service name uniqueness, DELETE body survival, tag normalization and live limits remain unverified here. Rechecked against the current Library view, including the card under the organized row, read-enabled controls, a settled card kept after an eviction, read-back kept across a running page or collection read and Apply refused while an agent's change applies, and against the owner's collection page slot fix: the view still prepares, applies and discards only through the shared owner, sends nothing new and draws read-only, so these claims are unchanged.",
    "sources": {
      "docs/PRIVACY.md": "8329197fdcad03173a38370a647f375fb3584a4d324063b7a1d5ac09d7f7cd22",
      "scenario/mcp/tools_scenario.py": "c3597642a8199cde05d1346120532681f7138572e3edf523fa3788489b5f3b3c",
      "scenario/core/jobs/organization.py": "69ad48086ff2b763c565a22bce2bf60e142afbc10e757c56d938daf2198fbeba",
      "scenario/core/api/sdk_adapter.py": "0add4688710b00326fc31381d028e42cd9b5415f84bd168f45b5a8434a48aa19",
      "tests/blender/test_asset_organization.py": "b00e136dfcf7667b1d93bb54b3efc84c1643380e88e8524ea12238edb6e793d5",
      "scenario/blender/library_view.py": "8f69ff39c990e3cc6cffd2c5980397c8d1b68241bf6f31d58885d52ca6fc0254",
      "scenario/core/ui/library_organization.py": "922eba9285e9794e3269dd60e7f28f6b2fe4dca334703dc2d7e2f42b55829e3c",
      "tests/blender/test_library_organization.py": "4422a822b32be3bb3e48b34318ebe2f69db471f943a970f09af5c5af6d832b70"
    }
  }
}
---

# Library and agent collection and tag changes

Evidence for [the canonical guide](../../PRIVACY.md#what-leaves-your-machine-and-when).
