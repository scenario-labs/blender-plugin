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
    "limits": "Records that the MP4 export is first-party code using Blender's built-in FFmpeg with optional ffprobe, not an adaptation of Studio film_export.py, and that the Studio case-study bundle remains separate. No Studio source was imported. Re-reviewed after destination-policy and error-wording changes; the adoption statement is unchanged. Re-reviewed after the review fixes; still first-party code and the adoption statement is unchanged. Re-reviewed after the inactive-session delivery test was added; the adoption statement is unchanged. Re-reviewed after the rebase onto 72723f02, whose native test registry adds two unrelated modules; the adoption statement is unchanged. Re-reviewed after the even default size and bounded export shutdown; still first-party code and the adoption statement is unchanged. Re-reviewed after the rebase onto 1d86f53d, whose native test registry adds three unrelated modules; still first-party code and the adoption statement is unchanged. Re-reviewed after the blocked-export test began driving reaper ticks; the change is a first-party test and the adoption statement is unchanged. Rechecked on 2026-10-13 after the shared installed-tool lookup: ffmpeg and ffprobe are now found by scenario/core/jobs/installed_tools.py (PATH first, then fixed macOS and Linux install folders; Windows uses PATH only) in media_probe.probe_tool, local_render.media_tools, local_export verification and film_export.verifier, and tests fake that lookup instead of shutil.which. This topic's claims are unchanged. Only the test_film_export_primitive.py and test_local_export.py fingerprints were refreshed; the review date and base revision are unchanged.",
    "sources": {
      "scenario/blender/film_export_worker.py": "2579da4238e9d16aaeae43e48787b8ecec5a8ea12590945e6b3933e4d17ed22a",
      "scenario/blender/local_capture.py": "d1d3a5bde72ca1f61bf879fbc971bbca59d344e31a6a5c96e42558148537a43d",
      "scenario/core/jobs/local_export.py": "222a920e32cef1bc861fb3c0d2e641c67e61f40cbe1b03af591c1bff8e0b60e4",
      "scenario/core/jobs/local_render.py": "8f21c27164761dd37053e5e6a06625ec6ac7b9efaf505b51527c10e4380df315",
      "scenario/core/jobs/mp4_inspection.py": "8a2be638990a79e15f5b112f32dcadde91aa2bbf6e2742c4451e9c7513103417",
      "tests/blender/run_all.py": "13dd9acde4cbaa95722afe08b87d7c0aa438f828c95fbb344eefea0770e66157",
      "tests/blender/test_film_export_primitive.py": "88394b5c3c9ad6e2d4b4466197b6a39d71db3a1526bdb9de91042f8dcdad8a90",
      "tests/unit/test_local_export.py": "741bc8623f1d26a7b19a5639500d0fb3649889de7a066101d39f4b46f8f332c8",
      "tests/unit/test_mp4_inspection.py": "4c6fad6decccf554c110784c6a268e1686e686e934648faee9547450b9d743c9"
    }
  }
}
---

Source evidence for [the canonical guide](../../STUDIO_ADOPTION.md).
