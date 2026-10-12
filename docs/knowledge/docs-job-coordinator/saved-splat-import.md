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
    "limits": "Reviewed the sentence that JobSession.prepare_model_import queues the coordinator command for reviewed saved splat imports: it uses _record_command into JobWorkers' local-operation slot, and the registered verification is consumed by one claim. The full installed suite passed 1,271 tests with 2 Windows-only skips on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1; Linux and Windows CI runs are not claimed. On 2026-10-12 this branch was rebuilt on the saved package import branch after that branch was rebuilt on main 72c5340c, which now holds #356, without the unmerged remote progress branch. The replay conflicted only in imports, the view projection, the job_status description, the generated prepare_result_application row, a transfer guide paragraph and test fixtures. These statements were rechecked against the rebuilt sources, including main's later coordinator, worker and result changes (Film export runs outside the local-operation slot; the splat preparation still uses it and registers one verification for one claim), and are unchanged; the unit suite passed and the fingerprints were refreshed. The installed results named here are from the earlier head. On 2026-10-12 the branch was rebuilt again on the package import branch, itself rebuilt on main 4bd0061d, which now holds #369 (remote progress), #402 (saved model import undo), #377 and #379 (the saved image first-frame handoff and its native control), #401 (composer session end), #373 (asset organization reviews), #378 (MCP organization tools) and #380 (Library organization); the earlier notes' main without #369 no longer applies. The replay kept #369's remote projection, job_status paragraph and test helpers, and the handoff's runtime wrapper, apply_saved_result branch, MCP purpose and native first-frame descriptor and operator, beside this import, and import_splat now records #402's two desktop Undo checkpoints when the saved-result command asks for history. The coordinator command sentence was rechecked and is unchanged. The unit suite and the full installed suite on macOS arm64 Blender 5.1.2 passed against the rebuilt code; the fingerprints were refreshed and the review date is unchanged. On 2026-10-12 the job_session.py, coordinator.py and workers.py fingerprints were refreshed after that rebuild: #373's organization review commands go through the shared request queue, not the local-operation slot, so the preparation and slot statements here are unchanged. On 2026-10-12 review fixes made a PLY verify on the ordinary queue while the local-operation slot is busy, importing only as a mesh, and made the native model import dialog report a ScenarioError reason. This topic's statements were rechecked against that change and are unchanged; the changed fingerprints were refreshed and the review date is unchanged.",
    "sources": {
      "scenario/blender/job_session.py": "d774d072c5b5f3b0c1739723fdcd4225a84ceda89b5832156e95951e15c919f2",
      "scenario/core/jobs/workers.py": "2127fde9e058254ccd165426cbfc8166da2813b3e598309c9000becf9565f6d6",
      "scenario/core/jobs/coordinator.py": "54e97b2ff7a51e563dfff542ccf0f579ce2324393491840bf10efb78939307e9",
      "tests/blender/test_model_generation.py": "f884c59fcd384e04b7025218f542cb64726385d660acc2e1880b3f7af58e239e"
    }
  }
}
---

# Saved Gaussian splat import

Evidence for [the canonical document](../../JOB_COORDINATOR.md#worker-splat-preparation).
