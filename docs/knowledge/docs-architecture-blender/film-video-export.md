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
    "limits": "Checked that bpy access stays in the main-thread snapshot and the standalone child worker, that rendering, verification and publishing run in bpy-free core code on the owned export thread, and that the working file, scene and frame are unchanged. Before the rebase onto 72723f02, a local macOS arm64 run of the full installed suite passed on Blender 5.1.2, including a real child export verified by Blender's decode check and by an installed ffprobe; earlier revisions of this module also passed locally on 5.0.1 and 5.2.1. Linux and Windows evidence is the PR CI installed baseline on Blender 5.0.1, 5.1.2 and 5.2.1, which runs this module. No human playback, desktop interaction or native/MCP control is established. The session validates each destination on the main thread against the staging root, extension user storage, the installed extension and Blender's user resource and extensions folders; installed tests show relative, private, existing and non-portable destinations are refused before any thread, placeholder or media hash. Channel and enclosing meta strip mutes now set the audio default. The session also refuses a specification whose child is not the running Blender with the bundled worker, and the worker sets an explicit 8-bit depth. Re-reviewed after the inactive-session delivery guard; the main-thread and bpy-free boundaries are unchanged. Re-reviewed after the rebase onto 72723f02, whose merged changes to the session, coordinator, workers and native test registry add Film review controls, upload retirement on deactivation, a restart-upload command, inference-only cancellation and two native test modules; export admission, delivery, retirement, shutdown ordering and thread ownership are unchanged, and the native export module stays registered. The guide's export wording was reconciled with the merged Film review controls: review scenes now have native/MCP controls, while export still has none. Re-reviewed after the even default size and bounded export shutdown: the default output size now rounds Blender's truncated size down to even, so 1920x1080 at 33% exports 632x356 instead of failing the even-dimension check; LocalExportWorker uses a daemon thread and its shutdown waits at most EXPORT_STOP_TIMEOUT (5 s) in total, logging a warning when a read blocked on file access keeps the thread alive. The guide's snapshot, child and thread wording remains accurate.",
    "sources": {
      "scenario/blender/film_export_worker.py": "2579da4238e9d16aaeae43e48787b8ecec5a8ea12590945e6b3933e4d17ed22a",
      "scenario/blender/job_session.py": "0ba497fdde65738c28b41c481aa8b95c93874a8a3d0d5a4a52fbdea3f69a9397",
      "scenario/blender/local_capture.py": "d1d3a5bde72ca1f61bf879fbc971bbca59d344e31a6a5c96e42558148537a43d",
      "scenario/core/jobs/coordinator.py": "bc513e99bc6fbf3d050edb2e340e8665570c69ab532d44eea939b158d742b2df",
      "scenario/core/jobs/local_export.py": "222a920e32cef1bc861fb3c0d2e641c67e61f40cbe1b03af591c1bff8e0b60e4",
      "scenario/core/jobs/local_render.py": "8f21c27164761dd37053e5e6a06625ec6ac7b9efaf505b51527c10e4380df315",
      "scenario/core/jobs/mp4_inspection.py": "8a2be638990a79e15f5b112f32dcadde91aa2bbf6e2742c4451e9c7513103417",
      "scenario/core/jobs/workers.py": "b3486cf5c374172c56f438c9662ac77a67d7f796fc19274ea5b2a8fcba1fafdb",
      "tests/blender/run_all.py": "67266a44bde0b3eba16f3cb206aab7dde03cf323e97ba08531450893e68fa14d",
      "tests/blender/test_film_export_primitive.py": "4f2603a3f7eeec9202263efa4ba7707ab9a0751cd4fa8c848ea954bbe828d33b",
      "tests/unit/test_local_export.py": "e9fc2544f802edf5d9ec472b5cf243a4dec9e3a5b52fe22256a1b90110d656d1",
      "tests/unit/test_mp4_inspection.py": "9de87e15ae3891c43b5b56918ad9c99d5451cf5a2625c0f460a290404cb9b945"
    }
  }
}
---

Source evidence for [the canonical guide](../../architecture/blender.md).
