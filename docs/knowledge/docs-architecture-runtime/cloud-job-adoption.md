---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.cloud-job-adoption",
  "title": "Completed cloud job adoption commands",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "scope": "cloud-job-adoption",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-04",
    "base_revision": "4589f22964cc9cf99e53ec37bb8c5dbe6948c96b",
    "limits": "SDK 2.2.0 read-only completed-model-job verification, scoped atomic cloud records without local quote or mesh provenance, existing worker/session commands, restart and explicit download/application. Synthetic transport and installed functional evidence only. Schema 2 through 6 upgrades preserve previous generation records and unfinished claims. No native history/MCP adoption entry points, live provider acceptance, paid generation, desktop interaction proof or production release/update acceptance.",
    "sources": {
      "scenario/core/jobs/store.py": "a1b579f9c804f2ef5594115b5a48980d6ac4d2b664abfc498c086bbb771450d7",
      "scenario/core/jobs/coordinator.py": "70788f976e8fe429f594525e09e00f97833b9f09840fd69eb4446fa83e932eb2",
      "scenario/core/jobs/workers.py": "7835e8aa9227b9140f4a17d75bcf6da79aa6c96ca3b3e588f48c2e632afc51c5",
      "scenario/blender/job_session.py": "b26fa5e5e7669f30a1e2a16b2897c147f9e897177d54a1c3a0b74320df89ea87",
      "scenario/blender/model_jobs.py": "5e262c242e5c747e03211ad42988ef2c109a0adfe85790953bc38c2eb381125f",
      "scenario/mcp/tools_scenario.py": "2c570f7e2f7230af79f81ee1afac19606cc82eaf9cdef30de9733c655461ee9d",
      "scenario/core/api/sdk_adapter.py": "6cc3758eebf05f066a0aa11ed4d5c6ec96fb87b72f02f3d609cfdd97b88b044e",
      "tests/unit/test_cloud_job_recovery.py": "26c1f12da331d74bc509eb882fc0e93e593b3a1d3c13825b847bd6212a714fcb",
      "tests/unit/test_job_store.py": "b69c0387271696b66187f4085b9bd6c46dc091c1a2f5f40a4a687249032bdb67",
      "tests/blender/test_job_store.py": "144f1bbedbfa4ccd50f7ba495e61b59b9009019a182b2485c62082829604868f",
      "tests/blender/test_job_session.py": "dd61fe6459e577e2290246f08618004fdf9dc86911f7359882b174e6fea74ab5",
      "tests/blender/test_model_generation.py": "b5dbf438d59992334fd783a5fb3bb9770e3e3547889546bfb3452ab6e499fd55"
    }
  }
}
---

# Completed cloud job adoption commands

Evidence for [the canonical guide](../../architecture/runtime.md).
