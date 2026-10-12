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
    "limits": "Reviewed JobSession admission without a scene origin, kind- and scope-checked drain, single-use deliver_asset_organization and refusal by generic and library delivery, the AssetOrganization prepare, apply, status, review, discard, collection page and poll methods, a failed collection page read raising only text written for these surfaces (an unknown worker error becomes a fixed message, as poll reports it), poll discarding a finished collection page nobody takes within the 10-minute review lifetime, which frees its admission slot, after which taking it asks for a new read, the JSON projection without URLs, owner IDs or service text, including the number of writes apply sends when each succeeds, review phases, with a discarded FINISHED review keeping its result, the 10-minute lifetime, 32-entry bound and one apply at a time, return to READY when apply cannot be queued, unknown outcomes reported as unconfirmed, runtime pump polling before the Library view, and retirement on file load and credential or project change. The closing sentences were re-reviewed against the local MCP tools, which accept a review only with the job_context_id issued alongside it, and the native Library, which uses the raw review accessor to update loaded rows from read-back records without another request and takes each collection page on the pump tick that finishes it. Installed-ZIP Blender 5.1.2 tests on macOS arm64 with synthetic worker-thread services cover these paths, including undo and scene switches keeping a review, a write in flight during file load, the MCP context binding, an applied review discarded through the MCP status tool keeping its result, an untaken collection page freeing its slot in a one-slot session, native row updates, including from a page read still running when the read-back arrives, and a Library Apply refused while an agent's change holds the single apply; those services refuse a re-add or more than 49 IDs as one 400 that writes nothing, as the service was observed to behave. The latest installed run was on this branch on main 1d86f53d, after its restack onto the parent's collection page slot fix, which conflicted only in evidence records, and with the Library fixes that keep read-back on rows and collections a running read replaces and name an agent's change holding the single apply; their three new installed tests failed before those fixes. That full run's one other failure was the saved remote job action expectation that main corrected after this stack's base, and the run passed with main's corrected test file in place. No live collection or tag write was made from this repository, and a desktop pass on an earlier candidate made reads only; the observed already-member 400 and one-transaction add, service name uniqueness, DELETE body survival, tag normalization and live limits remain unverified here. No desktop interaction or release acceptance is claimed. Blender 5.0 and 5.2 were not run for this topic.",
    "sources": {
      "docs/BLENDER_JOB_CONTEXT.md": "d1839748e88bbfc38bb72c59b5ea705499c3bba6b132c123da940138a889f055",
      "scenario/blender/job_session.py": "e2e6533c21e38805235a9929c8725445dfca9abbe14f085ddf73c1d3bfc9ef42",
      "scenario/blender/asset_organization.py": "2cddba739852c4f914398b8c9fd1d98029122fdb468aab61456268183f1fc75f",
      "scenario/blender/runtime.py": "67fdc8cb36158ef2bcf51c3d43d3db76fb8981b63ac18c5f5915819762bce983",
      "scenario/core/jobs/organization.py": "69ad48086ff2b763c565a22bce2bf60e142afbc10e757c56d938daf2198fbeba",
      "scenario/mcp/tools_scenario.py": "ac814890e57891397e7f124fb6e12568144ef858e05356028a73e03b03bde94e",
      "tests/blender/test_organization_session.py": "58804761b378747da91cb6e088b8e68ecdd4b6ce355b69f55892c5299383f450",
      "tests/blender/test_asset_organization.py": "b00e136dfcf7667b1d93bb54b3efc84c1643380e88e8524ea12238edb6e793d5",
      "tests/blender/run_all.py": "a3c22695eb7385958cc220fe7393e27a1fad92d135dc71a5d4c4279712c53b16",
      "scenario/blender/library_view.py": "8f69ff39c990e3cc6cffd2c5980397c8d1b68241bf6f31d58885d52ca6fc0254",
      "tests/blender/test_library_organization.py": "4422a822b32be3bb3e48b34318ebe2f69db471f943a970f09af5c5af6d832b70"
    }
  }
}
---

# Asset organization reviews

Evidence for [the canonical guide](../../BLENDER_JOB_CONTEXT.md#asset-organization-reviews).
