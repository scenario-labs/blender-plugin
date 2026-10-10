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
    "limits": "Reviewed the runtime-map claims: the pure bpy-free contract, including guarded writes that are never resent after an uncertain outcome (the one bounded resend after an already-member add refusal is described in the command contract), coordinator and worker execution through the selected adapter, the session-owned entry point, pump polling independent of an open view, connection-scoped session-local reviews kept across undo and scene switches and retired on file load or credential or project change, no job, upload or store schema change and no spending, and that the local MCP tools now prepare, apply and inspect these reviews. The library-reads paragraph points to these reviews. No live collection, tag or bulk request was made from this repository; the observed already-member 400 and one-transaction add, service name uniqueness, DELETE body survival, tag normalization and live limits remain unverified here. No native Library control, desktop interaction or release acceptance is claimed.",
    "sources": {
      "docs/architecture/runtime.md": "bb84f5b775b7cca53f94d27f4552f8a508f9db8e04c2850c52b605a8da34a5da",
      "scenario/core/jobs/organization.py": "69ad48086ff2b763c565a22bce2bf60e142afbc10e757c56d938daf2198fbeba",
      "scenario/blender/asset_organization.py": "553512e5363e7784a8b7f73b7578d4d670a877c65faf8f4c3d7c0d500fa40e51",
      "scenario/blender/job_session.py": "e33a7ff821ae27d3c354a017c8b85315b0ac81ccc972d9e402892fbfdbfb4702",
      "scenario/blender/runtime.py": "4dd15c99e830769b970cbffb8a2d895c657bc52be66b6e4c1e01a8ebebd5ed00",
      "scenario/mcp/tools_scenario.py": "ea3a218ec89fff1f01c6e52484e5552e4a3e09caee678ac7fc59d0013ea39d61",
      "tests/blender/test_organization_session.py": "a1b663c4e83c3028696c5ae64f06596aff85e78de5d7670d2e2a1323124de346",
      "tests/blender/test_asset_organization.py": "0d3264d136215d276cbadaaffc161d31d6ab60299dbae0085426fb20fd74154b"
    }
  }
}
---

# Shared asset organization reviews

Evidence for [the canonical guide](../../architecture/runtime.md#shared-asset-organization-reviews).
