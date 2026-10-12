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
    "reviewed_at": "2026-10-12",
    "base_revision": "1d86f53d3489b23f2447be69cb589140e2f3ba64",
    "limits": "Reviewed JobSession admission without a scene origin, kind- and scope-checked drain, single-use deliver_asset_organization and refusal by generic and library delivery, the AssetOrganization prepare, apply, status, discard, collection page and poll methods, a failed collection page read raising only text written for these surfaces (an unknown worker error becomes a fixed message, as poll reports it), poll discarding a finished collection page nobody takes within the 10-minute review lifetime, which frees its admission slot, after which taking it asks for a new read, the JSON projection without URLs, owner IDs or service text, including the number of writes apply sends when each succeeds, review phases, with a discarded FINISHED review keeping its result, the 10-minute lifetime, 32-entry bound and one apply at a time, return to READY when apply cannot be queued, unknown outcomes reported as unconfirmed, runtime pump polling, and retirement on file load and credential or project change. The closing sentence was re-reviewed against the local MCP tools, which use this owner and accept a review only with the job_context_id issued alongside it. Installed-ZIP Blender 5.1.2 tests on macOS arm64 with synthetic worker-thread services cover these paths, including undo and scene switches keeping a review, a write in flight during file load, the MCP context binding, an applied review discarded through the MCP status tool keeping its result and an untaken collection page freeing its slot in a one-slot session; those services refuse a re-add or more than 49 IDs as one 400 that writes nothing, as the service was observed to behave. The latest installed run was on this branch on main 1d86f53d, after its restack onto the parent's collection page error fix, which conflicted only in evidence records, and with the collection page slot fix; the slot test failed with SessionBusy without that fix. That full run's one other failure was the saved remote job action expectation that main corrected after this stack's base, and the run passed with main's corrected test file in place. The parent also unit-tests the discard behavior. No live collection, tag or bulk request was made from this repository; the observed already-member 400 and one-transaction add, service name uniqueness, DELETE body survival, tag normalization and live limits remain unverified here. No native Library control, desktop interaction or release acceptance is claimed. Blender 5.0 and 5.2 were not run for this topic.",
    "sources": {
      "docs/BLENDER_JOB_CONTEXT.md": "fbd6da057382e43734c46a86b36bdd24de84fb8bd5808440227d5ae51b80495a",
      "scenario/blender/job_session.py": "e2e6533c21e38805235a9929c8725445dfca9abbe14f085ddf73c1d3bfc9ef42",
      "scenario/blender/asset_organization.py": "b0e59563ab508d0382b8a4a846becdfbb7600664ae72bb8f452c2d2f58a2f647",
      "scenario/blender/runtime.py": "33d32a4f1f672715f6caf752a44ab11f2bb44c3b5e15aa8ad50cba5c0242659e",
      "scenario/core/jobs/organization.py": "69ad48086ff2b763c565a22bce2bf60e142afbc10e757c56d938daf2198fbeba",
      "scenario/mcp/tools_scenario.py": "ac814890e57891397e7f124fb6e12568144ef858e05356028a73e03b03bde94e",
      "tests/blender/test_organization_session.py": "58804761b378747da91cb6e088b8e68ecdd4b6ce355b69f55892c5299383f450",
      "tests/blender/test_asset_organization.py": "b00e136dfcf7667b1d93bb54b3efc84c1643380e88e8524ea12238edb6e793d5",
      "tests/blender/run_all.py": "c300758340e26c053fbf10306e763ac1abdee1f594e164196613a6dc71c72099"
    }
  }
}
---

# Asset organization reviews

Evidence for [the canonical guide](../../BLENDER_JOB_CONTEXT.md#asset-organization-reviews).
