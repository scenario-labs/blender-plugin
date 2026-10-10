---
{
  "type": "Evidence",
  "id": "docs-job-storage.schema-10-upgrade",
  "title": "Schema 10 upgrade from a real schema 9 store",
  "description": "One atomic, idempotent shared-store upgrade batching the persisted fields the accepted 0.10.0 designs need.",
  "evidence": {
    "path": "docs/JOB_STORAGE.md",
    "scope": "schema-10-upgrade",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "fb699b8555f7cee62147794516cc7aaa224864f7",
    "limits": "Reviewed the schema 2-9 to 10 upgrade in JobStore: every job row is decoded with absent source/projection defaults and rewritten, schema 9 Film upload rows are rechecked for scope key, task identity and the shared Film task namespace, and the empty trained_defaults table is created in the same immediate transaction. Unit tests upgrade a store rebuilt from the SQL dump of one written by the b57c398f schema 9 code (fifteen jobs, two scopes, every job state except the transient downloading and applying, every operation, receipts, roles, mesh/Film bindings, local claims, cloud record and Film upload) and compare every row, revision, key and association; they cover racing openers, idempotent reopen, damaged rows/associations, Film namespace conflicts and failed commits preserving every byte, and refusal of newer schemas. The native update check runs the actual schema 9 storage code from a predecessor ZIP built at fb699b85 (store code identical to b57c398f) inside Blender 5.1.2 with factory settings, against the store the candidate upgraded: it refused it as an unsupported format and every file in the store directory kept its bytes. The installed-ZIP test upgrades the same fixture with Blender 5.1.2's Python on macOS arm64; 5.0 and 5.2 runtimes and other platforms were not run for this change. Progress, composer lane binding, workflow decisions, previews, organization reviews and Film export state are intentionally not persisted. Three possible persisted fields (an intent-level panorama purpose, a first_frame application purpose, result parent and file names) remain open maintainer decisions, so the format is documented as not yet frozen. No live service call.",
    "sources": {
      "scenario/core/jobs/store.py": "5e94feb941bd943939901be0b8e0e447e424da24635cf28b5f44f7f159c60ec6",
      "tests/unit/test_job_store_schema10.py": "2987b1dcc859a30a2fe4ab1a922da74fa4ca1e6e56d0509f3639eee648d1bac7",
      "tests/unit/test_job_store.py": "7ca8d0999c4f124b66cb8f3581d800f5ccd21942161cc27cd14f15ef2bedcc2c",
      "tests/blender/test_job_store.py": "72d0faf5f71f7bc97de45dfad57d489814fdde9ccf9e4c5e7aaa90d8bd0d1a13",
      "tests/fixtures/synthetic/jobs-schema9.sql": "495aba1a859aa962030ba680389b583425621fb43a6dcc17816d7a2dd034f8fc",
      "tools/make_job_store_fixture.py": "67916df700850f90f68b932133eb353c20e1a485103214bd736d22f635abddda"
    }
  }
}
---

# Schema 10 upgrade from a real schema 9 store

Evidence for [the canonical document](../../JOB_STORAGE.md).
