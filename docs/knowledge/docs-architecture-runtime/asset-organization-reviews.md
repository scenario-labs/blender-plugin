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
    "base_revision": "1d86f53d3489b23f2447be69cb589140e2f3ba64",
    "limits": "Reviewed the runtime-map claims: the pure bpy-free contract, including guarded writes that are never resent after an uncertain outcome (the one bounded resend after an already-member add refusal is described in the command contract), coordinator and worker execution through the selected adapter, the session-owned entry point, pump polling independent of an open view, connection-scoped session-local reviews kept across undo and scene switches and retired on file load or credential or project change, no job, upload or store schema change and no spending, that the local MCP tools prepare, apply and inspect these reviews, and that the native Library uses the same owner. The library-reads paragraph points to these reviews. No live collection or tag write was made from this repository, and a desktop pass on an earlier candidate made reads only; the observed already-member 400 and one-transaction add, service name uniqueness, DELETE body survival, tag normalization and live limits remain unverified here. No desktop interaction or release acceptance is claimed. Rechecked after the Library view started drawing the review card under the organized asset's row, left the controls that start a read enabled while it runs, named a connection without collections in the Organize dialog and kept a settled card's outcome shown after another caller's prepare evicts its review: the view still prepares, applies and discards only through the shared owner, sends nothing new and draws read-only, so these claims are unchanged.",
    "sources": {
      "docs/architecture/runtime.md": "81db351224c74e912c8775b6306733689f626dab07448bef5ada4bed4d988037",
      "scenario/core/jobs/organization.py": "69ad48086ff2b763c565a22bce2bf60e142afbc10e757c56d938daf2198fbeba",
      "scenario/blender/asset_organization.py": "597a1026ad96d07f563f54ff2651591dc9c9fc4bf6a3f19bee5bf43509ada7ce",
      "scenario/blender/job_session.py": "e2e6533c21e38805235a9929c8725445dfca9abbe14f085ddf73c1d3bfc9ef42",
      "scenario/blender/runtime.py": "67fdc8cb36158ef2bcf51c3d43d3db76fb8981b63ac18c5f5915819762bce983",
      "scenario/mcp/tools_scenario.py": "ac814890e57891397e7f124fb6e12568144ef858e05356028a73e03b03bde94e",
      "tests/blender/test_organization_session.py": "a1b663c4e83c3028696c5ae64f06596aff85e78de5d7670d2e2a1323124de346",
      "tests/blender/test_asset_organization.py": "b00e136dfcf7667b1d93bb54b3efc84c1643380e88e8524ea12238edb6e793d5",
      "scenario/blender/library_view.py": "c6edd4e8d63907cb7cbb36fde39963b38844b40e9dbc5f21de99381cd0cfc5a3",
      "tests/blender/test_library_organization.py": "100262ba2e1c546fba06d25e06c6f6b778eb90cf0a01bf73447cb91f908834a6"
    }
  }
}
---

# Shared asset organization reviews

Evidence for [the canonical guide](../../architecture/runtime.md#shared-asset-organization-reviews).
