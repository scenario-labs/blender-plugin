---
{
  "type": "Evidence",
  "id": "tests-fixtures-readme.saved-media-playback",
  "title": "Generated audio in saved media tests",
  "evidence": {
    "path": "tests/fixtures/README.md",
    "scope": "saved-media-playback",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed that the saved media native tests synthesize their PCM tones, including a 1 s stereo 44.1 kHz tone added on 2026-10-12 for the wrapping test, a stub MP4 header and an undecodable MP3 stub at runtime and commit no media file. The Studio first-draw test added later on 2026-10-12 reuses that generated stereo tone; no other fixture or media file was added.",
    "sources": {
      "tests/blender/test_result_media.py": "b3c16d6844bd2bdfc4631913c53b26db050d4520f021ac7b4af7e567a516e73c",
      "tests/unit/test_playback.py": "316d50e43fd1e04fe672a03637059985426bd37c0b6741d8492e3b6bee3fa9b0"
    }
  }
}
---

# Generated audio in saved media tests

Evidence for [the canonical inventory](../../../tests/fixtures/README.md).
