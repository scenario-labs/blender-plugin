---
{
  "type": "Evidence",
  "id": "docs-user-guide.saved-image-first-frame-handoff",
  "title": "First frame from a saved image",
  "description": "User-facing description of the native and MCP first-frame handoff and its limits.",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "saved-image-first-frame-handoff",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed that local MCP prepare_result_application with purpose video_first_frame binds a downloaded PNG, JPEG or WebP saved result after apply_result_application, reuses its asset ID, starts no upload, stores no file path and invalidates the price, and that the sidebar and Studio saved-job controls draw Use as video first frame (N) only for the downloaded PNG, JPEG or WebP colour stills ModelJobs projects, open the scenario.use_saved_first_frame confirmation (scene, model, input, image, replaced file, enabled state, price invalidation, Use as first frame) and that the form then shows From a saved result without a thumbnail; Prompt Spark uses the bound frame. Unit tests cover the PNG, JPEG and WebP signature helper and the native descriptor: one control per projected asset, numbered over every saved asset, none without a projection, and a reuse action on applied jobs. Sixteen installed tests in test_first_frame_handoff cover: offering for downloaded PNG, JPEG and WebP colour results and not for EXR, normal maps, undownloaded results or prompt jobs; inert MCP preparation with no request, form or saved-job change; binding with the asset, scope, asset, kind and provenance markers, an empty first_frame_path, an enabled first frame, price invalidation, no upload work and no private path in the slot; request bodies for a first-frame image input the schema lets go with the clip, a Minimax-style firstFrameImage input and an image array where the frame orders first; a schema worded like Seedance 2.0 Fast, whose review reports sent_as reference_image with its reason and note and whose bound frame orders first in referenceImages with the clip kept and no image input in the request or dry-run body; the dry-run quote body; single use and an occupied slot; refusals for a pending upload slot, an occupied single-file input, a full array, a model without an image input, an unloaded schema without a model read and another scene; a changed model, chosen file, enabled state or reference list, undo or load invalidation and a retired context before apply; scene, form and slot changes during verification; tampered bytes before and after verification and a mislabelled container; Prompt Spark using the bound frame; a later chosen file, disabling and removal; and a blend saved uncompressed without the private result path, reopened under the same project and refused under another; and, for the native control, buttons drawn through job_recovery.draw_controls only for the projected colour stills (a normal map in the same job gets none) without store reads, the exact dialog lines with fixed lines within 59 characters, cancel discarding the approval, refusal reasons and the retired-connection message without an approval, an MCP-prepared approval consumed once through scenario.use_saved_first_frame, the read-only From a saved result line that edited or absent provenance does not draw, and memfile Undo/Redo of the binding with undo enabled in the installed runner's window. A reference form test covers provenance dropped by a saved-upload attachment. Installed tests used synthetic SDK transport and ran in the full suite on macOS arm64 Blender 5.1.2 only. The native control has installed tests only: no desktop interaction, screenshot, focus, DPI, small window, thumbnail, other OS or other Blender version is claimed, and whether the maintenance-pump timer records the undo step on the desktop is unproven on Blender 5.0, 5.1 and 5.2. A paid Seedance 2.0 Fast run with a handed-off frame in the image input and the scene clip was accepted, then failed because an image and reference images or videos aren't allowed together; no paid run has used a first frame sent as a reference image. Re-checked 2026-10-10: the handoff target is the shared render_lanes.first_frame_target, so a model whose input descriptions exclude its first frame with the clip input receives the frame as image 1 of its reference-image array, and params.Schema.exclusive file-input pairs are refused by shared validation before any quote; a setting described as exclusive is not refused.",
    "sources": {
      "scenario/mcp/tools_scenario.py": "aec3eb343134655b437721bcecc6504e8cb7ef5013bf8c8ddfb8bf2d111e12fc",
      "scenario/blender/first_frame_handoff.py": "cc5e5bb5ea7d9778cc535409a9ecbc15564217b0bffb9c68a54d4a2b6b3aa9f9",
      "scenario/core/ui/saved_job_actions.py": "f360aa25c33a2bb37889c559a824357946e5644bf6fe786dd937c5bd4e1ba8de",
      "tests/blender/test_first_frame_handoff.py": "ed9908d4541b89051ea64fdbcea51ac0fc9c74486e491bd09b45083047d0fba5",
      "scenario/blender/job_recovery.py": "012d4a61956de59aa057de3fa2d77c5290e95bccb09519e71de334fad88659ce",
      "scenario/blender/render_lanes.py": "0624d276a1039dae4361edd995e5de2a704d80ea84e8b8c7c5273779ee505200",
      "tests/blender/test_result_actions.py": "3ce294d7ef49195ac612d99f977571c460c1a0f0eccb992275ad12b6554a52ec",
      "scenario/blender/model_jobs.py": "96621235ce3f0c227b6a80648e1835cd501b6d79ec71610d54e458e545cb16ac",
      "scenario/blender/render_prompt_jobs.py": "5789166b017b45e9a56e5390ccc8ce7b9d374e03932c080dee1a189ff08a5edd"
    }
  }
}
---

# First frame from a saved image

Evidence for [the canonical document](../../USER_GUIDE.md).
