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
    "limits": "Reviewed the prepare_playback copy: allowed types and size, receipt rehash while copying, container signature, canonical media name, read-only file in a private play-* directory, receipt-level recheck, owner discards, the day-old sweep, metadata-based reuse and removal on cancellation, failure or retirement; and the scheduler's renditions filter and cancel for issued, running and in-flight local decodes, that a retry after cancel reads queued at once, including while a still poll for the same result is on the lane, and that a cancel after a retry waiting for that poll keeps the envelope canceled while the restart polls the still again, until a later retry. Unit tests use synthetic receipts offline; Installed-ZIP native tests ran on macOS arm64 Blender 5.1.2 with the system opener and the animation player process patched. Windows read-only deletion is handled in code but was not exercised on Windows here. Re-reviewed on 2026-10-12: the coverage sentence now matches the private report of two partial physical passes on macOS arm64 Blender 5.1.2 at UI scale 1.0, whose ZIPs predate the measured status wrapping. Play video opened the copy under cache/media-playback, read-only in a private directory and matching the saved bytes, in the system player; Play in Blender reused that copy in Blender's animation player; and Waveform drew. Play audio, desktop Cancel and Retry and human listening are stated as not exercised. The draw-time status wrapping (measured with Blender's interface font against the drawn region, or inside Studio the width it requests for its popup) and the summary's no-break spaces were re-checked; this topic's claims do not describe them.",
    "sources": {
      "scenario/core/jobs/playback.py": "234d2e58b7d0ebfd595b5409bad223e6d524052f2809433bbd752c69300e54c6",
      "scenario/core/jobs/results.py": "f6a9702a09824cb28c46d99cfa1a37fa194d64ba2ad1c830bf11884e1b66d31f",
      "scenario/core/jobs/coordinator.py": "bc0d07c4dc83ad352e26876ec33b71b21f26e6f6f70e96c0f71e20bedf7b7d7b",
      "scenario/core/jobs/workers.py": "49194c6957c52b431b4bb18c73a2595bdc85d130552f7b393bc0f8883a3f391c",
      "scenario/core/jobs/preview_scheduler.py": "b4deebeae3ff7a09c5b602df8af8f96608838a8b675e79c2fd6614a6b128186b",
      "scenario/blender/result_media.py": "4a5479d5592c54810687c12ace5190896747a7bb55443dfa0b5c485c204e5a88",
      "tests/unit/test_playback.py": "316d50e43fd1e04fe672a03637059985426bd37c0b6741d8492e3b6bee3fa9b0",
      "tests/unit/test_preview_scheduler.py": "13eb7154e89ed4aa5f945f71646a12acda7e81bba3994451538ca3d9ac00084f"
    }
  }
}
---

# Private player copies and envelope-only requests

Evidence for [the canonical guide](../../RESULT_PREVIEWS.md).
