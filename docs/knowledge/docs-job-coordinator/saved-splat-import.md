---
{
  "type": "Evidence",
  "id": "docs-job-coordinator.saved-splat-import",
  "title": "Saved Gaussian splat import",
  "description": "JobSession wiring of the worker splat preparation command.",
  "evidence": {
    "path": "docs/JOB_COORDINATOR.md",
    "scope": "saved-splat-import",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the sentence that JobSession.prepare_model_import queues the coordinator command for reviewed saved splat imports: it uses _record_command into JobWorkers' local-operation slot, and the registered verification is consumed by one claim. The full installed suite passed 1,271 tests with 2 Windows-only skips on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1; Linux and Windows CI runs are not claimed.",
    "sources": {
      "scenario/blender/job_session.py": "3ab7ea580ca986f9d86eb7a0735a96293627aa53016cc4172820fdc184e98163",
      "scenario/core/jobs/workers.py": "2d7b0820062d5a702d742f64fa25fd6c9ca472f0d1f258c7ea8fd17f81a2ba0a",
      "scenario/core/jobs/coordinator.py": "3807613afe3c4b8a3cb25e0e3862fbfabdd80ad649c7a96769c5a218dc60872a",
      "tests/blender/test_model_generation.py": "5e9481456f39de8b2fb18913ed38c73c72180424c953ab578f267c09e0377669"
    }
  }
}
---

# Saved Gaussian splat import

Evidence for [the canonical document](../../JOB_COORDINATOR.md#worker-splat-preparation).
