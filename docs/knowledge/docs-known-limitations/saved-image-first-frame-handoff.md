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
    "limits": "Reviewed the stated limits against the code: the handoff exists through the native scenario.use_saved_first_frame control and local MCP, stores no file path so render_lanes._draw_first_frame has no thumbnail for it, and records an undo step only when Blender allows one from the maintenance pump. The earlier dry-run claim is corrected: a free dry run resolves the asset ID (HTTP 404 for an unknown ID) but priced a Seedance first frame sent with the scene clip, a combination the service refuses only after accepting the job; the sanitized record is in the pull request without identifiers. params.Schema.exclusive (file-input pairs only), render_lanes.first_frame_target and shared validation implement the stated routing and refusal of a first frame with reference images or videos; the input-exclusivity topic covers settings, other lanes and the payload audit. Unit tests cover the PNG, JPEG and WebP signature helper and the native descriptor: one control per projected asset, numbered over every saved asset, none without a projection, and a reuse action on applied jobs. Sixteen installed tests in test_first_frame_handoff cover: offering for downloaded PNG, JPEG and WebP colour results and not for EXR, normal maps, undownloaded results or prompt jobs; inert MCP preparation with no request, form or saved-job change; binding with the asset, scope, asset, kind and provenance markers, an empty first_frame_path, an enabled first frame, price invalidation, no upload work and no private path in the slot; request bodies for a first-frame image input the schema lets go with the clip, a Minimax-style firstFrameImage input and an image array where the frame orders first; a schema worded like Seedance 2.0 Fast, whose review reports sent_as reference_image with its reason and note and whose bound frame orders first in referenceImages with the clip kept and no image input in the request or dry-run body; the dry-run quote body; single use and an occupied slot; refusals for a pending upload slot, an occupied single-file input, a full array, a model without an image input, an unloaded schema without a model read and another scene; a changed model, chosen file, enabled state or reference list, undo or load invalidation and a retired context before apply; scene, form and slot changes during verification; tampered bytes before and after verification and a mislabelled container; Prompt Spark using the bound frame; a later chosen file, disabling and removal; and a blend saved uncompressed without the private result path, reopened under the same project and refused under another; and, for the native control, buttons drawn through job_recovery.draw_controls only for the projected colour stills (a normal map in the same job gets none) without store reads, the exact dialog lines with fixed lines within 59 characters, cancel discarding the approval, refusal reasons and the retired-connection message without an approval, an MCP-prepared approval consumed once through scenario.use_saved_first_frame, the read-only From a saved result line that edited or absent provenance does not draw, and memfile Undo/Redo of the binding with undo enabled in the installed runner's window. A reference form test covers provenance dropped by a saved-upload attachment. Installed tests used synthetic SDK transport and ran in the full suite on macOS arm64 Blender 5.1.2 only. The native control has installed tests only: no desktop interaction, screenshot, focus, DPI, small window, thumbnail, other OS or other Blender version is claimed, and whether the maintenance-pump timer records the undo step on the desktop is unproven on Blender 5.0, 5.1 and 5.2. A paid Seedance 2.0 Fast run with a handed-off frame in the image input and the scene clip was accepted, then failed because an image and reference images or videos aren't allowed together; no paid run has used a first frame sent as a reference image. Re-checked 2026-10-10 after a new installed test_render_lanes test for style capacity with a first frame sent to referenceImages: the stated limits above are unchanged.",
    "sources": {
      "scenario/blender/first_frame_handoff.py": "cc5e5bb5ea7d9778cc535409a9ecbc15564217b0bffb9c68a54d4a2b6b3aa9f9",
      "scenario/blender/render_lanes.py": "0624d276a1039dae4361edd995e5de2a704d80ea84e8b8c7c5273779ee505200",
      "scenario/blender/model_jobs.py": "96621235ce3f0c227b6a80648e1835cd501b6d79ec71610d54e458e545cb16ac",
      "scenario/core/ui/saved_job_actions.py": "f360aa25c33a2bb37889c559a824357946e5644bf6fe786dd937c5bd4e1ba8de",
      "scenario/core/api/sdk_adapter.py": "aa638824ce7af67c9b70d12b759f361ab88f41cb0bc7f39213f1ce1d3e8d39ff",
      "tests/blender/test_first_frame_handoff.py": "ed9908d4541b89051ea64fdbcea51ac0fc9c74486e491bd09b45083047d0fba5",
      "scenario/blender/job_recovery.py": "012d4a61956de59aa057de3fa2d77c5290e95bccb09519e71de334fad88659ce",
      "tests/blender/test_result_actions.py": "3ce294d7ef49195ac612d99f977571c460c1a0f0eccb992275ad12b6554a52ec",
      "scenario/core/schema/params.py": "c94572f3737be87f1f419fb082664b6abe2ade2eca344ba22de589734dae85bb",
      "tests/blender/test_render_lanes.py": "7210d1d3f4b2af9b7c3d3c8100a137d1c1b8e1050207a833118e506d3eb8e421",
      "tests/unit/test_model_payload_validation.py": "c6316ccd6b9e9869e23173172c92162447168fa5e2cd4359cc94491cc448b9cf",
      "tools/audit_payloads.py": "bc72f41c8aaabaa2554dad87aea6c8bf9368b54a2d1626ec0e80622f6ba76063"
    }
  }
}
---

# First-frame handoff limits

Evidence for [the canonical document](../../KNOWN_LIMITATIONS.md).
