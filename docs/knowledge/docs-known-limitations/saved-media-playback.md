---
{
  "type": "Evidence",
  "id": "docs-known-limitations.saved-media-playback",
  "title": "Saved media playback and waveform limits",
  "evidence": {
    "path": "docs/KNOWN_LIMITATIONS.md",
    "scope": "saved-media-playback",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the saved media bullets against the controller, copy primitive and scheduler: the absent desktop, listening and MCP evidence, lane occupancy by copies and decodes, the four-copy and 1 GiB budget plus player-read copies, the untracked system player whose open copy eviction, retirement or unregistering can remove and which, through Blender 5.1.2's bundled wm.path_open (os.startfile or xdg-open), can inherit Blender's environment on Windows and Linux, Windows deletion deferred to the day-old sweep, the 60-second decode timeout and 120-second admission expiry, the once-per-second connection check while a waveform is shown and the missing-executable failures. The child start-up figures are carried from the offline envelope review; no new measurement was made. Installed-ZIP native tests ran on macOS arm64 Blender 5.1.2 with the system opener and the animation player process patched. Default-player absence, sandboxed packages and the animation player's soundtrack are stated as unverified. Re-reviewed on 2026-10-12: the evidence sentence now matches the private report of three partial physical passes on macOS arm64 Blender 5.1.2. In the first two, at UI scale 1.0 on ZIPs that predate the measured status wrapping, a saved video opened in the system player and in Blender's animation player and a waveform drew. The third, on a ZIP that had the measured wrapping but predates its Studio popup width declaration and hyphen rule, drew the sidebar rows at UI scales 1.0 and 2.0 (a 1122 px sidebar at 2.0): Waveform reached its summary and icon at both scales and kept 1.00 s whole. result_media.py is unchanged since that ZIP, label_wrap.py changed only for popups (a declared width, and a popup region that is not sized yet) and text_wrap.py only for hyphenated words, which these sidebar texts lack. Play audio, the waveform's desktop Cancel, Retry and close, clicking Play at UI scale 2.0, Studio at UI scale 2.0, other platforms and human listening are stated as without desktop evidence. The draw-time status wrapping (measured with Blender's interface font against the drawn region, or inside Studio the width it requests for its popup) and the summary's no-break spaces were re-checked; these bullets do not describe them. Re-checked on 2026-10-12 after the rebase onto main at 4bd0061d, not a full re-review: since the previous review main changed results.py (untransformed original downloads, saving the declared OpenEXR original of an image result instead of its preview, and splat import preparation); none of these changes touch the playback copy, its lane command, the waveform controller or their descriptors, so the claims above still hold and these sources' fingerprints are the rebased files'; the review date and base revision are unchanged.",
    "sources": {
      "scenario/blender/result_media.py": "4a5479d5592c54810687c12ace5190896747a7bb55443dfa0b5c485c204e5a88",
      "scenario/core/jobs/playback.py": "234d2e58b7d0ebfd595b5409bad223e6d524052f2809433bbd752c69300e54c6",
      "scenario/core/jobs/preview_scheduler.py": "b4deebeae3ff7a09c5b602df8af8f96608838a8b675e79c2fd6614a6b128186b",
      "scenario/core/jobs/results.py": "dc521e8bb414a4803962688a27b44d01f6ceb8eeb7fddff785ce63b5b5839c84",
      "tests/blender/test_result_media.py": "b3c16d6844bd2bdfc4631913c53b26db050d4520f021ac7b4af7e567a516e73c",
      "tests/unit/test_playback.py": "316d50e43fd1e04fe672a03637059985426bd37c0b6741d8492e3b6bee3fa9b0"
    }
  }
}
---

# Saved media playback and waveform limits

Evidence for [the canonical document](../../KNOWN_LIMITATIONS.md).
