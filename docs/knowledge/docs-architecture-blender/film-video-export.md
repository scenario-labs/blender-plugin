---
{
  "type": "Evidence",
  "id": "docs-architecture-blender.film-video-export",
  "title": "Owned offline Film video export",
  "evidence": {
    "path": "docs/architecture/blender.md",
    "scope": "film-video-export",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "fb699b8555f7cee62147794516cc7aaa224864f7",
    "limits": "Checked that bpy access stays in the main-thread snapshot and the standalone child worker, that rendering, verification and publishing run in bpy-free core code on the owned export thread, and that the working file, scene and frame are unchanged. At this revision a local macOS arm64 run of the full installed suite passes on Blender 5.1.2, including a real child export verified by Blender's decode check and by an installed ffprobe; earlier revisions of this module also passed locally on 5.0.1 and 5.2.1. Linux and Windows evidence is the PR CI installed baseline on Blender 5.0.1, 5.1.2 and 5.2.1, which runs this module. No human playback, desktop interaction or native/MCP control is established. The session validates each destination on the main thread against the staging root, extension user storage, the installed extension and Blender's user resource and extensions folders; installed tests show relative, private, existing and non-portable destinations are refused before any thread, placeholder or media hash. Channel and enclosing meta strip mutes now set the audio default. The session also refuses a specification whose child is not the running Blender with the bundled worker, and the worker sets an explicit 8-bit depth. Re-reviewed after the inactive-session delivery guard; the main-thread and bpy-free boundaries are unchanged.",
    "sources": {
      "scenario/blender/film_export_worker.py": "2579da4238e9d16aaeae43e48787b8ecec5a8ea12590945e6b3933e4d17ed22a",
      "scenario/blender/job_session.py": "35f3181e2c6f9be8f0d4ca1c18b6cf46d2d0e04bc0d2c6790c8d86ea206c5942",
      "scenario/blender/local_capture.py": "e0a07cda6bf8806368e7676d3fbbb3eaedc98cf62de8c76859e0e7091abcc50a",
      "scenario/core/jobs/coordinator.py": "58481d249c456139b8d228e7a91b3da4a6d0b03cfe0000e6ff53a5a27fc265f9",
      "scenario/core/jobs/local_export.py": "3fe9dec68501ab40b6e292d41d4b62f54fd7049d4d47fdcde95feeb744c0e4a7",
      "scenario/core/jobs/local_render.py": "8f21c27164761dd37053e5e6a06625ec6ac7b9efaf505b51527c10e4380df315",
      "scenario/core/jobs/mp4_inspection.py": "8a2be638990a79e15f5b112f32dcadde91aa2bbf6e2742c4451e9c7513103417",
      "scenario/core/jobs/workers.py": "fcfd589ac62e4a5c4eb97eda55c5a68ee0894cb16911c3b10ede65adf8820dc0",
      "tests/blender/run_all.py": "76114be12bc10852c9ba6c434552618d44cc840fc5adf6e9bafa49226682ebd6",
      "tests/blender/test_film_export_primitive.py": "7e0da5ad1922ebabdee66341a3de22fd564654324544a24019e5c9e83c3e0444",
      "tests/unit/test_local_export.py": "884432f51c50a8c7956528fc90bfc5c55307a97661606fbc25e3b8188a27bbec",
      "tests/unit/test_mp4_inspection.py": "9de87e15ae3891c43b5b56918ad9c99d5451cf5a2625c0f460a290404cb9b945"
    }
  }
}
---

Source evidence for [the canonical guide](../../architecture/blender.md).
