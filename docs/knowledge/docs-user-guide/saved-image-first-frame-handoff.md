---
{
  "type": "Evidence",
  "id": "docs-user-guide.saved-image-first-frame-handoff",
  "title": "First frame from a saved image through MCP",
  "description": "User-facing description of the MCP first-frame handoff and its missing native button.",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "saved-image-first-frame-handoff",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-11",
    "base_revision": "7fb15252f747f52db24f7e659f8d5048241f803e",
    "limits": "Reviewed that local MCP prepare_result_application with purpose video_first_frame binds a downloaded PNG, JPEG or WebP saved result after apply_result_application, reuses its asset ID, starts no upload, stores no file path and invalidates the price, and that saved_job_actions.MCP_ONLY keeps native surfaces from drawing a button. Unit tests cover the PNG, JPEG and WebP signature helper and the MCP-only descriptor. Ten installed tests in test_first_frame_handoff cover: offering for downloaded PNG, JPEG and WebP colour results and not for EXR, normal maps, undownloaded results or prompt jobs; inert MCP preparation with no request, form or saved-job change; binding with the asset, scope, asset, kind and provenance markers, an empty first_frame_path, an enabled first frame, price invalidation, no upload work and no private path in the slot; request bodies for a first-frame image input the schema lets go with the clip, a Minimax-style firstFrameImage input and an image array where the frame orders first; a schema worded like Seedance 2.0 Fast, whose review reports sent_as reference_image with its reason and note and whose bound frame orders first in referenceImages with the clip kept and no image input in the request or dry-run body; the dry-run quote body; single use and an occupied slot; refusals for a pending upload slot, an occupied single-file input, a full array, a model without an image input, an unloaded schema without a model read and another scene; a changed model, chosen file, enabled state or reference list, undo or load invalidation and a retired context before apply; scene, form and slot changes during verification; tampered bytes before and after verification and a mislabelled container; Prompt Spark using the bound frame; a later chosen file, disabling and removal; and a blend saved uncompressed without the private result path, reopened under the same project and refused under another. A reference form test covers provenance dropped by a saved-upload attachment. Installed tests used synthetic SDK transport and ran in the full suite on macOS arm64 Blender 5.1.2 only. No native control exists in this change, so no desktop interaction, dialog, thumbnail, desktop undo step from the maintenance pump, other OS, DPI or Blender version is claimed. A paid Seedance 2.0 Fast run with a handed-off frame in the image input and the scene clip was accepted, then failed because an image and reference images or videos aren't allowed together; no paid run has used a first frame sent as a reference image. Re-checked 2026-10-10: the handoff target is the shared render_lanes.first_frame_target, so a model whose input descriptions exclude its first frame with the clip input receives the frame as image 1 of its reference-image array, and params.Schema.exclusive file-input pairs are refused by shared validation before any quote; a setting described as exclusive is not refused. Re-checked 2026-10-11 after restacking on main 72723f02: merged tools_scenario adds result source and projection, history row kinds, inference-only cancellation, Film review and remote progress fields; the video_first_frame contract above is unchanged. After the restack the installed tests passed again in the full native suite on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1, whose only failure (test_result_actions expecting Cancel generation on an unconfirmed remote job) also fails on main. Re-checked 2026-10-11 after restacking on #369, now on main 7fb15252: merged tools_scenario adds older history paging and workflow upload wording, and saved_job_actions numbers World candidates from the ModelJobs projection; the video_first_frame contract above is unchanged. After this restack the installed tests passed again in the full native suite on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1, whose only failure is the known test_result_actions case expecting Cancel generation on an unconfirmed remote job.",
    "sources": {
      "scenario/mcp/tools_scenario.py": "988093f08603d113356cb568f20ff7bb24f028c21ce703a3bd58c4762be639b9",
      "scenario/blender/first_frame_handoff.py": "cc5e5bb5ea7d9778cc535409a9ecbc15564217b0bffb9c68a54d4a2b6b3aa9f9",
      "scenario/core/ui/saved_job_actions.py": "5dea4ea6c75ee42aa5c2f309c0405a9e33cfa511fc99e7ead28c7f49ec5d1806",
      "tests/blender/test_first_frame_handoff.py": "ef4a1f10b13233402920f7eb8e30d70f9f4d976bd74d7bfceb58c77d27dd3e44",
      "scenario/blender/render_lanes.py": "c644c891cb6d4e4a92b7bead7b5274592adfad943bca2b9257d9f745301b1782"
    }
  }
}
---

# First frame from a saved image through MCP

Evidence for [the canonical document](../../USER_GUIDE.md).
