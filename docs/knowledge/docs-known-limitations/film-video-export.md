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
    "limits": "Limitation wording reviewed against the export primitive: session commands exist without native/MCP controls, verification strength depends on ffprobe and Blender builds without H.264/AAC cannot export. The case-study bundle is absent. Builds lacking H.264/AAC encoders are detected only when the render child fails. Re-reviewed after the placeholder pin, free-space and cancellation checks and the distinct-file media budget; the limitation wording is unchanged.",
    "sources": {
      "scenario/blender/film_export_worker.py": "2579da4238e9d16aaeae43e48787b8ecec5a8ea12590945e6b3933e4d17ed22a",
      "scenario/blender/job_session.py": "070652fa2d92e43b01989823ef4bd20bc43bc6559a131a43297afc9b3ce8a498",
      "scenario/blender/local_capture.py": "e0a07cda6bf8806368e7676d3fbbb3eaedc98cf62de8c76859e0e7091abcc50a",
      "scenario/core/jobs/local_export.py": "ef8b3ccafefa6e0f101dedc462732ee2be7d33489aa86b72876418c308eaabf3",
      "scenario/core/jobs/local_render.py": "8f21c27164761dd37053e5e6a06625ec6ac7b9efaf505b51527c10e4380df315",
      "scenario/core/jobs/mp4_inspection.py": "8a2be638990a79e15f5b112f32dcadde91aa2bbf6e2742c4451e9c7513103417",
      "tests/unit/test_local_export.py": "884432f51c50a8c7956528fc90bfc5c55307a97661606fbc25e3b8188a27bbec"
    }
  }
}
---

Source evidence for [the canonical guide](../../KNOWN_LIMITATIONS.md).
