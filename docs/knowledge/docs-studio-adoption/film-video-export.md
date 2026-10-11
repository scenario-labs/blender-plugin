---
{
  "type": "Evidence",
  "id": "docs-studio-adoption.film-video-export",
  "title": "Owned offline Film video export",
  "evidence": {
    "path": "docs/STUDIO_ADOPTION.md",
    "scope": "film-video-export",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-11",
    "base_revision": "1d86f53d3489b23f2447be69cb589140e2f3ba64",
    "limits": "Records that the MP4 export is first-party code using Blender's built-in FFmpeg with optional ffprobe, not an adaptation of Studio film_export.py, and that the Studio case-study bundle remains separate. No Studio source was imported. Re-reviewed after destination-policy and error-wording changes; the adoption statement is unchanged. Re-reviewed after the review fixes; still first-party code and the adoption statement is unchanged. Re-reviewed after the inactive-session delivery test was added; the adoption statement is unchanged. Re-reviewed after the rebase onto 72723f02, whose native test registry adds two unrelated modules; the adoption statement is unchanged. Re-reviewed after the even default size and bounded export shutdown; still first-party code and the adoption statement is unchanged. Re-reviewed after the rebase onto 1d86f53d, whose native test registry adds three unrelated modules; still first-party code and the adoption statement is unchanged.",
    "sources": {
      "scenario/blender/film_export_worker.py": "2579da4238e9d16aaeae43e48787b8ecec5a8ea12590945e6b3933e4d17ed22a",
      "scenario/blender/local_capture.py": "d1d3a5bde72ca1f61bf879fbc971bbca59d344e31a6a5c96e42558148537a43d",
      "scenario/core/jobs/local_export.py": "222a920e32cef1bc861fb3c0d2e641c67e61f40cbe1b03af591c1bff8e0b60e4",
      "scenario/core/jobs/local_render.py": "8f21c27164761dd37053e5e6a06625ec6ac7b9efaf505b51527c10e4380df315",
      "scenario/core/jobs/mp4_inspection.py": "8a2be638990a79e15f5b112f32dcadde91aa2bbf6e2742c4451e9c7513103417",
      "tests/blender/run_all.py": "13dd9acde4cbaa95722afe08b87d7c0aa438f828c95fbb344eefea0770e66157",
      "tests/blender/test_film_export_primitive.py": "4f2603a3f7eeec9202263efa4ba7707ab9a0751cd4fa8c848ea954bbe828d33b",
      "tests/unit/test_local_export.py": "e9fc2544f802edf5d9ec472b5cf243a4dec9e3a5b52fe22256a1b90110d656d1",
      "tests/unit/test_mp4_inspection.py": "9de87e15ae3891c43b5b56918ad9c99d5451cf5a2625c0f460a290404cb9b945"
    }
  }
}
---

Source evidence for [the canonical guide](../../STUDIO_ADOPTION.md).
