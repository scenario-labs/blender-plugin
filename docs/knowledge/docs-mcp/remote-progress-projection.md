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
    "base_revision": "fb699b8555f7cee62147794516cc7aaa224864f7",
    "limits": "Reviewed ModelJobs.status, which adds lane, remote_status, progress, remote_observed_at and remote_stale from the in-memory binding and view projection, delivery_active from the same _delivering predicate that wait() uses and delivery_offline from _offline, and the job_status and wait_for_job descriptions in tools_scenario.py, including the measured-status, expired-wait and offline rules. _advancing is true only for a job owned by this session (in views), not paused, not settled, prepared only while queued, ready only while an automatic import is pending, and succeeded only when downloads_results holds (a workflow, or a model operation whose target is not the Blockout text model). _delivering is _advancing and not held offline; _offline is _advancing and held offline, where held offline means the saved state is remote, cancel_requested or succeeded (NEEDS_SCENARIO) and the Online Access value recorded by the last main-thread maintenance poll (_online_seen) is off. So paused, restarted, settled and finished prompt, translate or Blockout jobs report delivery_offline false. wait() runs on the HTTP worker and reads only that copy, never bpy; status() polls first, so it reports the current value. read_prompt_result, read_model_text and prepare_blockout_plan are the named text readers. Installed tests cover UI and MCP parity, null fields for restarted and terminal jobs, delivery_active true while remote and false after terminal delivery or restart, a restarted inspected job offline with delivery_paused true and delivery_offline false, lane null for a workflow submission, an explicit refresh after restart, wait timeout parity with job_status, an offline remote wait that returns in under 4 seconds with delivery_active false, delivery_offline true and no request, a succeeded job held offline that downloads once access returns, finished Prompt Spark, Translate and Blockout jobs inspected offline with delivery_paused true and delivery_active and delivery_offline false, a resumed Blockout plan that reaches succeeded with no download and all three false, and a prepared job whose dispatch raised returning delivery_active false; tools/gen_mcp_docs.py --check passes. Installed native tests on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 cover these claims. No desktop interaction, screenshot, other operating system or live provider progress is claimed. No live agent client is claimed.",
    "sources": {
      "scenario/mcp/tools_scenario.py": "364dc8cc70eb4761e698d9bc32c5d89fcfcb65a0e1e3bd8757030670528b20a9",
      "scenario/blender/model_jobs.py": "e49b0513dbaaa8c7805da01af007b0e0ff0598ac2c52f6d9afd583a9980b4163",
      "scenario/core/jobs/progress.py": "bf8bea9be0d1ba3c6ca7c2495fecf61eb67481ffb7499d1e30633cc154871af5",
      "tests/blender/test_model_generation.py": "9defb9e875aa425a4130ef3208994b20bb3f2c2ab27057b79d48635a13db5be7",
      "tests/blender/test_workflow_commands.py": "74086c3122b3c83103e08072be6669e510ac1026a1da6cbb6f0eeaa1c0f49338",
      "tests/blender/helpers.py": "642e7e9d178824befedb1eaf9f6344b0631af2baaf492e8c87993e533ad9d6e6",
      "tests/blender/test_prompt_tools.py": "3337cbe8e763b7436c69394e3de5b056dd2f02156acc5da3de8307267c275dde",
      "tests/blender/test_blockout_jobs.py": "6151fbd3136147da03d6221962fb8492dd67f60fa2f0748687a44b1367e575b4"
    }
  }
}
---

# Flat job_status progress fields

Evidence for [the canonical document](../../MCP.md).
