---
{
  "type": "Evidence",
  "id": "docs-job-coordinator.splat-preparation",
  "title": "Worker splat preparation commands",
  "evidence": {
    "path": "docs/JOB_COORDINATOR.md",
    "scope": "splat-preparation",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Inspected coordinator registration of the preparation's verification ticket, single-use claims, deactivation, cancellation and changed-record or changed-file rejection, and JobWorkers admission through the shared local-operation slot. Offline unit tests cover these commands with synthetic receipts and a service transport that fails on any request. JobSession, UI and MCP wiring, scene application and live acceptance are not established.",
    "sources": {
      "scenario/core/jobs/coordinator.py": "3807613afe3c4b8a3cb25e0e3862fbfabdd80ad649c7a96769c5a218dc60872a",
      "scenario/core/jobs/workers.py": "2d7b0820062d5a702d742f64fa25fd6c9ca472f0d1f258c7ea8fd17f81a2ba0a",
      "scenario/core/jobs/results.py": "348766da097df428012b4f119a170d2fa6cb628106f107c264c727965c8d6409",
      "scenario/core/scene/splats.py": "5cc9dc32ff65b595794cf609283828f17d683e40f23434f654b7a82fe48018a2",
      "tests/unit/test_model_import_preparation.py": "055c358f70e25fb550acbb59b93e557c4e1e55737aee6709d0ebe7db9214295e"
    }
  }
}
---

# Worker splat preparation commands

Evidence for [the canonical guide](../../JOB_COORDINATOR.md).
