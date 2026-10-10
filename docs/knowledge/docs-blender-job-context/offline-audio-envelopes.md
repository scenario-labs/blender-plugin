---
{
  "type": "Evidence",
  "id": "docs-blender-job-context.offline-audio-envelopes",
  "title": "Session decoder specification for audio envelopes",
  "evidence": {
    "path": "docs/BLENDER_JOB_CONTEXT.md",
    "scope": "offline-audio-envelopes",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "fb699b8555f7cee62147794516cc7aaa224864f7",
    "limits": "Inspected the preview_waveform constructor argument, the runtime's main-thread waveform_spec resolution and its None fallback, and retirement and shutdown with a running decode. Installed-ZIP native tests for the waveform decoder, session previews and the prototype preview passed on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1; Windows and Linux rest on hosted CI, not on this review. The native retirement test terminates a real child without the main thread joining it; extension disable during a decode and packaged builds without an executable path were not exercised natively.",
    "sources": {
      "scenario/blender/job_session.py": "9c6746c15fc4531eb132e28056abfaace4fdd94507300f37c59d18ebc0fa80d7",
      "scenario/blender/runtime.py": "286974e2a90e4776de71d081651a88424c543573add3ed125b072ad47c524883",
      "scenario/core/jobs/preview_scheduler.py": "259ba661bb90b15d33723bfd7bafc0eb70b4443b5c8a56e70d45b9ffa99ac466",
      "scenario/core/jobs/workers.py": "fb361cbf1291e9dc426502ba4eaf6a538bebd15a80da9f02dacac8c8fa466dc9",
      "scenario/core/jobs/local_render.py": "259ec65d914e12b8a8dce009ea68a07f4ab3ca1007a232a63a2c43fb64e5daaf",
      "tests/blender/test_result_previews.py": "fd31993233db037d73220f4c5e67355da6af5688c864fbe2f62848f228af4c80"
    }
  }
}
---

# Session decoder specification for audio envelopes

Evidence for [the canonical guide](../../BLENDER_JOB_CONTEXT.md).
