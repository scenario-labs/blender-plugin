---
{
  "type": "Evidence",
  "id": "docs-blender-job-context.asset-organization-reviews",
  "title": "Session-owned asset organization reviews",
  "description": "Connection-scoped admission, single delivery and the AssetOrganization owner on JobSession.",
  "evidence": {
    "path": "docs/BLENDER_JOB_CONTEXT.md",
    "scope": "asset-organization-reviews",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed JobSession admission without a scene origin, kind- and scope-checked drain, single-use deliver_asset_organization and refusal by generic and library delivery, the AssetOrganization prepare, apply, status, discard, collection page and poll methods, the JSON projection without URLs, owner IDs or service text, including the number of writes apply sends when each succeeds, review phases, the 10-minute lifetime, 32-entry bound and one apply at a time, return to READY when apply cannot be queued, unknown outcomes reported as unconfirmed, runtime pump polling, and retirement on file load and credential or project change. The closing sentence was re-reviewed against the local MCP tools, which use this owner and accept a review only with the job_context_id issued alongside it. Installed-ZIP Blender 5.1.2 tests on macOS arm64 with synthetic worker-thread services cover these paths, including undo and scene switches keeping a review, a write in flight during file load and the MCP context binding; those services refuse a re-add or more than 49 IDs as one 400 that writes nothing, as the service was observed to behave, and the latest installed run was on the stacked Library head that contains this branch. No live collection, tag or bulk request was made from this repository; the observed already-member 400 and one-transaction add, service name uniqueness, DELETE body survival, tag normalization and live limits remain unverified here. No native Library control, desktop interaction or release acceptance is claimed. Blender 5.0 and 5.2 were not run for this topic.",
    "sources": {
      "docs/BLENDER_JOB_CONTEXT.md": "63adab1be853680a0142f37b7e8c398864121a8976b26ee4e560e54e2ca4043b",
      "scenario/blender/job_session.py": "e33a7ff821ae27d3c354a017c8b85315b0ac81ccc972d9e402892fbfdbfb4702",
      "scenario/blender/asset_organization.py": "553512e5363e7784a8b7f73b7578d4d670a877c65faf8f4c3d7c0d500fa40e51",
      "scenario/blender/runtime.py": "4dd15c99e830769b970cbffb8a2d895c657bc52be66b6e4c1e01a8ebebd5ed00",
      "scenario/core/jobs/organization.py": "69ad48086ff2b763c565a22bce2bf60e142afbc10e757c56d938daf2198fbeba",
      "scenario/mcp/tools_scenario.py": "ea3a218ec89fff1f01c6e52484e5552e4a3e09caee678ac7fc59d0013ea39d61",
      "tests/blender/test_organization_session.py": "a1b663c4e83c3028696c5ae64f06596aff85e78de5d7670d2e2a1323124de346",
      "tests/blender/test_asset_organization.py": "0d3264d136215d276cbadaaffc161d31d6ab60299dbae0085426fb20fd74154b",
      "tests/blender/run_all.py": "aaf1d5affa3c7e35555a318e610d6c8f13d97878a8eccf65f91a58a30c8a603e"
    }
  }
}
---

# Asset organization reviews

Evidence for [the canonical guide](../../BLENDER_JOB_CONTEXT.md#asset-organization-reviews).
