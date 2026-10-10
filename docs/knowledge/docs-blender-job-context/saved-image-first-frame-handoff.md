---
{
  "type": "Evidence",
  "id": "docs-blender-job-context.saved-image-first-frame-handoff",
  "title": "Saved image to Render Video first frame",
  "description": "Offering, review, verification and binding of a saved image as the Render Video first frame.",
  "evidence": {
    "path": "docs/BLENDER_JOB_CONTEXT.md",
    "scope": "saved-image-first-frame-handoff",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed ModelJobs.actions offering use_first_frame for ready, apply_failed and applied jobs with a downloaded PNG, JPEG or WebP result whose texture role is absent or base, under the existing command, receipt, claim and 128-application gates; control() refuses it. prepare_first_frame_application reads no file, starts no request and changes no form: it checks the revision, scope, asset, approval capacity, selected scene and first_frame_handoff.target (loaded schema, render_references.target image input, no first-frame slot, input capacity) and binds the job, asset, receipt digest, captured scene and form key, model, input, chosen file and enabled state. _apply_first_frame consumes it once, rechecks the record, destination and form, then queues verify_results. bind consumes the completion through JobSession.verified_result without a claim, rehashes the receipt file (O_NOFOLLOW regular file, at most 128 MiB) and checks its container with image_signature_matches, rechecks scene and form, and adds one ASSET slot with scope, asset, kind and _RESULT provenance, clears first_frame_path, enables the first frame and marks the estimate dirty, removing the slot and restoring the path and flag on failure; it records an undo step only when mesh_result_application._undo_enabled allows. Failures pause the job with a status first_frame entry; the job state and local_applications are unchanged. render_references.first_frame_enabled accepts the asset slot without a file; render_prompt_jobs then uses it for video Spark. saved_job_actions.MCP_ONLY makes native descriptors skip the action. Unit tests cover the PNG, JPEG and WebP signature helper and the MCP-only descriptor. Nine installed tests in test_first_frame_handoff cover: offering for downloaded PNG, JPEG and WebP colour results and not for EXR, normal maps, undownloaded results or prompt jobs; inert MCP preparation with no request, form or saved-job change; binding with the asset, scope, asset, kind and provenance markers, an empty first_frame_path, an enabled first frame, price invalidation, no upload work and no private path in the slot; request bodies for a Seedance-style image input, a Minimax-style firstFrameImage input and an image array where the frame orders first; the dry-run quote body; single use and an occupied slot; refusals for a pending upload slot, an occupied single-file input, a full array, a model without an image input, an unloaded schema without a model read and another scene; a changed model, chosen file, enabled state or reference list, undo or load invalidation and a retired context before apply; scene, form and slot changes during verification; tampered bytes before and after verification and a mislabelled container; Prompt Spark using the bound frame; a later chosen file, disabling and removal; and a blend saved uncompressed without the private result path, reopened under the same project and refused under another. A reference form test covers provenance dropped by a saved-upload attachment. Installed tests used synthetic SDK transport and ran in the full suite on macOS arm64 Blender 5.1.2 only. No native control exists in this change, so no desktop interaction, dialog, thumbnail, desktop undo step from the maintenance pump, other OS, DPI or Blender version is claimed. No paid Render Video run has used a handed-off frame.",
    "sources": {
      "scenario/blender/first_frame_handoff.py": "d58cacd56de6d1f687f154f883b999af4dc2a745c40a2a76c5a3fd326e2e815e",
      "scenario/blender/model_jobs.py": "fcd51b54adfdc215e2fafda7267914ef3d6a800093f48f60cf1f140b6b048dea",
      "scenario/blender/job_session.py": "fc196b52049308278d50e25f9208edcbef3a872b9398f02af50b12dfe8e76ff2",
      "scenario/blender/render_references.py": "0f5cf2596e96aed0c8cc8a87d0940c6d2c493005621202ab04838ce82a6a2ff6",
      "scenario/blender/reference_form.py": "da7dd52526ea89c4871d791963fb84ba3432200f34b85c0e856abd5f8d100889",
      "scenario/blender/render_commands.py": "185662bd502e111dfba9c4fbbbafad6b6f5ba52ad251b82f529a8bdea98f308e",
      "scenario/blender/runtime.py": "0a371030d406343469b9decdb549a0085429e251b46f2211e4cc2f4841f62e1f",
      "scenario/core/ui/saved_job_actions.py": "e9f143bc0b13abd87595a526d4d1702506e229c4c209987932586103c70867bc",
      "scenario/core/jobs/result_metadata.py": "088354aff1317747cbed7270114714bd2106773b57a0fccad73836c4c6ab3baf",
      "scenario/blender/render_prompt_jobs.py": "5789166b017b45e9a56e5390ccc8ce7b9d374e03932c080dee1a189ff08a5edd",
      "tests/blender/test_first_frame_handoff.py": "5d3d77f046195b59880f6f9fe917d7bae3f1ae5e417a0f8dbc185b448c6fd7d4",
      "tests/blender/test_reference_form.py": "fed7cac0dd659b3de7cf86569530ccfe615a4da66f72b2a929d74d785183d888",
      "tests/unit/test_saved_job_actions.py": "6fec69e9f92ef092c7dcff4e7bb131e889c8f716c19abb726156de71f4d6b4aa",
      "tests/unit/test_result_metadata.py": "d4f4036235a01b6108d5926ec6ce4ff224ce50ed536ff7b2788fb574e6abf658"
    }
  }
}
---

# Saved image to Render Video first frame

Evidence for [the canonical document](../../BLENDER_JOB_CONTEXT.md).
