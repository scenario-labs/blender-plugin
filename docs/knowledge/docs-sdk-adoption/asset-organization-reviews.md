---
{
  "type": "Evidence",
  "id": "docs-sdk-adoption.asset-organization-reviews",
  "title": "Runtime consumers of the asset organization adapter methods",
  "description": "Which shared commands and surfaces call the organization adapter methods, and which do not yet.",
  "evidence": {
    "path": "docs/SDK_ADOPTION.md",
    "scope": "asset-organization-reviews",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-11",
    "base_revision": "7fb15252f747f52db24f7e659f8d5048241f803e",
    "limits": "Reviewed only the service inventory row, the adapter coverage sentence and the closing paragraph of the asset organization section: the shared organization commands call the adapter methods through the coordinator, its workers and the JobSession review owner, with a guard before each write and a get_bulk read-back, and after AlreadyMembers send only the assets read back as not yet members, within three add requests per review; the local MCP organization tools and the native Library controls prepare, apply and inspect those reviews and make no direct SDK call. No SDK method, raw exception or dependency changed. No live collection, tag or bulk request was made from this repository; the observed already-member 400 and one-transaction add, service name uniqueness, DELETE body survival, tag normalization and live limits remain unverified here. No desktop interaction or release acceptance is claimed.",
    "sources": {
      "docs/SDK_ADOPTION.md": "71ee6168dc61b35dd899591df77a77faf405d9abf9562366f0a8f2fc6b1d96fa",
      "scenario/core/jobs/organization.py": "69ad48086ff2b763c565a22bce2bf60e142afbc10e757c56d938daf2198fbeba",
      "scenario/core/jobs/coordinator.py": "bd23cca7936171f99803eb3e79d9979c0312e8e69ff1feeed4c497c3f1f00229",
      "scenario/blender/asset_organization.py": "597a1026ad96d07f563f54ff2651591dc9c9fc4bf6a3f19bee5bf43509ada7ce",
      "scenario/mcp/tools_scenario.py": "ac814890e57891397e7f124fb6e12568144ef858e05356028a73e03b03bde94e",
      "scenario/blender/library_view.py": "f2b832b67d2eb388901782f45621e49c009d3fa40e876c5b4ad4f35a98449555",
      "tests/blender/test_asset_organization.py": "b00e136dfcf7667b1d93bb54b3efc84c1643380e88e8524ea12238edb6e793d5",
      "scenario/core/ui/library_organization.py": "e583e5b900b4532c25f6fc146c97d4ab3989243a0295ec915546e6b9dadd974f",
      "tests/blender/test_library_organization.py": "54d7098acbae666f86ff0d14eb6a568da0af6972a1eb733b0cc6678c30a1f6a4"
    }
  }
}
---

# Runtime consumers of asset organization writes

Evidence for [the canonical guide](../../SDK_ADOPTION.md#asset-organization-writes).
