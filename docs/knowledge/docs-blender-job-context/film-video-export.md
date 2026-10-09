---
{
  "type": "Evidence",
  "id": "docs-blender-job-context.film-video-export",
  "title": "Owned offline Film video export",
  "evidence": {
    "path": "docs/BLENDER_JOB_CONTEXT.md",
    "scope": "film-video-export",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Inspected JobSession export admission, drain flagging, delivery without scene resolution, cancellation, retirement and shutdown ordering. Installed tests cover owned-thread delivery, mid-render retirement and copy-only re-publish. Local macOS arm64 runs of the installed export module pass on Blender 5.0.1, 5.1.2 and 5.2.1, including a real child export verified by Blender's decode check and by an installed ffprobe; Linux/Windows evidence comes from CI. No human playback, desktop interaction or native/MCP control is established.",
    "sources": {
      "scenario/blender/job_session.py": "96ed0e4825912df5de7dd939c8e963f7846e268326e256441e6c2e618801c55c",
      "scenario/core/jobs/coordinator.py": "08cfc053a4b27cac03e4002dab7429de06516ccdfeec9d1243a84e3414e7ba1d",
      "scenario/core/jobs/workers.py": "beb81e0452ad08b1691feebbf20a558b2c60c098ca28114d5255b4073208755d",
      "tests/blender/test_film_export_primitive.py": "90d538a6f230357096923a7c8b6c7af40487b5c1a44683dfa610cd6f8a79e21a",
      "tests/unit/test_local_export.py": "e941073573fed89af84a19ff91a15d890a7af36b93896fe0e4a03c696fe325af"
    }
  }
}
---

Source evidence for [the canonical guide](../../BLENDER_JOB_CONTEXT.md).
