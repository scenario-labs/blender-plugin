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
    "limits": "Inspected JobSession export admission, drain flagging, delivery without scene resolution, cancellation, retirement and shutdown ordering. Installed tests cover owned-thread delivery, mid-render retirement and copy-only re-publish. Before the rebase onto 72723f02, a local macOS arm64 run of the full installed suite passed on Blender 5.1.2, including a real child export verified by Blender's decode check and by an installed ffprobe; earlier revisions of this module also passed locally on 5.0.1 and 5.2.1. Linux and Windows evidence is the PR CI installed baseline on Blender 5.0.1, 5.1.2 and 5.2.1, which runs this module. No human playback, desktop interaction or native/MCP control is established. export_film and publish_film_export validate destinations on the main thread against staging, extension and Blender user storage; export_film also refuses a reused snapshot or a child other than this Blender with the bundled worker, all before any thread, placeholder or media hash. Installed tests cover relative, private, existing and non-portable refusals, reuse and a foreign Blender or worker. deliver_local_export now refuses an inactive session, as the asset library, workflow catalog and cloud read deliveries do, even while a failed shutdown still holds issued outcomes; an installed test retires the session with an issued receipt, checks the refusal and that the published file is kept, and failed on the previous revision. Re-reviewed after the rebase onto 72723f02, whose merged changes to the session, coordinator, workers and native test registry add Film review controls, upload retirement on deactivation, a restart-upload command, inference-only cancellation and two native test modules; export admission, delivery, retirement, shutdown ordering and thread ownership are unchanged, and the native export module stays registered. Re-reviewed after the bounded export shutdown: LocalExportWorker uses a daemon thread and its shutdown waits at most EXPORT_STOP_TIMEOUT (5 s) in total, logging a warning when a read blocked on file access keeps the thread alive. JobSession.shutdown then keeps the session owned until _reap_inactive finds the task done and shuts it down again; an inactive session never delivers the late outcome. An installed test blocks the media hash, checks the bound, retained ownership, the reaper release and that nothing is published. The guide's shutdown wording was updated.",
    "sources": {
      "scenario/blender/job_session.py": "0ba497fdde65738c28b41c481aa8b95c93874a8a3d0d5a4a52fbdea3f69a9397",
      "scenario/core/jobs/coordinator.py": "bc513e99bc6fbf3d050edb2e340e8665570c69ab532d44eea939b158d742b2df",
      "scenario/core/jobs/workers.py": "b3486cf5c374172c56f438c9662ac77a67d7f796fc19274ea5b2a8fcba1fafdb",
      "tests/blender/test_film_export_primitive.py": "4f2603a3f7eeec9202263efa4ba7707ab9a0751cd4fa8c848ea954bbe828d33b",
      "tests/unit/test_local_export.py": "e9fc2544f802edf5d9ec472b5cf243a4dec9e3a5b52fe22256a1b90110d656d1"
    }
  }
}
---

Source evidence for [the canonical guide](../../BLENDER_JOB_CONTEXT.md).
