---
{
  "type": "Evidence",
  "id": "tests-fixtures-readme.schema-9-job-store",
  "title": "Schema 9 job store fixture",
  "description": "Provenance and reproduction of the predecessor-written job database.",
  "evidence": {
    "path": "tests/fixtures/README.md",
    "scope": "schema-9-job-store",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Generated the SQL dump from b57c398f's extracted scenario package with tools/make_job_store_fixture.py; a database rebuilt from it has the same dump, schema version and application ID as the database that code wrote. Content is synthetic first-party data with no credentials, prompts, signed URLs or result files. SQLite page layout is not reproduced and is not relied on.",
    "sources": {
      "tests/fixtures/synthetic/jobs-schema9.sql": "495aba1a859aa962030ba680389b583425621fb43a6dcc17816d7a2dd034f8fc",
      "tools/make_job_store_fixture.py": "006cb388ca3fb2d7b35b81ee8e53e110a63c4fa92653b6e586ea8cabeeb9a927",
      "tests/unit/test_job_store_schema10.py": "fccd676a1500ba6107929be1ae093e30bb891f4e66c10f8b6395589d355ff1b1",
      "tests/blender/test_job_store.py": "925e0e759f6f8a08f46466d300a7cf2d2a06ee8c7bbd800579dc18f86e4c326b"
    }
  }
}
---

# Schema 9 job store fixture

Evidence for [the canonical document](../../../tests/fixtures/README.md).
