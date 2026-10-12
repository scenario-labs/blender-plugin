---
{
  "type": "Evidence",
  "id": "docs-user-guide.saved-model-undo",
  "title": "Saved model import undo",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "saved-model-undo",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "5f6fb8a9473e321090cb4749ef1ac66d252c84aa",
    "limits": "Inspected desktop history checkpoints around the saved-result GLB new-group import, recorded only when JobSession requests them: one before staging and one after publication and staging scene removal, with eligibility shared with saved mesh edits (desktop window, Global Undo, more than one undo step). A failed initial checkpoint stops before staging and fails the claim for fresh review; a failed final checkpoint keeps the applied import and logs a sanitized warning; background application and Film shot-build hero imports record no checkpoints; Undo/Redo leaves the durable job record, spending counters and reuse approval unchanged. Undo History step names and the absence of automatic Undo after a failed import are by inspection. Exact ZIP passed 1400 installed native tests (2 skipped) on macOS arm64 Blender 5.1.2; background test eligibility is explicitly forced to exercise real undo/redo operators with a recorded neighbouring step and an unrecorded script edit. No desktop menu or keyboard undo acceptance of this change, Blender 5.0/5.2 run, live provider, paid, other OS desktop or release acceptance claim. Other evidence topics retain their original scope.",
    "sources": {
      "scenario/blender/model_application.py": "a9efac3d383c5442c0aa36f4c9d9382d03ec65b8fbe0435e1494d36cca889709",
      "scenario/blender/mesh_result_application.py": "f873d4900a1f8a8cc86c8d0a729f6ac2b1905cac943ef224cdd4e0e553b3cf3b",
      "scenario/blender/job_session.py": "19452a4b6b2301eed95660769876a8948b666a8b737303e36f5b5a24d815cf31",
      "scenario/blender/model_jobs.py": "90528ee66a4d0702b805a070e426df6492685249338d30194071752f70809bee",
      "scenario/blender/job_recovery.py": "da8df6bde6c9a0613565ea0563e7f1211086448d75e9419414f9c738038bda63",
      "scenario/blender/pump.py": "14ca29af007afa5dbf35c7f39a3caf39a709914a16f8cefa938dff58efcf7f2d",
      "scenario/blender/film_scene.py": "ae866981d0d94b9ecd825d4f042693b6a62c45633be0bc03f8c2e346d7e9f9c2",
      "tests/blender/test_model_generation.py": "c9c358fd6b4eb05140bca934fde0ed86d21fc9faacd5bd5b00c0c5461020f48d",
      "tests/blender/test_film_scene.py": "9e9f3cb29a9671a23fd9393d60e2694f5ccc6703e4bf766f8b60659e49f4f890",
      "scenario/core/ui/saved_job_actions.py": "c98f130355ee502b298532005d2f0c12ac8041a8690fe66d324aaf4deb772b04"
    }
  }
}
---

# Saved model import undo

Evidence for [the canonical guide](../../USER_GUIDE.md).
