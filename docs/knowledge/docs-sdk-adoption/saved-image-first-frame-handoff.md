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
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed that the handoff adds no SDKAdapter method or raw request: generation.build_request sends ASSET references by asset ID and the shared quote uses SDKAdapter.estimate_model, which calls generate.with_raw_response.run_model with dry_run true through the configured zero-retry client. A free dry run on 2026-10-10 with the developer test credentials (reads and dryRun estimates only, no submission, no ipDetection) used SDKAdapter.estimate_model with a generated PNG asset ID as the first frame of model_bytedance-seedance-2-0 and model_minimax-h3 plus a saved video; both returned a quote equal to the same request without the frame, and an unknown asset ID returned HTTP 404. That equal quote shows the dry run did not check the combination: a later paid Seedance 2.0 Fast job with a first frame and the scene clip was accepted, then failed. The shared form preparation (forms.prepare_run through params.validate_requirements with Schema.exclusive) now refuses two file inputs whose descriptions say they can't be combined before SDKAdapter.estimate_model or submission (settings described that way are not checked); no SDK method, raw request or pin changed, and this is local validation rather than an SDK gap. test_model_payload_validation covers the captured Seedance 2.0 schema refused by validate_parameters, prepare_run and SDKAdapter.estimate_model without a request, and the reference-image body sent once. The sanitized record is in the pull request; raw responses and identifiers are not committed. Installed tests used synthetic SDK transport and ran in the full suite on macOS arm64 Blender 5.1.2 only. No native control exists in this change, so no desktop interaction, dialog, thumbnail, desktop undo step from the maintenance pump, other OS, DPI or Blender version is claimed. A paid Seedance 2.0 Fast run with a handed-off frame in the image input and the scene clip was accepted, then failed because an image and reference images or videos aren't allowed together; no paid run has used a first frame sent as a reference image.",
    "sources": {
      "scenario/blender/first_frame_handoff.py": "cc5e5bb5ea7d9778cc535409a9ecbc15564217b0bffb9c68a54d4a2b6b3aa9f9",
      "scenario/blender/generation.py": "6a4cfa47b950e48488dd5bb5acd122d7310662934b68de7e1c2b089b1a7dbc6d",
      "scenario/core/api/sdk_adapter.py": "aa638824ce7af67c9b70d12b759f361ab88f41cb0bc7f39213f1ce1d3e8d39ff",
      "tests/blender/test_first_frame_handoff.py": "ef4a1f10b13233402920f7eb8e30d70f9f4d976bd74d7bfceb58c77d27dd3e44",
      "scenario/core/schema/params.py": "c94572f3737be87f1f419fb082664b6abe2ade2eca344ba22de589734dae85bb",
      "scenario/core/schema/forms.py": "ef906b4563ccbbd1862a6b8073ad9feb79b9cc1fc15c264caaa02bae30c6c098",
      "tests/unit/test_model_payload_validation.py": "c6316ccd6b9e9869e23173172c92162447168fa5e2cd4359cc94491cc448b9cf"
    }
  }
}
---

# No new operation for the first-frame handoff

Evidence for [the canonical document](../../SDK_ADOPTION.md).
