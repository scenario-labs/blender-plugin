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
    "limits": "Reviewed only the Video/audio preview and sequencer row: saved shared results add receipt-bound Play, Play in Blender and waveform controls in result_media.py; desktop and listening acceptance remain open. No Studio code was adopted for these controls. On 2026-10-12 result_media.py and its native tests changed only the waveform box's draw-time status wrapping (measured with Blender's interface font against the drawn region, or inside Studio the width it requests for its popup) and the no-break spaces of the waveform summary; that diff was re-checked against this topic's claims, which do not describe either, so they stand as reviewed on 2026-10-10. This topic's evidence statements describe its own review; the partial physical desktop passes that UI_STYLE and KNOWN_LIMITATIONS record were not part of it. Re-checked on 2026-10-12 for the credential-free system player launch, not a full re-review: playback.system_open now starts the system player itself, /usr/bin/open on macOS, xdg-open on Linux and other systems, and on Windows Blender's Python interpreter run with -I -S calling os.startfile, each with player_environment() and discarded output, instead of Blender's wm.path_open, whose bundled Blender 5.1.2 source (read in background Blender) calls os.startfile, open or xdg-open with Blender's own environment; the macOS open manual page states that opened applications inherit its environment; result_media tracks that launcher, pins its copy until it exits and reports a failed launch, and its abandoned-copy collection catches Exception rather than BaseException. the adoption row still holds; apply_video.py is retained and its Play and Play in Blender now start their players without those variables. These sources' fingerprints are the changed files'; the review date and base revision are unchanged. Also re-checked on 2026-10-12: the saved media timer now logs and survives a failed redraw instead of being unregistered, with a native test; this topic's claims do not describe that path. Re-checked on 2026-10-13 for in-extension audio playback (#435), not a full re-review: the media row now also names in-extension Play audio and moves desktop playback and listening acceptance to #440. The fingerprints of result_media.py, test_result_media.py stay as recorded: they already differed on main before this change, for changes this re-check did not review. The review date and base revision are unchanged.",
    "sources": {
      "scenario/blender/result_media.py": "71974d5fb92b52b825ce281cfbae747baf4c38169aa995c478fb21aa485749da",
      "scenario/blender/apply_video.py": "48e4654a7601c2ec5d52302a0ba59968eded05e9dca838207402ca74c772ad61",
      "tests/blender/test_result_media.py": "7c255c3e9a9a04806f5588e0d1d50fb69d7fa46028f43c0458c9327a6f9921e9"
    }
  }
}
---

# Saved media controls in the retained preview row

Evidence for [the canonical inventory](../../STUDIO_ADOPTION.md).
