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
    "reviewed_at": "2026-10-12",
    "base_revision": "4bd0061d73f6d049a86adac37119cc7a2c37741c",
    "limits": "Inspected ModelApplicationApproval max_points and axes, revise_model_application, apply_saved_result queueing JobSession.prepare_model_import (a _record_command into JobWorkers' local-operation slot) or verify_results, drain binding a PreparedModelImport to its verified record's origin and scope, the coordinator registering the preparation's verification for one claim, apply_recovered_model checking the unit and exact options before claiming and building through splat_application.import_splat or continuing a mesh PLY through prepare_snapshot, _finish_model keeping receipt-only retry, and the session summary with splat counts, axes and the SPZ extension flag. The full installed suite passed 1,271 tests with 2 Windows-only skips on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1; Linux and Windows CI runs are not claimed. On 2026-10-12 this branch was rebuilt on the saved package import branch after that branch was rebuilt on main 72c5340c, which now holds #356, without the unmerged remote progress branch. The replay conflicted only in imports, the view projection, the job_status description, the generated prepare_result_application row, a transfer guide paragraph and test fixtures. These statements were rechecked against the rebuilt sources, including main's later coordinator, worker and result changes (Film export runs outside the local-operation slot; the splat preparation still uses it and registers one verification for one claim), and are unchanged; the unit suite passed and the fingerprints were refreshed. The installed results named here are from the earlier head. On 2026-10-12 the branch was rebuilt again on the package import branch, itself rebuilt on main 4bd0061d, which now holds #369 (remote progress), #402 (saved model import undo), #377 and #379 (the saved image first-frame handoff and its native control), #401 (composer session end), #373 (asset organization reviews), #378 (MCP organization tools) and #380 (Library organization); the earlier notes' main without #369 no longer applies. The replay kept #369's remote projection, job_status paragraph and test helpers, and the handoff's runtime wrapper, apply_saved_result branch, MCP purpose and native first-frame descriptor and operator, beside this import, and import_splat now records #402's two desktop Undo checkpoints when the saved-result command asks for history. apply_recovered_model passes history to import_splat and import_snapshot inside _finish_model after the claim, and ModelJobs sets view.meta import_notices before #369's _project_remote. The statements here were rechecked and are unchanged. The unit suite and the full installed suite on macOS arm64 Blender 5.1.2 passed against the rebuilt code; the fingerprints were refreshed and the review date is unchanged. On 2026-10-12 the job_session.py, runtime.py, coordinator.py and workers.py fingerprints were refreshed after that rebuild: #373's organization review commands go through the shared request queue, not the local-operation slot, so the preparation and slot statements here are unchanged. On 2026-10-12 review fixes changed two behaviors: while the local-operation slot is busy, a PLY now queues ordinary verification and apply_recovered_model imports it only through the mesh snapshot path, whose _snapshot_ply asks for a new review when it finds splat data, while SPZ and .splat imports are still refused before anything is queued; and the native model import dialog now reports a ScenarioError reason after Model import was not started. The apply_saved_result sentence now names the SPZ and .splat refusal and the PLY verification that apply_recovered_model accepts only for the mesh snapshot path; model_application.py was added as a source for that refusal. The other statements were rechecked and are unchanged. The unit suite and the full installed suite on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 passed against the fixed code; Linux and Windows CI runs of the new tests are not claimed. Scoped 2026-10-12 check of the compact composer job strip, not a full re-review: model_jobs.py only gains the read-only busy and imports_automatically accessors that the strip reads; the import-unit projection, model application approvals and import commands are unchanged. The claims above still hold; the review date and base revision are unchanged.",
    "sources": {
      "scenario/blender/model_jobs.py": "2f1d9b1f4dfd70898c47590a8b55c76af8f60e2377692e36c85138a4a3187377",
      "scenario/blender/job_session.py": "d774d072c5b5f3b0c1739723fdcd4225a84ceda89b5832156e95951e15c919f2",
      "scenario/blender/splat_application.py": "0bbd5b488b2f3b3874db281fa1f7516d919d566bea2a22c77c1258054b10c729",
      "scenario/blender/runtime.py": "a62737e55602985dba9fde0199e6ffd65d73e174df0de664c49e0277661671e1",
      "scenario/core/jobs/results.py": "fbf05ea8baed20b055b946a1eef66337b698002c1b8066de1551b84adfb2f4b7",
      "scenario/core/jobs/coordinator.py": "54e97b2ff7a51e563dfff542ccf0f579ce2324393491840bf10efb78939307e9",
      "scenario/core/jobs/workers.py": "2127fde9e058254ccd165426cbfc8166da2813b3e598309c9000becf9565f6d6",
      "tests/blender/test_model_generation.py": "f884c59fcd384e04b7025218f542cb64726385d660acc2e1880b3f7af58e239e",
      "scenario/blender/model_application.py": "5e3f5039a516f67d552e030e86119e24887b14c85580dc302ebda9be07e0d849"
    }
  }
}
---

# Saved Gaussian splat import

Evidence for [the canonical document](../../BLENDER_JOB_CONTEXT.md#explicit-saved-model-application).
