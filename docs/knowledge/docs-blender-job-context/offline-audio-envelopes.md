---
{
  "type": "Evidence",
  "id": "docs-blender-job-context.offline-audio-envelopes",
  "title": "Session decoder specification for audio envelopes",
  "evidence": {
    "path": "docs/BLENDER_JOB_CONTEXT.md",
    "scope": "offline-audio-envelopes",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-11",
    "base_revision": "72723f02a97a7226b1c697c31d8124b77ac92c86",
    "limits": "Inspected the preview_waveform constructor argument, the runtime's main-thread waveform_spec resolution and its None fallback, and retirement and shutdown with a running decode. Installed-ZIP native tests for the waveform decoder, session previews and the prototype preview passed on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1; Windows and Linux rest on hosted CI, not on this review. The native retirement test terminates a real child without the main thread joining it; extension disable during a decode and packaged builds without an executable path were not exercised natively.",
    "sources": {
      "scenario/blender/job_session.py": "eca075ce7911e8aae4c5ee2746aaa8d4b1dcb6b40538723de437be4104948124",
      "scenario/blender/runtime.py": "c9b8c98af5796ac40f7baaf89813b15fa46f5cea7bc68c56a00e414a143a046a",
      "scenario/core/jobs/preview_scheduler.py": "df19ea81e2b0afb1628ce345f0c45fa918f0d64195a3a37ed3360f95fb7e8e78",
      "scenario/core/jobs/workers.py": "df2830bcfd58445dcf67845e605f49a0305a103275a0aa8bf3d52450ae9a3658",
      "scenario/core/jobs/local_render.py": "259ec65d914e12b8a8dce009ea68a07f4ab3ca1007a232a63a2c43fb64e5daaf",
      "tests/blender/test_result_previews.py": "fd31993233db037d73220f4c5e67355da6af5688c864fbe2f62848f228af4c80"
    }
  }
}
---

# Session decoder specification for audio envelopes

Evidence for [the canonical guide](../../BLENDER_JOB_CONTEXT.md).
