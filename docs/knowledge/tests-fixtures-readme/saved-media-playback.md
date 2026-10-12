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
    "limits": "Reviewed that the saved media native tests synthesize their PCM tones, including a 1 s stereo 44.1 kHz tone added on 2026-10-12 for the wrapping test, a stub MP4 header and an undecodable MP3 stub at runtime and commit no media file. The Studio first-draw test added later on 2026-10-12 reuses that generated stereo tone; no other fixture or media file was added. Re-checked on 2026-10-12, not a full re-review: test_result_media.py added system player launcher tests and test_playback.py launcher tests and a local env fixture; they use the stub MP4 header, a runtime shell script standing in for xdg-open and no committed media file. These sources' fingerprints are the changed files'; the review date and base revision are unchanged. Also re-checked on 2026-10-12: the saved media timer now logs and survives a failed redraw instead of being unregistered, with a native test; this topic's claims do not describe that path.",
    "sources": {
      "tests/blender/test_result_media.py": "7c255c3e9a9a04806f5588e0d1d50fb69d7fa46028f43c0458c9327a6f9921e9",
      "tests/unit/test_playback.py": "09c7c327ec0adfd7ef0dc711797eaa6430234cf05784fbd2a4f897231af894ba"
    }
  }
}
---

# Generated audio in saved media tests

Evidence for [the canonical inventory](../../../tests/fixtures/README.md).
