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
    "reviewed_at": "2026-10-11",
    "base_revision": "7fb15252f747f52db24f7e659f8d5048241f803e",
    "limits": "Reviewed JobSession admission without a scene origin, kind- and scope-checked drain, single-use deliver_asset_organization and refusal by generic and library delivery, the AssetOrganization prepare, apply, status, discard, collection page and poll methods, the JSON projection without URLs, owner IDs or service text, including the number of writes apply sends when each succeeds, review phases, with a discarded FINISHED review keeping its result, the 10-minute lifetime, 32-entry bound and one apply at a time, return to READY when apply cannot be queued, unknown outcomes reported as unconfirmed, runtime pump polling, and retirement on file load and credential or project change. The closing sentence was re-reviewed against the local MCP tools, which use this owner and accept a review only with the job_context_id issued alongside it. Installed-ZIP Blender 5.1.2 tests on macOS arm64 with synthetic worker-thread services cover these paths, including undo and scene switches keeping a review, a write in flight during file load, the MCP context binding and an applied review discarded through the MCP status tool keeping its result; those services refuse a re-add or more than 49 IDs as one 400 that writes nothing, as the service was observed to behave. The session tests last ran installed on the parent branch after its rebase onto main; the MCP tests last ran installed on the stacked Library head before this branch was restacked onto that parent. Neither restack changed this branch's organization code or installed organization tests: the first changed its expected tool count and evidence records, the second brought in the parent's unit tests, the guide's discard sentence and evidence records. The parent also unit-tests the discard behavior. No live collection, tag or bulk request was made from this repository; the observed already-member 400 and one-transaction add, service name uniqueness, DELETE body survival, tag normalization and live limits remain unverified here. No native Library control, desktop interaction or release acceptance is claimed. Blender 5.0 and 5.2 were not run for this topic.",
    "sources": {
      "docs/BLENDER_JOB_CONTEXT.md": "19d80e1411eb418b300e245a8ef992a521906eaa8c7f5c50b733dda3c4cb07d6",
      "scenario/blender/job_session.py": "e2e6533c21e38805235a9929c8725445dfca9abbe14f085ddf73c1d3bfc9ef42",
      "scenario/blender/asset_organization.py": "553512e5363e7784a8b7f73b7578d4d670a877c65faf8f4c3d7c0d500fa40e51",
      "scenario/blender/runtime.py": "33d32a4f1f672715f6caf752a44ab11f2bb44c3b5e15aa8ad50cba5c0242659e",
      "scenario/core/jobs/organization.py": "69ad48086ff2b763c565a22bce2bf60e142afbc10e757c56d938daf2198fbeba",
      "scenario/mcp/tools_scenario.py": "9397f121a88365b8a4605447630701ae2a14a74dee747be274cc6a4e1bad0830",
      "tests/blender/test_organization_session.py": "a1b663c4e83c3028696c5ae64f06596aff85e78de5d7670d2e2a1323124de346",
      "tests/blender/test_asset_organization.py": "b00e136dfcf7667b1d93bb54b3efc84c1643380e88e8524ea12238edb6e793d5",
      "tests/blender/run_all.py": "70b7675e472f4cf02946f1f6e204ffa8b0f87f96b4e9ef4a389978af1645f851"
    }
  }
}
---

# Asset organization reviews

Evidence for [the canonical guide](../../BLENDER_JOB_CONTEXT.md#asset-organization-reviews).
