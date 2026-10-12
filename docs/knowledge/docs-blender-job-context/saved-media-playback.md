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
    "limits": "Reviewed the playback descriptors' saved-state and media-type conditions, their operators' context, revision and receipt checks, JobSession.prepare_playback and cancel_playback on the preview lane, and the controller's ownership: latest-request opening, reuse, the copy and player budgets, envelope-only waveform requests, scheduler cancellation, late-result rejection and cleanup on retirement, file load and unregister, including a persistent update timer that survives a file load and a retirement that first reaps exited animation players. The animation player environment omits SCENARIO_, PYTHON and proxy variables. Installed-ZIP native tests ran on macOS arm64 Blender 5.1.2 with the system opener and the animation player process patched; no player was opened and no desktop interaction, screenshot or human listening is claimed. On 2026-10-12 result_media.py and its native tests changed only the waveform box's draw-time status wrapping (measured with Blender's interface font against the drawn region, or inside Studio the width it requests for its popup) and the no-break spaces of the waveform summary; that diff was re-checked against this topic's claims, which do not describe either, so they stand as reviewed on 2026-10-10. This topic's evidence statements describe its own review; the partial physical desktop passes that UI_STYLE and KNOWN_LIMITATIONS record were not part of it.",
    "sources": {
      "scenario/blender/job_session.py": "fb42ae76844e48b22a7ef48d3cc408370392ce7be3d78cb4f3e587ea9d5c2c47",
      "scenario/blender/result_media.py": "4a5479d5592c54810687c12ace5190896747a7bb55443dfa0b5c485c204e5a88",
      "scenario/core/ui/saved_job_actions.py": "075c3dbe813629c45bbb28c6c3a79a43d4f282454a68ee2e9e3fef8f62fbe2d6",
      "scenario/blender/job_recovery.py": "4b237b2c40e440f138a2fe5d21c6a6398221074c47edf88b9f7cd1389ba1b267",
      "scenario/core/jobs/preview_scheduler.py": "b4deebeae3ff7a09c5b602df8af8f96608838a8b675e79c2fd6614a6b128186b",
      "scenario/core/jobs/playback.py": "234d2e58b7d0ebfd595b5409bad223e6d524052f2809433bbd752c69300e54c6",
      "scenario/blender/runtime.py": "9663be27e3ae2ffff183b051cb92ec74d02ec7ceaeb531949b74e74a82d2a05a",
      "tests/blender/test_result_media.py": "b3c16d6844bd2bdfc4631913c53b26db050d4520f021ac7b4af7e567a516e73c"
    }
  }
}
---

# Playback descriptors and player copy ownership

Evidence for [the canonical guide](../../BLENDER_JOB_CONTEXT.md).
