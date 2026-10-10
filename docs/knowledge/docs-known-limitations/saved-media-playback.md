---
{
  "type": "Evidence",
  "id": "docs-known-limitations.saved-media-playback",
  "title": "Saved media playback and waveform limits",
  "evidence": {
    "path": "docs/KNOWN_LIMITATIONS.md",
    "scope": "saved-media-playback",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the saved media bullets against the controller, copy primitive and scheduler: the absent desktop, listening and MCP evidence, lane occupancy by copies and decodes, the four-copy and 1 GiB budget plus player-read copies, Windows deletion deferred to the day-old sweep, the 60-second decode timeout and 120-second admission expiry, the once-per-second connection check while a waveform is shown and the missing-executable failures. The child start-up figures are carried from the offline envelope review; no new measurement was made. Installed-ZIP native tests ran on macOS arm64 Blender 5.1.2 with the system opener and the animation player process patched; no player was opened and no desktop interaction, screenshot or human listening is claimed. Default-player absence, sandboxed packages and the animation player's soundtrack are stated as unverified.",
    "sources": {
      "scenario/blender/result_media.py": "3dedc599853505ebbb12be68bd2406e45cf5eaee16090de77237fd2b4dba1607",
      "scenario/core/jobs/playback.py": "234d2e58b7d0ebfd595b5409bad223e6d524052f2809433bbd752c69300e54c6",
      "scenario/core/jobs/preview_scheduler.py": "82e9f844d23182c83bb1ac50b4585c4def319160cbcb4c55cd81a77b51122499",
      "scenario/core/jobs/results.py": "d4c1198e482511cc526730e4a25ddc96860e78731fe56b51284c63f5b6e17453",
      "tests/blender/test_result_media.py": "250abc036f5b46890c384b17d25311ee8c59e57fb1cb84e45233e77cd49c8a2f",
      "tests/unit/test_playback.py": "316d50e43fd1e04fe672a03637059985426bd37c0b6741d8492e3b6bee3fa9b0"
    }
  }
}
---

# Saved media playback and waveform limits

Evidence for [the canonical document](../../KNOWN_LIMITATIONS.md).
