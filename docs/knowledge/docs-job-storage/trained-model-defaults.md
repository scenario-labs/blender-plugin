---
{
  "type": "Evidence",
  "id": "docs-job-storage.trained-model-defaults",
  "title": "Per-scope lane defaults for trained and private models",
  "description": "Revision-checked trained_defaults table keyed by the selected JobScope and lane.",
  "evidence": {
    "path": "docs/JOB_STORAGE.md",
    "scope": "trained-model-defaults",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Reviewed the trained_defaults table and JobStore get/list/set/clear API: scope key shared with jobs, repeated full scope in each row, strict decode, stack/composition/custom/direct route invariants, a 16-pick bound, finite optional strengths, monotonic revisions kept by clearing, and no raw model metadata. Unit tests cover isolation by credential pseudonym, project, team and service, races, stale revisions after clear, failed commits, corrupt rows and invalid values; the installed-ZIP test saves a default in an upgraded store. Storage only: no UI, MCP tool, route derivation, schema recheck or quote uses it yet, and nothing here establishes trained-model acceptance for #97.",
    "sources": {
      "scenario/core/jobs/store.py": "af6a1aca80668fb15001ca1ac75dabecef5d7118c045a2223caee9b404c844e1",
      "tests/unit/test_job_store_schema10.py": "fccd676a1500ba6107929be1ae093e30bb891f4e66c10f8b6395589d355ff1b1",
      "tests/blender/test_job_store.py": "925e0e759f6f8a08f46466d300a7cf2d2a06ee8c7bbd800579dc18f86e4c326b"
    }
  }
}
---

# Per-scope lane defaults for trained and private models

Evidence for [the canonical document](../../JOB_STORAGE.md).
