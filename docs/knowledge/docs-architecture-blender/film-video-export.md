---
{
  "type": "Evidence",
  "id": "docs-architecture-blender.film-video-export",
  "title": "Owned offline Film video export",
  "evidence": {
    "path": "docs/architecture/blender.md",
    "scope": "film-video-export",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-11",
    "base_revision": "72723f02a97a7226b1c697c31d8124b77ac92c86",
    "limits": "Checked that bpy access stays in the main-thread snapshot and the standalone child worker, that rendering, verification and publishing run in bpy-free core code on the owned export thread, and that the working file, scene and frame are unchanged. Before the rebase onto 72723f02, a local macOS arm64 run of the full installed suite passed on Blender 5.1.2, including a real child export verified by Blender's decode check and by an installed ffprobe; earlier revisions of this module also passed locally on 5.0.1 and 5.2.1. Linux and Windows evidence is the PR CI installed baseline on Blender 5.0.1, 5.1.2 and 5.2.1, which runs this module. No human playback, desktop interaction or native/MCP control is established. The session validates each destination on the main thread against the staging root, extension user storage, the installed extension and Blender's user resource and extensions folders; installed tests show relative, private, existing and non-portable destinations are refused before any thread, placeholder or media hash. Channel and enclosing meta strip mutes now set the audio default. The session also refuses a specification whose child is not the running Blender with the bundled worker, and the worker sets an explicit 8-bit depth. Re-reviewed after the inactive-session delivery guard; the main-thread and bpy-free boundaries are unchanged. Re-reviewed after the rebase onto 72723f02, whose merged changes to the session, coordinator, workers and native test registry add Film review controls, upload retirement on deactivation, a restart-upload command, inference-only cancellation and two native test modules; export admission, delivery, retirement, shutdown ordering and thread ownership are unchanged, and the native export module stays registered. The guide's export wording was reconciled with the merged Film review controls: review scenes now have native/MCP controls, while export still has none.",
    "sources": {
      "scenario/blender/film_export_worker.py": "2579da4238e9d16aaeae43e48787b8ecec5a8ea12590945e6b3933e4d17ed22a",
      "scenario/blender/job_session.py": "c49b46b2d62815199cd4a1a1e0920900d577d38cdac9e6cbdf0150d4b1f690eb",
      "scenario/blender/local_capture.py": "e0a07cda6bf8806368e7676d3fbbb3eaedc98cf62de8c76859e0e7091abcc50a",
      "scenario/core/jobs/coordinator.py": "0fbcc48fcd785e870d468782352ebca63778e76e184d9e4e197cfdc6d9c1663e",
      "scenario/core/jobs/local_export.py": "3fe9dec68501ab40b6e292d41d4b62f54fd7049d4d47fdcde95feeb744c0e4a7",
      "scenario/core/jobs/local_render.py": "8f21c27164761dd37053e5e6a06625ec6ac7b9efaf505b51527c10e4380df315",
      "scenario/core/jobs/mp4_inspection.py": "8a2be638990a79e15f5b112f32dcadde91aa2bbf6e2742c4451e9c7513103417",
      "scenario/core/jobs/workers.py": "7089d332f856f0c69218df0af8e8f1842a631f0476899dd2bcbbef0c2e2c1910",
      "tests/blender/run_all.py": "67266a44bde0b3eba16f3cb206aab7dde03cf323e97ba08531450893e68fa14d",
      "tests/blender/test_film_export_primitive.py": "7e0da5ad1922ebabdee66341a3de22fd564654324544a24019e5c9e83c3e0444",
      "tests/unit/test_local_export.py": "884432f51c50a8c7956528fc90bfc5c55307a97661606fbc25e3b8188a27bbec",
      "tests/unit/test_mp4_inspection.py": "9de87e15ae3891c43b5b56918ad9c99d5451cf5a2625c0f460a290404cb9b945"
    }
  }
}
---

Source evidence for [the canonical guide](../../architecture/blender.md).
