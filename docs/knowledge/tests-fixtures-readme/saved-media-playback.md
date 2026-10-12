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
    "limits": "Reviewed that the saved media native tests synthesize their PCM tones, including a 1 s stereo 44.1 kHz tone added on 2026-10-12 for the wrapping test, a stub MP4 header and an undecodable MP3 stub at runtime and commit no media file. The Studio first-draw test added later on 2026-10-12 reuses that generated stereo tone; no other fixture or media file was added. Re-checked on 2026-10-12, not a full re-review: test_result_media.py added system player launcher tests and test_playback.py launcher tests and a local env fixture; they use the stub MP4 header, a runtime shell script standing in for xdg-open and no committed media file. These sources' fingerprints are the changed files'; the review date and base revision are unchanged.",
    "sources": {
      "tests/blender/test_result_media.py": "1691143a5c0673fd811651255980faa939a425fbd0837b8eaffc4c86229b6bdd",
      "tests/unit/test_playback.py": "09c7c327ec0adfd7ef0dc711797eaa6430234cf05784fbd2a4f897231af894ba"
    }
  }
}
---

# Generated audio in saved media tests

Evidence for [the canonical inventory](../../../tests/fixtures/README.md).
