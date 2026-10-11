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
    "base_revision": "72723f02a97a7226b1c697c31d8124b77ac92c86",
    "limits": "Reviewed that the Render Image / Render Video row's first-frame claim matches the code: a downloaded saved PNG, JPEG or WebP colour result can be bound to the Render Video first-frame slot by reusing its asset ID, through the native scenario.use_saved_first_frame control drawn by the shared saved-job descriptors in the sidebar and Studio pages and through MCP prepare_result_application with purpose video_first_frame, both after an explicit single-use approval. Nothing is uploaded or generated and no file path is stored. Installed tests on macOS arm64 Blender 5.1.2 only cover the shared command, the MCP purpose and the native control. Desktop interaction on Blender 5.0, 5.1 and 5.2, the pump undo step on the desktop and a paid Render Video run with a handed-off frame remain under #68; the free dry-run evidence belongs to the shared command change. Re-checked 2026-10-10 after restacking on the exclusive first-frame routing: scenario.use_saved_first_frame stores the target's route reason at invoke and draws render_lanes.first_frame_route_lines under the input (No exact first frame with the scene clip, then Sent as image 1 of the input), the same two lines render_lanes._draw_first_frame draws once a frame is chosen; a new installed test covers that dialog for a schema worded like Seedance 2.0 Fast within 59-character lines, while the earlier dialog and native control tests use a first-frame fixture without declared exclusivity. Re-checked 2026-10-10 after restacking on the guard-scope fix: its tools_scenario.py change only rewords the render_form description (two file inputs whose descriptions say they can't be combined are refused; settings are not checked); the prepare_result_application video_first_frame contract this row relies on is unchanged. Re-checked 2026-10-11 after restacking on main 72723f02: merged studio adds the Film Review page and keeps the Jobs and Results pages on the shared saved-job controls; merged tools_scenario adds result source and projection, history row kinds, inference-only cancellation, Film review and remote progress fields; merged ModelJobs adds inference-only cancellation and remote progress and still projects first_frame_assets. The prepare_result_application video_first_frame contract and the native control this row relies on are unchanged. Installed tests were not rerun after this restack.",
    "sources": {
      "scenario/blender/first_frame_handoff.py": "cc5e5bb5ea7d9778cc535409a9ecbc15564217b0bffb9c68a54d4a2b6b3aa9f9",
      "scenario/blender/job_recovery.py": "759b3f1ad658739d9a99a3ac5cecd11cc1083df1f5d4e89ee48052ceac4e7b8a",
      "scenario/blender/model_jobs.py": "fa47b6f1b3b6d0e79a6fa80b7f002401d787263c01686e7c02a094fe71d24c1f",
      "scenario/blender/studio.py": "7a4a6b694ba4becb7a51dac11f95838a35d9f2a3dc752d85a50e1b1cd0f1f071",
      "scenario/core/ui/saved_job_actions.py": "f360aa25c33a2bb37889c559a824357946e5644bf6fe786dd937c5bd4e1ba8de",
      "scenario/mcp/tools_scenario.py": "91d7740aa90b0be40f644e3638f09bfedcaea321a7d9525b74cbbeed0a1905b2",
      "tests/blender/test_first_frame_handoff.py": "32ca88c20a19cafef5327cfdba3f94a880ea3532f3875c1ba63c8c0005317e7b"
    }
  }
}
---

# Restored saved-image first-frame handoff

Evidence for [the canonical document](../../STUDIO_ADOPTION.md).
