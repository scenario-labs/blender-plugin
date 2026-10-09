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
    "limits": "Reviewed ModelJobs.status, which adds lane, remote_status, progress, remote_observed_at and remote_stale from the in-memory binding and view projection, delivery_active from the same _delivering predicate that wait() uses and delivery_offline from _offline, and the job_status and wait_for_job descriptions in tools_scenario.py, including the measured-status, expired-wait and offline rules. _delivering is false when the job is settled, paused, not owned by this session, prepared but not in the submission queue, ready without a pending automatic import, or held offline; _offline is true when the saved state is remote, cancel_requested or succeeded (NEEDS_SCENARIO) and the Online Access value recorded by the last main-thread maintenance poll (_online_seen) is off. wait() runs on the HTTP worker and reads only that copy, never bpy; status() polls first, so it reports the current value. Installed tests cover UI and MCP parity, null fields for restarted and terminal jobs, delivery_active true while remote and false after terminal delivery or restart, lane null for a workflow submission, an explicit refresh after restart, wait timeout parity with job_status, an offline remote wait that returns in under 4 seconds with delivery_active false, delivery_offline true and no request, a succeeded job held offline that downloads once access returns, and a prepared job whose dispatch raised returning delivery_active false; tools/gen_mcp_docs.py --check passes. Installed native tests on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 cover these claims. No desktop interaction, screenshot, other operating system or live provider progress is claimed. No live agent client is claimed.",
    "sources": {
      "scenario/mcp/tools_scenario.py": "226fb7b9d14aef80e41cc5198f10ff020da376ce7eb1da882eefd6d2a639898c",
      "scenario/blender/model_jobs.py": "2daeab1ce44043c115f8956bd70e08ad19a73d2e70140f72f4e8fbda7a3e524f",
      "scenario/core/jobs/progress.py": "bf8bea9be0d1ba3c6ca7c2495fecf61eb67481ffb7499d1e30633cc154871af5",
      "tests/blender/test_model_generation.py": "bdac7e6d4f3909bf1c03abe96b49753b77f2e655728b388bcf485bb55b9669c8",
      "tests/blender/test_workflow_commands.py": "74086c3122b3c83103e08072be6669e510ac1026a1da6cbb6f0eeaa1c0f49338"
    }
  }
}
---

# Flat job_status progress fields

Evidence for [the canonical document](../../MCP.md).
