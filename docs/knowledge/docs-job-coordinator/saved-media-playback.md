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
    "limits": "Reviewed prepare_playback's exact-revision admission, owner discards and sweep before copying, unchanged-copy reuse, receipt-level recheck, removal after a cancellation or inactive coordinator, and that it runs on the ScenarioPreview lane without network, job transitions or claims, as the sixth preview lane command beside the maintenance-only pass. Unit tests use synthetic receipts and real workers offline. Re-checked on 2026-10-12 after the rebase onto main at 4bd0061d, not a full re-review: since the previous review main changed coordinator.py (inference-only cancellation, trained-model route checks before quoting, Film export, upload restart, splat preparation and asset organization reviews), results.py (untransformed original downloads, saving the declared OpenEXR original of an image result instead of its preview, and splat import preparation) and workers.py (the Film export slot, upload restart, splat preparation and queued asset organization reviews); none of these changes touch the playback copy, its lane command, the waveform controller or their descriptors, so the claims above still hold and these sources' fingerprints are the rebased files'; the review date and base revision are unchanged.",
    "sources": {
      "scenario/core/jobs/coordinator.py": "6c4f07b6244d219ce18e64341f80ee9a1f46f59d1d064c7eed219cb6565833f0",
      "scenario/core/jobs/results.py": "dc521e8bb414a4803962688a27b44d01f6ceb8eeb7fddff785ce63b5b5839c84",
      "scenario/core/jobs/playback.py": "234d2e58b7d0ebfd595b5409bad223e6d524052f2809433bbd752c69300e54c6",
      "scenario/core/jobs/workers.py": "2f4c97160d61cc7f5e299f7bdc33fc047422ee96469f966d33f30a2d43d09439",
      "tests/unit/test_playback.py": "316d50e43fd1e04fe672a03637059985426bd37c0b6741d8492e3b6bee3fa9b0"
    }
  }
}
---

# Playback copy command on the preview lane

Evidence for [the canonical guide](../../JOB_COORDINATOR.md).
