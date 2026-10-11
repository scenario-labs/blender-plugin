---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.asset-organization-reviews",
  "title": "Shared asset organization reviews in the runtime map",
  "description": "Where organization reviews sit in the shared runtime and what they leave open.",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "scope": "asset-organization-reviews",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-11",
    "base_revision": "72723f02a97a7226b1c697c31d8124b77ac92c86",
    "limits": "Reviewed the runtime-map claims: the pure bpy-free contract, including guarded writes that are never resent after an uncertain outcome (the one bounded resend after an already-member add refusal is described in the command contract), coordinator and worker execution through the selected adapter, the session-owned entry point, pump polling independent of an open view, connection-scoped session-local reviews kept across undo and scene switches and retired on file load or credential or project change, and no job, upload or store schema change and no spending. The library-reads paragraph now points to these reviews. No live collection, tag or bulk request was made from this repository; the observed already-member 400 and one-transaction add, service name uniqueness, DELETE body survival, tag normalization and live limits remain unverified here. No native Library or local MCP control, desktop interaction or release acceptance is claimed.",
    "sources": {
      "docs/architecture/runtime.md": "bae83449ddcb66e830bbf90f6a8989515d91962333394bfdb5a276031918c0c8",
      "scenario/core/jobs/organization.py": "f6db3dcc4502aef9186fb456fa0983277f6a9b753e4556eded0e2df91a4547c7",
      "scenario/blender/asset_organization.py": "553512e5363e7784a8b7f73b7578d4d670a877c65faf8f4c3d7c0d500fa40e51",
      "scenario/blender/job_session.py": "716ded390ab45861111d5ed0146d7ca3f28175c2730f2d2b9e6c7a0480ae7572",
      "scenario/blender/runtime.py": "318b14ef4b0c0ebac6cddeb498a58c571379e0f4a6e297d7b0752867a19bd0f3",
      "tests/blender/test_organization_session.py": "a1b663c4e83c3028696c5ae64f06596aff85e78de5d7670d2e2a1323124de346"
    }
  }
}
---

# Shared asset organization reviews

Evidence for [the canonical guide](../../architecture/runtime.md#shared-asset-organization-reviews).
