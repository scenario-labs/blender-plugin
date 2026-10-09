---
{
  "type": "Evidence",
  "id": "docs-blender-job-context.remote-progress-projection",
  "title": "Remote progress readings and scene lane bindings",
  "description": "In-memory remote progress projection and display-only submission bindings.",
  "evidence": {
    "path": "docs/BLENDER_JOB_CONTEXT.md",
    "scope": "remote-progress-projection",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Reviewed that ModelJobs._observe is the only consumer of refresh_remote and cancel_remote snapshots and calls progress.observe, which yields a reading only for a remote or cancel_requested record whose response jobId matches and whose status is one of the five active SDK statuses. Booleans, strings, missing, non-finite and out-of-range fractions become None; percent exists only for in-progress or finalizing above zero. Each poll drops a reading when the state, remote ID or revision changes and marks it stale when Online Access is off, delivery is paused or the scheduled poll time plus STALE_GRACE has passed. Active refreshes keep the saved revision; nothing is persisted. ModelJobs.submit records JobBinding(scene session_uid, lane) before dispatch for UI and MCP model lanes; workflow and Film submissions are unbound; bound_views reads only in-memory dictionaries; bindings retire with their owner. Unit tests cover validation, display words and the SDK status literal set. Installed tests cover UI and MCP binding, a 0.42 projection, an invalid fraction, terminal clearing, offline and overdue staleness, explicit refresh after restart, credential and file retirement, binding stability across real memfile undo and redo, and wait parity. Installed native tests on macOS arm64 Blender 5.1.2 cover these claims. No desktop interaction, screenshot, Blender 5.0/5.2 run, other operating system or live provider progress is claimed. No compact composer surface uses the binding yet.",
    "sources": {
      "scenario/core/jobs/progress.py": "286563456f871fb3073ad32932cc3d9b750f12b9d263abef2fe931cbc5568f92",
      "scenario/blender/model_jobs.py": "ef10249154c8842a96da012d07395bf8c1554bc762542cdc27f1539ae1590e85",
      "scenario/core/jobs/coordinator.py": "a8b7efb39e74a1a34f350ff7274e2e714a06933383743744dd22e6e1b7d7096d",
      "tests/unit/test_job_progress.py": "4d3ff074ca2970f79b48b944f25c2d19326142a8457b505968ad60994b072ddb",
      "tests/blender/test_model_generation.py": "a7994ea7cf89c4c26b29701682b9cf9e39971e6fef54a031f4394b9ed57e2f66"
    }
  }
}
---

# Remote progress readings and scene lane bindings

Evidence for [the canonical document](../../BLENDER_JOB_CONTEXT.md).
