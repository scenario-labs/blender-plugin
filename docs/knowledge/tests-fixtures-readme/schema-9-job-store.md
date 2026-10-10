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
    "base_revision": "fb699b8555f7cee62147794516cc7aaa224864f7",
    "limits": "Generated the SQL dump from b57c398f's extracted scenario package with tools/make_job_store_fixture.py; a database rebuilt from it has the same dump, schema version and application ID as the database that code wrote. Following the documented commands into a new output path reproduced a byte-identical file (cmp), as did the same commands run on fb699b85's package; the tool refuses an existing output. Content is synthetic first-party data with no credentials, prompts, signed URLs or result files. SQLite page layout is not reproduced and is not relied on.",
    "sources": {
      "tests/fixtures/synthetic/jobs-schema9.sql": "495aba1a859aa962030ba680389b583425621fb43a6dcc17816d7a2dd034f8fc",
      "tools/make_job_store_fixture.py": "67916df700850f90f68b932133eb353c20e1a485103214bd736d22f635abddda",
      "tests/unit/test_job_store_schema10.py": "2987b1dcc859a30a2fe4ab1a922da74fa4ca1e6e56d0509f3639eee648d1bac7",
      "tests/blender/test_job_store.py": "72d0faf5f71f7bc97de45dfad57d489814fdde9ccf9e4c5e7aaa90d8bd0d1a13"
    }
  }
}
---

# Schema 9 job store fixture

Evidence for [the canonical document](../../../tests/fixtures/README.md).
