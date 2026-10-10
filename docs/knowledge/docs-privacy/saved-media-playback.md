---
{
  "type": "Evidence",
  "id": "docs-privacy.saved-media-playback",
  "title": "Local player copies of saved media",
  "evidence": {
    "path": "docs/PRIVACY.md",
    "scope": "saved-media-playback",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed where Play copies are written (cache/media-playback), their read-only private storage, the reuse budget, removal on a connection change, file load or extension disable unless a running animation player reads them, the day-old sweep and the animation player environment without SCENARIO_, PYTHON or proxy variables. What the operating system's default player records is outside this review. Installed-ZIP native tests ran on macOS arm64 Blender 5.1.2 with the system opener and the animation player process patched; no player was opened and no desktop interaction, screenshot or human listening is claimed.",
    "sources": {
      "scenario/core/jobs/playback.py": "234d2e58b7d0ebfd595b5409bad223e6d524052f2809433bbd752c69300e54c6",
      "scenario/blender/result_media.py": "3dedc599853505ebbb12be68bd2406e45cf5eaee16090de77237fd2b4dba1607",
      "scenario/core/jobs/results.py": "d4c1198e482511cc526730e4a25ddc96860e78731fe56b51284c63f5b6e17453",
      "tests/unit/test_playback.py": "316d50e43fd1e04fe672a03637059985426bd37c0b6741d8492e3b6bee3fa9b0",
      "tests/blender/test_result_media.py": "250abc036f5b46890c384b17d25311ee8c59e57fb1cb84e45233e77cd49c8a2f"
    }
  }
}
---

# Local player copies of saved media

Evidence for [the canonical policy](../../PRIVACY.md).
