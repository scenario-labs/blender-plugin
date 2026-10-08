---
{
  "type": "Evidence",
  "id": "docs-film-plan.film-media-verification",
  "title": "Receipt-bound Film media preparation",
  "evidence": {
    "path": "docs/FILM_PLAN.md",
    "scope": "film-media-verification",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-08",
    "base_revision": "2cff5f27132c51d42728427f588b928c3984836d",
    "limits": "Inspected the local receipt-bound media command, shared worker cancellation/admission, exact timing observations, saved-source rechecks and guarded session delivery. No SDK call, new store, download, upload, quote or scene mutation. Optional installed ffprobe measures container metadata, not full decode or human media quality. Model files must be downloaded and upload staging retained. Active UI/MCP draft review, quote integration, final assembly/export and live/release acceptance remain separate. This record covers only the media preparation topic, not other guide claims. M4A upload MIME audio/m4a and container MIME audio/mp4 both use the same forced MOV demuxer and receipt-verified private copy, covered by offline probe regressions. Pending or failed model-result downloads report an explicit download-first diagnostic before file verification or ffprobe. Three unit regressions cover remote success, downloading and failed downloads without mutation or network I/O. Unavailable average video frame rates remain unknown while verified duration still controls composition coverage; parsing, worker and installed-session regressions preserve duration checks and reject invalid reported rates without guessing a rate.",
    "sources": {
      "scenario/core/jobs/media_probe.py": "6db22b8cb051d6cabd6847b207d8380e181c80f28a5f50b2a987174bd9a95c7a",
      "scenario/core/jobs/film_media.py": "a3eb437f59768cd6abd7eb7ca9efb7300607fb5c0ee0ea19cf49cf355148e1a0",
      "scenario/core/jobs/film_finishing.py": "c069872429651a3f333a828e5f13f3be7f8c5e893acf5548f646d73406be1a06",
      "scenario/core/jobs/coordinator.py": "30ce016cda224073c794a9ef115aba343fa002aa244e027f3895838b94bfa947",
      "scenario/core/jobs/results.py": "d1e9ae96786d9bfaf92f8e1eddc5a0ca467a3b6e834e99f0c4633ffb4d32c15f",
      "scenario/core/jobs/uploads.py": "1d5319f979d0ed7f6210325c58ed2b13f8cff3ba8deabccedc9f8045e98b4df8",
      "scenario/core/jobs/upload_sources.py": "5beb6a3a8a5c4ab696e6a8aff78426c4b6615b9256599a59fbad30ac56cc388e",
      "scenario/core/jobs/workers.py": "3e36131961d4440f8cd04084994d05f6061773df834cb84cfced2a892be50474",
      "scenario/core/jobs/local_render.py": "e1b66441cffa68baa1c3ab5a5045c11a0ec183a15e17a46bdced50306c9fb930",
      "scenario/blender/job_session.py": "2a1f6bc5468db94de66fbc0f582a7589016de4409cb3722fce791a7ce87dbe78",
      "tests/unit/test_media_probe.py": "ca73cd0928ebd5438554123cb80c72187112838eb895fdd9a432d4fbb51fd847",
      "tests/unit/test_film_media.py": "689f4825ad303c42ab2059dfdc2a71f02713b071160e098a7829dee882478231",
      "tests/unit/test_job_workers.py": "f5210455f75ae2144c4e3dda971c1dca9dc8693691e10e5c067af5381250f7ad",
      "tests/blender/test_film_finishing.py": "5b76f182bc2cbc8d8645f0285411f119f68f492956fd3c9944e695211ea2dbe8"
    }
  }
}
---

Source evidence for [the canonical guide](../../FILM_PLAN.md).
