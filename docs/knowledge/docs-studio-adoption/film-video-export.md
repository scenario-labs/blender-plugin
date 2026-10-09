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
    "limits": "Records that the MP4 export is first-party code using Blender's built-in FFmpeg with optional ffprobe, not an adaptation of Studio film_export.py, and that the Studio case-study bundle remains separate. No Studio source was imported.",
    "sources": {
      "scenario/blender/film_export_worker.py": "3078e5770af2245c84690a2dff7509aa235ed053052da04e64cd2ef4426ad04f",
      "scenario/blender/local_capture.py": "79391e7f3eb1f59c07bc948ec267841ce4ef682159437aae64b9b03b21fc6dd7",
      "scenario/core/jobs/local_export.py": "ca449fe8eb3969af94534488bfadd3789c98985205dc421225431398c4a81164",
      "scenario/core/jobs/local_render.py": "3d6172f16877deb9397bd4057c934af05acac3e762e3e9d94eb7ac495561da6c",
      "scenario/core/jobs/mp4_inspection.py": "daaf36bdc305f1735f1fea471c621537298fbffc4963657209489a89505ce041",
      "tests/blender/run_all.py": "76114be12bc10852c9ba6c434552618d44cc840fc5adf6e9bafa49226682ebd6",
      "tests/blender/test_film_export_primitive.py": "90d538a6f230357096923a7c8b6c7af40487b5c1a44683dfa610cd6f8a79e21a",
      "tests/unit/test_local_export.py": "e941073573fed89af84a19ff91a15d890a7af36b93896fe0e4a03c696fe325af",
      "tests/unit/test_mp4_inspection.py": "9de87e15ae3891c43b5b56918ad9c99d5451cf5a2625c0f460a290404cb9b945"
    }
  }
}
---

Source evidence for [the canonical guide](../../STUDIO_ADOPTION.md).
