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
    "limits": "Reviewed the prepare_playback copy: allowed types and size, receipt rehash while copying, container signature, canonical media name, read-only file in a private play-* directory, receipt-level recheck, owner discards, the day-old sweep, metadata-based reuse and removal on cancellation, failure or retirement; and the scheduler's renditions filter and cancel for issued, running and in-flight local decodes. Unit tests use synthetic receipts offline; Installed-ZIP native tests ran on macOS arm64 Blender 5.1.2 with the system opener and the animation player process patched; no player was opened and no desktop interaction, screenshot or human listening is claimed. Windows read-only deletion is handled in code but was not exercised on Windows here.",
    "sources": {
      "scenario/core/jobs/playback.py": "234d2e58b7d0ebfd595b5409bad223e6d524052f2809433bbd752c69300e54c6",
      "scenario/core/jobs/results.py": "d4c1198e482511cc526730e4a25ddc96860e78731fe56b51284c63f5b6e17453",
      "scenario/core/jobs/coordinator.py": "282a5d59693f33b76ad0986e0c3c4550678baee8123e973004ab0fab68e0c1b5",
      "scenario/core/jobs/workers.py": "bfd54007c372f503ece8154807d74fc7406d2a119e95cbc10b1fbdd30ee927f2",
      "scenario/core/jobs/preview_scheduler.py": "82e9f844d23182c83bb1ac50b4585c4def319160cbcb4c55cd81a77b51122499",
      "scenario/blender/result_media.py": "276b32bbb8e7c1eafa904d4e2762ecfbfaf8e9cfb3c611ffac300f1bea080b69",
      "tests/unit/test_playback.py": "316d50e43fd1e04fe672a03637059985426bd37c0b6741d8492e3b6bee3fa9b0",
      "tests/unit/test_preview_scheduler.py": "bcffc376b056726033947f60e91f965c33b400ffce970a3ff2147398778348b3"
    }
  }
}
---

# Private player copies and envelope-only requests

Evidence for [the canonical guide](../../RESULT_PREVIEWS.md).
