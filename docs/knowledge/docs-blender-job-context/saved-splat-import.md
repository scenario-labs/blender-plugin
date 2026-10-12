---
{
  "type": "Evidence",
  "id": "docs-blender-job-context.saved-splat-import",
  "title": "Saved Gaussian splat import",
  "description": "Session ownership of worker splat preparation, its completion and the reviewed splat claim.",
  "evidence": {
    "path": "docs/BLENDER_JOB_CONTEXT.md",
    "scope": "saved-splat-import",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Inspected ModelApplicationApproval max_points and axes, revise_model_application, apply_saved_result queueing JobSession.prepare_model_import (a _record_command into JobWorkers' local-operation slot) or verify_results, drain binding a PreparedModelImport to its verified record's origin and scope, the coordinator registering the preparation's verification for one claim, apply_recovered_model checking the unit and exact options before claiming and building through splat_application.import_splat or continuing a mesh PLY through prepare_snapshot, _finish_model keeping receipt-only retry, and the session summary with splat counts, axes and the SPZ extension flag. The full installed suite passed 1,271 tests with 2 Windows-only skips on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1; Linux and Windows CI runs are not claimed.",
    "sources": {
      "scenario/blender/model_jobs.py": "6d091ac315d207654aa209d3b84b5ea51b85dbf8fbf1eba02423dccc64471a4d",
      "scenario/blender/job_session.py": "3ab7ea580ca986f9d86eb7a0735a96293627aa53016cc4172820fdc184e98163",
      "scenario/blender/splat_application.py": "0395a8ce98a15e45d2d7dc78ad4b3f4b0e1578b1b97010b00b70670cabf7454a",
      "scenario/blender/runtime.py": "a71f3d3d63d4bd67961387fa2209b38aa1bf774f380b107f5fd97bc6ffa0c28c",
      "scenario/core/jobs/results.py": "f29048daaca9cafd1a5ceaef4d8eebb70ac2328bae25ded45451be9672dddac7",
      "scenario/core/jobs/coordinator.py": "3807613afe3c4b8a3cb25e0e3862fbfabdd80ad649c7a96769c5a218dc60872a",
      "scenario/core/jobs/workers.py": "2d7b0820062d5a702d742f64fa25fd6c9ca472f0d1f258c7ea8fd17f81a2ba0a",
      "tests/blender/test_model_generation.py": "5e9481456f39de8b2fb18913ed38c73c72180424c953ab578f267c09e0377669"
    }
  }
}
---

# Saved Gaussian splat import

Evidence for [the canonical document](../../BLENDER_JOB_CONTEXT.md#explicit-saved-model-application).
