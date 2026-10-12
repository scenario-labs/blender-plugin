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
    "limits": "Inspected desktop history checkpoints around the saved-result GLB new-group import, recorded only when JobSession requests them: one before staging and one after publication and staging scene removal, with eligibility shared with saved mesh edits (desktop window, Global Undo, more than one undo step). A failed initial checkpoint stops before staging and fails the claim for fresh review; a failed final checkpoint keeps the applied import and logs a sanitized warning; background application and Film shot-build hero imports record no checkpoints; Undo/Redo leaves the durable job record, spending counters and reuse approval unchanged. Undo History step names and the absence of automatic Undo after a failed import are by inspection. Exact ZIP passed 1400 installed native tests (2 skipped) on macOS arm64 Blender 5.1.2; background test eligibility is explicitly forced to exercise real undo/redo operators with a recorded neighbouring step and an unrecorded script edit. No desktop menu or keyboard undo acceptance of this change, Blender 5.0/5.2 run, live provider, paid, other OS desktop or release acceptance claim. Other evidence topics retain their original scope. On 2026-10-12 the model_application.py, job_recovery.py and saved_job_actions.py fingerprints were refreshed after the saved model package import was rebuilt on this change. That import moves these checkpoints from apply_model into import_snapshot, which every saved GLB, glTF, FBX, OBJ and mesh PLY import uses, with the same eligibility, step names and failure rules. JobSession.apply_recovered_model requests them with history after the claim, and apply_model, which only Film shots call, records none. Statements here that name only the GLB import now hold for every saved model format; an installed test also undoes and redoes an OBJ package import. These claims were rechecked and the review date is unchanged. The guide's undo paragraph now names the button to import again by format, such as Import GLB model (N), instead of Import model (N). On 2026-10-12 the model_application.py, job_recovery.py and saved_job_actions.py fingerprints were refreshed again after saved splat import was stacked on the package import. A saved splat import records the same two checkpoints through import_splat, before the point build and after publication, with the same eligibility, step names and failure rules; installed tests undo and redo one and check that a failed first checkpoint builds nothing and returns the job to review. These claims were rechecked and hold for saved splats too; the review date is unchanged. The guide's undo paragraph covers splat imports without change. On 2026-10-12 review fixes made a PLY verify on the ordinary queue while the local-operation slot is busy, importing only as a mesh, and made the native model import dialog report a ScenarioError reason through the shared _refusal wording. This topic's statements were rechecked against that change and are unchanged; only the fingerprints of the sources that change touched were refreshed, other drift is left as it was, and the review date is unchanged.",
    "sources": {
      "scenario/blender/model_application.py": "5e3f5039a516f67d552e030e86119e24887b14c85580dc302ebda9be07e0d849",
      "scenario/blender/mesh_result_application.py": "f873d4900a1f8a8cc86c8d0a729f6ac2b1905cac943ef224cdd4e0e553b3cf3b",
      "scenario/blender/job_session.py": "19452a4b6b2301eed95660769876a8948b666a8b737303e36f5b5a24d815cf31",
      "scenario/blender/model_jobs.py": "90528ee66a4d0702b805a070e426df6492685249338d30194071752f70809bee",
      "scenario/blender/job_recovery.py": "a01e758c030606442395f7cda47695b2eff6cbe11d82eadbb259a2cdf6296fb3",
      "scenario/blender/pump.py": "14ca29af007afa5dbf35c7f39a3caf39a709914a16f8cefa938dff58efcf7f2d",
      "scenario/blender/film_scene.py": "ae866981d0d94b9ecd825d4f042693b6a62c45633be0bc03f8c2e346d7e9f9c2",
      "tests/blender/test_model_generation.py": "c9c358fd6b4eb05140bca934fde0ed86d21fc9faacd5bd5b00c0c5461020f48d",
      "tests/blender/test_film_scene.py": "9e9f3cb29a9671a23fd9393d60e2694f5ccc6703e4bf766f8b60659e49f4f890",
      "scenario/core/ui/saved_job_actions.py": "a9399b90b3228503301b106005a47fcaff03b2bd3bf2a9a69af1a6b9b8347f9f"
    }
  }
}
---

# Saved model import undo

Evidence for [the canonical guide](../../USER_GUIDE.md).
