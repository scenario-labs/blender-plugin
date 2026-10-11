---
{
  "type": "Evidence",
  "id": "docs-blender-job-context.film-video-export",
  "title": "Owned offline Film video export",
  "evidence": {
    "path": "docs/BLENDER_JOB_CONTEXT.md",
    "scope": "film-video-export",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-11",
    "base_revision": "72723f02a97a7226b1c697c31d8124b77ac92c86",
    "limits": "Inspected JobSession export admission, drain flagging, delivery without scene resolution, cancellation, retirement and shutdown ordering. Installed tests cover owned-thread delivery, mid-render retirement and copy-only re-publish. Before the rebase onto 72723f02, a local macOS arm64 run of the full installed suite passed on Blender 5.1.2, including a real child export verified by Blender's decode check and by an installed ffprobe; earlier revisions of this module also passed locally on 5.0.1 and 5.2.1. Linux and Windows evidence is the PR CI installed baseline on Blender 5.0.1, 5.1.2 and 5.2.1, which runs this module. No human playback, desktop interaction or native/MCP control is established. export_film and publish_film_export validate destinations on the main thread against staging, extension and Blender user storage; export_film also refuses a reused snapshot or a child other than this Blender with the bundled worker, all before any thread, placeholder or media hash. Installed tests cover relative, private, existing and non-portable refusals, reuse and a foreign Blender or worker. deliver_local_export now refuses an inactive session, as the asset library, workflow catalog and cloud read deliveries do, even while a failed shutdown still holds issued outcomes; an installed test retires the session with an issued receipt, checks the refusal and that the published file is kept, and failed on the previous revision. Re-reviewed after the rebase onto 72723f02, whose merged changes to the session, coordinator, workers and native test registry add Film review controls, upload retirement on deactivation, a restart-upload command, inference-only cancellation and two native test modules; export admission, delivery, retirement, shutdown ordering and thread ownership are unchanged, and the native export module stays registered.",
    "sources": {
      "scenario/blender/job_session.py": "c49b46b2d62815199cd4a1a1e0920900d577d38cdac9e6cbdf0150d4b1f690eb",
      "scenario/core/jobs/coordinator.py": "0fbcc48fcd785e870d468782352ebca63778e76e184d9e4e197cfdc6d9c1663e",
      "scenario/core/jobs/workers.py": "7089d332f856f0c69218df0af8e8f1842a631f0476899dd2bcbbef0c2e2c1910",
      "tests/blender/test_film_export_primitive.py": "7e0da5ad1922ebabdee66341a3de22fd564654324544a24019e5c9e83c3e0444",
      "tests/unit/test_local_export.py": "884432f51c50a8c7956528fc90bfc5c55307a97661606fbc25e3b8188a27bbec"
    }
  }
}
---

Source evidence for [the canonical guide](../../BLENDER_JOB_CONTEXT.md).
