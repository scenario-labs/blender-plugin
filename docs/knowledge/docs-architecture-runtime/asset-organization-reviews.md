---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.asset-organization-reviews",
  "title": "Shared asset organization reviews in the runtime map",
  "description": "Where organization reviews sit in the shared runtime, which surfaces use them and what they leave open.",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "scope": "asset-organization-reviews",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-11",
    "base_revision": "7fb15252f747f52db24f7e659f8d5048241f803e",
    "limits": "Reviewed the runtime-map claims: the pure bpy-free contract, including guarded writes that are never resent after an uncertain outcome (the one bounded resend after an already-member add refusal is described in the command contract), coordinator and worker execution through the selected adapter, the session-owned entry point, pump polling independent of an open view, connection-scoped session-local reviews kept across undo and scene switches and retired on file load or credential or project change, no job, upload or store schema change and no spending, that the local MCP tools prepare, apply and inspect these reviews, and that the native Library uses the same owner. The library-reads paragraph points to these reviews. No live collection, tag or bulk request was made from this repository; the observed already-member 400 and one-transaction add, service name uniqueness, DELETE body survival, tag normalization and live limits remain unverified here. No desktop interaction or release acceptance is claimed.",
    "sources": {
      "docs/architecture/runtime.md": "977a750d116c419356bbc5fad844e5cc2d51b65eec3054f390c6062ac35577c8",
      "scenario/core/jobs/organization.py": "69ad48086ff2b763c565a22bce2bf60e142afbc10e757c56d938daf2198fbeba",
      "scenario/blender/asset_organization.py": "597a1026ad96d07f563f54ff2651591dc9c9fc4bf6a3f19bee5bf43509ada7ce",
      "scenario/blender/job_session.py": "e2e6533c21e38805235a9929c8725445dfca9abbe14f085ddf73c1d3bfc9ef42",
      "scenario/blender/runtime.py": "67fdc8cb36158ef2bcf51c3d43d3db76fb8981b63ac18c5f5915819762bce983",
      "scenario/mcp/tools_scenario.py": "ac814890e57891397e7f124fb6e12568144ef858e05356028a73e03b03bde94e",
      "tests/blender/test_organization_session.py": "a1b663c4e83c3028696c5ae64f06596aff85e78de5d7670d2e2a1323124de346",
      "tests/blender/test_asset_organization.py": "b00e136dfcf7667b1d93bb54b3efc84c1643380e88e8524ea12238edb6e793d5",
      "scenario/blender/library_view.py": "f2b832b67d2eb388901782f45621e49c009d3fa40e876c5b4ad4f35a98449555",
      "tests/blender/test_library_organization.py": "54d7098acbae666f86ff0d14eb6a568da0af6972a1eb733b0cc6678c30a1f6a4"
    }
  }
}
---

# Shared asset organization reviews

Evidence for [the canonical guide](../../architecture/runtime.md#shared-asset-organization-reviews).
