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
    "reviewed_at": "2026-10-12",
    "base_revision": "4ca693cb8f0e02a5c27c12d39bedbbc166b4e725",
    "limits": "Reviewed ModelJobs.status, which adds lane, remote_status, progress, remote_observed_at and remote_stale from the in-memory binding and view projection, delivery_active from the same _delivering predicate that wait() uses and delivery_offline from _offline, and the job_status and wait_for_job descriptions in tools_scenario.py, including the measured-status, expired-wait and offline rules. _advancing is true only for a job owned by this session (in views), not paused, not settled, prepared only while queued, ready only while an automatic import is pending, and succeeded only when downloads_results holds (a workflow, or a model operation whose target is not the Blockout text model). _delivering is _advancing and not held offline; _offline is _advancing and held offline, where held offline means the saved state is remote, cancel_requested or succeeded (NEEDS_SCENARIO) and the Online Access value recorded by the last main-thread maintenance poll (_online_seen) is off. So paused, restarted, settled and finished prompt, translate or Blockout jobs report delivery_offline false. wait() runs on the HTTP worker and reads only that copy, never bpy; status() polls first, so it reports the current value. read_prompt_result, read_model_text and prepare_blockout_plan are the named text readers. Installed tests cover UI and MCP parity, null fields for restarted and terminal jobs, delivery_active true while remote and false after terminal delivery or restart, a restarted inspected job offline with delivery_paused true and delivery_offline false, lane null for a workflow submission, an explicit refresh after restart, wait timeout parity with job_status, an offline remote wait that returns in under 4 seconds with delivery_active false, delivery_offline true and no request, a succeeded job held offline that downloads once access returns, finished Prompt Spark, Translate and Blockout jobs inspected offline with delivery_paused true and delivery_active and delivery_offline false, a resumed Blockout plan that reaches succeeded with no download and all three false, and a prepared job whose dispatch raised returning delivery_active false; tools/gen_mcp_docs.py --check passes. Installed native tests on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 cover these claims. No desktop interaction, screenshot, other operating system or live provider progress is claimed. No live agent client is claimed. Scoped 2026-10-12 check of the Render Video first-frame handoff, not a full re-review: ModelJobs adds the use_first_frame action, its single-use approval, the verify_first_frame command and the session-local first_frame status field; polling, delivery predicates, progress projection, bindings and other actions are unchanged; tools_scenario adds the video_first_frame purpose and description text for it, job_status first_frame, render_form source_result and first_frame_route, and refusal of described exclusive file inputs in raw generate bodies; other contracts are unchanged. The claims above still hold; the review date and base revision are unchanged. Scoped 2026-10-12 check of the native first-frame control, not a full re-review: ModelJobs.poll also writes first_frame_assets, the eligible still asset IDs, into each saved view's meta for the native descriptor; status words, progress, delivery, offline lines and redraws are unchanged. The claims above still hold; the review date and base revision are unchanged. On 2026-10-12 the model_jobs.py, tools_scenario.py and helpers.py fingerprints were refreshed after the saved model package import was rebuilt on this topic's sources. It adds import-unit projection, status fields, per-format import controls and package journeys beside the unchanged progress projection: view.meta import_units is set before _project_remote, and status adds import_units, import_findings and model_import beside lane and the remote fields. The job_status description keeps this topic's paragraph after the new import sentence, and the status, _delivering and _offline rules are unchanged. These claims were rechecked and the review date is unchanged.",
    "sources": {
      "scenario/mcp/tools_scenario.py": "091d7ccab76864c6e8f583b1edd20f89240639bc546a44169915ffbd8afbe342",
      "scenario/blender/model_jobs.py": "f9bb80a01c12136fd1d463c3cf825c2b049c373aa4ed0f8e4a1022cee8f24838",
      "scenario/core/jobs/progress.py": "bf8bea9be0d1ba3c6ca7c2495fecf61eb67481ffb7499d1e30633cc154871af5",
      "tests/blender/test_model_generation.py": "505d6e569450a339535038db01c26484550a6bfd0bc0c1dffb1d35d207da8df9",
      "tests/blender/test_workflow_commands.py": "991bd75a0c7c4157fef02d6d74866d13a42b3b227c22c8581114add76dd90a77",
      "tests/blender/helpers.py": "2465fcd3df8c5dccb71e9f02f22f056bbebbb84fd959b1b23fc9d627778c4bfe",
      "tests/blender/test_prompt_tools.py": "a9c04c117248f0630d8a9f02af2df95357904fae5ae767e260a97d0531d9a10b",
      "tests/blender/test_blockout_jobs.py": "94a8e8157b551e2604229b3d5a57df0e9a74b8572476fbd527a077b4ff8a4069"
    }
  }
}
---

# Flat job_status progress fields

Evidence for [the canonical document](../../MCP.md).
