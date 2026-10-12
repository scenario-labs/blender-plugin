---
{
  "type": "Evidence",
  "id": "docs-user-guide.saved-splat-import",
  "title": "Saved Gaussian splat import",
  "description": "User steps for Import splats, point limits, saved axes and the post-import notices.",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "saved-splat-import",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "4bd0061d73f6d049a86adac37119cc7a2c37741c",
    "limits": "Reviewed the 3D guidance and the worlds sentence against the Import splats and Import PLY model labels, the Points and Saved axes dropdown items and defaults, the PLY mesh or splat routing, the unlit point-cloud material needing Material Preview or Rendered view, the Point scale and Max radius modifier inputs, the Shown as points and extension notices and the SPZ v4 refusal. The full installed suite passed 1,271 tests with 2 Windows-only skips on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1; Linux and Windows CI runs are not claimed. No desktop screenshot of the dialog, provider world or axis evidence is claimed. On 2026-10-12 this branch was rebuilt on the saved package import branch after that branch was rebuilt on main 72c5340c, which now holds #356, without the unmerged remote progress branch. The replay conflicted only in imports, the view projection, the job_status description, the generated prepare_result_application row, a transfer guide paragraph and test fixtures. These statements were rechecked against the rebuilt sources, including main's later coordinator, worker and result changes (Film export runs outside the local-operation slot; the splat preparation still uses it and registers one verification for one claim), and are unchanged; the unit suite passed and the fingerprints were refreshed. The installed results named here are from the earlier head. On 2026-10-12 the worlds sentence under Generate was corrected to name the buttons saved_job_actions draws, Import splats: SPZ (N), Import splats: .splat (N) and, for a PLY, Import PLY model (N), instead of a plain Import splats; the other statements and the review date are unchanged. On 2026-10-12 the branch was rebuilt again on the package import branch, itself rebuilt on main 4bd0061d, which now holds #369 (remote progress), #402 (saved model import undo), #377 and #379 (the saved image first-frame handoff and its native control), #401 (composer session end), #373 (asset organization reviews), #378 (MCP organization tools) and #380 (Library organization); the earlier notes' main without #369 no longer applies. The replay kept #369's remote projection, job_status paragraph and test helpers, and the handoff's runtime wrapper, apply_saved_result branch, MCP purpose and native first-frame descriptor and operator, beside this import, and import_splat now records #402's two desktop Undo checkpoints when the saved-result command asks for history. The 3D guidance was rechecked and is unchanged; the guide's Undo paragraph, covered by the saved-model-undo topic, now applies to splat imports too. The unit suite and the full installed suite on macOS arm64 Blender 5.1.2 passed against the rebuilt code; the fingerprints were refreshed and the review date is unchanged. On 2026-10-12 review fixes changed two behaviors: while the local-operation slot is busy, a PLY now queues ordinary verification and apply_recovered_model imports it only through the mesh snapshot path, whose _snapshot_ply asks for a new review when it finds splat data, while SPZ and .splat imports are still refused before anything is queued; and the native model import dialog now reports a ScenarioError reason after Model import was not started. The 3D guidance now says splats are read one file at a time in the slot that Render capture and Film composition and review preparation also use, that an SPZ or .splat import then says why it did not start, that a splat PLY says Nothing was imported, and that a mesh PLY still imports; job_session.py and model_application.py were added as sources. The unit suite and the full installed suite on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 passed against the fixed code; Linux and Windows CI runs of the new tests are not claimed. Scoped 2026-10-12 check of the compact composer job strip, not a full re-review: model_jobs.py only gains the read-only busy and imports_automatically accessors that the strip reads; the import-unit projection, model application approvals and import commands are unchanged. The claims above still hold; the review date and base revision are unchanged.",
    "sources": {
      "scenario/blender/job_recovery.py": "b6e28f0b4c8b1ff282ffc5e2d1a574bde07867a7e94176e667b05ad5232a342e",
      "scenario/core/ui/saved_job_actions.py": "d25a4144d0357e0025606e6d3befb7dde6558df45f7c85b8f1db9383d83ba086",
      "scenario/blender/splat_application.py": "0bbd5b488b2f3b3874db281fa1f7516d919d566bea2a22c77c1258054b10c729",
      "scenario/blender/model_jobs.py": "2f1d9b1f4dfd70898c47590a8b55c76af8f60e2377692e36c85138a4a3187377",
      "tests/blender/test_model_generation.py": "f884c59fcd384e04b7025218f542cb64726385d660acc2e1880b3f7af58e239e",
      "scenario/blender/job_session.py": "d774d072c5b5f3b0c1739723fdcd4225a84ceda89b5832156e95951e15c919f2",
      "scenario/blender/model_application.py": "5e3f5039a516f67d552e030e86119e24887b14c85580dc302ebda9be07e0d849"
    }
  }
}
---

# Saved Gaussian splat import

Evidence for [the canonical document](../../USER_GUIDE.md#3d).
