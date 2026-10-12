---
{
  "type": "Evidence",
  "id": "release-acceptance.saved-media-playback",
  "title": "Issue 189 status after saved media playback",
  "evidence": {
    "path": "docs/maintenance/release-acceptance.md",
    "scope": "saved-media-playback",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed only the #189 status row against the current code and, on 2026-10-12, against the private report of two partial physical desktop passes on macOS arm64 Blender 5.1.2 at UI scale 1.0, whose ZIPs predate the measured waveform status wrapping: a saved video opened in the system player and in Blender's animation player, and a waveform drew. That is not candidate acceptance. No candidate ZIP, listening or release evidence is added; #189 stays open.",
    "sources": {
      "scenario/blender/result_media.py": "4a5479d5592c54810687c12ace5190896747a7bb55443dfa0b5c485c204e5a88",
      "scenario/core/jobs/playback.py": "234d2e58b7d0ebfd595b5409bad223e6d524052f2809433bbd752c69300e54c6",
      "tests/blender/test_result_media.py": "b3c16d6844bd2bdfc4631913c53b26db050d4520f021ac7b4af7e567a516e73c"
    }
  }
}
---

# Issue 189 status after saved media playback

Evidence for [the canonical record](../../maintenance/release-acceptance.md).
