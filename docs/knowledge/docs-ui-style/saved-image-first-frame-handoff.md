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
    "reviewed_at": "2026-10-11",
    "base_revision": "1d86f53d3489b23f2447be69cb589140e2f3ba64",
    "limits": "Reviewed that ModelJobs.poll projects first_frame_assets from first_frame_handoff.eligible_assets (downloaded PNG, JPEG or WebP results with no texture role or the base role, excluding prompt and translate jobs) and that saved_job_actions draws one Use as video first frame (N) control per projected asset, numbered over every saved asset, only while ModelJobs.actions offers use_first_frame, so pending work hides it rather than disabling it. job_recovery.SCENARIO_OT_use_saved_first_frame calls runtime.prepare_first_frame_application in invoke, stores only prepared values and opens a 520 px invoke_props_dialog titled Use as video first frame with confirm text Use as first frame; draw only reads those values (scene, Form: Render Video, model, input, image, reuse and no-upload lines, the replaced file and Turn on lines only when they apply, price invalidation and slot removal); cancel discards the approval; execute calls runtime.apply_saved_result once and sets the verifying message; ScenarioError reasons are reported, with a native message when the context token is retired. The operator has no UNDO option because binding happens later in the pump. render_lanes._draw_first_frame adds the read-only From a saved result label (FILE_REFRESH) from first_frame_handoff.provenance only and never switches lanes. The Reference inputs rule links to this handoff instead of Use as reference. Installed tests on macOS arm64 Blender 5.1.2 only cover per-asset buttons for two colour stills and none for a normal map drawn through draw_controls without store reads, the exact dialog lines with fixed lines within 59 characters, cancel, refusal reasons and the retired-connection message without an approval, an MCP-prepared approval consumed once through bpy.ops, the provenance label with edited or absent provenance, and memfile Undo/Redo of the binding with undo enabled in the runner's window; unit tests cover descriptor numbering, projection and reuse. No desktop interaction, screenshot, focus, DPI, small window, other OS or Blender 5.0/5.2 run is claimed, and whether the pump timer records the undo step on the desktop is unproven. Re-checked 2026-10-10 after restacking on the exclusive first-frame routing: scenario.use_saved_first_frame stores the target's route reason at invoke and draws render_lanes.first_frame_route_lines under the input (No exact first frame with the scene clip, then Sent as image 1 of the input), the same two lines render_lanes._draw_first_frame draws once a frame is chosen; a new installed test covers that dialog for a schema worded like Seedance 2.0 Fast within 59-character lines, while the earlier dialog and native control tests use a first-frame fixture without declared exclusivity. Re-checked 2026-10-11 after restacking on main 72723f02: merged panels changes only history row kinds and merged studio adds the Film Review page; the sidebar Jobs and Generations panels and the Studio Jobs and Results pages still draw saved-job controls through job_recovery.draw_controls. Merged ModelJobs adds inference-only cancellation and remote progress and still projects first_frame_assets beside the offered actions; job_recovery, saved_job_actions and render_lanes are byte-identical to the pre-restack head, so the claims above still hold. Installed tests were not rerun after this restack. Re-checked 2026-10-11 after restacking on #377 dc704539, now on main 1d86f53d: merged panels adds older history paging and still draws saved-job controls through job_recovery.draw_controls, studio is unchanged, merged ModelJobs.poll writes world_assets beside first_frame_assets, and saved_job_actions numbers both World candidates and Use as video first frame (N) controls over every saved asset; job_recovery, render_lanes and first_frame_handoff are byte-identical to the pre-restack head, so the claims above still hold. Installed tests were not rerun after this restack. Re-checked 2026-10-11 after the native confirmation began discarding its own approval when it is refused: SCENARIO_OT_use_saved_first_frame.execute now calls cancel on a ScenarioError or any other failure, so confirming after the connection is retired reports First frame was not set: The connection changed; inspect saved jobs again and leaves no approval on the reviewing ModelJobs; one new installed test covers that case. Cancel, refusal reasons, the retired-connection message and single use of an MCP-prepared approval are unchanged. The full native suite passed on macOS arm64 Blender 5.1.2 except the known test_result_actions case expecting Cancel generation on an unconfirmed remote job.",
    "sources": {
      "scenario/blender/job_recovery.py": "708183b9df9637902b40c3c2cff0c7a6c9e13bb2b8a2ba474ea212d2b34a2a6a",
      "scenario/core/ui/saved_job_actions.py": "8dc3f4dd9b5272b1c1ba15818c36f4e0971afaa5ee5b85e491a17d46185de494",
      "scenario/blender/model_jobs.py": "c1d7d31db6f1293cffabad7c98e6ad22bdf214d8d720c256ef0f5dd8529b53b0",
      "scenario/blender/first_frame_handoff.py": "cc5e5bb5ea7d9778cc535409a9ecbc15564217b0bffb9c68a54d4a2b6b3aa9f9",
      "scenario/blender/render_lanes.py": "059119b06a18bcd0083c93dd51f00f923140db33776a2ccb56366e0ad78669b7",
      "scenario/blender/panels.py": "8c9ed56c0d83b4c0cfd4578e7158c05f1df895f7c2765319c0894c1ca0491e83",
      "scenario/blender/studio.py": "7a4a6b694ba4becb7a51dac11f95838a35d9f2a3dc752d85a50e1b1cd0f1f071",
      "tests/blender/test_first_frame_handoff.py": "17d353e42a028bace5b19cdb8bc20846f319b81d245e370624fd9b78762e6cfb",
      "tests/blender/test_result_actions.py": "e6cdd95c54dcc70cbe908b882943a24f2511548b9c5f62ab4c48d73d3a31dc23",
      "tests/unit/test_saved_job_actions.py": "1e99be091c4b6d01f800ef92457c0e58a9c762f48a00c27759e7b0d70de84326"
    }
  }
}
---

# Saved image first-frame handoff controls

Evidence for [the canonical document](../../UI_STYLE.md).
