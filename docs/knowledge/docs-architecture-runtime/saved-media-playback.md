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
    "limits": "Reviewed the Result previews row: the saved media controller draws envelopes for Waveform and opens lane-made private copies for Play and Play in Blender. Installed-ZIP native tests ran on macOS arm64 Blender 5.1.2 with the system opener and the animation player process patched; no player was opened and no desktop interaction, screenshot or human listening is claimed. Image decoding, still and clip display, MCP parity and live thumbnails remain open. On 2026-10-12 result_media.py and its native tests changed only the waveform box's draw-time status wrapping (measured with Blender's interface font against the drawn region, or inside Studio the width it requests for its popup) and the no-break spaces of the waveform summary; that diff was re-checked against this topic's claims, which do not describe either, so they stand as reviewed on 2026-10-10. This topic's evidence statements describe its own review; the partial physical desktop passes that UI_STYLE and KNOWN_LIMITATIONS record were not part of it. Re-checked on 2026-10-12 after the rebase onto main at 4bd0061d, not a full re-review: since the previous review main changed job_session.py (Film export, Film review commands, upload restart, an undo step for saved model imports, first-frame verification and asset organization review entry points); none of these changes touch the playback copy, its lane command, the waveform controller or their descriptors, so the claims above still hold and these sources' fingerprints are the rebased files'; the review date and base revision are unchanged. Re-checked on 2026-10-12 for the credential-free system player launch, not a full re-review: playback.system_open now starts the system player itself, /usr/bin/open on macOS, xdg-open on Linux and other systems, and on Windows Blender's Python interpreter run with -I -S calling os.startfile, each with player_environment() and discarded output, instead of Blender's wm.path_open, whose bundled Blender 5.1.2 source (read in background Blender) calls os.startfile, open or xdg-open with Blender's own environment; the macOS open manual page states that opened applications inherit its environment; result_media tracks that launcher, pins its copy until it exits and reports a failed launch, and its abandoned-copy collection catches Exception rather than BaseException. the Result previews row does not describe how players start, so it still holds. Main at 4fbb69e1 (saved OBJ, FBX, glTF and PLY mesh imports) changed job_recovery.py, job_session.py, runtime.py and saved_job_actions.py only for model import controls, not the playback descriptors, their row, the player copies or the waveform controller. These sources' fingerprints are the changed files'; the review date and base revision are unchanged. Also re-checked on 2026-10-12: the saved media timer now logs and survives a failed redraw instead of being unregistered, with a native test; this topic's claims do not describe that path.",
    "sources": {
      "scenario/blender/result_media.py": "71974d5fb92b52b825ce281cfbae747baf4c38169aa995c478fb21aa485749da",
      "scenario/blender/job_session.py": "5b35e3627eaa7dbf33ed982273177b7e1669a5d9869cf84741534e3c3b46f534",
      "scenario/core/jobs/playback.py": "45af1bda413c4a8a31128fff66473be163df84c0ace157da389c6031ddbae83d",
      "tests/blender/test_result_media.py": "7c255c3e9a9a04806f5588e0d1d50fb69d7fa46028f43c0458c9327a6f9921e9"
    }
  }
}
---

# Runtime map entry for saved media playback

Evidence for [the canonical guide](../../architecture/runtime.md).
