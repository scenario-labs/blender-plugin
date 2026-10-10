---
{
  "type": "Evidence",
  "id": "docs-ui-style.saved-image-first-frame-handoff",
  "title": "Saved image first-frame handoff controls",
  "description": "Native Use as video first frame buttons, confirmation and form label.",
  "evidence": {
    "path": "docs/UI_STYLE.md",
    "scope": "saved-image-first-frame-handoff",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed that ModelJobs.poll projects first_frame_assets from first_frame_handoff.eligible_assets (downloaded PNG, JPEG or WebP results with no texture role or the base role, excluding prompt and translate jobs) and that saved_job_actions draws one Use as video first frame (N) control per projected asset, numbered over every saved asset, only while ModelJobs.actions offers use_first_frame, so pending work hides it rather than disabling it. job_recovery.SCENARIO_OT_use_saved_first_frame calls runtime.prepare_first_frame_application in invoke, stores only prepared values and opens a 520 px invoke_props_dialog titled Use as video first frame with confirm text Use as first frame; draw only reads those values (scene, Form: Render Video, model, input, image, reuse and no-upload lines, the replaced file and Turn on lines only when they apply, price invalidation and slot removal); cancel discards the approval; execute calls runtime.apply_saved_result once and sets the verifying message; ScenarioError reasons are reported, with a native message when the context token is retired. The operator has no UNDO option because binding happens later in the pump. render_lanes._draw_first_frame adds the read-only From a saved result label (FILE_REFRESH) from first_frame_handoff.provenance only and never switches lanes. The Reference inputs rule links to this handoff instead of Use as reference. Installed tests on macOS arm64 Blender 5.1.2 only cover per-asset buttons for two colour stills and none for a normal map drawn through draw_controls without store reads, the exact dialog lines with fixed lines within 59 characters, cancel, refusal reasons and the retired-connection message without an approval, an MCP-prepared approval consumed once through bpy.ops, the provenance label with edited or absent provenance, and memfile Undo/Redo of the binding with undo enabled in the runner's window; unit tests cover descriptor numbering, projection and reuse. No desktop interaction, screenshot, focus, DPI, small window, other OS or Blender 5.0/5.2 run is claimed, and whether the pump timer records the undo step on the desktop is unproven. Re-checked 2026-10-10 after restacking on the exclusive first-frame routing: scenario.use_saved_first_frame stores the target's route reason at invoke and draws render_lanes.first_frame_route_lines under the input (No exact first frame with the scene clip, then Sent as image 1 of the input), the same two lines render_lanes._draw_first_frame draws once a frame is chosen; a new installed test covers that dialog for a schema worded like Seedance 2.0 Fast within 59-character lines, while the earlier dialog and native control tests use a first-frame fixture without declared exclusivity.",
    "sources": {
      "scenario/blender/job_recovery.py": "759b3f1ad658739d9a99a3ac5cecd11cc1083df1f5d4e89ee48052ceac4e7b8a",
      "scenario/core/ui/saved_job_actions.py": "f360aa25c33a2bb37889c559a824357946e5644bf6fe786dd937c5bd4e1ba8de",
      "scenario/blender/model_jobs.py": "96621235ce3f0c227b6a80648e1835cd501b6d79ec71610d54e458e545cb16ac",
      "scenario/blender/first_frame_handoff.py": "cc5e5bb5ea7d9778cc535409a9ecbc15564217b0bffb9c68a54d4a2b6b3aa9f9",
      "scenario/blender/render_lanes.py": "059119b06a18bcd0083c93dd51f00f923140db33776a2ccb56366e0ad78669b7",
      "scenario/blender/panels.py": "683cbe1ba4486ce2e59cc203bbac153d9ea6c31e3f0bc7710cf01bb028019d54",
      "scenario/blender/studio.py": "d4ba0b268cdcc1a6d9477cb5f190ebb18233010de5b5963fecf941ba05995fb8",
      "tests/blender/test_first_frame_handoff.py": "4d4756832fbe651dedb0f0daf7d3c9c4a7b4d65760aa9e784667046b16aa6568",
      "tests/blender/test_result_actions.py": "3ce294d7ef49195ac612d99f977571c460c1a0f0eccb992275ad12b6554a52ec",
      "tests/unit/test_saved_job_actions.py": "d0a5cb367bac4f68316ed06b13e7d5443053b3a20bb1a01dcd614fbc908ec5c9"
    }
  }
}
---

# Saved image first-frame handoff controls

Evidence for [the canonical document](../../UI_STYLE.md).
