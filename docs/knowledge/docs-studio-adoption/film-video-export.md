---
{
  "type": "Evidence",
  "id": "docs-studio-adoption.film-video-export",
  "title": "Owned offline Film video export",
  "evidence": {
    "path": "docs/STUDIO_ADOPTION.md",
    "scope": "film-video-export",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Records that the MP4 export is first-party code using Blender's built-in FFmpeg with optional ffprobe, not an adaptation of Studio film_export.py, and that the Studio case-study bundle remains separate. No Studio source was imported. Re-reviewed after destination-policy and error-wording changes; the adoption statement is unchanged.",
    "sources": {
      "scenario/blender/film_export_worker.py": "1db3f5daf6f8f202fc631a7f1fa927c494c5a3b6fb40eb7e0dfba2c087dafda2",
      "scenario/blender/local_capture.py": "0273dc52526b0805491eef982cc37708a4f80e8d2518f48de43d1babde52b2a2",
      "scenario/core/jobs/local_export.py": "244d39066b8da9af7fd365e04313b54de46732bafbb0167a82111b4d142d4f79",
      "scenario/core/jobs/local_render.py": "3d6172f16877deb9397bd4057c934af05acac3e762e3e9d94eb7ac495561da6c",
      "scenario/core/jobs/mp4_inspection.py": "daaf36bdc305f1735f1fea471c621537298fbffc4963657209489a89505ce041",
      "tests/blender/run_all.py": "76114be12bc10852c9ba6c434552618d44cc840fc5adf6e9bafa49226682ebd6",
      "tests/blender/test_film_export_primitive.py": "47918d02540835724ef6acb93611b9170df5a9c58ae53b04f22903f37f69fd27",
      "tests/unit/test_local_export.py": "3f0453957fa751f6ab9344eb0cc2e8ce05b47a7c979a681ec498a511c25aba3e",
      "tests/unit/test_mp4_inspection.py": "9de87e15ae3891c43b5b56918ad9c99d5451cf5a2625c0f460a290404cb9b945"
    }
  }
}
---

Source evidence for [the canonical guide](../../STUDIO_ADOPTION.md).
