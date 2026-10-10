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
    "limits": "Inspected ModelJobs._plan (classification cached per saved revision, no file reads), actions offering import_model only for importable units and apply_mesh only for model/gltf-binary results, the view.meta import_units rows, prepare_model_application keyed by unit, prepare_asset_application routing for model-family files, the verify_model dispatch, the ModelPreflightError pause (Nothing was imported) that leaves the saved record unchanged, JobSession.apply_recovered_model, the session-local model_import summary retired on history change, status import_units and import_findings, and the unit-based import_model descriptors. Installed tests cover an OBJ package import and reuse claim with every member, a member changed after verification leaving the record unchanged, a changed GLB staying ready, the FBX frame-rate mismatch, splat and unsupported results never offered, and the native review and cancel. The full installed suite passed 1,253 tests with 2 Windows-only skips on macOS arm64 Blender 5.1.2 only (exact ZIP SHA-256 06f5e16d233224123993950150a7609945d4eaaeed5aa9581ff460ef7958aec3). No Blender 5.0 or 5.2 run, desktop interaction, live provider acceptance or splat import is claimed.",
    "sources": {
      "scenario/blender/model_jobs.py": "a40917107e28be6b41e7c813bbb0721dd9f4ca3df1365067201687ae1b172dc5",
      "scenario/blender/job_session.py": "07eb472d0ecdc831cb3491b6f7c521436736e138db86a5dd35ed404f83d000a3",
      "scenario/blender/model_application.py": "77c373fe556c7dd66dd47c70b8602254c56c66f9e678e4e489d61c6a6dabef17",
      "scenario/core/ui/saved_job_actions.py": "d88da9348592b0de6d7d800ad22c276075e7ef7ec24b4ead2775cb711d8fe41b",
      "scenario/blender/job_recovery.py": "dca1e9698f00e36f052144a88f6aa0a6443908b2e2597f5172964042f5471320",
      "scenario/mcp/tools_scenario.py": "ab08d69c3d107831c5d4e99a050594f10e431cc829c2f3077b22a08fa9668020",
      "tests/blender/test_model_generation.py": "2c5f2efe6eb50b2adada205aa04fd0ac8770f78ca1a9dab737192cad6c508ab3",
      "tests/unit/test_saved_job_actions.py": "cb947e78c0c296ad94315a4263155aa8bc52981715b0e78f500b8b4eb774d7a6",
      "tests/blender/test_result_actions.py": "f32d2f046510bd6ad0a5e1bbd5b82253e021e6dd2f84ce25be66e6b8f2615394"
    }
  }
}
---

# Saved model package approval and preflight

Evidence for [the canonical document](../../BLENDER_JOB_CONTEXT.md#explicit-saved-model-application).
