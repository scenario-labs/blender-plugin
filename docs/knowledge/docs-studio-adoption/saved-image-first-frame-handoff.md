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
    "limits": "Reviewed that the Render Image / Render Video row's first-frame claim matches the code: a downloaded saved PNG, JPEG or WebP colour result can be bound to the Render Video first-frame slot by reusing its asset ID, through the native scenario.use_saved_first_frame control drawn by the shared saved-job descriptors in the sidebar and Studio pages and through MCP prepare_result_application with purpose video_first_frame, both after an explicit single-use approval. Nothing is uploaded or generated and no file path is stored. Installed tests on macOS arm64 Blender 5.1.2 only cover the shared command, the MCP purpose and the native control. Desktop interaction on Blender 5.0, 5.1 and 5.2, the pump undo step on the desktop and a paid Render Video run with a handed-off frame remain under #68; the free dry-run evidence belongs to the shared command change.",
    "sources": {
      "scenario/blender/first_frame_handoff.py": "d58cacd56de6d1f687f154f883b999af4dc2a745c40a2a76c5a3fd326e2e815e",
      "scenario/blender/job_recovery.py": "012d4a61956de59aa057de3fa2d77c5290e95bccb09519e71de334fad88659ce",
      "scenario/blender/model_jobs.py": "96621235ce3f0c227b6a80648e1835cd501b6d79ec71610d54e458e545cb16ac",
      "scenario/blender/studio.py": "d4ba0b268cdcc1a6d9477cb5f190ebb18233010de5b5963fecf941ba05995fb8",
      "scenario/core/ui/saved_job_actions.py": "f360aa25c33a2bb37889c559a824357946e5644bf6fe786dd937c5bd4e1ba8de",
      "scenario/mcp/tools_scenario.py": "78997d23290c801cdf6926dc4d53d125b2dcc045c39cbcaad505150affeb008f",
      "tests/blender/test_first_frame_handoff.py": "85109ba5f94dad6bbfce2516200a2e62dec62d0738d8cc97e388895cb153bd15"
    }
  }
}
---

# Restored saved-image first-frame handoff

Evidence for [the canonical document](../../STUDIO_ADOPTION.md).
