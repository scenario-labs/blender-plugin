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
    "limits": "Reviewed the stated limits against the code: the handoff exists only through local MCP (saved_job_actions.MCP_ONLY hides it natively), stores no file path so render_lanes._draw_first_frame has no thumbnail for it, and records an undo step only when Blender allows one from the maintenance pump. The earlier dry-run claim is corrected: a free dry run resolves the asset ID (HTTP 404 for an unknown ID) but priced a Seedance first frame sent with the scene clip, a combination the service refuses only after accepting the job; the sanitized record is in the pull request without identifiers. params.Schema.exclusive, render_lanes.first_frame_target and shared validation implement the stated rule, and tools/audit_payloads.py reports exclusivity wording the parser does not recognize. Unit tests cover the PNG, JPEG and WebP signature helper and the MCP-only descriptor. Ten installed tests in test_first_frame_handoff cover: offering for downloaded PNG, JPEG and WebP colour results and not for EXR, normal maps, undownloaded results or prompt jobs; inert MCP preparation with no request, form or saved-job change; binding with the asset, scope, asset, kind and provenance markers, an empty first_frame_path, an enabled first frame, price invalidation, no upload work and no private path in the slot; request bodies for a first-frame image input the schema lets go with the clip, a Minimax-style firstFrameImage input and an image array where the frame orders first; a schema worded like Seedance 2.0 Fast, whose review reports sent_as reference_image with its reason and note and whose bound frame orders first in referenceImages with the clip kept and no image input in the request or dry-run body; the dry-run quote body; single use and an occupied slot; refusals for a pending upload slot, an occupied single-file input, a full array, a model without an image input, an unloaded schema without a model read and another scene; a changed model, chosen file, enabled state or reference list, undo or load invalidation and a retired context before apply; scene, form and slot changes during verification; tampered bytes before and after verification and a mislabelled container; Prompt Spark using the bound frame; a later chosen file, disabling and removal; and a blend saved uncompressed without the private result path, reopened under the same project and refused under another. A reference form test covers provenance dropped by a saved-upload attachment. Installed tests used synthetic SDK transport and ran in the full suite on macOS arm64 Blender 5.1.2 only. No native control exists in this change, so no desktop interaction, dialog, thumbnail, desktop undo step from the maintenance pump, other OS, DPI or Blender version is claimed. A paid Seedance 2.0 Fast run with a handed-off frame in the image input and the scene clip was accepted, then failed because an image and reference images or videos aren't allowed together; no paid run has used a first frame sent as a reference image.",
    "sources": {
      "scenario/blender/first_frame_handoff.py": "cc5e5bb5ea7d9778cc535409a9ecbc15564217b0bffb9c68a54d4a2b6b3aa9f9",
      "scenario/blender/render_lanes.py": "c644c891cb6d4e4a92b7bead7b5274592adfad943bca2b9257d9f745301b1782",
      "scenario/blender/model_jobs.py": "fcd51b54adfdc215e2fafda7267914ef3d6a800093f48f60cf1f140b6b048dea",
      "scenario/core/ui/saved_job_actions.py": "e9f143bc0b13abd87595a526d4d1702506e229c4c209987932586103c70867bc",
      "scenario/core/api/sdk_adapter.py": "aa638824ce7af67c9b70d12b759f361ab88f41cb0bc7f39213f1ce1d3e8d39ff",
      "tests/blender/test_first_frame_handoff.py": "ef4a1f10b13233402920f7eb8e30d70f9f4d976bd74d7bfceb58c77d27dd3e44",
      "scenario/core/schema/params.py": "17055f6619bef706452ec7282d7ba2121fbf90735a9cd2cfc6a26fa5a52bd889",
      "tests/blender/test_render_lanes.py": "6bb71ad049498cd2a942c231c6876bacbd8d284ec580c4eb4e4fc06a7d3f0aaf",
      "tests/unit/test_model_payload_validation.py": "6267928cda81698a1674db4f923b4606813ba8cf690ca19b817f3bd4aef70969",
      "tools/audit_payloads.py": "4fa342a36dbaca1bce72308f41019fd8d4053713095b1f5bb821f9c90582a8cd"
    }
  }
}
---

# First-frame handoff limits

Evidence for [the canonical document](../../KNOWN_LIMITATIONS.md).
