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
    "limits": "Reviewed JobSession admission without a scene origin, kind- and scope-checked drain, single-use deliver_asset_organization and refusal by generic and library delivery, the AssetOrganization prepare, apply, status, review, discard, collection page and poll methods, the JSON projection without URLs, owner IDs or service text, including the number of writes apply sends when each succeeds, review phases, the 10-minute lifetime, 32-entry bound and one apply at a time, return to READY when apply cannot be queued, unknown outcomes reported as unconfirmed, runtime pump polling before the Library view, and retirement on file load and credential or project change. The closing sentences were re-reviewed against the local MCP tools, which accept a review only with the job_context_id issued alongside it, and the native Library, which uses the raw review accessor to update loaded rows from read-back records without another request. Installed-ZIP Blender 5.1.2 tests on macOS arm64 with synthetic worker-thread services cover these paths, including undo and scene switches keeping a review, a write in flight during file load, the MCP context binding and native row updates; those services refuse a re-add or more than 49 IDs as one 400 that writes nothing, as the service was observed to behave, and the latest installed run was on the stacked Library head that contains this branch. No live collection, tag or bulk request was made from this repository; the observed already-member 400 and one-transaction add, service name uniqueness, DELETE body survival, tag normalization and live limits remain unverified here. No desktop interaction or release acceptance is claimed. Blender 5.0 and 5.2 were not run for this topic.",
    "sources": {
      "docs/BLENDER_JOB_CONTEXT.md": "8b31a9258e55cf81338e62062018c0eb8befd209a67b39dd435bc0a2eb62cd8d",
      "scenario/blender/job_session.py": "e33a7ff821ae27d3c354a017c8b85315b0ac81ccc972d9e402892fbfdbfb4702",
      "scenario/blender/asset_organization.py": "597a1026ad96d07f563f54ff2651591dc9c9fc4bf6a3f19bee5bf43509ada7ce",
      "scenario/blender/runtime.py": "9468693ddd2941575470018633b425885401ae68551c89fc88773ef0fce20933",
      "scenario/core/jobs/organization.py": "69ad48086ff2b763c565a22bce2bf60e142afbc10e757c56d938daf2198fbeba",
      "scenario/mcp/tools_scenario.py": "f4e87186806f93466220ef04f7c2530f0532ded790d4a8754a2a5b81183db08a",
      "tests/blender/test_organization_session.py": "a1b663c4e83c3028696c5ae64f06596aff85e78de5d7670d2e2a1323124de346",
      "tests/blender/test_asset_organization.py": "b00e136dfcf7667b1d93bb54b3efc84c1643380e88e8524ea12238edb6e793d5",
      "tests/blender/run_all.py": "b3019328085a8334dd3347248a9b145d3a23533ffbafcfac9304962df189a6c8",
      "scenario/blender/library_view.py": "f2b832b67d2eb388901782f45621e49c009d3fa40e876c5b4ad4f35a98449555",
      "tests/blender/test_library_organization.py": "54d7098acbae666f86ff0d14eb6a568da0af6972a1eb733b0cc6678c30a1f6a4"
    }
  }
}
---

# Asset organization reviews

Evidence for [the canonical guide](../../BLENDER_JOB_CONTEXT.md#asset-organization-reviews).
