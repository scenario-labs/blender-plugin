---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.saved-package-import",
  "title": "Runtime saved model package import",
  "description": "Runtime map entries for classified saved model units and their claims.",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "scope": "saved-package-import",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the runtime map's saved model sentences and the application claims row against ModelJobs, JobSession.apply_recovered_model, model_application and the native and MCP controls: one classified unit per approval, the main-thread preflight before the claim, reuse claims listing every member and unchanged receipt retry. The full installed suite passed 1,253 tests with 2 Windows-only skips on macOS arm64 Blender 5.1.2 only (exact ZIP SHA-256 06f5e16d233224123993950150a7609945d4eaaeed5aa9581ff460ef7958aec3). Splat import and in-place rig transfer remain open. On 2026-10-10 fingerprints were refreshed after saved splat import. Statements here about splat refusal, splats not being offered or splat import remaining open describe the package review only and are superseded: SPZ, .splat and PLY units are now prepared on a worker and offered, a PLY without splat data continues through this package snapshot, and the summary gains a splat field, as covered by the saved-splat-import topic of this document. The package snapshot, image guard, claim and rollback claims were rechecked and are unchanged; the review date is unchanged. On 2026-10-10 fingerprints were refreshed after import_snapshot began reading bound OBJ normal, roughness and metallic maps as Non-Color by saved texture role and adding a Normal Map node only when one is missing; the statements here were rechecked and are unchanged, as is the review date. On 2026-10-12 this branch was rebuilt on main 72c5340c without the unmerged remote progress branch it had been stacked on. The replay conflicted only in imports, ModelJobs fields, the view projection, status and the job_status description, where main's cancellation, World candidate and workflow cost code was kept beside this import. These statements were rechecked against the rebuilt sources and are unchanged; the unit suite passed and the fingerprints were refreshed. The installed results named here are from the earlier head. On 2026-10-12 the branch was rebuilt again, on main 4bd0061d, which now holds #369 (remote progress), #402 (saved model import undo), #377 and #379 (the saved image first-frame handoff and its native control), #401 (composer session end), #373 (asset organization reviews), #378 (MCP organization tools) and #380 (Library organization); the earlier notes' main without #369 no longer applies. The replay kept #369's remote projection, status fields, job_status paragraph and test helpers, and the handoff's use_first_frame action, native first-frame descriptor and operator, first_frame status field and video_first_frame purpose, beside this import, and moved #402's two desktop Undo checkpoints from apply_model into import_snapshot, which every saved model format uses; apply_model, now called only by Film shots, records none. The runtime map's saved model sentences and the application claims row were rechecked against #369 and #402 and are unchanged: one classified unit per approval, the main-thread preflight before the claim, reuse claims listing every member and unchanged receipt retry; #402's checkpoints run after the claim. The unit suite and the full installed suite on macOS arm64 Blender 5.1.2 passed against the rebuilt code; the fingerprints were refreshed and the review date is unchanged.",
    "sources": {
      "scenario/blender/model_jobs.py": "f9bb80a01c12136fd1d463c3cf825c2b049c373aa4ed0f8e4a1022cee8f24838",
      "scenario/blender/job_session.py": "85701e0372d616d0141315e65c632dec057c35893870f1a70ab3e23cfacfbbf9",
      "scenario/blender/model_application.py": "ede45e886635fcb3768673ba83c0ee7e5b99d59ed2f8fc9a8d537028b9832dc9",
      "scenario/blender/job_recovery.py": "ff6c45e43a0dc79666a98ee6c0bdf421cc0e6d4a173c2e5d81d3c448c2796346",
      "scenario/mcp/tools_scenario.py": "794987607f30634e0d0eda74940b8264641c80ac4a5a04b5d8a8880662033183",
      "tests/blender/test_model_generation.py": "5e9481456f39de8b2fb18913ed38c73c72180424c953ab578f267c09e0377669"
    }
  }
}
---

# Runtime saved model package import

Evidence for [the canonical document](../../architecture/runtime.md#active-sdk-cost-previews-and-model-submission).
