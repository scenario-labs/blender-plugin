---
{
  "type": "Evidence",
  "id": "docs-job-storage.schema-10-upgrade",
  "title": "Schema 10 upgrade from a real schema 9 store",
  "description": "One atomic, idempotent shared-store upgrade batching every 0.10.0 persisted field.",
  "evidence": {
    "path": "docs/JOB_STORAGE.md",
    "scope": "schema-10-upgrade",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Reviewed the schema 2-9 to 10 upgrade in JobStore: every job row is decoded with absent source/projection defaults and rewritten, schema 9 Film upload rows are rechecked for scope key, task identity and the shared Film task namespace, and the empty trained_defaults table is created in the same immediate transaction. Unit tests upgrade a store rebuilt from the SQL dump of one written by the b57c398f schema 9 code (fifteen jobs, two scopes, every state and operation, receipts, roles, mesh/Film bindings, local claims, cloud record and Film upload) and compare every row, revision, key and association; they cover racing openers, idempotent reopen, damaged rows/associations, Film namespace conflicts and failed commits preserving every byte, and refusal of newer schemas. The actual b57c398f reader was run against an upgraded copy and refused it as an unsupported format without changing it; that manual check is not a committed test. The installed-ZIP test upgrades the same fixture with Blender 5.1.2's Python on macOS arm64; 5.0 and 5.2 runtimes and other platforms were not run for this change. Progress, composer lane binding, workflow decisions, previews, organization reviews and Film export state are intentionally not persisted. No live service call.",
    "sources": {
      "scenario/core/jobs/store.py": "af6a1aca80668fb15001ca1ac75dabecef5d7118c045a2223caee9b404c844e1",
      "tests/unit/test_job_store_schema10.py": "fccd676a1500ba6107929be1ae093e30bb891f4e66c10f8b6395589d355ff1b1",
      "tests/unit/test_job_store.py": "7ca8d0999c4f124b66cb8f3581d800f5ccd21942161cc27cd14f15ef2bedcc2c",
      "tests/blender/test_job_store.py": "925e0e759f6f8a08f46466d300a7cf2d2a06ee8c7bbd800579dc18f86e4c326b",
      "tests/fixtures/synthetic/jobs-schema9.sql": "495aba1a859aa962030ba680389b583425621fb43a6dcc17816d7a2dd034f8fc",
      "tools/make_job_store_fixture.py": "006cb388ca3fb2d7b35b81ee8e53e110a63c4fa92653b6e586ea8cabeeb9a927"
    }
  }
}
---

# Schema 10 upgrade from a real schema 9 store

Evidence for [the canonical document](../../JOB_STORAGE.md).
