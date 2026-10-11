---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.offline-audio-envelopes",
  "title": "Runtime map entry for offline audio envelopes",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "scope": "offline-audio-envelopes",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-11",
    "base_revision": "72723f02a97a7226b1c697c31d8124b77ac92c86",
    "limits": "Reviewed the result previews row against the scheduler, decode command and session wiring. No view schedules previews yet; image decoding, UI, MCP parity and live thumbnail coverage remain open.",
    "sources": {
      "scenario/core/jobs/preview_scheduler.py": "df19ea81e2b0afb1628ce345f0c45fa918f0d64195a3a37ed3360f95fb7e8e78",
      "scenario/core/jobs/result_previews.py": "b08399a5f91362d9ccffa7ac615088f8dcd8c66984f86736245daca529dae741",
      "scenario/core/jobs/audio_decode.py": "45d1cc7aa8964ad0b7014bf28a23f3d3a46e336eee4770581e79a8aa293d0064",
      "scenario/blender/job_session.py": "eca075ce7911e8aae4c5ee2746aaa8d4b1dcb6b40538723de437be4104948124"
    }
  }
}
---

# Runtime map entry for offline audio envelopes

Evidence for [the canonical guide](../../architecture/runtime.md).
