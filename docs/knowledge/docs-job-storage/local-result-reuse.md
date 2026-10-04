---
{
  "type": "Evidence",
  "id": "docs-job-storage.local-result-reuse",
  "title": "Durable local result reuse",
  "description": "Separate scoped local application claims without reopening completed generation.",
  "evidence": {
    "path": "docs/JOB_STORAGE.md",
    "scope": "local-result-reuse",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-04",
    "base_revision": "93c0f72f5f1303662a338cfd9dbd1f6faf68c14b",
    "limits": "Inspected schema 5 local application records and atomic upgrades from supported schemas 2/3/4, unchanged original job intent/state/results, revision-bound claims, scope separation, bounded history, corruption rejection, owner-issued verification, origin guards, recovery disposition and outcome-only receipt retries. Offline contracts cover competing connections, stale/fabricated context, before/after-commit failures, immutable outcomes, restart uncertainty and capacity. Installed native checks exercise storage persistence, schema 3/4 upgrades and local claims with Blender SQLite/Python. No UI/MCP reuse controls or Blender mutation are added; purpose-specific decoding, approval presentation, uncertain-scene resolution and full library reuse remain integration work. No new service operation, paid request, prototype migration or release acceptance. Other evidence topics retain their own scope.",
    "sources": {
      "scenario/core/jobs/store.py": "884a342106149d9e56f25d7bc2462a342b9f555dddf9f44084e408bed3734244",
      "scenario/core/jobs/coordinator.py": "3fa2983e2e5f078548e9710b57c9ca04d0810bdeebed9bcca55fd3da3c750c16",
      "tests/unit/test_job_store.py": "c5387f52b4b851f13ff46f02093d05f9653c76f5a0602b97a859f9d380cfbc8c",
      "tests/unit/test_application_claims.py": "760dcc5d01bb1bce31ba7c9482211e0f2afed8942a69707f6654f13ad88c813b",
      "tests/blender/test_job_store.py": "47745fbb29d03564091ca3674f3c01ccd8ddb1ee5ee3a9b5187c273bfc45b521"
    }
  }
}
---

# Durable local result reuse

Evidence for [the canonical document](../../JOB_STORAGE.md).
