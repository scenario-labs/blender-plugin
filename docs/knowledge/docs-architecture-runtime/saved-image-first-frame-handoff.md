---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.saved-image-first-frame-handoff",
  "title": "Saved image first-frame handoff",
  "description": "Runtime map entries for the MCP first-frame handoff as a claimless form binding.",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "scope": "saved-image-first-frame-handoff",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed that the handoff reuses the saved asset ID with no upload or stored file path, that render requests accept an uploaded or handed-off first frame through render_references.first_frame_enabled and require_uploaded, and that JobSession.verified_result consumes the verification without an application claim, so ModelJobs leaves the job state and local_applications unchanged. No native control exists. Unit tests cover the PNG, JPEG and WebP signature helper and the MCP-only descriptor. Nine installed tests in test_first_frame_handoff cover: offering for downloaded PNG, JPEG and WebP colour results and not for EXR, normal maps, undownloaded results or prompt jobs; inert MCP preparation with no request, form or saved-job change; binding with the asset, scope, asset, kind and provenance markers, an empty first_frame_path, an enabled first frame, price invalidation, no upload work and no private path in the slot; request bodies for a Seedance-style image input, a Minimax-style firstFrameImage input and an image array where the frame orders first; the dry-run quote body; single use and an occupied slot; refusals for a pending upload slot, an occupied single-file input, a full array, a model without an image input, an unloaded schema without a model read and another scene; a changed model, chosen file, enabled state or reference list, undo or load invalidation and a retired context before apply; scene, form and slot changes during verification; tampered bytes before and after verification and a mislabelled container; Prompt Spark using the bound frame; a later chosen file, disabling and removal; and a blend saved uncompressed without the private result path, reopened under the same project and refused under another. A reference form test covers provenance dropped by a saved-upload attachment. Installed tests used synthetic SDK transport and ran in the full suite on macOS arm64 Blender 5.1.2 only. No native control exists in this change, so no desktop interaction, dialog, thumbnail, desktop undo step from the maintenance pump, other OS, DPI or Blender version is claimed. No paid Render Video run has used a handed-off frame.",
    "sources": {
      "scenario/blender/first_frame_handoff.py": "d58cacd56de6d1f687f154f883b999af4dc2a745c40a2a76c5a3fd326e2e815e",
      "scenario/blender/model_jobs.py": "fcd51b54adfdc215e2fafda7267914ef3d6a800093f48f60cf1f140b6b048dea",
      "scenario/blender/job_session.py": "fc196b52049308278d50e25f9208edcbef3a872b9398f02af50b12dfe8e76ff2",
      "scenario/blender/render_references.py": "0f5cf2596e96aed0c8cc8a87d0940c6d2c493005621202ab04838ce82a6a2ff6",
      "tests/blender/test_first_frame_handoff.py": "5d3d77f046195b59880f6f9fe917d7bae3f1ae5e417a0f8dbc185b448c6fd7d4"
    }
  }
}
---

# Saved image first-frame handoff

Evidence for [the canonical document](../../architecture/runtime.md).
