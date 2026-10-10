---
{
  "type": "Evidence",
  "id": "docs-sdk-adoption.saved-image-first-frame-handoff",
  "title": "No new operation for the first-frame handoff",
  "description": "The handoff places an existing asset ID in the existing quote and submission path.",
  "evidence": {
    "path": "docs/SDK_ADOPTION.md",
    "scope": "saved-image-first-frame-handoff",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed that the handoff adds no SDKAdapter method or raw request: generation.build_request sends ASSET references by asset ID and the shared quote uses SDKAdapter.estimate_model, which calls generate.with_raw_response.run_model with dry_run true through the configured zero-retry client. A free dry run on 2026-10-10 with the developer test credentials (reads and dryRun estimates only, no submission, no ipDetection) used SDKAdapter.estimate_model with a generated PNG asset ID as the first frame of model_bytedance-seedance-2-0 and model_minimax-h3 plus a saved video; both returned a quote equal to the same request without the frame, and an unknown asset ID returned HTTP 404. The sanitized record is in the pull request; raw responses and identifiers are not committed. Installed tests used synthetic SDK transport and ran in the full suite on macOS arm64 Blender 5.1.2 only. No native control exists in this change, so no desktop interaction, dialog, thumbnail, desktop undo step from the maintenance pump, other OS, DPI or Blender version is claimed. No paid Render Video run has used a handed-off frame.",
    "sources": {
      "scenario/blender/first_frame_handoff.py": "d58cacd56de6d1f687f154f883b999af4dc2a745c40a2a76c5a3fd326e2e815e",
      "scenario/blender/generation.py": "6f73c4ba35ceb97097d1356b2267c5b2b7a2a7105b6900d0376d2604f9e9de8f",
      "scenario/core/api/sdk_adapter.py": "aa638824ce7af67c9b70d12b759f361ab88f41cb0bc7f39213f1ce1d3e8d39ff",
      "tests/blender/test_first_frame_handoff.py": "5d3d77f046195b59880f6f9fe917d7bae3f1ae5e417a0f8dbc185b448c6fd7d4"
    }
  }
}
---

# No new operation for the first-frame handoff

Evidence for [the canonical document](../../SDK_ADOPTION.md).
