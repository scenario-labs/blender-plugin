---
{
  "type": "Evidence",
  "id": "docs-maintenance-backlog.saved-media-playback",
  "title": "Backlog disposition for saved media playback",
  "evidence": {
    "path": "docs/maintenance/backlog.md",
    "scope": "saved-media-playback",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the audio waveform row against the saved media controller, the offline envelope decoder and the retirement of the unreleased prototype waveform. On 2026-10-12 its desktop clause was reconciled with the private report of three partial physical passes on macOS arm64 Blender 5.1.2, in the sidebar at UI scale 1.0 and, in the third, also at 2.0. MCP envelope parity, further desktop evidence, #189 acceptance and #68 listening remain open; this is not release acceptance. Re-checked on 2026-10-12 after the rebase onto main at 4bd0061d, not a full re-review: since the previous review main changed panels.py (Edit 3D lane routing, workflow cost labels, derived history row kinds and cloud history paging); none of these changes touch the playback copy, its lane command, the waveform controller or their descriptors, so the claims above still hold and these sources' fingerprints are the rebased files'; the review date and base revision are unchanged. Re-checked on 2026-10-12 for the credential-free system player launch, not a full re-review: playback.system_open now starts the system player itself, /usr/bin/open on macOS, xdg-open on Linux and other systems, and on Windows Blender's Python interpreter run with -I -S calling os.startfile, each with player_environment() and discarded output, instead of Blender's wm.path_open, whose bundled Blender 5.1.2 source (read in background Blender) calls os.startfile, open or xdg-open with Blender's own environment; the macOS open manual page states that opened applications inherit its environment; result_media tracks that launcher, pins its copy until it exits and reports a failed launch, and its abandoned-copy collection catches Exception rather than BaseException. the backlog row does not describe how a player starts, so it still holds. These sources' fingerprints are the changed files'; the review date and base revision are unchanged. Also re-checked on 2026-10-12: the saved media timer now logs and survives a failed redraw instead of being unregistered, with a native test; this topic's claims do not describe that path. Also re-checked after the rebase onto main at ff8d29d8 (Environment lane, compact composer job strip), not a full re-review: panels.py gained draw_result(..., collapsible=False) for the composer's job card and studio.py a track_popup helper; the job strip dispatches only receipt, cancel, recover and apply descriptors, so the playback row is unchanged in Jobs, Generations and Studio and the job card draws the same panel rows. These fingerprints are the rebased files'. Re-checked on 2026-10-13 for in-extension audio playback (#435), not a full re-review: the Audio waveform row now also names in-extension Play audio with Stop and moves the remaining desktop and listening acceptance to #440, since #189 and #68 are closed. The fingerprints of result_media.py, test_result_media.py stay as recorded: they already differed on main before this change, for changes this re-check did not review. The review date and base revision are unchanged.",
    "sources": {
      "scenario/blender/result_media.py": "71974d5fb92b52b825ce281cfbae747baf4c38169aa995c478fb21aa485749da",
      "scenario/core/jobs/audio_decode.py": "22a905adefc34dce78cacbf2068e9d7b48c6e2cda26ec5ca09473a5ee35d609b",
      "scenario/blender/panels.py": "ba62d496363b0dcb9e4c420eaf788da8d321f01def9a3b3bf4ab48edb30274ec",
      "tests/blender/test_result_media.py": "7c255c3e9a9a04806f5588e0d1d50fb69d7fa46028f43c0458c9327a6f9921e9"
    }
  }
}
---

# Backlog disposition for saved media playback

Evidence for [the canonical document](../../maintenance/backlog.md).
