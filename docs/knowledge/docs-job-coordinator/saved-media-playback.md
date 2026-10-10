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
    "limits": "Reviewed prepare_playback's exact-revision admission, owner discards and sweep before copying, unchanged-copy reuse, receipt-level recheck, removal after a cancellation or inactive coordinator, and that it runs on the ScenarioPreview lane without network, job transitions or claims, as the sixth preview lane command beside the maintenance-only pass. Unit tests use synthetic receipts and real workers offline.",
    "sources": {
      "scenario/core/jobs/coordinator.py": "bc0d07c4dc83ad352e26876ec33b71b21f26e6f6f70e96c0f71e20bedf7b7d7b",
      "scenario/core/jobs/results.py": "f6a9702a09824cb28c46d99cfa1a37fa194d64ba2ad1c830bf11884e1b66d31f",
      "scenario/core/jobs/playback.py": "234d2e58b7d0ebfd595b5409bad223e6d524052f2809433bbd752c69300e54c6",
      "scenario/core/jobs/workers.py": "49194c6957c52b431b4bb18c73a2595bdc85d130552f7b393bc0f8883a3f391c",
      "tests/unit/test_playback.py": "316d50e43fd1e04fe672a03637059985426bd37c0b6741d8492e3b6bee3fa9b0"
    }
  }
}
---

# Playback copy command on the preview lane

Evidence for [the canonical guide](../../JOB_COORDINATOR.md).
