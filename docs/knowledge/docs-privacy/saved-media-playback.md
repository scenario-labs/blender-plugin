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
    "limits": "Reviewed where Play copies are written (cache/media-playback), their read-only private storage, the reuse budget, removal on a connection change, file load or extension disable unless a running animation player reads them, the day-old sweep and the animation player environment without SCENARIO_, PYTHON or proxy variables. The system player is opened through Blender's wm.path_open, whose bundled Blender 5.1.2 implementation calls os.startfile on Windows and xdg-open on Linux with Blender's own environment, so only the animation player's environment is filtered; that inheritance is read from the operator source, not observed in a launched player. What the operating system's default player records is outside this review. Installed-ZIP native tests ran on macOS arm64 Blender 5.1.2 with the system opener and the animation player process patched; no player was opened and no desktop interaction, screenshot or human listening is claimed. On 2026-10-12 result_media.py and its native tests changed only the waveform box's draw-time status wrapping (measured with Blender's interface font against the drawn region, or inside Studio the width it requests for its popup) and the no-break spaces of the waveform summary; that diff was re-checked against this topic's claims, which do not describe either, so they stand as reviewed on 2026-10-10. This topic's evidence statements describe its own review; the partial physical desktop passes that UI_STYLE and KNOWN_LIMITATIONS record were not part of it. Re-checked on 2026-10-12 after the rebase onto main at 4bd0061d, not a full re-review: since the previous review main changed results.py (untransformed original downloads, saving the declared OpenEXR original of an image result instead of its preview, and splat import preparation); none of these changes touch the playback copy, its lane command, the waveform controller or their descriptors, so the claims above still hold and these sources' fingerprints are the rebased files'; the review date and base revision are unchanged.",
    "sources": {
      "scenario/core/jobs/playback.py": "234d2e58b7d0ebfd595b5409bad223e6d524052f2809433bbd752c69300e54c6",
      "scenario/blender/result_media.py": "4a5479d5592c54810687c12ace5190896747a7bb55443dfa0b5c485c204e5a88",
      "scenario/core/jobs/results.py": "dc521e8bb414a4803962688a27b44d01f6ceb8eeb7fddff785ce63b5b5839c84",
      "tests/unit/test_playback.py": "316d50e43fd1e04fe672a03637059985426bd37c0b6741d8492e3b6bee3fa9b0",
      "tests/blender/test_result_media.py": "b3c16d6844bd2bdfc4631913c53b26db050d4520f021ac7b4af7e567a516e73c"
    }
  }
}
---

# Local player copies of saved media

Evidence for [the canonical policy](../../PRIVACY.md).
