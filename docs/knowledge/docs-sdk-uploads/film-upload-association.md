---
{
  "type": "Evidence",
  "id": "docs-sdk-uploads.film-upload-association",
  "title": "Film upload association and scoped reference reuse",
  "evidence": {
    "path": "docs/SDK_UPLOADS.md",
    "scope": "film-upload-association",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-04",
    "base_revision": "4589f22964cc9cf99e53ec37bb8c5dbe6948c96b",
    "limits": "Local association of an already imported scoped upload with a Film task, using the existing coordinator, upload store, workers and JobSession. Schema 9 adds immutable reference metadata in the same job database, with atomic model/upload task namespace and supported-schema migration. Quotes recheck imported state/revision/source/asset and do not require cleaned staging bytes. Tests cover races, corruption, uncertain uploads, scope, source replacement, saved receipts and changed/repeated native delivery. No new upload mutation, SDK endpoint, raw fallback, file-transfer engine, production-state file, UI picker or MCP Film entry point. Existing upload/live permissions and media acceptance still apply. Native update rehearsal uses actual predecessor code with synthetic version metadata and does not prove public or published release acceptance.",
    "sources": {
      "scenario/core/jobs/store.py": "e183f93bbe72bbaf6c204238e4e46dba0b37cf9c4989256327b87a7e02612ec3",
      "scenario/core/jobs/film_tasks.py": "dea0522e39f9272d951275a00a04a16b69af9b2b05bb77afb70c0962ffaea1a6",
      "scenario/core/jobs/coordinator.py": "3dcf192150b0a661303ae04244d5ea8c37d30c7096ad068cd7ff6af038ecdad6",
      "scenario/core/jobs/workers.py": "d855d2ab93354354ae628765ec1740b486c0d5a8e8a95e554499c0f848fe50d5",
      "scenario/blender/job_session.py": "4df7f649e6d0f9b835a953cd1c4b00079b2d3c5528e25bf310f1412ff22a1728",
      "scenario/core/jobs/upload_store.py": "e5a609291095c112a00184d99795d8d21c177ddc6bc801a5c113bb489df27053",
      "tests/unit/test_film_uploads.py": "b2dc681a3a7dda8182b55ada0ec7d56686516095eac455760e86361d694b84b0",
      "tests/unit/test_job_store.py": "36a4e54b904fdc99717e4419498eeb4383321bfa9d351e986ada7a6801c63040",
      "tests/blender/test_film_uploads.py": "76596143176782f0b1431b7f01e25302dfc7332684718550f69d141884a62177",
      "tests/blender/test_job_store.py": "d2dc4386e7387e75eb8411647f7d5d5d3e69b532a22be402f2b6e8ba0127ae52",
      "tests/blender/package_update.py": "346332b3ffe7e60bee497838c74271bf8752931f3dae3362711a7b0dfc584cce"
    }
  }
}
---

Source evidence for [the canonical guide](../../SDK_UPLOADS.md).
