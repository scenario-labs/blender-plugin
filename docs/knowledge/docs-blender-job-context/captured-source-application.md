---
{
  "type": "Evidence",
  "id": "docs-blender-job-context.captured-source-application",
  "title": "Captured mesh source application",
  "evidence": {
    "path": "docs/BLENDER_JOB_CONTEXT.md",
    "scope": "captured-source-application",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-04",
    "base_revision": "4589f22964cc9cf99e53ec37bb8c5dbe6948c96b",
    "limits": "Inspected export-time live static-mesh guards, exact persisted input binding, single-source UI/MCP approval, source revalidation and session retirement. Installed synthetic tests and isolated macOS arm64 Blender 5.1.2 desktop interaction cover original-source selection despite a different active object, cancellation, confirmation and preservation of the other mesh. The exact ZIP and interaction limits are recorded in UI_STYLE. Provenance alone cannot recreate authority after undo/load/restart. Provider alignment, rigs/retexture/segmentation, multi-source selection, global undo, persistent restoration, other OS desktop behavior and release acceptance remain incomplete. No new SDK operation or paid test; other topic records retain their own scope.",
    "sources": {
      "scenario/blender/mesh_provenance.py": "b0448c24c92ca272424f5a499fa39c26c206ecce7b7042f9f5c634afb5887d01",
      "scenario/blender/job_session.py": "67ea833c9edcf0982e4518c61c1095348259d94a22a92265e63716496f98e5a7",
      "scenario/blender/model_jobs.py": "9bd2ad2ff2e55b69aecc5e49e44ea66e71d153d4936cbe1eed0bfc7988a74a09",
      "scenario/blender/job_recovery.py": "229ad61cb156895722b83a0b3baa376a89a2d1b4c21e699cd716c59fe078f4f3",
      "scenario/blender/runtime.py": "fad8c3b706e8826740c57c357052099fcad3e6b147e0acc9ee95332ce6ea2fc5",
      "scenario/blender/mesh_application.py": "99e0af39cd720903982dee3480a20dd25164f318ca14d2550b4fc31ed8e6d935",
      "scenario/blender/mesh_result_application.py": "73ef54edb7fe04c6c3807db817b35f13655fdb2d57aaf83b622f6fd6a8aee70f",
      "scenario/mcp/tools_scenario.py": "48b084e7e0e730745c09c1070075e7b839a2fc8be94394d4b8a733036ee09e12",
      "tests/blender/test_model_generation.py": "8268f7b6a8ee13039d4c34062843df27f46e6cc2916abea8cca349dd81ad79b4",
      "tests/blender/test_reference_uploads.py": "8ca8c09de043a2011fd812cf9921c8b4580c4fc929ee3a70dffef3c6000f7285"
    }
  }
}
---

# Captured mesh source application

Evidence for [the canonical guide](../../BLENDER_JOB_CONTEXT.md).
