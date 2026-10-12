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
    "limits": "Inspected ModelJobs._plan (classification cached per saved revision, no file reads), actions offering import_model only for importable units and apply_mesh only for model/gltf-binary results, the view.meta import_units rows, prepare_model_application keyed by unit, prepare_asset_application routing for model-family files, the verify_model dispatch, the ModelPreflightError pause (Nothing was imported) that leaves the saved record unchanged, JobSession.apply_recovered_model, the session-local model_import summary retired on history change, status import_units and import_findings, and the unit-based import_model descriptors. Installed tests cover an OBJ package import and reuse claim with every member, a member changed after verification leaving the record unchanged, a changed GLB staying ready, the FBX frame-rate mismatch, splat and unsupported results never offered, and the native review and cancel. The full installed suite passed 1,253 tests with 2 Windows-only skips on macOS arm64 Blender 5.1.2 only (exact ZIP SHA-256 06f5e16d233224123993950150a7609945d4eaaeed5aa9581ff460ef7958aec3). No Blender 5.0 or 5.2 run, desktop interaction, live provider acceptance or splat import is claimed. On 2026-10-10 fingerprints were refreshed after saved splat import. Statements here about splat refusal, splats not being offered or splat import remaining open describe the package review only and are superseded: SPZ, .splat and PLY units are now prepared on a worker and offered, a PLY without splat data continues through this package snapshot, and the summary gains a splat field, as covered by the saved-splat-import topic of this document. The package snapshot, image guard, claim and rollback claims were rechecked and are unchanged; the review date is unchanged. On 2026-10-10 fingerprints were refreshed after import_snapshot began reading bound OBJ normal, roughness and metallic maps as Non-Color by saved texture role and adding a Normal Map node only when one is missing; the statements here were rechecked and are unchanged, as is the review date. On 2026-10-12 this branch was rebuilt on main 72c5340c without the unmerged remote progress branch it had been stacked on. The replay conflicted only in imports, ModelJobs fields, the view projection, status and the job_status description, where main's cancellation, World candidate and workflow cost code was kept beside this import. These statements were rechecked against the rebuilt sources and are unchanged; the unit suite passed and the fingerprints were refreshed. The installed results named here are from the earlier head. On 2026-10-12 the branch was rebuilt again, on main 4bd0061d, which now holds #369 (remote progress), #402 (saved model import undo), #377 and #379 (the saved image first-frame handoff and its native control), #401 (composer session end), #373 (asset organization reviews), #378 (MCP organization tools) and #380 (Library organization); the earlier notes' main without #369 no longer applies. The replay kept #369's remote projection, status fields, job_status paragraph and test helpers, and the handoff's use_first_frame action, native first-frame descriptor and operator, first_frame status field and video_first_frame purpose, beside this import, and moved #402's two desktop Undo checkpoints from apply_model into import_snapshot, which every saved model format uses; apply_model, now called only by Film shots, records none. ModelJobs sets view.meta import_units before #369's _project_remote and status reports import_units, import_findings and model_import beside #369's lane and remote fields; JobSession.apply_recovered_model passes history to import_snapshot after the claim. These statements were rechecked and are unchanged. The unit suite and the full installed suite on macOS arm64 Blender 5.1.2 passed against the rebuilt code; the fingerprints were refreshed and the review date is unchanged. On 2026-10-12 the fingerprints were refreshed again after the splat import branch was rebuilt on this rebuild. It adds splat options, worker preparation and the point builder beside this import; import_splat records the same Undo checkpoints as import_snapshot. The statements here were rechecked and are unchanged.",
    "sources": {
      "scenario/blender/model_jobs.py": "31ec59656bb44b4e87111e3ea535cd76e9e988b2123d56cdc4aa8968273f6aff",
      "scenario/blender/job_session.py": "48375992376c9d905ec7dbb2c7acb04444acfa6e09a5e6534eeb1c4f0ebeab88",
      "scenario/blender/model_application.py": "501ba21b816ecd4db78d9f3da35cfa5b507f2e6cff5409ad87b5d118ad325753",
      "scenario/core/ui/saved_job_actions.py": "d25a4144d0357e0025606e6d3befb7dde6558df45f7c85b8f1db9383d83ba086",
      "scenario/blender/job_recovery.py": "4b4768790db13f35adbe3d80ee3c52ee63fc34e84955f4a56d2448b65f545eeb",
      "scenario/mcp/tools_scenario.py": "ce080d1ee9f995ab01ecbb6bba9f802f772b8f2d6b3fd061695e6f985f1a58a5",
      "tests/blender/test_model_generation.py": "1627264d78606a37f6414d68ed57ddf8cc5761cfe0268c8e78ed935b0c2290a3",
      "tests/unit/test_saved_job_actions.py": "a93fffad40b95de2714cd98b4370edf41059a2e995c4e748d27cc9bf45807903",
      "tests/blender/test_result_actions.py": "db78c091c4cbf3f70e2a3efd216340f816c2219740b9f7186b31bbdd8f3cfe8b"
    }
  }
}
---

# Saved model package approval and preflight

Evidence for [the canonical document](../../BLENDER_JOB_CONTEXT.md#explicit-saved-model-application).
