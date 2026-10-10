---
{
  "type": "Evidence",
  "id": "docs-sdk-adoption.asset-organization-reviews",
  "title": "Runtime consumers of the asset organization adapter methods",
  "description": "Which shared commands call the organization adapter methods, and which surfaces do not yet.",
  "evidence": {
    "path": "docs/SDK_ADOPTION.md",
    "scope": "asset-organization-reviews",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed only the service inventory row, the adapter coverage sentence and the closing paragraph of the asset organization section: the shared organization commands call the adapter methods through the coordinator, its workers and the JobSession review owner, with a guard before each write and a get_bulk read-back, and after AlreadyMembers send only the assets read back as not yet members, within three add requests per review; no local MCP tool or native Library control calls them. No SDK method, raw exception or dependency changed. No live collection, tag or bulk request was made from this repository; the observed already-member 400 and one-transaction add, service name uniqueness, DELETE body survival, tag normalization and live limits remain unverified here. No native Library or local MCP control, desktop interaction or release acceptance is claimed.",
    "sources": {
      "docs/SDK_ADOPTION.md": "5b43d52c163b7ac22b52c3524894412956854bca537af84d77576bff4f244f62",
      "scenario/core/jobs/organization.py": "f208af0469bb4c93d655f908412889825329ac18ab78a87524fade111660db26",
      "scenario/core/jobs/coordinator.py": "329f641b24e7cd23603d1eae840072006a080a03b2911dca44d17b8b9aa56e9a",
      "scenario/blender/asset_organization.py": "553512e5363e7784a8b7f73b7578d4d670a877c65faf8f4c3d7c0d500fa40e51",
      "scenario/mcp/tools_scenario.py": "8613fe347b43421261f0462fe3972e777fffb6f35f17f9cd4a26d8b321d25331",
      "scenario/blender/library_view.py": "4ce0e8ca5a402136d7b5e2dbbe5b0f24f2b5480ed81afb3782c38252b3a65039"
    }
  }
}
---

# Runtime consumers of asset organization writes

Evidence for [the canonical guide](../../SDK_ADOPTION.md#asset-organization-writes).
