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
    "limits": "Reviewed the saved media bullets against the controller, copy primitive and scheduler: the absent desktop, listening and MCP evidence, lane occupancy by copies and decodes, the four-copy and 1 GiB budget plus player-read copies, the untracked system player whose open copy eviction, retirement or unregistering can remove and which, through Blender 5.1.2's bundled wm.path_open (os.startfile or xdg-open), can inherit Blender's environment on Windows and Linux, Windows deletion deferred to the day-old sweep, the 60-second decode timeout and 120-second admission expiry, the once-per-second connection check while a waveform is shown and the missing-executable failures. The child start-up figures are carried from the offline envelope review; no new measurement was made. Installed-ZIP native tests ran on macOS arm64 Blender 5.1.2 with the system opener and the animation player process patched; no player was opened and no desktop interaction, screenshot or human listening is claimed. Default-player absence, sandboxed packages and the animation player's soundtrack are stated as unverified.",
    "sources": {
      "scenario/blender/result_media.py": "276b32bbb8e7c1eafa904d4e2762ecfbfaf8e9cfb3c611ffac300f1bea080b69",
      "scenario/core/jobs/playback.py": "234d2e58b7d0ebfd595b5409bad223e6d524052f2809433bbd752c69300e54c6",
      "scenario/core/jobs/preview_scheduler.py": "969bd75231ed09bc81d32d27089405b47281cfe98391907d6769623d3350af8c",
      "scenario/core/jobs/results.py": "f6a9702a09824cb28c46d99cfa1a37fa194d64ba2ad1c830bf11884e1b66d31f",
      "tests/blender/test_result_media.py": "07c7686367b0fd38838a82ceafcafb2bd549063335aba11720420985feb1da9a",
      "tests/unit/test_playback.py": "316d50e43fd1e04fe672a03637059985426bd37c0b6741d8492e3b6bee3fa9b0"
    }
  }
}
---

# Saved media playback and waveform limits

Evidence for [the canonical document](../../KNOWN_LIMITATIONS.md).
