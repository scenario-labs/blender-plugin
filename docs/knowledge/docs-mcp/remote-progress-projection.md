---
{
  "type": "Evidence",
  "id": "docs-mcp.remote-progress-projection",
  "title": "Flat job_status progress fields",
  "description": "MCP job_status and wait_for_job remote projection fields.",
  "evidence": {
    "path": "docs/MCP.md",
    "scope": "remote-progress-projection",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed ModelJobs.status, which adds lane, remote_status, progress, remote_observed_at and remote_stale from the in-memory binding and view projection, delivery_active from the same _delivering predicate that wait() uses and delivery_offline from _offline, and the job_status and wait_for_job descriptions in tools_scenario.py, including the measured-status, expired-wait and offline rules. _advancing is true only for a job owned by this session (in views), not paused, not settled, prepared only while queued, ready only while an automatic import is pending, and succeeded only when downloads_results holds (a workflow, or a model operation whose target is not the Blockout text model). _delivering is _advancing and not held offline; _offline is _advancing and held offline, where held offline means the saved state is remote, cancel_requested or succeeded (NEEDS_SCENARIO) and the Online Access value recorded by the last main-thread maintenance poll (_online_seen) is off. So paused, restarted, settled and finished prompt, translate or Blockout jobs report delivery_offline false. wait() runs on the HTTP worker and reads only that copy, never bpy; status() polls first, so it reports the current value. read_prompt_result, read_model_text and prepare_blockout_plan are the named text readers. Installed tests cover UI and MCP parity, null fields for restarted and terminal jobs, delivery_active true while remote and false after terminal delivery or restart, a restarted inspected job offline with delivery_paused true and delivery_offline false, lane null for a workflow submission, an explicit refresh after restart, wait timeout parity with job_status, an offline remote wait that returns in under 4 seconds with delivery_active false, delivery_offline true and no request, a succeeded job held offline that downloads once access returns, finished Prompt Spark, Translate and Blockout jobs inspected offline with delivery_paused true and delivery_active and delivery_offline false, a resumed Blockout plan that reaches succeeded with no download and all three false, and a prepared job whose dispatch raised returning delivery_active false; tools/gen_mcp_docs.py --check passes. Installed native tests on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 cover these claims. No desktop interaction, screenshot, other operating system or live provider progress is claimed. No live agent client is claimed. Scoped 2026-10-10 check of the Render Video first-frame handoff, not a full re-review: ModelJobs adds the use_first_frame action, its single-use approval, the verify_first_frame command and the session-local first_frame status field; polling, delivery predicates, progress projection, bindings and other actions are unchanged; tools_scenario adds the video_first_frame purpose and description text for it, job_status first_frame and render_form source_result; other contracts are unchanged. The claims above still hold; the review date and base revision are unchanged.",
    "sources": {
      "scenario/mcp/tools_scenario.py": "78997d23290c801cdf6926dc4d53d125b2dcc045c39cbcaad505150affeb008f",
      "scenario/blender/model_jobs.py": "fcd51b54adfdc215e2fafda7267914ef3d6a800093f48f60cf1f140b6b048dea",
      "scenario/core/jobs/progress.py": "bf8bea9be0d1ba3c6ca7c2495fecf61eb67481ffb7499d1e30633cc154871af5",
      "tests/blender/test_model_generation.py": "3cca6011fa4ce6a1ea72922da75ff8846ae0c6ec0155b00143a6e3c724b8c02d",
      "tests/blender/test_workflow_commands.py": "74086c3122b3c83103e08072be6669e510ac1026a1da6cbb6f0eeaa1c0f49338",
      "tests/blender/helpers.py": "fdecbd78905c23b88f8400a111f4a8f732fa0b1c8d4825456ad03d73b0137858",
      "tests/blender/test_prompt_tools.py": "3337cbe8e763b7436c69394e3de5b056dd2f02156acc5da3de8307267c275dde",
      "tests/blender/test_blockout_jobs.py": "6151fbd3136147da03d6221962fb8492dd67f60fa2f0748687a44b1367e575b4"
    }
  }
}
---

# Flat job_status progress fields

Evidence for [the canonical document](../../MCP.md).
