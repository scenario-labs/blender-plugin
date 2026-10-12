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
    "reviewed_at": "2026-10-12",
    "base_revision": "72c5340cea11e688f1b62a35cf9c1e5f903193d3",
    "limits": "Reviewed the runtime-map claims: the pure bpy-free contract, including guarded writes that are never resent after an uncertain outcome (the one bounded resend after an already-member add refusal is described in the command contract), coordinator and worker execution through the selected adapter, the session-owned entry point, pump polling independent of an open view, connection-scoped session-local reviews kept across undo and scene switches and retired on file load or credential or project change, and no job, upload or store schema change and no spending. The library-reads paragraph now points to these reviews. No live collection, tag or bulk request was made from this repository; the observed already-member 400 and one-transaction add, service name uniqueness, DELETE body survival, tag normalization and live limits remain unverified here. No native Library or local MCP control, desktop interaction or release acceptance is claimed.",
    "sources": {
      "docs/architecture/runtime.md": "9fe9c6a4dd09dbdd7b48379307e1cbb5b3e07a9d12a621a629c3ed06ea584357",
      "scenario/core/jobs/organization.py": "69ad48086ff2b763c565a22bce2bf60e142afbc10e757c56d938daf2198fbeba",
      "scenario/blender/asset_organization.py": "3624f8cce6d0b4f57bccabd103b83495aa770e3aaf1a75523d8d6cd84e17c2ae",
      "scenario/blender/job_session.py": "f065103af678936bdd575474698ae7d36cea79f4269ae668fb5d7acd865ddddf",
      "scenario/blender/runtime.py": "41ab09a2a6dcad710c88302d2a73eaa289e6574133641bf575dccdbc601dd5cd",
      "tests/blender/test_organization_session.py": "c9cea281f8efd42103cab317dac5b579a48b122d2258c47c982b487dfc354e91"
    }
  }
}
---

# Shared asset organization reviews

Evidence for [the canonical guide](../../architecture/runtime.md#shared-asset-organization-reviews).
