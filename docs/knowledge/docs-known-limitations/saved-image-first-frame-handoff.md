---
{
  "type": "Evidence",
  "id": "docs-known-limitations.saved-image-first-frame-handoff",
  "title": "First-frame handoff limits",
  "description": "Dry-run evidence and remaining limits of the MCP first-frame handoff.",
  "evidence": {
    "path": "docs/KNOWN_LIMITATIONS.md",
    "scope": "saved-image-first-frame-handoff",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the stated limits against the code: the handoff exists only through local MCP (saved_job_actions.MCP_ONLY hides it natively), stores no file path so render_lanes._draw_first_frame has no thumbnail for it, and records an undo step only when Blender allows one from the maintenance pump. The dry-run claim (2026-10-10, developer test scope, Seedance 2.0 and Minimax H3 accepted through SDKAdapter.estimate_model, unknown ID rejected with HTTP 404) comes from a private probe whose sanitized outcome is in the pull request. Unit tests cover the PNG, JPEG and WebP signature helper and the MCP-only descriptor. Nine installed tests in test_first_frame_handoff cover: offering for downloaded PNG, JPEG and WebP colour results and not for EXR, normal maps, undownloaded results or prompt jobs; inert MCP preparation with no request, form or saved-job change; binding with the asset, scope, asset, kind and provenance markers, an empty first_frame_path, an enabled first frame, price invalidation, no upload work and no private path in the slot; request bodies for a Seedance-style image input, a Minimax-style firstFrameImage input and an image array where the frame orders first; the dry-run quote body; single use and an occupied slot; refusals for a pending upload slot, an occupied single-file input, a full array, a model without an image input, an unloaded schema without a model read and another scene; a changed model, chosen file, enabled state or reference list, undo or load invalidation and a retired context before apply; scene, form and slot changes during verification; tampered bytes before and after verification and a mislabelled container; Prompt Spark using the bound frame; a later chosen file, disabling and removal; and a blend saved uncompressed without the private result path, reopened under the same project and refused under another. A reference form test covers provenance dropped by a saved-upload attachment. Installed tests used synthetic SDK transport and ran in the full suite on macOS arm64 Blender 5.1.2 only. No native control exists in this change, so no desktop interaction, dialog, thumbnail, desktop undo step from the maintenance pump, other OS, DPI or Blender version is claimed. No paid Render Video run has used a handed-off frame.",
    "sources": {
      "scenario/blender/first_frame_handoff.py": "d58cacd56de6d1f687f154f883b999af4dc2a745c40a2a76c5a3fd326e2e815e",
      "scenario/blender/render_lanes.py": "ccf9178bc587f97a79c7d663311f0d3622f8d19e32ede912000b4198cc7d43aa",
      "scenario/blender/model_jobs.py": "fcd51b54adfdc215e2fafda7267914ef3d6a800093f48f60cf1f140b6b048dea",
      "scenario/core/ui/saved_job_actions.py": "e9f143bc0b13abd87595a526d4d1702506e229c4c209987932586103c70867bc",
      "scenario/core/api/sdk_adapter.py": "aa638824ce7af67c9b70d12b759f361ab88f41cb0bc7f39213f1ce1d3e8d39ff",
      "tests/blender/test_first_frame_handoff.py": "5d3d77f046195b59880f6f9fe917d7bae3f1ae5e417a0f8dbc185b448c6fd7d4"
    }
  }
}
---

# First-frame handoff limits

Evidence for [the canonical document](../../KNOWN_LIMITATIONS.md).
