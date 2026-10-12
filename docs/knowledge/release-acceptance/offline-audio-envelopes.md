---
{
  "type": "Evidence",
  "id": "release-acceptance.offline-audio-envelopes",
  "title": "Issue 189 status after offline audio envelopes",
  "evidence": {
    "path": "docs/maintenance/release-acceptance.md",
    "scope": "offline-audio-envelopes",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "759f764dff9c9d9b1f50efecdd46835471f19189",
    "limits": "Reviewed only the #189 status row against the current code. No candidate ZIP, desktop, listening or release evidence is added; #189 stays open. Re-checked after the main-thread lock test changed; the #189 row is unaffected.",
    "sources": {
      "scenario/blender/audio_preview.py": "e77b8d21f7733322b9714a17ff8b982d24cd993e5702e6b0403d7b5b3ddfbb22",
      "scenario/core/jobs/preview_scheduler.py": "df19ea81e2b0afb1628ce345f0c45fa918f0d64195a3a37ed3360f95fb7e8e78",
      "scenario/core/jobs/audio_decode.py": "45d1cc7aa8964ad0b7014bf28a23f3d3a46e336eee4770581e79a8aa293d0064",
      "tests/blender/test_waveform_worker.py": "47a54f6b3bf1c7faa5bb372312986980eb7d76936dfe90c14d86b20c220b9561"
    }
  }
}
---

# Issue 189 status after offline audio envelopes

Evidence for [the canonical record](../../maintenance/release-acceptance.md).
