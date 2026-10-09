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
    "limits": "Reviewed that ModelJobs._observe is the only consumer of refresh_remote and cancel_remote snapshots and calls progress.observe, which yields a reading only for a remote or cancel_requested record whose response jobId matches and whose status is one of the five active SDK statuses. _observe runs after the next poll is scheduled and outside the delivery exception mapping; a failing projection drops the reading, logs only the exception type and never pauses delivery. Booleans, strings, missing, non-finite and out-of-range fractions become None; percent exists only for in-progress or finalizing above zero and floors round(fraction * 100, 6), so 0.29 shows 29. Each poll drops a reading when the state, remote ID or revision changes and marks it stale when Online Access is off, delivery is paused or the scheduled poll time plus STALE_GRACE has passed. Active refreshes keep the saved revision; nothing is persisted. ModelJobs._delivering is the one predicate for wait() and MCP delivery_active. ModelJobs.submit records JobBinding(scene session_uid, lane) before dispatch for UI and MCP model lanes; workflow and Film submissions are unbound; bound_views reads only in-memory dictionaries; bindings retire with their owner. Unit tests cover validation, display words, percent snapping and the SDK status literal set. Installed tests cover UI and MCP binding, a 0.42 projection, an invalid fraction, terminal clearing, revision and remote ID mismatch drops, a failed projection that keeps delivery and polling, a cancel_remote completion rebound to the cancel_requested revision, offline and overdue staleness, explicit refresh after restart, credential and file retirement, binding stability across real memfile undo and redo, an unbound workflow submission and wait parity. Installed native tests on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 cover these claims. No desktop interaction, screenshot, other operating system or live provider progress is claimed. Film submissions are unbound by code review only. No compact composer surface uses the binding yet.",
    "sources": {
      "scenario/core/jobs/progress.py": "bf8bea9be0d1ba3c6ca7c2495fecf61eb67481ffb7499d1e30633cc154871af5",
      "scenario/blender/model_jobs.py": "7278524fcd4cac373ce186782e741cc58b5a18e0a8ddca17d4c6cd1045fc52a6",
      "scenario/core/jobs/coordinator.py": "a8b7efb39e74a1a34f350ff7274e2e714a06933383743744dd22e6e1b7d7096d",
      "tests/unit/test_job_progress.py": "c6ab3586b2b9ae8f4abf957a36b066b20cb8f01259fda6d9db5c858b11204a17",
      "tests/blender/test_model_generation.py": "e0f1b143a429bee22f5715ce420ff0d364916efc11bc94b630e8ad067a466f10",
      "tests/blender/test_workflow_commands.py": "74086c3122b3c83103e08072be6669e510ac1026a1da6cbb6f0eeaa1c0f49338"
    }
  }
}
---

# Remote progress readings and scene lane bindings

Evidence for [the canonical document](../../BLENDER_JOB_CONTEXT.md).
