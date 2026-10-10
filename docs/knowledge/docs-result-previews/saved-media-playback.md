---
{
  "type": "Evidence",
  "id": "docs-result-previews.saved-media-playback",
  "title": "Private player copies and envelope-only requests",
  "evidence": {
    "path": "docs/RESULT_PREVIEWS.md",
    "scope": "saved-media-playback",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the prepare_playback copy: allowed types and size, receipt rehash while copying, container signature, canonical media name, read-only file in a private play-* directory, receipt-level recheck, owner discards, the day-old sweep, metadata-based reuse and removal on cancellation, failure or retirement; and the scheduler's renditions filter and cancel for issued, running and in-flight local decodes, and that a retry after cancel reads queued at once, including while a still poll for the same result is on the lane. Unit tests use synthetic receipts offline; Installed-ZIP native tests ran on macOS arm64 Blender 5.1.2 with the system opener and the animation player process patched; no player was opened and no desktop interaction, screenshot or human listening is claimed. Windows read-only deletion is handled in code but was not exercised on Windows here.",
    "sources": {
      "scenario/core/jobs/playback.py": "234d2e58b7d0ebfd595b5409bad223e6d524052f2809433bbd752c69300e54c6",
      "scenario/core/jobs/results.py": "f6a9702a09824cb28c46d99cfa1a37fa194d64ba2ad1c830bf11884e1b66d31f",
      "scenario/core/jobs/coordinator.py": "bc0d07c4dc83ad352e26876ec33b71b21f26e6f6f70e96c0f71e20bedf7b7d7b",
      "scenario/core/jobs/workers.py": "49194c6957c52b431b4bb18c73a2595bdc85d130552f7b393bc0f8883a3f391c",
      "scenario/core/jobs/preview_scheduler.py": "969bd75231ed09bc81d32d27089405b47281cfe98391907d6769623d3350af8c",
      "scenario/blender/result_media.py": "276b32bbb8e7c1eafa904d4e2762ecfbfaf8e9cfb3c611ffac300f1bea080b69",
      "tests/unit/test_playback.py": "316d50e43fd1e04fe672a03637059985426bd37c0b6741d8492e3b6bee3fa9b0",
      "tests/unit/test_preview_scheduler.py": "0fbe15293b51a75f740f1bfa8e67a25b25ca863d399e7c08521b46e986dd165f"
    }
  }
}
---

# Private player copies and envelope-only requests

Evidence for [the canonical guide](../../RESULT_PREVIEWS.md).
