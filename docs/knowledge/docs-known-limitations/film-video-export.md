---
{
  "type": "Evidence",
  "id": "docs-known-limitations.film-video-export",
  "title": "Owned offline Film video export",
  "evidence": {
    "path": "docs/KNOWN_LIMITATIONS.md",
    "scope": "film-video-export",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-11",
    "base_revision": "1d86f53d3489b23f2447be69cb589140e2f3ba64",
    "limits": "Limitation wording reviewed against the export primitive: session commands exist without native/MCP controls, verification strength depends on ffprobe and Blender builds without H.264/AAC cannot export. The case-study bundle is absent. Builds lacking H.264/AAC encoders are detected only when the render child fails. Re-reviewed after the placeholder pin, free-space and cancellation checks and the distinct-file media budget; the limitation wording is unchanged. Re-reviewed after the inactive-session delivery guard; the limitation wording is unchanged. Re-reviewed after the rebase onto 72723f02, whose merged changes to the session, coordinator, workers and native test registry add Film review controls, upload retirement on deactivation, a restart-upload command, inference-only cancellation and two native test modules; export admission, delivery, retirement, shutdown ordering and thread ownership are unchanged, and the native export module stays registered. The guide's export wording was reconciled with the merged Film review controls: review scenes now have native/MCP controls, while export still has none. Re-reviewed after the even default size and bounded export shutdown; the limitation text remains accurate. Re-reviewed after the rebase onto 1d86f53d, whose session changes add the saved-result preview scheduler; the resolution releases its copies only after the export thread stops as well, and the limitation text remains accurate. Rechecked on 2026-10-13 after the shared installed-tool lookup: ffmpeg and ffprobe are now found by scenario/core/jobs/installed_tools.py (PATH first, then fixed macOS and Linux install folders; Windows uses PATH only) in media_probe.probe_tool, local_render.media_tools, local_export verification and film_export.verifier, and tests fake that lookup instead of shutil.which. This topic's claims are unchanged. Only the test_local_export.py fingerprint was refreshed; the review date and base revision are unchanged.",
    "sources": {
      "scenario/blender/film_export_worker.py": "2579da4238e9d16aaeae43e48787b8ecec5a8ea12590945e6b3933e4d17ed22a",
      "scenario/blender/job_session.py": "19e3964a7d15d913c4097f7802e765fc1b28b23c9f535716444535464cb062e8",
      "scenario/blender/local_capture.py": "d1d3a5bde72ca1f61bf879fbc971bbca59d344e31a6a5c96e42558148537a43d",
      "scenario/core/jobs/local_export.py": "222a920e32cef1bc861fb3c0d2e641c67e61f40cbe1b03af591c1bff8e0b60e4",
      "scenario/core/jobs/local_render.py": "8f21c27164761dd37053e5e6a06625ec6ac7b9efaf505b51527c10e4380df315",
      "scenario/core/jobs/mp4_inspection.py": "8a2be638990a79e15f5b112f32dcadde91aa2bbf6e2742c4451e9c7513103417",
      "tests/unit/test_local_export.py": "741bc8623f1d26a7b19a5639500d0fb3649889de7a066101d39f4b46f8f332c8"
    }
  }
}
---

Source evidence for [the canonical guide](../../KNOWN_LIMITATIONS.md).
