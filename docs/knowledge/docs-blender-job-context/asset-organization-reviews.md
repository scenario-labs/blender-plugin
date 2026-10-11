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
    "base_revision": "1d86f53d3489b23f2447be69cb589140e2f3ba64",
    "limits": "Reviewed JobSession admission without a scene origin, kind- and scope-checked drain, single-use deliver_asset_organization and refusal by generic and library delivery, the AssetOrganization prepare, apply, status, discard, collection page and poll methods, a failed collection page read raising only text written for these surfaces (an unknown worker error becomes a fixed message, as poll reports it), the JSON projection without URLs, owner IDs or service text, including the number of writes apply sends when each succeeds, review phases, with a discarded FINISHED review keeping its result (unit-tested only), the 10-minute lifetime, 32-entry bound and one apply at a time, return to READY when apply cannot be queued, unknown outcomes reported as unconfirmed, runtime pump polling, and retirement on file load and credential or project change. Installed-ZIP Blender 5.1.2 tests on macOS arm64 with a synthetic worker-thread service cover these paths, including undo and scene switches keeping a review and a write in flight during file load; that service refuses a re-add or more than 49 IDs as one 400 that writes nothing, as the service was observed to behave. The latest installed run was on this branch on main 1d86f53d, with JobSession and the runtime pump merged with the result preview owner, after the collection page error fix; its new test failed without that fix. No live collection, tag or bulk request was made from this repository; the observed already-member 400 and one-transaction add, service name uniqueness, DELETE body survival, tag normalization and live limits remain unverified here. No native Library or local MCP control, desktop interaction or release acceptance is claimed. Blender 5.0 and 5.2 were not run for this topic.",
    "sources": {
      "docs/BLENDER_JOB_CONTEXT.md": "73642d75fb22112498e75a37ddc51c40b9b734e592d32639946fc1c7a1881b47",
      "scenario/blender/job_session.py": "e2e6533c21e38805235a9929c8725445dfca9abbe14f085ddf73c1d3bfc9ef42",
      "scenario/blender/asset_organization.py": "3624f8cce6d0b4f57bccabd103b83495aa770e3aaf1a75523d8d6cd84e17c2ae",
      "scenario/blender/runtime.py": "33d32a4f1f672715f6caf752a44ab11f2bb44c3b5e15aa8ad50cba5c0242659e",
      "scenario/core/jobs/organization.py": "69ad48086ff2b763c565a22bce2bf60e142afbc10e757c56d938daf2198fbeba",
      "tests/blender/test_organization_session.py": "c9cea281f8efd42103cab317dac5b579a48b122d2258c47c982b487dfc354e91",
      "tests/blender/run_all.py": "70b7675e472f4cf02946f1f6e204ffa8b0f87f96b4e9ef4a389978af1645f851"
    }
  }
}
---

# Asset organization reviews

Evidence for [the canonical guide](../../BLENDER_JOB_CONTEXT.md#asset-organization-reviews).
