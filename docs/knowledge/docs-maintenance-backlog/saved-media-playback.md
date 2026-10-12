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
    "limits": "Reviewed the audio waveform row against the saved media controller, the offline envelope decoder and the retirement of the unreleased prototype waveform. On 2026-10-12 its desktop clause was reconciled with the private report of three partial physical passes on macOS arm64 Blender 5.1.2, in the sidebar at UI scale 1.0 and, in the third, also at 2.0. MCP envelope parity, further desktop evidence, #189 acceptance and #68 listening remain open; this is not release acceptance. Re-checked on 2026-10-12 after the rebase onto main at 4bd0061d, not a full re-review: since the previous review main changed panels.py (Edit 3D lane routing, workflow cost labels, derived history row kinds and cloud history paging); none of these changes touch the playback copy, its lane command, the waveform controller or their descriptors, so the claims above still hold and these sources' fingerprints are the rebased files'; the review date and base revision are unchanged. Re-checked on 2026-10-12 for the credential-free system player launch, not a full re-review: playback.system_open now starts the system player itself, /usr/bin/open on macOS, xdg-open on Linux and other systems, and on Windows Blender's Python interpreter run with -I -S calling os.startfile, each with player_environment() and discarded output, instead of Blender's wm.path_open, whose bundled Blender 5.1.2 source (read in background Blender) calls os.startfile, open or xdg-open with Blender's own environment; the macOS open manual page states that opened applications inherit its environment; result_media tracks that launcher, pins its copy until it exits and reports a failed launch, and its abandoned-copy collection catches Exception rather than BaseException. the backlog row does not describe how a player starts, so it still holds. These sources' fingerprints are the changed files'; the review date and base revision are unchanged.",
    "sources": {
      "scenario/blender/result_media.py": "a7bae9b893ccaffc117f9c4b5dfbd5d9f337d867239e8caf8a4d290eb8fbc429",
      "scenario/core/jobs/audio_decode.py": "22a905adefc34dce78cacbf2068e9d7b48c6e2cda26ec5ca09473a5ee35d609b",
      "scenario/blender/panels.py": "a2cb353c67f0f4dc834e76432795a7d3fd8cd1df5ceca9faf0f7bfe9b4ce6fd9",
      "tests/blender/test_result_media.py": "1691143a5c0673fd811651255980faa939a425fbd0837b8eaffc4c86229b6bdd"
    }
  }
}
---

# Backlog disposition for saved media playback

Evidence for [the canonical document](../../maintenance/backlog.md).
