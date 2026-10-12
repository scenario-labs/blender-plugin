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
    "limits": "Reviewed prepare_playback's exact-revision admission, owner discards and sweep before copying, unchanged-copy reuse, receipt-level recheck, removal after a cancellation or inactive coordinator, and that it runs on the ScenarioPreview lane without network, job transitions or claims, as the sixth preview lane command beside the maintenance-only pass. Unit tests use synthetic receipts and real workers offline. Re-checked on 2026-10-12 after the rebase onto main at 4bd0061d, not a full re-review: since the previous review main changed coordinator.py (inference-only cancellation, trained-model route checks before quoting, Film export, upload restart, splat preparation and asset organization reviews), results.py (untransformed original downloads, saving the declared OpenEXR original of an image result instead of its preview, and splat import preparation) and workers.py (the Film export slot, upload restart, splat preparation and queued asset organization reviews); none of these changes touch the playback copy, its lane command, the waveform controller or their descriptors, so the claims above still hold and these sources' fingerprints are the rebased files'; the review date and base revision are unchanged. Re-checked on 2026-10-12 for the credential-free system player launch, not a full re-review: playback.system_open now starts the system player itself, /usr/bin/open on macOS, xdg-open on Linux and other systems, and on Windows Blender's Python interpreter run with -I -S calling os.startfile, each with player_environment() and discarded output, instead of Blender's wm.path_open, whose bundled Blender 5.1.2 source (read in background Blender) calls os.startfile, open or xdg-open with Blender's own environment; the macOS open manual page states that opened applications inherit its environment; result_media tracks that launcher, pins its copy until it exits and reports a failed launch, and its abandoned-copy collection catches Exception rather than BaseException. this topic's claims cover the prepare_playback copy command, which is unchanged, and the shared env fixture of the playback unit tests is now a local fixture over the result preview tests' context manager. These sources' fingerprints are the changed files'; the review date and base revision are unchanged.",
    "sources": {
      "scenario/core/jobs/coordinator.py": "6c4f07b6244d219ce18e64341f80ee9a1f46f59d1d064c7eed219cb6565833f0",
      "scenario/core/jobs/results.py": "dc521e8bb414a4803962688a27b44d01f6ceb8eeb7fddff785ce63b5b5839c84",
      "scenario/core/jobs/playback.py": "45af1bda413c4a8a31128fff66473be163df84c0ace157da389c6031ddbae83d",
      "scenario/core/jobs/workers.py": "2f4c97160d61cc7f5e299f7bdc33fc047422ee96469f966d33f30a2d43d09439",
      "tests/unit/test_playback.py": "09c7c327ec0adfd7ef0dc711797eaa6430234cf05784fbd2a4f897231af894ba"
    }
  }
}
---

# Playback copy command on the preview lane

Evidence for [the canonical guide](../../JOB_COORDINATOR.md).
