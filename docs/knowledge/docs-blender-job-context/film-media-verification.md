---
{
  "type": "Evidence",
  "id": "docs-blender-job-context.film-media-verification",
  "title": "Receipt-bound Film media preparation",
  "evidence": {
    "path": "docs/BLENDER_JOB_CONTEXT.md",
    "scope": "film-media-verification",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-05",
    "base_revision": "4589f22964cc9cf99e53ec37bb8c5dbe6948c96b",
    "limits": "Inspected the local receipt-bound media command, shared worker cancellation/admission, exact timing observations, saved-source rechecks and guarded session delivery. No SDK call, new store, download, upload, quote or scene mutation. Optional installed ffprobe measures container metadata, not full decode or human media quality. Model files must be downloaded and upload staging retained. Active UI/MCP draft review, quote integration, final assembly/export and live/release acceptance remain separate. This record covers only the media preparation topic, not other guide claims.",
    "sources": {
      "scenario/core/jobs/media_probe.py": "0444d851fa289856cc350e467f929e9c5490d966f56b420055d5e6ad1a0389f1",
      "scenario/core/jobs/film_media.py": "a3eb437f59768cd6abd7eb7ca9efb7300607fb5c0ee0ea19cf49cf355148e1a0",
      "scenario/core/jobs/film_finishing.py": "c069872429651a3f333a828e5f13f3be7f8c5e893acf5548f646d73406be1a06",
      "scenario/core/jobs/coordinator.py": "30ce016cda224073c794a9ef115aba343fa002aa244e027f3895838b94bfa947",
      "scenario/core/jobs/results.py": "660f379f25774d2e4fa3fd8e2d15f9577d75e4f4de7039423d5a6207a10522dc",
      "scenario/core/jobs/uploads.py": "1d5319f979d0ed7f6210325c58ed2b13f8cff3ba8deabccedc9f8045e98b4df8",
      "scenario/core/jobs/upload_sources.py": "5beb6a3a8a5c4ab696e6a8aff78426c4b6615b9256599a59fbad30ac56cc388e",
      "scenario/core/jobs/workers.py": "3e36131961d4440f8cd04084994d05f6061773df834cb84cfced2a892be50474",
      "scenario/core/jobs/local_render.py": "e1b66441cffa68baa1c3ab5a5045c11a0ec183a15e17a46bdced50306c9fb930",
      "scenario/blender/job_session.py": "2a1f6bc5468db94de66fbc0f582a7589016de4409cb3722fce791a7ce87dbe78",
      "tests/unit/test_media_probe.py": "c5079fa1c88c7732ad3a8425fcd3bbfd8ada7f57a4bac9e667fd50e6b9d32784",
      "tests/unit/test_film_media.py": "1f8e098fd38d32100ce22c42ddbaa23eb955731f6b2c96467a8bebde7ba3cfbd",
      "tests/unit/test_job_workers.py": "f5210455f75ae2144c4e3dda971c1dca9dc8693691e10e5c067af5381250f7ad",
      "tests/blender/test_film_finishing.py": "808e55b63f968d551385d71bbbdb3fb174ed486c4288469ed8860e2a08beaebe"
    }
  }
}
---

Source evidence for [the canonical guide](../../BLENDER_JOB_CONTEXT.md).
