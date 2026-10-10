---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.saved-image-first-frame-handoff",
  "title": "Saved image first-frame handoff",
  "description": "Runtime map entries for the MCP first-frame handoff as a claimless form binding.",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "scope": "saved-image-first-frame-handoff",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed that the handoff reuses the saved asset ID with no upload or stored file path, that render requests accept an uploaded or handed-off first frame through render_references.first_frame_enabled and require_uploaded, and that JobSession.verified_result consumes the verification without an application claim, so ModelJobs leaves the job state and local_applications unchanged. The native scenario.use_saved_first_frame control in job_recovery prepares and applies the same approval through the runtime facades. Unit tests cover the PNG, JPEG and WebP signature helper and the native descriptor: one control per projected asset, numbered over every saved asset, none without a projection, and a reuse action on applied jobs. Seventeen installed tests in test_first_frame_handoff cover: offering for downloaded PNG, JPEG and WebP colour results and not for EXR, normal maps, undownloaded results or prompt jobs; inert MCP preparation with no request, form or saved-job change; binding with the asset, scope, asset, kind and provenance markers, an empty first_frame_path, an enabled first frame, price invalidation, no upload work and no private path in the slot; request bodies for a first-frame image input the schema lets go with the clip, a Minimax-style firstFrameImage input and an image array where the frame orders first; a schema worded like Seedance 2.0 Fast, whose review reports sent_as reference_image with its reason and note and whose bound frame orders first in referenceImages with the clip kept and no image input in the request or dry-run body; the dry-run quote body; single use and an occupied slot; refusals for a pending upload slot, an occupied single-file input, a full array, a model without an image input, an unloaded schema without a model read and another scene; a changed model, chosen file, enabled state or reference list, undo or load invalidation and a retired context before apply; scene, form and slot changes during verification; tampered bytes before and after verification and a mislabelled container; Prompt Spark using the bound frame; a later chosen file, disabling and removal; and a blend saved uncompressed without the private result path, reopened under the same project and refused under another; and, for the native control, buttons drawn through job_recovery.draw_controls only for the projected colour stills (a normal map in the same job gets none) without store reads, the exact dialog lines with fixed lines within 59 characters, cancel discarding the approval, refusal reasons and the retired-connection message without an approval, an MCP-prepared approval consumed once through scenario.use_saved_first_frame, the read-only From a saved result line that edited or absent provenance does not draw, and memfile Undo/Redo of the binding with undo enabled in the installed runner's window. A reference form test covers provenance dropped by a saved-upload attachment. Installed tests used synthetic SDK transport and ran in the full suite on macOS arm64 Blender 5.1.2 only. The native control has installed tests only: no desktop interaction, screenshot, focus, DPI, small window, thumbnail, other OS or other Blender version is claimed, and whether the maintenance-pump timer records the undo step on the desktop is unproven on Blender 5.0, 5.1 and 5.2. A paid Seedance 2.0 Fast run with a handed-off frame in the image input and the scene clip was accepted, then failed because an image and reference images or videos aren't allowed together; no paid run has used a first frame sent as a reference image. Re-checked 2026-10-10: the handoff target is the shared render_lanes.first_frame_target, so a model whose input descriptions exclude its first frame with the clip input receives the frame as image 1 of its reference-image array, and params.Schema.exclusive pairs are refused by shared validation before any quote. Re-checked 2026-10-10 after restacking on the exclusive first-frame routing: scenario.use_saved_first_frame stores the target's route reason at invoke and draws render_lanes.first_frame_route_lines under the input (No exact first frame with the scene clip, then Sent as image 1 of the input), the same two lines render_lanes._draw_first_frame draws once a frame is chosen; a new installed test covers that dialog for a schema worded like Seedance 2.0 Fast within 59-character lines, while the earlier dialog and native control tests use a first-frame fixture without declared exclusivity.",
    "sources": {
      "scenario/blender/first_frame_handoff.py": "cc5e5bb5ea7d9778cc535409a9ecbc15564217b0bffb9c68a54d4a2b6b3aa9f9",
      "scenario/blender/model_jobs.py": "96621235ce3f0c227b6a80648e1835cd501b6d79ec71610d54e458e545cb16ac",
      "scenario/blender/job_session.py": "fc196b52049308278d50e25f9208edcbef3a872b9398f02af50b12dfe8e76ff2",
      "scenario/blender/render_references.py": "4897d8fe89d4bfbd9e171392cfa88feff4fa6a35ba88c40e4f63158fdb93aa47",
      "tests/blender/test_first_frame_handoff.py": "4d4756832fbe651dedb0f0daf7d3c9c4a7b4d65760aa9e784667046b16aa6568",
      "scenario/blender/job_recovery.py": "759b3f1ad658739d9a99a3ac5cecd11cc1083df1f5d4e89ee48052ceac4e7b8a",
      "scenario/blender/runtime.py": "0a371030d406343469b9decdb549a0085429e251b46f2211e4cc2f4841f62e1f",
      "scenario/blender/render_lanes.py": "059119b06a18bcd0083c93dd51f00f923140db33776a2ccb56366e0ad78669b7"
    }
  }
}
---

# Saved image first-frame handoff

Evidence for [the canonical document](../../architecture/runtime.md).
