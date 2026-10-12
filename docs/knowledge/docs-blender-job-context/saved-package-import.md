---
{
  "type": "Evidence",
  "id": "docs-blender-job-context.saved-package-import",
  "title": "Saved model package approval and preflight",
  "description": "Unit-keyed model approval, projection and preflight before the claim in the shared session.",
  "evidence": {
    "path": "docs/BLENDER_JOB_CONTEXT.md",
    "scope": "saved-package-import",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Inspected ModelJobs._plan (classification cached per saved revision, no file reads), actions offering import_model only for importable units and apply_mesh only for model/gltf-binary results, the view.meta import_units rows, prepare_model_application keyed by unit, prepare_asset_application routing for model-family files, the verify_model dispatch, the ModelPreflightError pause (Nothing was imported) that leaves the saved record unchanged, JobSession.apply_recovered_model, the session-local model_import summary retired on history change, status import_units and import_findings, and the unit-based import_model descriptors. Installed tests cover an OBJ package import and reuse claim with every member, a member changed after verification leaving the record unchanged, a changed GLB staying ready, the FBX frame-rate mismatch, splat and unsupported results never offered, and the native review and cancel. The full installed suite passed 1,253 tests with 2 Windows-only skips on macOS arm64 Blender 5.1.2 only (exact ZIP SHA-256 06f5e16d233224123993950150a7609945d4eaaeed5aa9581ff460ef7958aec3). No Blender 5.0 or 5.2 run, desktop interaction, live provider acceptance or splat import is claimed. On 2026-10-10 fingerprints were refreshed after import_snapshot began reading bound OBJ normal, roughness and metallic maps as Non-Color by saved texture role and adding a Normal Map node only when one is missing; the statements here were rechecked and are unchanged, as is the review date. On 2026-10-12 this branch was rebuilt on main 72c5340c without the unmerged remote progress branch it had been stacked on. The replay conflicted only in imports, ModelJobs fields, the view projection, status and the job_status description, where main's cancellation, World candidate and workflow cost code was kept beside this import. These statements were rechecked against the rebuilt sources and are unchanged; the unit suite passed and the fingerprints were refreshed. The installed results named here are from the earlier head. On 2026-10-12 the branch was rebuilt again, on main 4bd0061d, which now holds #369 (remote progress), #402 (saved model import undo), #377 and #379 (the saved image first-frame handoff and its native control), #401 (composer session end), #373 (asset organization reviews), #378 (MCP organization tools) and #380 (Library organization); the earlier notes' main without #369 no longer applies. The replay kept #369's remote projection, status fields, job_status paragraph and test helpers, and the handoff's use_first_frame action, native first-frame descriptor and operator, first_frame status field and video_first_frame purpose, beside this import, and moved #402's two desktop Undo checkpoints from apply_model into import_snapshot, which every saved model format uses; apply_model, now called only by Film shots, records none. ModelJobs sets view.meta import_units before #369's _project_remote and status reports import_units, import_findings and model_import beside #369's lane and remote fields; JobSession.apply_recovered_model passes history to import_snapshot after the claim. These statements were rechecked and are unchanged. The unit suite and the full installed suite on macOS arm64 Blender 5.1.2 passed against the rebuilt code; the fingerprints were refreshed and the review date is unchanged.",
    "sources": {
      "scenario/blender/model_jobs.py": "f9bb80a01c12136fd1d463c3cf825c2b049c373aa4ed0f8e4a1022cee8f24838",
      "scenario/blender/job_session.py": "85701e0372d616d0141315e65c632dec057c35893870f1a70ab3e23cfacfbbf9",
      "scenario/blender/model_application.py": "d956046473b0cc174ea79daa95c07c22f730f192612c6d8cadc4e9229e50a816",
      "scenario/core/ui/saved_job_actions.py": "4315254386cf9c91788694ce8a3a4dd0435ab8325e6727727d21b1efe726120a",
      "scenario/blender/job_recovery.py": "ff6c45e43a0dc79666a98ee6c0bdf421cc0e6d4a173c2e5d81d3c448c2796346",
      "scenario/mcp/tools_scenario.py": "794987607f30634e0d0eda74940b8264641c80ac4a5a04b5d8a8880662033183",
      "tests/blender/test_model_generation.py": "65f32ea3bda91376a16f5e3331ae917aad6bfd77d0b38c901f223af949632aad",
      "tests/unit/test_saved_job_actions.py": "b32432e2c1acbb3ca99fb7fb21bf6ac37785d4ed284a236c611ebda273e424be",
      "tests/blender/test_result_actions.py": "db78c091c4cbf3f70e2a3efd216340f816c2219740b9f7186b31bbdd8f3cfe8b"
    }
  }
}
---

# Saved model package approval and preflight

Evidence for [the canonical document](../../BLENDER_JOB_CONTEXT.md#explicit-saved-model-application).
