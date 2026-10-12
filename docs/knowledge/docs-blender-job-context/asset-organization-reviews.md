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
    "base_revision": "72c5340cea11e688f1b62a35cf9c1e5f903193d3",
    "limits": "Reviewed JobSession admission without a scene origin, kind- and scope-checked drain, single-use deliver_asset_organization and refusal by generic and library delivery, the AssetOrganization prepare, apply, status, discard, collection page and poll methods, a failed collection page read raising only text written for these surfaces (an unknown worker error becomes a fixed message, as poll reports it), the JSON projection without URLs, owner IDs or service text, including the number of writes apply sends when each succeeds, review phases, with a discarded FINISHED review keeping its result (unit-tested only), the 10-minute lifetime, 32-entry bound and one apply at a time, return to READY when apply cannot be queued, unknown outcomes reported as unconfirmed, runtime pump polling, and retirement on file load and credential or project change. Installed-ZIP Blender 5.1.2 tests on macOS arm64 with a synthetic worker-thread service cover these paths, including undo and scene switches keeping a review and a write in flight during file load; that service refuses a re-add or more than 49 IDs as one 400 that writes nothing, as the service was observed to behave. The latest installed run was on this branch on main 72c5340c, with JobSession completions and deactivation merged with the local Film export owner; the collection page error fix's new test failed without that fix in an earlier run. No live collection, tag or bulk request was made from this repository; the observed already-member 400 and one-transaction add, service name uniqueness, DELETE body survival, tag normalization and live limits remain unverified here. No native Library or local MCP control, desktop interaction or release acceptance is claimed. Blender 5.0 and 5.2 were not run for this topic.",
    "sources": {
      "docs/BLENDER_JOB_CONTEXT.md": "cc8f29182f5f602f3cc171f1f6628fc4dc76e9dfe647b23d803ac328393fa6fb",
      "scenario/blender/job_session.py": "f065103af678936bdd575474698ae7d36cea79f4269ae668fb5d7acd865ddddf",
      "scenario/blender/asset_organization.py": "3624f8cce6d0b4f57bccabd103b83495aa770e3aaf1a75523d8d6cd84e17c2ae",
      "scenario/blender/runtime.py": "41ab09a2a6dcad710c88302d2a73eaa289e6574133641bf575dccdbc601dd5cd",
      "scenario/core/jobs/organization.py": "69ad48086ff2b763c565a22bce2bf60e142afbc10e757c56d938daf2198fbeba",
      "tests/blender/test_organization_session.py": "c9cea281f8efd42103cab317dac5b579a48b122d2258c47c982b487dfc354e91",
      "tests/blender/run_all.py": "fbe2df99dbf8153be7afa9ca4b04c92c6290ebe09da00d1395fa33ed72dc2b24"
    }
  }
}
---

# Asset organization reviews

Evidence for [the canonical guide](../../BLENDER_JOB_CONTEXT.md#asset-organization-reviews).
