---
{
  "type": "Evidence",
  "id": "docs-job-coordinator.saved-media-playback",
  "title": "Playback copy command on the preview lane",
  "evidence": {
    "path": "docs/JOB_COORDINATOR.md",
    "scope": "saved-media-playback",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed prepare_playback's exact-revision admission, owner discards and sweep before copying, unchanged-copy reuse, receipt-level recheck, removal after a cancellation or inactive coordinator, and that it runs on the ScenarioPreview lane without network, job transitions or claims. Unit tests use synthetic receipts and real workers offline.",
    "sources": {
      "scenario/core/jobs/coordinator.py": "282a5d59693f33b76ad0986e0c3c4550678baee8123e973004ab0fab68e0c1b5",
      "scenario/core/jobs/results.py": "d4c1198e482511cc526730e4a25ddc96860e78731fe56b51284c63f5b6e17453",
      "scenario/core/jobs/playback.py": "234d2e58b7d0ebfd595b5409bad223e6d524052f2809433bbd752c69300e54c6",
      "scenario/core/jobs/workers.py": "bfd54007c372f503ece8154807d74fc7406d2a119e95cbc10b1fbdd30ee927f2",
      "tests/unit/test_playback.py": "316d50e43fd1e04fe672a03637059985426bd37c0b6741d8492e3b6bee3fa9b0"
    }
  }
}
---

# Playback copy command on the preview lane

Evidence for [the canonical guide](../../JOB_COORDINATOR.md).
