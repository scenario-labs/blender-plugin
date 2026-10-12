---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.saved-media-playback",
  "title": "Runtime map entry for saved media playback",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "scope": "saved-media-playback",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the Result previews row: the saved media controller draws envelopes for Waveform and opens lane-made private copies for Play and Play in Blender. Installed-ZIP native tests ran on macOS arm64 Blender 5.1.2 with the system opener and the animation player process patched; no player was opened and no desktop interaction, screenshot or human listening is claimed. Image decoding, still and clip display, MCP parity and live thumbnails remain open. On 2026-10-12 result_media.py and its native tests changed only the waveform box's draw-time status wrapping (measured with Blender's interface font against the drawn region, or inside Studio the width it requests for its popup) and the no-break spaces of the waveform summary; that diff was re-checked against this topic's claims, which do not describe either, so they stand as reviewed on 2026-10-10. This topic's evidence statements describe its own review; the partial physical desktop passes that UI_STYLE and KNOWN_LIMITATIONS record were not part of it. Re-checked on 2026-10-12 after the rebase onto main at 4bd0061d, not a full re-review: since the previous review main changed job_session.py (Film export, Film review commands, upload restart, an undo step for saved model imports, first-frame verification and asset organization review entry points); none of these changes touch the playback copy, its lane command, the waveform controller or their descriptors, so the claims above still hold and these sources' fingerprints are the rebased files'; the review date and base revision are unchanged.",
    "sources": {
      "scenario/blender/result_media.py": "4a5479d5592c54810687c12ace5190896747a7bb55443dfa0b5c485c204e5a88",
      "scenario/blender/job_session.py": "32cb7d9b8a929038b37bcf0979625076f1d9d1bf699f25cf3cd65439cc13e567",
      "scenario/core/jobs/playback.py": "234d2e58b7d0ebfd595b5409bad223e6d524052f2809433bbd752c69300e54c6",
      "tests/blender/test_result_media.py": "b3c16d6844bd2bdfc4631913c53b26db050d4520f021ac7b4af7e567a516e73c"
    }
  }
}
---

# Runtime map entry for saved media playback

Evidence for [the canonical guide](../../architecture/runtime.md).
