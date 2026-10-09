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
    "reviewed_at": "2026-10-09",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed JobSession admission without a scene origin, kind- and scope-checked drain, single-use deliver_asset_organization and refusal by generic and library delivery, the AssetOrganization prepare, apply, status, discard, collection page and poll methods, the JSON projection without URLs, owner IDs or service text, review phases, the 10-minute lifetime, 32-entry bound and one apply at a time, return to READY when apply cannot be queued, unknown outcomes reported as unconfirmed, runtime pump polling, and retirement on file load and credential or project change. Installed-ZIP Blender 5.1.2 tests on macOS arm64 with a synthetic worker-thread service cover these paths, including undo and scene switches keeping a review and a write in flight during file load. No live collection, tag or bulk request was made; service name uniqueness, re-adding a member, DELETE body survival, tag normalization and live limits remain unverified. No native Library or local MCP control, desktop interaction or release acceptance is claimed. Blender 5.0 and 5.2 were not run for this topic.",
    "sources": {
      "docs/BLENDER_JOB_CONTEXT.md": "98ae105f6731c9df6394869c7bb56b28f9a7cedff9471ca205eb1196d9f5dda9",
      "scenario/blender/job_session.py": "e33a7ff821ae27d3c354a017c8b85315b0ac81ccc972d9e402892fbfdbfb4702",
      "scenario/blender/asset_organization.py": "553512e5363e7784a8b7f73b7578d4d670a877c65faf8f4c3d7c0d500fa40e51",
      "scenario/blender/runtime.py": "4dd15c99e830769b970cbffb8a2d895c657bc52be66b6e4c1e01a8ebebd5ed00",
      "scenario/core/jobs/organization.py": "fca49ea65b119b66c9787ea9cfbc0c94e5bf3cb8dcc17743fa8800539cc8cce4",
      "tests/blender/test_organization_session.py": "925e173b839cdf9aafc784dc3f6abdb36de5d53dd912601055eb3f8cb18551ae",
      "tests/blender/run_all.py": "b12a3cef706fe3336bcf4c9329600c92a88a0156e812b34742c562938e9c164e"
    }
  }
}
---

# Asset organization reviews

Evidence for [the canonical guide](../../BLENDER_JOB_CONTEXT.md#asset-organization-reviews).
