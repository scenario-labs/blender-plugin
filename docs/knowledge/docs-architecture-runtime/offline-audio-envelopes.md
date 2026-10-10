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
      "scenario/core/jobs/preview_scheduler.py": "259ba661bb90b15d33723bfd7bafc0eb70b4443b5c8a56e70d45b9ffa99ac466",
      "scenario/core/jobs/result_previews.py": "613ba1dcd0c807b0300fcad030739185bbe45a04a53de481f1c42652fd35ed73",
      "scenario/core/jobs/audio_decode.py": "45d1cc7aa8964ad0b7014bf28a23f3d3a46e336eee4770581e79a8aa293d0064",
      "scenario/blender/job_session.py": "9c6746c15fc4531eb132e28056abfaace4fdd94507300f37c59d18ebc0fa80d7"
    }
  }
}
---

# Runtime map entry for offline audio envelopes

Evidence for [the canonical guide](../../architecture/runtime.md).
