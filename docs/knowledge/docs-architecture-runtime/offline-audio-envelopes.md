---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.offline-audio-envelopes",
  "title": "Runtime map entry for offline audio envelopes",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "scope": "offline-audio-envelopes",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "fb699b8555f7cee62147794516cc7aaa224864f7",
    "limits": "Reviewed the result previews row against the scheduler, decode command and session wiring. No view schedules previews yet; image decoding, UI, MCP parity and live thumbnail coverage remain open.",
    "sources": {
      "scenario/core/jobs/preview_scheduler.py": "21d0b8d0265c2e70dc9d9c27372a8205bb6a10cfaeb5e896759705a37c0d482e",
      "scenario/core/jobs/result_previews.py": "b08399a5f91362d9ccffa7ac615088f8dcd8c66984f86736245daca529dae741",
      "scenario/core/jobs/audio_decode.py": "45d1cc7aa8964ad0b7014bf28a23f3d3a46e336eee4770581e79a8aa293d0064",
      "scenario/blender/job_session.py": "9c6746c15fc4531eb132e28056abfaace4fdd94507300f37c59d18ebc0fa80d7"
    }
  }
}
---

# Runtime map entry for offline audio envelopes

Evidence for [the canonical guide](../../architecture/runtime.md).
