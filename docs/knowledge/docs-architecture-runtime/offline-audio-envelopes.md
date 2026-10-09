---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.offline-audio-envelopes",
  "title": "Runtime map entry for offline audio envelopes",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "scope": "offline-audio-envelopes",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "fb699b8555f7cee62147794516cc7aaa224864f7",
    "limits": "Reviewed the result previews row against the scheduler, decode command and session wiring. No view schedules previews yet; image decoding, UI, MCP parity and live thumbnail coverage remain open.",
    "sources": {
      "scenario/core/jobs/preview_scheduler.py": "259ba661bb90b15d33723bfd7bafc0eb70b4443b5c8a56e70d45b9ffa99ac466",
      "scenario/core/jobs/result_previews.py": "1bc82a1318619cb3771377caa6db67d107d6180a85575fbcc2d5470c087e5467",
      "scenario/core/jobs/audio_decode.py": "332645a336308d1a52690fa55b888073fffff5213f95cc59460a2314ca973720",
      "scenario/blender/job_session.py": "3dd23377c9c1883be489a8af292984c5af606a3c85a1bdb39981906b7c2767bd"
    }
  }
}
---

# Runtime map entry for offline audio envelopes

Evidence for [the canonical guide](../../architecture/runtime.md).
