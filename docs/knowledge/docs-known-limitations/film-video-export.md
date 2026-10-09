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
    "base_revision": "fb699b8555f7cee62147794516cc7aaa224864f7",
    "limits": "Limitation wording reviewed against the export primitive: session commands exist without native/MCP controls, verification strength depends on ffprobe and Blender builds without H.264/AAC cannot export. The case-study bundle is absent. Builds lacking H.264/AAC encoders are detected only when the render child fails. Re-reviewed after the placeholder pin, free-space and cancellation checks and the distinct-file media budget; the limitation wording is unchanged. Re-reviewed after the inactive-session delivery guard; the limitation wording is unchanged.",
    "sources": {
      "scenario/blender/film_export_worker.py": "2579da4238e9d16aaeae43e48787b8ecec5a8ea12590945e6b3933e4d17ed22a",
      "scenario/blender/job_session.py": "35f3181e2c6f9be8f0d4ca1c18b6cf46d2d0e04bc0d2c6790c8d86ea206c5942",
      "scenario/blender/local_capture.py": "e0a07cda6bf8806368e7676d3fbbb3eaedc98cf62de8c76859e0e7091abcc50a",
      "scenario/core/jobs/local_export.py": "3fe9dec68501ab40b6e292d41d4b62f54fd7049d4d47fdcde95feeb744c0e4a7",
      "scenario/core/jobs/local_render.py": "8f21c27164761dd37053e5e6a06625ec6ac7b9efaf505b51527c10e4380df315",
      "scenario/core/jobs/mp4_inspection.py": "8a2be638990a79e15f5b112f32dcadde91aa2bbf6e2742c4451e9c7513103417",
      "tests/unit/test_local_export.py": "884432f51c50a8c7956528fc90bfc5c55307a97661606fbc25e3b8188a27bbec"
    }
  }
}
---

Source evidence for [the canonical guide](../../KNOWN_LIMITATIONS.md).
