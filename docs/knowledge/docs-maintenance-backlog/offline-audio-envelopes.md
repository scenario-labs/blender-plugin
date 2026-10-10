---
{
  "type": "Evidence",
  "id": "docs-maintenance-backlog.offline-audio-envelopes",
  "title": "Backlog disposition for audio waveforms",
  "evidence": {
    "path": "docs/maintenance/backlog.md",
    "scope": "offline-audio-envelopes",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "fb699b8555f7cee62147794516cc7aaa224864f7",
    "limits": "Reviewed the audio waveform row against the prototype preview and the shared preview lane. Shared-view integration, #189 acceptance and #68 listening remain open; this is not release acceptance. After this review, the unreleased prototype waveform preview was retired; its sources here were replaced by their successors, result_media.py and test_result_media.py, without re-reviewing this topic's other claims. The current saved media claims are evidenced by this document's saved-media-playback topic.",
    "sources": {
      "scenario/blender/result_media.py": "276b32bbb8e7c1eafa904d4e2762ecfbfaf8e9cfb3c611ffac300f1bea080b69",
      "scenario/core/jobs/audio_decode.py": "45d1cc7aa8964ad0b7014bf28a23f3d3a46e336eee4770581e79a8aa293d0064",
      "scenario/core/jobs/preview_scheduler.py": "df19ea81e2b0afb1628ce345f0c45fa918f0d64195a3a37ed3360f95fb7e8e78"
    }
  }
}
---

# Backlog disposition for audio waveforms

Evidence for [the canonical document](../../maintenance/backlog.md).
