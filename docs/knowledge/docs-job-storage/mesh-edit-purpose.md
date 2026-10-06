---
{
  "type": "Evidence",
  "id": "docs-job-storage.mesh-edit-purpose",
  "title": "Distinct durable mesh-edit purpose",
  "evidence": {
    "path": "docs/JOB_STORAGE.md",
    "scope": "mesh-edit-purpose",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-06",
    "base_revision": "82f0abb2e8fe4cdeab78558c17491e250459bc77",
    "limits": "Reviewed the new mesh_edit local-application purpose through the session claim, storage allowlist, persisted decoding and status projection. Native and unit regressions distinguish model imports from mesh replacements after reopening storage and retain the original generation record and existing purpose labels. No schema field or version change, historical reclassification, live provider or global undo claim. Other topics retain their own evidence and source-drift warnings.",
    "sources": {
      "scenario/core/jobs/store.py": "39148598ed88286b9933dcf4fe52e847d7ab073999a2c581c2f971e882a0911c",
      "scenario/blender/job_session.py": "9aed31fe6298e1c80c33899e19dc8cd2735539706843c9e4c0b334d054837fcb",
      "scenario/blender/model_jobs.py": "925f6000e83cb9aca1acf8f5c7822168e9c0f2b4eaf249803d851da7d3413fb5",
      "tests/unit/test_job_store.py": "5261ac660f822580f26c2ec6a29c31ee2dafad1e96d9032f60db2b0b3fe437dd",
      "tests/blender/test_model_generation.py": "6fd3cec01b58164c0b66957fad69b237fa579ec0614d687ab9e641b6f3c0fba4"
    }
  }
}
---

# Distinct durable mesh-edit purpose

Evidence for [the canonical guide](../../JOB_STORAGE.md).
