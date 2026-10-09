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
    "limits": "Inspected JobSession export admission, drain flagging, delivery without scene resolution, cancellation, retirement and shutdown ordering. Installed tests cover owned-thread delivery, mid-render retirement and copy-only re-publish. Local macOS arm64 runs of the installed export module pass on Blender 5.0.1, 5.1.2 and 5.2.1, including a real child export verified by Blender's decode check and by an installed ffprobe; Linux/Windows evidence comes from CI. No human playback, desktop interaction or native/MCP control is established. export_film and publish_film_export validate destinations on the main thread against staging, extension and Blender user storage and refuse a reused snapshot before any thread, placeholder or media hash; installed tests cover relative, private, existing and non-portable refusals and reuse.",
    "sources": {
      "scenario/blender/job_session.py": "6eadb9ccb81a2a5c570980160ba9d20e5072136cccd5de71c6538920645bf11c",
      "scenario/core/jobs/coordinator.py": "58481d249c456139b8d228e7a91b3da4a6d0b03cfe0000e6ff53a5a27fc265f9",
      "scenario/core/jobs/workers.py": "fcfd589ac62e4a5c4eb97eda55c5a68ee0894cb16911c3b10ede65adf8820dc0",
      "tests/blender/test_film_export_primitive.py": "47918d02540835724ef6acb93611b9170df5a9c58ae53b04f22903f37f69fd27",
      "tests/unit/test_local_export.py": "3f0453957fa751f6ab9344eb0cc2e8ce05b47a7c979a681ec498a511c25aba3e"
    }
  }
}
---

Source evidence for [the canonical guide](../../BLENDER_JOB_CONTEXT.md).
