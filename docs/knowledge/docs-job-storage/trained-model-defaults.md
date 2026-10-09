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
    "limits": "Reviewed the trained_defaults table and JobStore get/list/set/clear API: scope key shared with jobs, repeated full scope in each row, strict decode, stack/composition/custom/direct route invariants, a 16-pick bound, finite optional strengths, monotonic revisions kept by clearing, and no raw model metadata. Lane names are bounded lowercase identifiers that may start with a digit, checked the same way on write and decode and never against the catalog. Unit tests round-trip set, get, list and clear for every catalog GENERATION_LANES and composer LANE_ORDER value, including 3d, keep a retired lane readable, and cover isolation by credential pseudonym, project, team and service, races, stale revisions after clear, failed commits, corrupt rows and invalid values. Installed-ZIP tests on Blender 5.1.2 (macOS arm64) repeat the round trip for the installed catalog, composer and props lanes and save a default in an upgraded store. Storage only: no UI, MCP tool, route derivation, schema recheck or quote uses it yet, and nothing here establishes trained-model acceptance for #97.",
    "sources": {
      "scenario/core/jobs/store.py": "5e94feb941bd943939901be0b8e0e447e424da24635cf28b5f44f7f159c60ec6",
      "scenario/core/api/catalog.py": "7a082b55f054ef3105e94f4a9e450ad321c5867a7b6cc178810160db51c64a8f",
      "scenario/core/ui/composer_layout.py": "ec5a7e92e881a9c356f1a20619170b1cf4f2a930db15dbe057e5bead2d11453a",
      "tests/unit/test_job_store_schema10.py": "2987b1dcc859a30a2fe4ab1a922da74fa4ca1e6e56d0509f3639eee648d1bac7",
      "tests/blender/test_job_store.py": "72d0faf5f71f7bc97de45dfad57d489814fdde9ccf9e4c5e7aaa90d8bd0d1a13"
    }
  }
}
---

# Per-scope lane defaults for trained and private models

Evidence for [the canonical document](../../JOB_STORAGE.md).
