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
    "reviewed_at": "2026-10-11",
    "base_revision": "7fb15252f747f52db24f7e659f8d5048241f803e",
    "limits": "Reviewed only the service inventory row, the adapter coverage sentence and the closing paragraph of the asset organization section: the shared organization commands call the adapter methods through the coordinator, its workers and the JobSession review owner, with a guard before each write and a get_bulk read-back, and after AlreadyMembers send only the assets read back as not yet members, within three add requests per review; no local MCP tool or native Library control calls them. No SDK method, raw exception or dependency changed. No live collection, tag or bulk request was made from this repository; the observed already-member 400 and one-transaction add, service name uniqueness, DELETE body survival, tag normalization and live limits remain unverified here. No native Library or local MCP control, desktop interaction or release acceptance is claimed.",
    "sources": {
      "docs/SDK_ADOPTION.md": "e0adef0ee973be767007ac6b5f136d002f434159a3dbb84912773a55e23c0516",
      "scenario/core/jobs/organization.py": "69ad48086ff2b763c565a22bce2bf60e142afbc10e757c56d938daf2198fbeba",
      "scenario/core/jobs/coordinator.py": "bd23cca7936171f99803eb3e79d9979c0312e8e69ff1feeed4c497c3f1f00229",
      "scenario/blender/asset_organization.py": "553512e5363e7784a8b7f73b7578d4d670a877c65faf8f4c3d7c0d500fa40e51",
      "scenario/mcp/tools_scenario.py": "a711332963d3f99d20c60b1439976d054655846af89ac51604c2a7cc6379b7cb",
      "scenario/blender/library_view.py": "4ce0e8ca5a402136d7b5e2dbbe5b0f24f2b5480ed81afb3782c38252b3a65039"
    }
  }
}
---

# Runtime consumers of asset organization writes

Evidence for [the canonical guide](../../SDK_ADOPTION.md#asset-organization-writes).
