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
    "base_revision": "3acb9625dc28bc74a6b764163ce6a6ca27144528",
    "limits": "Reviewed JobSession admission without a scene origin, kind- and scope-checked drain, single-use deliver_asset_organization and refusal by generic and library delivery, the AssetOrganization prepare, apply, status, discard, collection page and poll methods, a failed collection page read raising only text written for these surfaces (an unknown worker error becomes a fixed message, as poll reports it), poll discarding a finished collection page nobody takes within the 10-minute review lifetime, which frees its admission slot, after which taking it asks for a new read, the JSON projection without URLs, owner IDs or service text, including the number of writes apply sends when each succeeds, review phases, with a discarded FINISHED review keeping its result, the 10-minute lifetime, 32-entry bound and one apply at a time, return to READY when apply cannot be queued, unknown outcomes reported as unconfirmed, runtime pump polling, and retirement on file load and credential or project change. The closing sentence was re-reviewed against the local MCP tools, which use this owner and accept a review only with the job_context_id issued alongside it. Installed-ZIP Blender 5.1.2 tests on macOS arm64 with synthetic worker-thread services cover these paths, including undo and scene switches keeping a review, a write in flight during file load, the MCP context binding, an applied review discarded through the MCP status tool keeping its result and an untaken collection page freeing its slot in a one-slot session; those services refuse a re-add or more than 49 IDs as one 400 that writes nothing, as the service was observed to behave. The latest installed run was on this branch on main 3acb9625, after its restack onto the parent's rebase over the local Film export owner, whose JobSession completions and deactivation now serve both owners; the restack conflicted only in evidence records, and the full run passed. In an earlier run, the slot test failed with SessionBusy without the collection page slot fix. The parent also unit-tests the discard behavior. No live collection, tag or bulk request was made from this repository; the observed already-member 400 and one-transaction add, service name uniqueness, DELETE body survival, tag normalization and live limits remain unverified here. No native Library control, desktop interaction or release acceptance is claimed. Blender 5.0 and 5.2 were not run for this topic.",
    "sources": {
      "docs/BLENDER_JOB_CONTEXT.md": "3c2b7bd21cb49815f0901526d105b76cd2c4d7d605f67448229c1ae802b81ecb",
      "scenario/blender/job_session.py": "f065103af678936bdd575474698ae7d36cea79f4269ae668fb5d7acd865ddddf",
      "scenario/blender/asset_organization.py": "b0e59563ab508d0382b8a4a846becdfbb7600664ae72bb8f452c2d2f58a2f647",
      "scenario/blender/runtime.py": "41ab09a2a6dcad710c88302d2a73eaa289e6574133641bf575dccdbc601dd5cd",
      "scenario/core/jobs/organization.py": "69ad48086ff2b763c565a22bce2bf60e142afbc10e757c56d938daf2198fbeba",
      "scenario/mcp/tools_scenario.py": "c3597642a8199cde05d1346120532681f7138572e3edf523fa3788489b5f3b3c",
      "tests/blender/test_organization_session.py": "58804761b378747da91cb6e088b8e68ecdd4b6ce355b69f55892c5299383f450",
      "tests/blender/test_asset_organization.py": "b00e136dfcf7667b1d93bb54b3efc84c1643380e88e8524ea12238edb6e793d5",
      "tests/blender/run_all.py": "4070edd1a886731a19b128e3e0f06e795cb921cff93a421486d6c369911ccf56"
    }
  }
}
---

# Asset organization reviews

Evidence for [the canonical guide](../../BLENDER_JOB_CONTEXT.md#asset-organization-reviews).
