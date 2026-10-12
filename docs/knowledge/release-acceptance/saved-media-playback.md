---
{
  "type": "Evidence",
  "id": "release-acceptance.saved-media-playback",
  "title": "Issue 189 status after saved media playback",
  "evidence": {
    "path": "docs/maintenance/release-acceptance.md",
    "scope": "saved-media-playback",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed only the #189 status row against the current code and, on 2026-10-12, against the private report of three partial physical desktop passes on macOS arm64 Blender 5.1.2: at UI scale 1.0, on ZIPs that predate the measured waveform status wrapping, a saved video opened in the system player and in Blender's animation player and a waveform drew; the third, on a ZIP with the measured wrapping before its later Studio popup width and hyphen amendments, drew a waveform in the sidebar at UI scales 1.0 and 2.0. Play audio, the waveform's desktop Cancel and Retry, Studio at UI scale 2.0 and other platforms are stated as not recorded. That is not candidate acceptance. No candidate ZIP, listening or release evidence is added; #189 stays open. Re-checked on 2026-10-12 for the credential-free system player launch, not a full re-review: playback.system_open now starts the system player itself, /usr/bin/open on macOS, xdg-open on Linux and other systems, and on Windows Blender's Python interpreter run with -I -S calling os.startfile, each with player_environment() and discarded output, instead of Blender's wm.path_open, whose bundled Blender 5.1.2 source (read in background Blender) calls os.startfile, open or xdg-open with Blender's own environment; the macOS open manual page states that opened applications inherit its environment; result_media tracks that launcher, pins its copy until it exits and reports a failed launch, and its abandoned-copy collection catches Exception rather than BaseException. the #189 row does not describe the launcher, and its desktop passes predate it, as KNOWN_LIMITATIONS and UI_STYLE now state; #189 stays open. These sources' fingerprints are the changed files'; the review date and base revision are unchanged.",
    "sources": {
      "scenario/blender/result_media.py": "a7bae9b893ccaffc117f9c4b5dfbd5d9f337d867239e8caf8a4d290eb8fbc429",
      "scenario/core/jobs/playback.py": "45af1bda413c4a8a31128fff66473be163df84c0ace157da389c6031ddbae83d",
      "tests/blender/test_result_media.py": "1691143a5c0673fd811651255980faa939a425fbd0837b8eaffc4c86229b6bdd"
    }
  }
}
---

# Issue 189 status after saved media playback

Evidence for [the canonical record](../../maintenance/release-acceptance.md).
