---
{
  "type": "Evidence",
  "id": "docs-blender-job-context.film-video-export",
  "title": "Owned offline Film video export",
  "evidence": {
    "path": "docs/BLENDER_JOB_CONTEXT.md",
    "scope": "film-video-export",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Inspected JobSession export admission, drain flagging, delivery without scene resolution, cancellation, retirement and shutdown ordering. Installed tests cover owned-thread delivery, mid-render retirement and copy-only re-publish. At this revision a local macOS arm64 run of the full installed suite passes on Blender 5.1.2, including a real child export verified by Blender's decode check and by an installed ffprobe; earlier revisions of this module also passed locally on 5.0.1 and 5.2.1. Linux and Windows evidence is the PR CI installed baseline on Blender 5.0.1, 5.1.2 and 5.2.1, which runs this module. No human playback, desktop interaction or native/MCP control is established. export_film and publish_film_export validate destinations on the main thread against staging, extension and Blender user storage; export_film also refuses a reused snapshot or a child other than this Blender with the bundled worker, all before any thread, placeholder or media hash. Installed tests cover relative, private, existing and non-portable refusals, reuse and a foreign Blender or worker.",
    "sources": {
      "scenario/blender/job_session.py": "070652fa2d92e43b01989823ef4bd20bc43bc6559a131a43297afc9b3ce8a498",
      "scenario/core/jobs/coordinator.py": "58481d249c456139b8d228e7a91b3da4a6d0b03cfe0000e6ff53a5a27fc265f9",
      "scenario/core/jobs/workers.py": "fcfd589ac62e4a5c4eb97eda55c5a68ee0894cb16911c3b10ede65adf8820dc0",
      "tests/blender/test_film_export_primitive.py": "ab91fa90c80dea9dc1e06edfb53e7741b647c72f8a0297562b195302983e2fdc",
      "tests/unit/test_local_export.py": "884432f51c50a8c7956528fc90bfc5c55307a97661606fbc25e3b8188a27bbec"
    }
  }
}
---

Source evidence for [the canonical guide](../../BLENDER_JOB_CONTEXT.md).
