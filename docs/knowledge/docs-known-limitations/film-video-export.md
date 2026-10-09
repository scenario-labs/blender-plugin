---
{
  "type": "Evidence",
  "id": "docs-known-limitations.film-video-export",
  "title": "Owned offline Film video export",
  "evidence": {
    "path": "docs/KNOWN_LIMITATIONS.md",
    "scope": "film-video-export",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Limitation wording reviewed against the export primitive: session commands exist without native/MCP controls, verification strength depends on ffprobe and Blender builds without H.264/AAC cannot export. The case-study bundle is absent. Builds lacking H.264/AAC encoders are detected only when the render child fails.",
    "sources": {
      "scenario/blender/film_export_worker.py": "1db3f5daf6f8f202fc631a7f1fa927c494c5a3b6fb40eb7e0dfba2c087dafda2",
      "scenario/blender/job_session.py": "6eadb9ccb81a2a5c570980160ba9d20e5072136cccd5de71c6538920645bf11c",
      "scenario/blender/local_capture.py": "0273dc52526b0805491eef982cc37708a4f80e8d2518f48de43d1babde52b2a2",
      "scenario/core/jobs/local_export.py": "244d39066b8da9af7fd365e04313b54de46732bafbb0167a82111b4d142d4f79",
      "scenario/core/jobs/local_render.py": "3d6172f16877deb9397bd4057c934af05acac3e762e3e9d94eb7ac495561da6c",
      "scenario/core/jobs/mp4_inspection.py": "daaf36bdc305f1735f1fea471c621537298fbffc4963657209489a89505ce041",
      "tests/unit/test_local_export.py": "3f0453957fa751f6ab9344eb0cc2e8ce05b47a7c979a681ec498a511c25aba3e"
    }
  }
}
---

Source evidence for [the canonical guide](../../KNOWN_LIMITATIONS.md).
