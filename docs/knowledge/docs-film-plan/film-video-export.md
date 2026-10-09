---
{
  "type": "Evidence",
  "id": "docs-film-plan.film-video-export",
  "title": "Owned offline Film video export",
  "evidence": {
    "path": "docs/FILM_PLAN.md",
    "scope": "film-video-export",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Inspected the main-thread export snapshot (view-layer sync, blocked strip types, media stamps), specification bounds, offline child arguments and environment, built-in FFmpeg settings, bounded progress, container inspection, ffprobe and Blender decode verification, destination validation, exclusive placeholder, identity-checked publish, copy-only re-publish and session-owned thread ownership. Unit tests use synthetic MP4 boxes and simulated processes; the Blender fallback does not decode every frame or report pixel format. Local macOS arm64 runs of the installed export module pass on Blender 5.0.1, 5.1.2 and 5.2.1, including a real child export verified by Blender's decode check and by an installed ffprobe; Linux/Windows evidence comes from CI. No human playback, desktop interaction or native/MCP control is established. Destination names follow Python 3.13 ntpath.isreserved rules (checked against it locally) with Windows extended-prefix and macOS case-insensitive containment; the hidden partial file has a fixed-length name, so a 255-byte destination publishes. Reused snapshots are refused before hashing and staging or report OSErrors become path-free errors. A build lacking an H.264 or AAC encoder is not detected before rendering and was not exercised; it surfaces as the generic child failure.",
    "sources": {
      "scenario/blender/film_export_worker.py": "1db3f5daf6f8f202fc631a7f1fa927c494c5a3b6fb40eb7e0dfba2c087dafda2",
      "scenario/blender/job_session.py": "6eadb9ccb81a2a5c570980160ba9d20e5072136cccd5de71c6538920645bf11c",
      "scenario/blender/local_capture.py": "0273dc52526b0805491eef982cc37708a4f80e8d2518f48de43d1babde52b2a2",
      "scenario/core/jobs/coordinator.py": "58481d249c456139b8d228e7a91b3da4a6d0b03cfe0000e6ff53a5a27fc265f9",
      "scenario/core/jobs/local_export.py": "244d39066b8da9af7fd365e04313b54de46732bafbb0167a82111b4d142d4f79",
      "scenario/core/jobs/local_render.py": "3d6172f16877deb9397bd4057c934af05acac3e762e3e9d94eb7ac495561da6c",
      "scenario/core/jobs/mp4_inspection.py": "daaf36bdc305f1735f1fea471c621537298fbffc4963657209489a89505ce041",
      "scenario/core/jobs/workers.py": "fcfd589ac62e4a5c4eb97eda55c5a68ee0894cb16911c3b10ede65adf8820dc0",
      "tests/blender/run_all.py": "76114be12bc10852c9ba6c434552618d44cc840fc5adf6e9bafa49226682ebd6",
      "tests/blender/test_film_export_primitive.py": "47918d02540835724ef6acb93611b9170df5a9c58ae53b04f22903f37f69fd27",
      "tests/unit/test_local_export.py": "3f0453957fa751f6ab9344eb0cc2e8ce05b47a7c979a681ec498a511c25aba3e",
      "tests/unit/test_mp4_inspection.py": "9de87e15ae3891c43b5b56918ad9c99d5451cf5a2625c0f460a290404cb9b945"
    }
  }
}
---

Source evidence for [the canonical guide](../../FILM_PLAN.md).
