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
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed that the Render Image / Render Video row's first-frame claim matches the code: a downloaded saved PNG, JPEG or WebP colour result can be bound to the Render Video first-frame slot by reusing its asset ID, through the native scenario.use_saved_first_frame control drawn by the shared saved-job descriptors in the sidebar and Studio pages and through MCP prepare_result_application with purpose video_first_frame, both after an explicit single-use approval. Nothing is uploaded or generated and no file path is stored. Installed tests on macOS arm64 Blender 5.1.2 only cover the shared command, the MCP purpose and the native control. Desktop interaction on Blender 5.0, 5.1 and 5.2, the pump undo step on the desktop and a paid Render Video run with a handed-off frame remain under #68; the free dry-run evidence belongs to the shared command change. Re-checked 2026-10-10 after restacking on the exclusive first-frame routing: scenario.use_saved_first_frame stores the target's route reason at invoke and draws render_lanes.first_frame_route_lines under the input (No exact first frame with the scene clip, then Sent as image 1 of the input), the same two lines render_lanes._draw_first_frame draws once a frame is chosen; a new installed test covers that dialog for a schema worded like Seedance 2.0 Fast within 59-character lines, while the earlier dialog and native control tests use a first-frame fixture without declared exclusivity.",
    "sources": {
      "scenario/blender/first_frame_handoff.py": "cc5e5bb5ea7d9778cc535409a9ecbc15564217b0bffb9c68a54d4a2b6b3aa9f9",
      "scenario/blender/job_recovery.py": "759b3f1ad658739d9a99a3ac5cecd11cc1083df1f5d4e89ee48052ceac4e7b8a",
      "scenario/blender/model_jobs.py": "96621235ce3f0c227b6a80648e1835cd501b6d79ec71610d54e458e545cb16ac",
      "scenario/blender/studio.py": "d4ba0b268cdcc1a6d9477cb5f190ebb18233010de5b5963fecf941ba05995fb8",
      "scenario/core/ui/saved_job_actions.py": "f360aa25c33a2bb37889c559a824357946e5644bf6fe786dd937c5bd4e1ba8de",
      "scenario/mcp/tools_scenario.py": "b1a1e0be95d4968a717e385e95c1bd2382dec3550d8b531a1373e6fbcf4a8fa8",
      "tests/blender/test_first_frame_handoff.py": "4d4756832fbe651dedb0f0daf7d3c9c4a7b4d65760aa9e784667046b16aa6568"
    }
  }
}
---

# Restored saved-image first-frame handoff

Evidence for [the canonical document](../../STUDIO_ADOPTION.md).
