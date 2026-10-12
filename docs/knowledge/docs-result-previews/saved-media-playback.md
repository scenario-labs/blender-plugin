---
{
  "type": "Evidence",
  "id": "docs-result-previews.saved-media-playback",
  "title": "Private player copies and envelope-only requests",
  "evidence": {
    "path": "docs/RESULT_PREVIEWS.md",
    "scope": "saved-media-playback",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the prepare_playback copy: allowed types and size, receipt rehash while copying, container signature, canonical media name, read-only file in a private play-* directory, receipt-level recheck, owner discards, the day-old sweep, metadata-based reuse and removal on cancellation, failure or retirement; and the scheduler's renditions filter and cancel for issued, running and in-flight local decodes, that a retry after cancel reads queued at once, including while a still poll for the same result is on the lane, and that a cancel after a retry waiting for that poll keeps the envelope canceled while the restart polls the still again, until a later retry. Unit tests use synthetic receipts offline; Installed-ZIP native tests ran on macOS arm64 Blender 5.1.2 with the system opener and the animation player process patched. Windows read-only deletion is handled in code but was not exercised on Windows here. Re-reviewed on 2026-10-12: the coverage sentence now matches the private report of three partial physical passes on macOS arm64 Blender 5.1.2. In the first two, at UI scale 1.0 on ZIPs that predate the measured status wrapping, Play video opened the copy under cache/media-playback, read-only in a private directory and matching the saved bytes, in the system player; Play in Blender reused that copy in Blender's animation player; and Waveform drew. In the third, in the sidebar at UI scales 1.0 and 2.0, Waveform drew again. Play audio, the waveform's desktop Cancel and Retry and human listening are stated as not exercised. The draw-time status wrapping (measured with Blender's interface font against the drawn region, or inside Studio the width it requests for its popup) and the summary's no-break spaces were re-checked; this topic's claims do not describe them. Re-checked on 2026-10-12 after the rebase onto main at 4bd0061d, not a full re-review: since the previous review main changed results.py (untransformed original downloads, saving the declared OpenEXR original of an image result instead of its preview, and splat import preparation), coordinator.py (inference-only cancellation, trained-model route checks before quoting, Film export, upload restart, splat preparation and asset organization reviews), workers.py (the Film export slot, upload restart, splat preparation and queued asset organization reviews) and test_preview_scheduler.py (a still whose transfer declares no length, polled again); none of these changes touch the playback copy, its lane command, the waveform controller or their descriptors, so the claims above still hold and these sources' fingerprints are the rebased files'; the review date and base revision are unchanged.",
    "sources": {
      "scenario/core/jobs/playback.py": "234d2e58b7d0ebfd595b5409bad223e6d524052f2809433bbd752c69300e54c6",
      "scenario/core/jobs/results.py": "dc521e8bb414a4803962688a27b44d01f6ceb8eeb7fddff785ce63b5b5839c84",
      "scenario/core/jobs/coordinator.py": "6c4f07b6244d219ce18e64341f80ee9a1f46f59d1d064c7eed219cb6565833f0",
      "scenario/core/jobs/workers.py": "2f4c97160d61cc7f5e299f7bdc33fc047422ee96469f966d33f30a2d43d09439",
      "scenario/core/jobs/preview_scheduler.py": "b4deebeae3ff7a09c5b602df8af8f96608838a8b675e79c2fd6614a6b128186b",
      "scenario/blender/result_media.py": "4a5479d5592c54810687c12ace5190896747a7bb55443dfa0b5c485c204e5a88",
      "tests/unit/test_playback.py": "316d50e43fd1e04fe672a03637059985426bd37c0b6741d8492e3b6bee3fa9b0",
      "tests/unit/test_preview_scheduler.py": "61d2ed127ad2390d2cf035a40124471ab98ea8cd2f11df70b62e5bd0e75b8483"
    }
  }
}
---

# Private player copies and envelope-only requests

Evidence for [the canonical guide](../../RESULT_PREVIEWS.md).
