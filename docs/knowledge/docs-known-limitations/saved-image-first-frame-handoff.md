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
    "reviewed_at": "2026-10-11",
    "base_revision": "7fb15252f747f52db24f7e659f8d5048241f803e",
    "limits": "Reviewed the stated limits against the code: the handoff exists only through local MCP (saved_job_actions.MCP_ONLY hides it natively), stores no file path so render_lanes._draw_first_frame has no thumbnail for it, and records an undo step only when Blender allows one from the maintenance pump. The earlier dry-run claim is corrected: a free dry run resolves the asset ID (HTTP 404 for an unknown ID) but priced a Seedance first frame sent with the scene clip, a combination the service refuses only after accepting the job; the sanitized record is in the pull request without identifiers. params.Schema.exclusive (file-input pairs only), render_lanes.first_frame_target and shared validation implement the stated routing and refusal of a first frame with reference images or videos; the input-exclusivity topic covers settings, other lanes and the payload audit. Unit tests cover the PNG, JPEG and WebP signature helper and the MCP-only descriptor. Ten installed tests in test_first_frame_handoff cover: offering for downloaded PNG, JPEG and WebP colour results and not for EXR, normal maps, undownloaded results or prompt jobs; inert MCP preparation with no request, form or saved-job change; binding with the asset, scope, asset, kind and provenance markers, an empty first_frame_path, an enabled first frame, price invalidation, no upload work and no private path in the slot; request bodies for a first-frame image input the schema lets go with the clip, a Minimax-style firstFrameImage input and an image array where the frame orders first; a schema worded like Seedance 2.0 Fast, whose review reports sent_as reference_image with its reason and note and whose bound frame orders first in referenceImages with the clip kept and no image input in the request or dry-run body; the dry-run quote body; single use and an occupied slot; refusals for a pending upload slot, an occupied single-file input, a full array, a model without an image input, an unloaded schema without a model read and another scene; a changed model, chosen file, enabled state or reference list, undo or load invalidation and a retired context before apply; scene, form and slot changes during verification; tampered bytes before and after verification and a mislabelled container; Prompt Spark using the bound frame; a later chosen file, disabling and removal; and a blend saved uncompressed without the private result path, reopened under the same project and refused under another. A reference form test covers provenance dropped by a saved-upload attachment. Installed tests used synthetic SDK transport and ran in the full suite on macOS arm64 Blender 5.1.2 only. No native control exists in this change, so no desktop interaction, dialog, thumbnail, desktop undo step from the maintenance pump, other OS, DPI or Blender version is claimed. A paid Seedance 2.0 Fast run with a handed-off frame in the image input and the scene clip was accepted, then failed because an image and reference images or videos aren't allowed together; no paid run has used a first frame sent as a reference image. Re-checked 2026-10-10 after a new installed test_render_lanes test for style capacity with a first frame sent to referenceImages: the stated limits above are unchanged. Re-checked 2026-10-11 after restacking on main 72723f02: merged ModelJobs cancellation and progress, SDKAdapter asset organization writes and params undeclared conditional siblings leave the stated limits, the dry-run path and Schema.exclusive unchanged. After the restack the installed tests passed again in the full native suite on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1, whose only failure (test_result_actions expecting Cancel generation on an unconfirmed remote job) also fails on main. Re-checked 2026-10-11 after restacking on #369, now on main 7fb15252: merged World candidate projection in ModelJobs and saved_job_actions, and SDKAdapter original-asset reads, bulk previews, workflow decisions and the prepare_model guard that never targets a trained record, leave the stated limits, the dry-run path and Schema.exclusive unchanged. After this restack the installed tests passed again in the full native suite on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1, whose only failure is the known test_result_actions case expecting Cancel generation on an unconfirmed remote job.",
    "sources": {
      "scenario/blender/first_frame_handoff.py": "cc5e5bb5ea7d9778cc535409a9ecbc15564217b0bffb9c68a54d4a2b6b3aa9f9",
      "scenario/blender/render_lanes.py": "c644c891cb6d4e4a92b7bead7b5274592adfad943bca2b9257d9f745301b1782",
      "scenario/blender/model_jobs.py": "55304ebf9e94ea291a401b3266164896367b437f9c656781f7a64f340620e797",
      "scenario/core/ui/saved_job_actions.py": "5dea4ea6c75ee42aa5c2f309c0405a9e33cfa511fc99e7ead28c7f49ec5d1806",
      "scenario/core/api/sdk_adapter.py": "784ac9f7f7c071291086eef894a4bcb3d895e53b8b26a233efea2d119f395765",
      "tests/blender/test_first_frame_handoff.py": "ef4a1f10b13233402920f7eb8e30d70f9f4d976bd74d7bfceb58c77d27dd3e44",
      "scenario/core/schema/params.py": "9ac7ae09d361b0d7931c77e32efa7d2d4e06f9e7a51d608deaecfa4cc9ddf8ab",
      "tests/blender/test_render_lanes.py": "7210d1d3f4b2af9b7c3d3c8100a137d1c1b8e1050207a833118e506d3eb8e421",
      "tests/unit/test_model_payload_validation.py": "54bca0e711adc77e41ca66ce752c24fb46137f1040546f1f0f3d635beb5ef0e8",
      "tools/audit_payloads.py": "bc72f41c8aaabaa2554dad87aea6c8bf9368b54a2d1626ec0e80622f6ba76063"
    }
  }
}
---

# First-frame handoff limits

Evidence for [the canonical document](../../KNOWN_LIMITATIONS.md).
