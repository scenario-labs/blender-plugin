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
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the runtime-map claims: the pure bpy-free contract, including guarded writes that are never resent after an uncertain outcome (the one bounded resend after an already-member add refusal is described in the command contract), coordinator and worker execution through the selected adapter, the session-owned entry point, pump polling independent of an open view, connection-scoped session-local reviews kept across undo and scene switches and retired on file load or credential or project change, no job, upload or store schema change and no spending, that the local MCP tools prepare, apply and inspect these reviews, and that the native Library uses the same owner. The library-reads paragraph points to these reviews. No live collection, tag or bulk request was made from this repository; the observed already-member 400 and one-transaction add, service name uniqueness, DELETE body survival, tag normalization and live limits remain unverified here. No desktop interaction or release acceptance is claimed.",
    "sources": {
      "docs/architecture/runtime.md": "f324d1826fdd87ecf9a9be6dcc71d19d715fa016ecd7a626eadc3135c90bb5ad",
      "scenario/core/jobs/organization.py": "69ad48086ff2b763c565a22bce2bf60e142afbc10e757c56d938daf2198fbeba",
      "scenario/blender/asset_organization.py": "597a1026ad96d07f563f54ff2651591dc9c9fc4bf6a3f19bee5bf43509ada7ce",
      "scenario/blender/job_session.py": "e33a7ff821ae27d3c354a017c8b85315b0ac81ccc972d9e402892fbfdbfb4702",
      "scenario/blender/runtime.py": "9468693ddd2941575470018633b425885401ae68551c89fc88773ef0fce20933",
      "scenario/mcp/tools_scenario.py": "f4e87186806f93466220ef04f7c2530f0532ded790d4a8754a2a5b81183db08a",
      "tests/blender/test_organization_session.py": "a1b663c4e83c3028696c5ae64f06596aff85e78de5d7670d2e2a1323124de346",
      "tests/blender/test_asset_organization.py": "b00e136dfcf7667b1d93bb54b3efc84c1643380e88e8524ea12238edb6e793d5",
      "scenario/blender/library_view.py": "128d5f59000c37e6ddce965fbe2c1f61da7d6e55a45a33661ba8a13baf20cc14",
      "tests/blender/test_library_organization.py": "54dc4032b89c4849760280aced9e784855552fb8296f61e6c0a6128bdc4c1653"
    }
  }
}
---

# Shared asset organization reviews

Evidence for [the canonical guide](../../architecture/runtime.md#shared-asset-organization-reviews).
