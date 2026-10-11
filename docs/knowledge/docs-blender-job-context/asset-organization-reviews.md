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
    "limits": "Reviewed JobSession admission without a scene origin, kind- and scope-checked drain, single-use deliver_asset_organization and refusal by generic and library delivery, the AssetOrganization prepare, apply, status, review, discard, collection page and poll methods, the JSON projection without URLs, owner IDs or service text, including the number of writes apply sends when each succeeds, review phases, with a discarded FINISHED review keeping its result, the 10-minute lifetime, 32-entry bound and one apply at a time, return to READY when apply cannot be queued, unknown outcomes reported as unconfirmed, runtime pump polling before the Library view, and retirement on file load and credential or project change. The closing sentences were re-reviewed against the local MCP tools, which accept a review only with the job_context_id issued alongside it, and the native Library, which uses the raw review accessor to update loaded rows from read-back records without another request. Installed-ZIP Blender 5.1.2 tests on macOS arm64 with synthetic worker-thread services cover these paths, including undo and scene switches keeping a review, a write in flight during file load, the MCP context binding, an applied review discarded through the MCP status tool keeping its result and native row updates; those services refuse a re-add or more than 49 IDs as one 400 that writes nothing, as the service was observed to behave. The session and MCP tests, including the applied review discard, and native row updates last ran installed on the stacked Library head after its restack onto the MCP branch's apply return-shape description fix, which brought in only that description, its unit test and evidence records; no organization code or installed organization test changed in that restack. No live collection or tag write was made from this repository, and a desktop pass on an earlier candidate made reads only; the observed already-member 400 and one-transaction add, service name uniqueness, DELETE body survival, tag normalization and live limits remain unverified here. No desktop interaction or release acceptance is claimed. Blender 5.0 and 5.2 were not run for this topic. Rechecked after the Library view started drawing the review card under the organized asset's row, left the controls that start a read enabled while it runs, named a connection without collections in the Organize dialog and kept a settled card's outcome shown after another caller's prepare evicts its review: the view still prepares, applies and discards only through the shared owner, sends nothing new and draws read-only, so these claims are unchanged.",
    "sources": {
      "docs/BLENDER_JOB_CONTEXT.md": "e32fd8256fa59c047083eb618d6ab6961d7e5e0030bc320b32e973e7a55910be",
      "scenario/blender/job_session.py": "e2e6533c21e38805235a9929c8725445dfca9abbe14f085ddf73c1d3bfc9ef42",
      "scenario/blender/asset_organization.py": "597a1026ad96d07f563f54ff2651591dc9c9fc4bf6a3f19bee5bf43509ada7ce",
      "scenario/blender/runtime.py": "67fdc8cb36158ef2bcf51c3d43d3db76fb8981b63ac18c5f5915819762bce983",
      "scenario/core/jobs/organization.py": "69ad48086ff2b763c565a22bce2bf60e142afbc10e757c56d938daf2198fbeba",
      "scenario/mcp/tools_scenario.py": "ac814890e57891397e7f124fb6e12568144ef858e05356028a73e03b03bde94e",
      "tests/blender/test_organization_session.py": "a1b663c4e83c3028696c5ae64f06596aff85e78de5d7670d2e2a1323124de346",
      "tests/blender/test_asset_organization.py": "b00e136dfcf7667b1d93bb54b3efc84c1643380e88e8524ea12238edb6e793d5",
      "tests/blender/run_all.py": "a3c22695eb7385958cc220fe7393e27a1fad92d135dc71a5d4c4279712c53b16",
      "scenario/blender/library_view.py": "c6edd4e8d63907cb7cbb36fde39963b38844b40e9dbc5f21de99381cd0cfc5a3",
      "tests/blender/test_library_organization.py": "100262ba2e1c546fba06d25e06c6f6b778eb90cf0a01bf73447cb91f908834a6"
    }
  }
}
---

# Asset organization reviews

Evidence for [the canonical guide](../../BLENDER_JOB_CONTEXT.md#asset-organization-reviews).
