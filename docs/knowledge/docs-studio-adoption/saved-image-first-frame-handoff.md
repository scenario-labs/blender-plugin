---
{
  "type": "Evidence",
  "id": "docs-studio-adoption.saved-image-first-frame-handoff",
  "title": "Restored saved-image first-frame handoff",
  "description": "The retained Render Video first-frame capability restored as a native and MCP action.",
  "evidence": {
    "path": "docs/STUDIO_ADOPTION.md",
    "scope": "saved-image-first-frame-handoff",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-11",
    "base_revision": "1d86f53d3489b23f2447be69cb589140e2f3ba64",
    "limits": "Reviewed that the Render Image / Render Video row's first-frame claim matches the code: a downloaded saved PNG, JPEG or WebP colour result can be bound to the Render Video first-frame slot by reusing its asset ID, through the native scenario.use_saved_first_frame control drawn by the shared saved-job descriptors in the sidebar and Studio pages and through MCP prepare_result_application with purpose video_first_frame, both after an explicit single-use approval. Nothing is uploaded or generated and no file path is stored. Installed tests on macOS arm64 Blender 5.1.2 only cover the shared command, the MCP purpose and the native control. Desktop interaction on Blender 5.0, 5.1 and 5.2, the pump undo step on the desktop and a paid Render Video run with a handed-off frame remain under #68; the free dry-run evidence belongs to the shared command change. Re-checked 2026-10-10 after restacking on the exclusive first-frame routing: scenario.use_saved_first_frame stores the target's route reason at invoke and draws render_lanes.first_frame_route_lines under the input (No exact first frame with the scene clip, then Sent as image 1 of the input), the same two lines render_lanes._draw_first_frame draws once a frame is chosen; a new installed test covers that dialog for a schema worded like Seedance 2.0 Fast within 59-character lines, while the earlier dialog and native control tests use a first-frame fixture without declared exclusivity. Re-checked 2026-10-10 after restacking on the guard-scope fix: its tools_scenario.py change only rewords the render_form description (two file inputs whose descriptions say they can't be combined are refused; settings are not checked); the prepare_result_application video_first_frame contract this row relies on is unchanged. Re-checked 2026-10-11 after restacking on main 72723f02: merged studio adds the Film Review page and keeps the Jobs and Results pages on the shared saved-job controls; merged tools_scenario adds result source and projection, history row kinds, inference-only cancellation, Film review and remote progress fields; merged ModelJobs adds inference-only cancellation and remote progress and still projects first_frame_assets. The prepare_result_application video_first_frame contract and the native control this row relies on are unchanged. Installed tests were not rerun after this restack. Re-checked 2026-10-11 after restacking on #377 dc704539, now on main 1d86f53d: merged tools_scenario adds older history paging and workflow upload wording, merged ModelJobs.poll writes world_assets beside first_frame_assets and saved_job_actions numbers World candidates from that projection; studio, job_recovery and first_frame_handoff are byte-identical to the pre-restack head, and the prepare_result_application video_first_frame contract and the native control this row relies on are unchanged. Installed tests were not rerun after this restack. Re-checked 2026-10-11 after the native confirmation began discarding its own approval when it is refused: SCENARIO_OT_use_saved_first_frame.execute now calls cancel on a ScenarioError or any other failure, so confirming after the connection is retired reports First frame was not set: The connection changed; inspect saved jobs again and leaves no approval on the reviewing ModelJobs; one new installed test covers that case. Cancel, refusal reasons, the retired-connection message and single use of an MCP-prepared approval are unchanged. The full native suite passed on macOS arm64 Blender 5.1.2 except the known test_result_actions case expecting Cancel generation on an unconfirmed remote job.",
    "sources": {
      "scenario/blender/first_frame_handoff.py": "cc5e5bb5ea7d9778cc535409a9ecbc15564217b0bffb9c68a54d4a2b6b3aa9f9",
      "scenario/blender/job_recovery.py": "708183b9df9637902b40c3c2cff0c7a6c9e13bb2b8a2ba474ea212d2b34a2a6a",
      "scenario/blender/model_jobs.py": "c1d7d31db6f1293cffabad7c98e6ad22bdf214d8d720c256ef0f5dd8529b53b0",
      "scenario/blender/studio.py": "7a4a6b694ba4becb7a51dac11f95838a35d9f2a3dc752d85a50e1b1cd0f1f071",
      "scenario/core/ui/saved_job_actions.py": "8dc3f4dd9b5272b1c1ba15818c36f4e0971afaa5ee5b85e491a17d46185de494",
      "scenario/mcp/tools_scenario.py": "988093f08603d113356cb568f20ff7bb24f028c21ce703a3bd58c4762be639b9",
      "tests/blender/test_first_frame_handoff.py": "17d353e42a028bace5b19cdb8bc20846f319b81d245e370624fd9b78762e6cfb"
    }
  }
}
---

# Restored saved-image first-frame handoff

Evidence for [the canonical document](../../STUDIO_ADOPTION.md).
