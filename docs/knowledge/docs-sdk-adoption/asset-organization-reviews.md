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
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed only the service inventory row, the adapter coverage sentence and the closing paragraph of the asset organization section: the shared organization commands call the adapter methods through the coordinator, its workers and the JobSession review owner, with a guard before each write and a get_bulk read-back, and after AlreadyMembers send only the assets read back as not yet members, within three add requests per review; the local MCP organization tools and the native Library controls prepare, apply and inspect those reviews and make no direct SDK call. No SDK method, raw exception or dependency changed. No live collection, tag or bulk request was made from this repository; the observed already-member 400 and one-transaction add, service name uniqueness, DELETE body survival, tag normalization and live limits remain unverified here. No desktop interaction or release acceptance is claimed.",
    "sources": {
      "docs/SDK_ADOPTION.md": "9e4e15cf2f33c6d081175c75ca921e3be40e87e43e925d382f400244a949b4a4",
      "scenario/core/jobs/organization.py": "69ad48086ff2b763c565a22bce2bf60e142afbc10e757c56d938daf2198fbeba",
      "scenario/core/jobs/coordinator.py": "329f641b24e7cd23603d1eae840072006a080a03b2911dca44d17b8b9aa56e9a",
      "scenario/blender/asset_organization.py": "597a1026ad96d07f563f54ff2651591dc9c9fc4bf6a3f19bee5bf43509ada7ce",
      "scenario/mcp/tools_scenario.py": "f4e87186806f93466220ef04f7c2530f0532ded790d4a8754a2a5b81183db08a",
      "scenario/blender/library_view.py": "128d5f59000c37e6ddce965fbe2c1f61da7d6e55a45a33661ba8a13baf20cc14",
      "tests/blender/test_asset_organization.py": "b00e136dfcf7667b1d93bb54b3efc84c1643380e88e8524ea12238edb6e793d5",
      "scenario/core/ui/library_organization.py": "79ce2541b2ec332797e64c56a436e917f7431b9e96e45866d2b7abb413aabd20",
      "tests/blender/test_library_organization.py": "54dc4032b89c4849760280aced9e784855552fb8296f61e6c0a6128bdc4c1653"
    }
  }
}
---

# Runtime consumers of asset organization writes

Evidence for [the canonical guide](../../SDK_ADOPTION.md#asset-organization-writes).
