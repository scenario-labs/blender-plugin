---
{
  "type": "Evidence",
  "id": "docs-maintenance-backlog.saved-media-playback",
  "title": "Backlog disposition for saved media playback",
  "evidence": {
    "path": "docs/maintenance/backlog.md",
    "scope": "saved-media-playback",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the audio waveform row against the saved media controller, the offline envelope decoder and the retirement of the unreleased prototype waveform. On 2026-10-12 its desktop clause was reconciled with the private report of three partial physical passes on macOS arm64 Blender 5.1.2, in the sidebar at UI scale 1.0 and, in the third, also at 2.0. MCP envelope parity, further desktop evidence, #189 acceptance and #68 listening remain open; this is not release acceptance. Re-checked on 2026-10-12 after the rebase onto main at 4bd0061d, not a full re-review: since the previous review main changed panels.py (Edit 3D lane routing, workflow cost labels, derived history row kinds and cloud history paging); none of these changes touch the playback copy, its lane command, the waveform controller or their descriptors, so the claims above still hold and these sources' fingerprints are the rebased files'; the review date and base revision are unchanged.",
    "sources": {
      "scenario/blender/result_media.py": "4a5479d5592c54810687c12ace5190896747a7bb55443dfa0b5c485c204e5a88",
      "scenario/core/jobs/audio_decode.py": "22a905adefc34dce78cacbf2068e9d7b48c6e2cda26ec5ca09473a5ee35d609b",
      "scenario/blender/panels.py": "a2cb353c67f0f4dc834e76432795a7d3fd8cd1df5ceca9faf0f7bfe9b4ce6fd9",
      "tests/blender/test_result_media.py": "b3c16d6844bd2bdfc4631913c53b26db050d4520f021ac7b4af7e567a516e73c"
    }
  }
}
---

# Backlog disposition for saved media playback

Evidence for [the canonical document](../../maintenance/backlog.md).
