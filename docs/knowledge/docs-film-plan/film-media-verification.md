---
{
  "type": "Evidence",
  "id": "docs-film-plan.film-media-verification",
  "title": "Receipt-bound Film media preparation",
  "evidence": {
    "path": "docs/FILM_PLAN.md",
    "scope": "film-media-verification",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-07",
    "base_revision": "04f434d3ed1375d5a4d4669cb25508d0b74fc0f3",
    "limits": "Inspected the local receipt-bound media command, shared worker cancellation/admission, exact timing observations, saved-source rechecks and guarded session delivery. No SDK call, new store, download, upload, quote or scene mutation. Optional installed ffprobe measures container metadata, not full decode or human media quality. Model files must be downloaded and upload staging retained. Active UI/MCP draft review, quote integration, final assembly/export and live/release acceptance remain separate. This record covers only the media preparation topic, not other guide claims. M4A upload MIME audio/m4a and container MIME audio/mp4 both use the same forced MOV demuxer and receipt-verified private copy, covered by offline probe regressions. Pending or failed model-result downloads report an explicit download-first diagnostic before file verification or ffprobe. Three unit regressions cover remote success, downloading and failed downloads without mutation or network I/O.",
    "sources": {
      "scenario/core/jobs/media_probe.py": "b663e46c2e79411fe4fdbcd11f00f5cad07ad083692c8814b06c892387be7360",
      "scenario/core/jobs/film_media.py": "a3eb437f59768cd6abd7eb7ca9efb7300607fb5c0ee0ea19cf49cf355148e1a0",
      "scenario/core/jobs/film_finishing.py": "c069872429651a3f333a828e5f13f3be7f8c5e893acf5548f646d73406be1a06",
      "scenario/core/jobs/coordinator.py": "30ce016cda224073c794a9ef115aba343fa002aa244e027f3895838b94bfa947",
      "scenario/core/jobs/results.py": "d1e9ae96786d9bfaf92f8e1eddc5a0ca467a3b6e834e99f0c4633ffb4d32c15f",
      "scenario/core/jobs/uploads.py": "1d5319f979d0ed7f6210325c58ed2b13f8cff3ba8deabccedc9f8045e98b4df8",
      "scenario/core/jobs/upload_sources.py": "5beb6a3a8a5c4ab696e6a8aff78426c4b6615b9256599a59fbad30ac56cc388e",
      "scenario/core/jobs/workers.py": "3e36131961d4440f8cd04084994d05f6061773df834cb84cfced2a892be50474",
      "scenario/core/jobs/local_render.py": "e1b66441cffa68baa1c3ab5a5045c11a0ec183a15e17a46bdced50306c9fb930",
      "scenario/blender/job_session.py": "2a1f6bc5468db94de66fbc0f582a7589016de4409cb3722fce791a7ce87dbe78",
      "tests/unit/test_media_probe.py": "72efffd4d1a9b61c1963d0b5ee3a100bd02d2936b3f8a42e422f46fa91e8d14c",
      "tests/unit/test_film_media.py": "b974f5865e38a8f3358cdfc093877cd21cb028fcd9aed39c524cca4a438d6bc3",
      "tests/unit/test_job_workers.py": "f5210455f75ae2144c4e3dda971c1dca9dc8693691e10e5c067af5381250f7ad",
      "tests/blender/test_film_finishing.py": "808e55b63f968d551385d71bbbdb3fb174ed486c4288469ed8860e2a08beaebe"
    }
  }
}
---

Source evidence for [the canonical guide](../../FILM_PLAN.md).
