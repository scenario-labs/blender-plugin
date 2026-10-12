---
{
  "type": "Evidence",
  "id": "docs-sdk-adoption.saved-image-first-frame-handoff",
  "title": "No new operation for the first-frame handoff",
  "description": "The handoff places an existing asset ID in the existing quote and submission path.",
  "evidence": {
    "path": "docs/SDK_ADOPTION.md",
    "scope": "saved-image-first-frame-handoff",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "4ca693cb8f0e02a5c27c12d39bedbbc166b4e725",
    "limits": "Reviewed that the handoff adds no SDKAdapter method or raw request: generation.build_request sends ASSET references by asset ID and the shared quote uses SDKAdapter.estimate_model, which calls generate.with_raw_response.run_model with dry_run true through the configured zero-retry client. A free dry run on 2026-10-10 with the developer test credentials (reads and dryRun estimates only, no submission, no ipDetection) used SDKAdapter.estimate_model with a generated PNG asset ID as the first frame of model_bytedance-seedance-2-0 and model_minimax-h3 plus a saved video; both returned a quote equal to the same request without the frame, and an unknown asset ID returned HTTP 404. That equal quote shows the dry run did not check the combination: a later paid Seedance 2.0 Fast job with a first frame and the scene clip was accepted, then failed. The shared form preparation (forms.prepare_run through params.validate_requirements with Schema.exclusive) now refuses two file inputs whose descriptions say they can't be combined before SDKAdapter.estimate_model or submission (settings described that way are not checked); no SDK method, raw request or pin changed, and this is local validation rather than an SDK gap. test_model_payload_validation covers the captured Seedance 2.0 schema refused by validate_parameters, prepare_run and SDKAdapter.estimate_model without a request, and the reference-image body sent once. The sanitized record is in the pull request; raw responses and identifiers are not committed. Installed tests used synthetic SDK transport and ran in the full suite on macOS arm64 Blender 5.1.2 only. No native control exists in this change, so no desktop interaction, dialog, thumbnail, desktop undo step from the maintenance pump, other OS, DPI or Blender version is claimed. A paid Seedance 2.0 Fast run with a handed-off frame in the image input and the scene clip was accepted, then failed because an image and reference images or videos aren't allowed together; no paid run has used a first frame sent as a reference image. Re-checked 2026-10-11 after restacking on main 72723f02: merged SDKAdapter adds asset organization writes and keeps estimate_model on generate.with_raw_response.run_model with dry_run through the zero-retry client; merged params and forms accept undeclared conditional siblings, and generation keeps another scene's price pending instead of failed; Schema.exclusive refusal before quotes and the claims above are unchanged. After the restack the installed tests passed again in the full native suite on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1, whose only failure (test_result_actions expecting Cancel generation on an unconfirmed remote job) also fails on main. Re-checked 2026-10-11 after restacking on #369, now on main 1d86f53d: merged SDKAdapter adds prepare_model, which refuses a trained record as a target, original-asset reads and bulk previews, and estimate_model still quotes the prepared payload through generate.with_raw_response.run_model with dry_run through the zero-retry client; merged forms add LoRA route checks after shared validation, and generation shows their fixed refusal text; prepare_run still refuses Schema.exclusive pairs through validate_requirements before any quote, and the claims above are unchanged. After this restack the installed tests passed again in the full native suite on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1, whose only failure is the known test_result_actions case expecting Cancel generation on an unconfirmed remote job. Re-checked 2026-10-12 after restacking on #369, now on main 4ca693cb: merged SDKAdapter counts workflow loop nodes for estimate_workflow and keeps them on Estimate.loop_steps; estimate_model still quotes the prepared payload through generate.with_raw_response.run_model with dry_run through the zero-retry client, prepare_run still refuses Schema.exclusive pairs before any quote, and the claims above are unchanged. After this restack the installed tests passed in the full native suite on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 with no failures.",
    "sources": {
      "scenario/blender/first_frame_handoff.py": "cc5e5bb5ea7d9778cc535409a9ecbc15564217b0bffb9c68a54d4a2b6b3aa9f9",
      "scenario/blender/generation.py": "9ea7d7a562a5178fe0264bb125855bcbea64257d0e4a3c21fd77e006854bc73d",
      "scenario/core/api/sdk_adapter.py": "0add4688710b00326fc31381d028e42cd9b5415f84bd168f45b5a8434a48aa19",
      "tests/blender/test_first_frame_handoff.py": "ef4a1f10b13233402920f7eb8e30d70f9f4d976bd74d7bfceb58c77d27dd3e44",
      "scenario/core/schema/params.py": "9ac7ae09d361b0d7931c77e32efa7d2d4e06f9e7a51d608deaecfa4cc9ddf8ab",
      "scenario/core/schema/forms.py": "6c13428b31421d71aa28f2f8fd2c95c7594eaa31fcadd49fc92782c462e274f6",
      "tests/unit/test_model_payload_validation.py": "54bca0e711adc77e41ca66ce752c24fb46137f1040546f1f0f3d635beb5ef0e8"
    }
  }
}
---

# No new operation for the first-frame handoff

Evidence for [the canonical document](../../SDK_ADOPTION.md).
