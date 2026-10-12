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
    "limits": "Inspected ModelApplicationApproval max_points and axes, revise_model_application, apply_saved_result queueing JobSession.prepare_model_import (a _record_command into JobWorkers' local-operation slot) or verify_results, drain binding a PreparedModelImport to its verified record's origin and scope, the coordinator registering the preparation's verification for one claim, apply_recovered_model checking the unit and exact options before claiming and building through splat_application.import_splat or continuing a mesh PLY through prepare_snapshot, _finish_model keeping receipt-only retry, and the session summary with splat counts, axes and the SPZ extension flag. The full installed suite passed 1,271 tests with 2 Windows-only skips on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1; Linux and Windows CI runs are not claimed. On 2026-10-12 this branch was rebuilt on the saved package import branch after that branch was rebuilt on main 72c5340c, which now holds #356, without the unmerged remote progress branch. The replay conflicted only in imports, the view projection, the job_status description, the generated prepare_result_application row, a transfer guide paragraph and test fixtures. These statements were rechecked against the rebuilt sources, including main's later coordinator, worker and result changes (Film export runs outside the local-operation slot; the splat preparation still uses it and registers one verification for one claim), and are unchanged; the unit suite passed and the fingerprints were refreshed. The installed results named here are from the earlier head. On 2026-10-12 the branch was rebuilt again on the package import branch, itself rebuilt on main 4bd0061d, which now holds #369 (remote progress), #402 (saved model import undo), #377 and #379 (the saved image first-frame handoff and its native control), #401 (composer session end), #373 (asset organization reviews), #378 (MCP organization tools) and #380 (Library organization); the earlier notes' main without #369 no longer applies. The replay kept #369's remote projection, job_status paragraph and test helpers, and the handoff's runtime wrapper, apply_saved_result branch, MCP purpose and native first-frame descriptor and operator, beside this import, and import_splat now records #402's two desktop Undo checkpoints when the saved-result command asks for history. apply_recovered_model passes history to import_splat and import_snapshot inside _finish_model after the claim, and ModelJobs sets view.meta import_notices before #369's _project_remote. The statements here were rechecked and are unchanged. The unit suite and the full installed suite on macOS arm64 Blender 5.1.2 passed against the rebuilt code; the fingerprints were refreshed and the review date is unchanged. On 2026-10-12 the job_session.py, runtime.py, coordinator.py and workers.py fingerprints were refreshed after that rebuild: #373's organization review commands go through the shared request queue, not the local-operation slot, so the preparation and slot statements here are unchanged.",
    "sources": {
      "scenario/blender/model_jobs.py": "31ec59656bb44b4e87111e3ea535cd76e9e988b2123d56cdc4aa8968273f6aff",
      "scenario/blender/job_session.py": "48375992376c9d905ec7dbb2c7acb04444acfa6e09a5e6534eeb1c4f0ebeab88",
      "scenario/blender/splat_application.py": "0bbd5b488b2f3b3874db281fa1f7516d919d566bea2a22c77c1258054b10c729",
      "scenario/blender/runtime.py": "a62737e55602985dba9fde0199e6ffd65d73e174df0de664c49e0277661671e1",
      "scenario/core/jobs/results.py": "fbf05ea8baed20b055b946a1eef66337b698002c1b8066de1551b84adfb2f4b7",
      "scenario/core/jobs/coordinator.py": "54e97b2ff7a51e563dfff542ccf0f579ce2324393491840bf10efb78939307e9",
      "scenario/core/jobs/workers.py": "2127fde9e058254ccd165426cbfc8166da2813b3e598309c9000becf9565f6d6",
      "tests/blender/test_model_generation.py": "1627264d78606a37f6414d68ed57ddf8cc5761cfe0268c8e78ed935b0c2290a3"
    }
  }
}
---

# Saved Gaussian splat import

Evidence for [the canonical document](../../BLENDER_JOB_CONTEXT.md#explicit-saved-model-application).
