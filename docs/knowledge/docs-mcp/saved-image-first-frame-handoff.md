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
    "limits": "Reviewed prepare_result_application purpose video_first_frame: it requires a nonempty asset_id, calls runtime.prepare_first_frame_application with the context check and returns kind, lane, model_id, input, asset_id, file, replaces_first_frame_path, enables_first_frame and mode reuse_asset without reuse, making no request. apply_result_application routes the approval through ModelJobs.apply_saved_result and _finish_recovery; status first_frame reports bound or failed with scene, input, asset_id, undo_recorded and error. render_form inspect reports source_result (request_id, asset_id and saved from first_frame_handoff.saved_source) and keeps an empty first_frame_path. job_status lists use_first_frame and its description maps it to this purpose. The generated reference table was regenerated with tools/gen_mcp_docs.py. Unit tests cover the PNG, JPEG and WebP signature helper and the MCP-only descriptor. Nine installed tests in test_first_frame_handoff cover: offering for downloaded PNG, JPEG and WebP colour results and not for EXR, normal maps, undownloaded results or prompt jobs; inert MCP preparation with no request, form or saved-job change; binding with the asset, scope, asset, kind and provenance markers, an empty first_frame_path, an enabled first frame, price invalidation, no upload work and no private path in the slot; request bodies for a Seedance-style image input, a Minimax-style firstFrameImage input and an image array where the frame orders first; the dry-run quote body; single use and an occupied slot; refusals for a pending upload slot, an occupied single-file input, a full array, a model without an image input, an unloaded schema without a model read and another scene; a changed model, chosen file, enabled state or reference list, undo or load invalidation and a retired context before apply; scene, form and slot changes during verification; tampered bytes before and after verification and a mislabelled container; Prompt Spark using the bound frame; a later chosen file, disabling and removal; and a blend saved uncompressed without the private result path, reopened under the same project and refused under another. A reference form test covers provenance dropped by a saved-upload attachment. Installed tests used synthetic SDK transport and ran in the full suite on macOS arm64 Blender 5.1.2 only. No native control exists in this change, so no desktop interaction, dialog, thumbnail, desktop undo step from the maintenance pump, other OS, DPI or Blender version is claimed. No paid Render Video run has used a handed-off frame.",
    "sources": {
      "scenario/mcp/tools_scenario.py": "78997d23290c801cdf6926dc4d53d125b2dcc045c39cbcaad505150affeb008f",
      "scenario/blender/render_commands.py": "185662bd502e111dfba9c4fbbbafad6b6f5ba52ad251b82f529a8bdea98f308e",
      "scenario/blender/model_jobs.py": "fcd51b54adfdc215e2fafda7267914ef3d6a800093f48f60cf1f140b6b048dea",
      "scenario/blender/first_frame_handoff.py": "d58cacd56de6d1f687f154f883b999af4dc2a745c40a2a76c5a3fd326e2e815e",
      "scenario/blender/runtime.py": "0a371030d406343469b9decdb549a0085429e251b46f2211e4cc2f4841f62e1f",
      "scenario/core/ui/saved_job_actions.py": "e9f143bc0b13abd87595a526d4d1702506e229c4c209987932586103c70867bc",
      "tests/blender/test_first_frame_handoff.py": "5d3d77f046195b59880f6f9fe917d7bae3f1ae5e417a0f8dbc185b448c6fd7d4",
      "tests/unit/test_saved_job_actions.py": "6fec69e9f92ef092c7dcff4e7bb131e889c8f716c19abb726156de71f4d6b4aa"
    }
  }
}
---

# Render Video first frame from a saved image

Evidence for [the canonical document](../../MCP.md).
