---
{
  "type": "Evidence",
  "id": "docs-blender-job-context.offline-audio-envelopes",
  "title": "Session decoder specification for audio envelopes",
  "evidence": {
    "path": "docs/BLENDER_JOB_CONTEXT.md",
    "scope": "offline-audio-envelopes",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "fb699b8555f7cee62147794516cc7aaa224864f7",
    "limits": "Inspected the preview_waveform constructor argument, the runtime's main-thread waveform_spec resolution and its None fallback, and retirement and shutdown with a running decode. Installed-ZIP native tests for the waveform decoder, session previews and the prototype preview passed on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1; Windows and Linux rest on hosted CI, not on this review. The native retirement test terminates a real child without the main thread joining it; extension disable during a decode and packaged builds without an executable path were not exercised natively.",
    "sources": {
      "scenario/blender/job_session.py": "3dd23377c9c1883be489a8af292984c5af606a3c85a1bdb39981906b7c2767bd",
      "scenario/blender/runtime.py": "1c597c458a32872241b53724886fb7ba89efd9a6b5b2a3c7daeb2c94d1b5d401",
      "scenario/core/jobs/preview_scheduler.py": "259ba661bb90b15d33723bfd7bafc0eb70b4443b5c8a56e70d45b9ffa99ac466",
      "scenario/core/jobs/workers.py": "fb361cbf1291e9dc426502ba4eaf6a538bebd15a80da9f02dacac8c8fa466dc9",
      "scenario/core/jobs/local_render.py": "37c57537f75172892b868c56c9e0bcb641617c271ec1dae5a037e96ecabaeaf8",
      "tests/blender/test_result_previews.py": "5b389797a45805c3c80966e6ee1ab4a07e36b6ad90b5ae3b7daf0139c9fbfb69"
    }
  }
}
---

# Session decoder specification for audio envelopes

Evidence for [the canonical guide](../../BLENDER_JOB_CONTEXT.md).
