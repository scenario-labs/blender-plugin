---
{
  "type": "Evidence",
  "id": "docs-architecture-blender.film-video-export",
  "title": "Owned offline Film video export",
  "evidence": {
    "path": "docs/architecture/blender.md",
    "scope": "film-video-export",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Checked that bpy access stays in the main-thread snapshot and the standalone child worker, that rendering, verification and publishing run in bpy-free core code on the owned export thread, and that the working file, scene and frame are unchanged. Local macOS arm64 runs of the installed export module pass on Blender 5.0.1, 5.1.2 and 5.2.1, including a real child export verified by Blender's decode check and by an installed ffprobe; Linux/Windows evidence comes from CI. No human playback, desktop interaction or native/MCP control is established.",
    "sources": {
      "scenario/blender/film_export_worker.py": "3078e5770af2245c84690a2dff7509aa235ed053052da04e64cd2ef4426ad04f",
      "scenario/blender/job_session.py": "96ed0e4825912df5de7dd939c8e963f7846e268326e256441e6c2e618801c55c",
      "scenario/blender/local_capture.py": "79391e7f3eb1f59c07bc948ec267841ce4ef682159437aae64b9b03b21fc6dd7",
      "scenario/core/jobs/coordinator.py": "08cfc053a4b27cac03e4002dab7429de06516ccdfeec9d1243a84e3414e7ba1d",
      "scenario/core/jobs/local_export.py": "ca449fe8eb3969af94534488bfadd3789c98985205dc421225431398c4a81164",
      "scenario/core/jobs/local_render.py": "3d6172f16877deb9397bd4057c934af05acac3e762e3e9d94eb7ac495561da6c",
      "scenario/core/jobs/mp4_inspection.py": "daaf36bdc305f1735f1fea471c621537298fbffc4963657209489a89505ce041",
      "scenario/core/jobs/workers.py": "beb81e0452ad08b1691feebbf20a558b2c60c098ca28114d5255b4073208755d",
      "tests/blender/run_all.py": "76114be12bc10852c9ba6c434552618d44cc840fc5adf6e9bafa49226682ebd6",
      "tests/blender/test_film_export_primitive.py": "90d538a6f230357096923a7c8b6c7af40487b5c1a44683dfa610cd6f8a79e21a",
      "tests/unit/test_local_export.py": "e941073573fed89af84a19ff91a15d890a7af36b93896fe0e4a03c696fe325af",
      "tests/unit/test_mp4_inspection.py": "9de87e15ae3891c43b5b56918ad9c99d5451cf5a2625c0f460a290404cb9b945"
    }
  }
}
---

Source evidence for [the canonical guide](../../architecture/blender.md).
