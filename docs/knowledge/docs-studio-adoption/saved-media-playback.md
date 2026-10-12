---
{
  "type": "Evidence",
  "id": "docs-studio-adoption.saved-media-playback",
  "title": "Saved media controls in the retained preview row",
  "evidence": {
    "path": "docs/STUDIO_ADOPTION.md",
    "scope": "saved-media-playback",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed only the Video/audio preview and sequencer row: saved shared results add receipt-bound Play, Play in Blender and waveform controls in result_media.py; desktop and listening acceptance remain open. No Studio code was adopted for these controls. On 2026-10-12 result_media.py and its native tests changed only the waveform box's draw-time status wrapping (measured with Blender's interface font against the drawn region, or inside Studio the width it requests for its popup) and the no-break spaces of the waveform summary; that diff was re-checked against this topic's claims, which do not describe either, so they stand as reviewed on 2026-10-10. This topic's evidence statements describe its own review; the partial physical desktop passes that UI_STYLE and KNOWN_LIMITATIONS record were not part of it.",
    "sources": {
      "scenario/blender/result_media.py": "4a5479d5592c54810687c12ace5190896747a7bb55443dfa0b5c485c204e5a88",
      "scenario/blender/apply_video.py": "decc84acdf125fe0d4f19c13e3e84b58a8c23e332daea92b5ac5ad6a5f1f8282",
      "tests/blender/test_result_media.py": "b3c16d6844bd2bdfc4631913c53b26db050d4520f021ac7b4af7e567a516e73c"
    }
  }
}
---

# Saved media controls in the retained preview row

Evidence for [the canonical inventory](../../STUDIO_ADOPTION.md).
