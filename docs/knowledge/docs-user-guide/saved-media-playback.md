---
{
  "type": "Evidence",
  "id": "docs-user-guide.saved-media-playback",
  "title": "Play and waveform controls for saved video and audio",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "saved-media-playback",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the Video, Audio, panel summary and Files and folders claims about saved-result Play, Play in Blender and Waveform: their place in Jobs and Generations, private read-only copies named by the saved type, the credential-free animation player and its two-player limit, offline operation, Cancel, Retry and close, receipt-keyed envelope reuse, retirement on a connection change or file load, and the format and size limits. Installed-ZIP native tests ran on macOS arm64 Blender 5.1.2 with the system opener and the animation player process patched; no player was opened and no desktop interaction, screenshot or human listening is claimed. Soundtrack playback in Blender's animation player is stated as unverified. The retained prototype controls' wording and the older panel screenshots were not re-reviewed. On 2026-10-12 result_media.py and its native tests changed only the waveform box's draw-time status wrapping (measured with Blender's interface font against the drawn region, or inside Studio the width it requests for its popup) and the no-break spaces of the waveform summary; that diff was re-checked against this topic's claims, which do not describe either, so they stand as reviewed on 2026-10-10. This topic's evidence statements describe its own review; the partial physical desktop passes that UI_STYLE and KNOWN_LIMITATIONS record were not part of it. Re-checked on 2026-10-12 after the rebase onto main at 4bd0061d, not a full re-review: since the previous review main changed saved_job_actions.py (native first-frame descriptors replacing the MCP-only handoff, and World candidate numbering), job_recovery.py (the native Use as video first frame review operator) and panels.py (Edit 3D lane routing, workflow cost labels, derived history row kinds and cloud history paging); none of these changes touch the playback copy, its lane command, the waveform controller or their descriptors, so the claims above still hold and these sources' fingerprints are the rebased files'; the review date and base revision are unchanged.",
    "sources": {
      "scenario/blender/result_media.py": "4a5479d5592c54810687c12ace5190896747a7bb55443dfa0b5c485c204e5a88",
      "scenario/core/jobs/playback.py": "234d2e58b7d0ebfd595b5409bad223e6d524052f2809433bbd752c69300e54c6",
      "scenario/core/ui/saved_job_actions.py": "7648560ca76f49835e680fdad677dae5537db9c5de5c5393874c25b81a9916eb",
      "scenario/blender/job_recovery.py": "2480e375c1a9c16a3bd84bd2975ad6276084d659d1bfaa82cca36367fe1b57af",
      "scenario/blender/panels.py": "a2cb353c67f0f4dc834e76432795a7d3fd8cd1df5ceca9faf0f7bfe9b4ce6fd9",
      "tests/blender/test_result_media.py": "b3c16d6844bd2bdfc4631913c53b26db050d4520f021ac7b4af7e567a516e73c",
      "tests/unit/test_playback.py": "316d50e43fd1e04fe672a03637059985426bd37c0b6741d8492e3b6bee3fa9b0"
    }
  }
}
---

# Play and waveform controls for saved video and audio

Evidence for [the canonical document](../../USER_GUIDE.md).
