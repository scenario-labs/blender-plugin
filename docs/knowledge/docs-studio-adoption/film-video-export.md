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
    "base_revision": "fb699b8555f7cee62147794516cc7aaa224864f7",
    "limits": "Records that the MP4 export is first-party code using Blender's built-in FFmpeg with optional ffprobe, not an adaptation of Studio film_export.py, and that the Studio case-study bundle remains separate. No Studio source was imported. Re-reviewed after destination-policy and error-wording changes; the adoption statement is unchanged. Re-reviewed after the review fixes; still first-party code and the adoption statement is unchanged. Re-reviewed after the inactive-session delivery test was added; the adoption statement is unchanged.",
    "sources": {
      "scenario/blender/film_export_worker.py": "2579da4238e9d16aaeae43e48787b8ecec5a8ea12590945e6b3933e4d17ed22a",
      "scenario/blender/local_capture.py": "e0a07cda6bf8806368e7676d3fbbb3eaedc98cf62de8c76859e0e7091abcc50a",
      "scenario/core/jobs/local_export.py": "3fe9dec68501ab40b6e292d41d4b62f54fd7049d4d47fdcde95feeb744c0e4a7",
      "scenario/core/jobs/local_render.py": "8f21c27164761dd37053e5e6a06625ec6ac7b9efaf505b51527c10e4380df315",
      "scenario/core/jobs/mp4_inspection.py": "8a2be638990a79e15f5b112f32dcadde91aa2bbf6e2742c4451e9c7513103417",
      "tests/blender/run_all.py": "76114be12bc10852c9ba6c434552618d44cc840fc5adf6e9bafa49226682ebd6",
      "tests/blender/test_film_export_primitive.py": "7e0da5ad1922ebabdee66341a3de22fd564654324544a24019e5c9e83c3e0444",
      "tests/unit/test_local_export.py": "884432f51c50a8c7956528fc90bfc5c55307a97661606fbc25e3b8188a27bbec",
      "tests/unit/test_mp4_inspection.py": "9de87e15ae3891c43b5b56918ad9c99d5451cf5a2625c0f460a290404cb9b945"
    }
  }
}
---

Source evidence for [the canonical guide](../../STUDIO_ADOPTION.md).
