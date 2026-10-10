---
{
  "type": "Evidence",
  "id": "docs-blender-job-context.saved-media-playback",
  "title": "Playback descriptors and player copy ownership",
  "evidence": {
    "path": "docs/BLENDER_JOB_CONTEXT.md",
    "scope": "saved-media-playback",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the playback descriptors' saved-state and media-type conditions, their operators' context, revision and receipt checks, JobSession.prepare_playback and cancel_playback on the preview lane, and the controller's ownership: latest-request opening, reuse, the copy and player budgets, envelope-only waveform requests, scheduler cancellation, late-result rejection and cleanup on retirement, file load and unregister. The animation player environment omits SCENARIO_, PYTHON and proxy variables. Installed-ZIP native tests ran on macOS arm64 Blender 5.1.2 with the system opener and the animation player process patched; no player was opened and no desktop interaction, screenshot or human listening is claimed.",
    "sources": {
      "scenario/blender/job_session.py": "fb42ae76844e48b22a7ef48d3cc408370392ce7be3d78cb4f3e587ea9d5c2c47",
      "scenario/blender/result_media.py": "3dedc599853505ebbb12be68bd2406e45cf5eaee16090de77237fd2b4dba1607",
      "scenario/core/ui/saved_job_actions.py": "075c3dbe813629c45bbb28c6c3a79a43d4f282454a68ee2e9e3fef8f62fbe2d6",
      "scenario/blender/job_recovery.py": "4b237b2c40e440f138a2fe5d21c6a6398221074c47edf88b9f7cd1389ba1b267",
      "scenario/core/jobs/preview_scheduler.py": "82e9f844d23182c83bb1ac50b4585c4def319160cbcb4c55cd81a77b51122499",
      "scenario/core/jobs/playback.py": "234d2e58b7d0ebfd595b5409bad223e6d524052f2809433bbd752c69300e54c6",
      "scenario/blender/runtime.py": "9663be27e3ae2ffff183b051cb92ec74d02ec7ceaeb531949b74e74a82d2a05a",
      "tests/blender/test_result_media.py": "250abc036f5b46890c384b17d25311ee8c59e57fb1cb84e45233e77cd49c8a2f"
    }
  }
}
---

# Playback descriptors and player copy ownership

Evidence for [the canonical guide](../../BLENDER_JOB_CONTEXT.md).
