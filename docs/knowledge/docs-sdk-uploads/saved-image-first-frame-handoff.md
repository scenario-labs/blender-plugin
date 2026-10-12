---
{
  "type": "Evidence",
  "id": "docs-sdk-uploads.saved-image-first-frame-handoff",
  "title": "First frames that need no upload",
  "description": "A handed-off Render Video first frame reuses an existing asset without upload markers.",
  "evidence": {
    "path": "docs/SDK_UPLOADS.md",
    "scope": "saved-image-first-frame-handoff",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-11",
    "base_revision": "1d86f53d3489b23f2447be69cb589140e2f3ba64",
    "limits": "Reviewed that first_frame_handoff.bind writes source ASSET with the saved asset ID and the existing reference_form scope, asset and kind markers, no _MARKER upload marker and no file path, so no ReferenceUploads work starts and scope_error applies as for other scoped assets; reference_form.apply_attachment drops the _RESULT provenance when a saved upload replaces the slot. Unit tests cover the PNG, JPEG and WebP signature helper and the MCP-only descriptor. Ten installed tests in test_first_frame_handoff cover: offering for downloaded PNG, JPEG and WebP colour results and not for EXR, normal maps, undownloaded results or prompt jobs; inert MCP preparation with no request, form or saved-job change; binding with the asset, scope, asset, kind and provenance markers, an empty first_frame_path, an enabled first frame, price invalidation, no upload work and no private path in the slot; request bodies for a first-frame image input the schema lets go with the clip, a Minimax-style firstFrameImage input and an image array where the frame orders first; a schema worded like Seedance 2.0 Fast, whose review reports sent_as reference_image with its reason and note and whose bound frame orders first in referenceImages with the clip kept and no image input in the request or dry-run body; the dry-run quote body; single use and an occupied slot; refusals for a pending upload slot, an occupied single-file input, a full array, a model without an image input, an unloaded schema without a model read and another scene; a changed model, chosen file, enabled state or reference list, undo or load invalidation and a retired context before apply; scene, form and slot changes during verification; tampered bytes before and after verification and a mislabelled container; Prompt Spark using the bound frame; a later chosen file, disabling and removal; and a blend saved uncompressed without the private result path, reopened under the same project and refused under another. A reference form test covers provenance dropped by a saved-upload attachment. Installed tests used synthetic SDK transport and ran in the full suite on macOS arm64 Blender 5.1.2 only. No native control exists in this change, so no desktop interaction, dialog, thumbnail, desktop undo step from the maintenance pump, other OS, DPI or Blender version is claimed. A paid Seedance 2.0 Fast run with a handed-off frame in the image input and the scene clip was accepted, then failed because an image and reference images or videos aren't allowed together; no paid run has used a first frame sent as a reference image. Re-checked 2026-10-10: the handoff target is the shared render_lanes.first_frame_target, so a model whose input descriptions exclude its first frame with the clip input receives the frame as image 1 of its reference-image array, and params.Schema.exclusive pairs are refused by shared validation before any quote. Re-checked 2026-10-11 after restacking on main 72723f02: merged reference_form adds upload restart and the ABANDONED state for marked upload slots; a handoff slot carries no upload marker, so the claims above are unchanged. After the restack the installed tests passed again in the full native suite on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1, whose only failure (test_result_actions expecting Cancel generation on an unconfirmed remote job) also fails on main. Re-checked 2026-10-11 after restacking on #369, now on main 1d86f53d: merged reference_form routes workflow-lane saved uploads to workflow_uploads and counts workflow forms toward upload capacity; model-lane destination keys are unchanged and a handoff slot still carries no upload marker, so the claims above are unchanged. After this restack the installed tests passed again in the full native suite on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1, whose only failure is the known test_result_actions case expecting Cancel generation on an unconfirmed remote job.",
    "sources": {
      "scenario/blender/first_frame_handoff.py": "cc5e5bb5ea7d9778cc535409a9ecbc15564217b0bffb9c68a54d4a2b6b3aa9f9",
      "scenario/blender/reference_form.py": "f7b43fd7511e12168a7ec875410b619ad5e72b128cb5873dfcef8995f194e095",
      "scenario/blender/render_references.py": "4897d8fe89d4bfbd9e171392cfa88feff4fa6a35ba88c40e4f63158fdb93aa47",
      "tests/blender/test_first_frame_handoff.py": "91fa3b05e9a6bb44cf59072996c79d47a894adf8f1546ba6262d6c15d01c951c",
      "tests/blender/test_reference_form.py": "a86e6ef2d78061609cf1eab489a9682e1d0dd6131c4a47075bbceb306b1d5ec6",
      "scenario/blender/render_lanes.py": "c644c891cb6d4e4a92b7bead7b5274592adfad943bca2b9257d9f745301b1782"
    }
  }
}
---

# First frames that need no upload

Evidence for [the canonical document](../../SDK_UPLOADS.md).
