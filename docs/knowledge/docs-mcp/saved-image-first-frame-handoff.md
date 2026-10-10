---
{
  "type": "Evidence",
  "id": "docs-mcp.saved-image-first-frame-handoff",
  "title": "Render Video first frame from a saved image",
  "description": "MCP purpose video_first_frame, its status field and render_form provenance.",
  "evidence": {
    "path": "docs/MCP.md",
    "scope": "saved-image-first-frame-handoff",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed prepare_result_application purpose video_first_frame: it requires a nonempty asset_id, calls runtime.prepare_first_frame_application with the context check and returns kind, lane, model_id, input, input_label, sent_as, reason, asset_id, file, replaces_first_frame_path, enables_first_frame and mode reuse_asset without reuse, with the route note first in note, making no request. apply_result_application routes the approval through ModelJobs.apply_saved_result and _finish_recovery; status first_frame reports bound or failed with scene, input, asset_id, undo_recorded and error. render_form inspect reports source_result (request_id, asset_id and saved from first_frame_handoff.saved_source) and first_frame_route from render_lanes.first_frame_route, and keeps an empty first_frame_path. job_status lists use_first_frame and its description maps it to this purpose. The generated reference table was regenerated with tools/gen_mcp_docs.py. Unit tests cover the PNG, JPEG and WebP signature helper and the MCP-only descriptor. Ten installed tests in test_first_frame_handoff cover: offering for downloaded PNG, JPEG and WebP colour results and not for EXR, normal maps, undownloaded results or prompt jobs; inert MCP preparation with no request, form or saved-job change; binding with the asset, scope, asset, kind and provenance markers, an empty first_frame_path, an enabled first frame, price invalidation, no upload work and no private path in the slot; request bodies for a first-frame image input the schema lets go with the clip, a Minimax-style firstFrameImage input and an image array where the frame orders first; a schema worded like Seedance 2.0 Fast, whose review reports sent_as reference_image with its reason and note and whose bound frame orders first in referenceImages with the clip kept and no image input in the request or dry-run body; the dry-run quote body; single use and an occupied slot; refusals for a pending upload slot, an occupied single-file input, a full array, a model without an image input, an unloaded schema without a model read and another scene; a changed model, chosen file, enabled state or reference list, undo or load invalidation and a retired context before apply; scene, form and slot changes during verification; tampered bytes before and after verification and a mislabelled container; Prompt Spark using the bound frame; a later chosen file, disabling and removal; and a blend saved uncompressed without the private result path, reopened under the same project and refused under another. A reference form test covers provenance dropped by a saved-upload attachment. Installed tests used synthetic SDK transport and ran in the full suite on macOS arm64 Blender 5.1.2 only. No native control exists in this change, so no desktop interaction, dialog, thumbnail, desktop undo step from the maintenance pump, other OS, DPI or Blender version is claimed. A paid Seedance 2.0 Fast run with a handed-off frame in the image input and the scene clip was accepted, then failed because an image and reference images or videos aren't allowed together; no paid run has used a first frame sent as a reference image. Re-checked 2026-10-10: the handoff target is the shared render_lanes.first_frame_target, so a model whose input descriptions exclude its first frame with the clip input receives the frame as image 1 of its reference-image array, and params.Schema.exclusive file-input pairs are refused by shared validation before any quote; a setting described as exclusive is not refused.",
    "sources": {
      "scenario/mcp/tools_scenario.py": "aec3eb343134655b437721bcecc6504e8cb7ef5013bf8c8ddfb8bf2d111e12fc",
      "scenario/blender/render_commands.py": "1fa0f892d8b5d867a164cfed57b642bfb7c884f913a4333c04af715d74547c41",
      "scenario/blender/model_jobs.py": "fcd51b54adfdc215e2fafda7267914ef3d6a800093f48f60cf1f140b6b048dea",
      "scenario/blender/first_frame_handoff.py": "cc5e5bb5ea7d9778cc535409a9ecbc15564217b0bffb9c68a54d4a2b6b3aa9f9",
      "scenario/blender/runtime.py": "0a371030d406343469b9decdb549a0085429e251b46f2211e4cc2f4841f62e1f",
      "scenario/core/ui/saved_job_actions.py": "e9f143bc0b13abd87595a526d4d1702506e229c4c209987932586103c70867bc",
      "tests/blender/test_first_frame_handoff.py": "ef4a1f10b13233402920f7eb8e30d70f9f4d976bd74d7bfceb58c77d27dd3e44",
      "tests/unit/test_saved_job_actions.py": "6fec69e9f92ef092c7dcff4e7bb131e889c8f716c19abb726156de71f4d6b4aa",
      "scenario/blender/render_lanes.py": "c644c891cb6d4e4a92b7bead7b5274592adfad943bca2b9257d9f745301b1782"
    }
  }
}
---

# Render Video first frame from a saved image

Evidence for [the canonical document](../../MCP.md).
