---
{
  "type": "Evidence",
  "id": "docs-blender-job-context.prepared-job-cancellation",
  "title": "Native prepared-job cancellation parity",
  "description": "Saved-job control sharing the MCP local cancellation command.",
  "evidence": {
    "path": "docs/BLENDER_JOB_CONTEXT.md",
    "scope": "prepared-job-cancellation",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Reviewed the cancel_prepared saved-job action for prepared model and workflow intents, including submissions queued in the current session. The native operator confirms through invoke_confirm and calls runtime.cancel_prepared_job, the command used by MCP cancel_prepared_job, with the context token and observed revision; ModelJobs.control rejects it. The shared command updates an existing view; a queued submission rejected by a canceled record is not reported as a failed submission. Installed native tests on macOS arm64 Blender 5.1.2 cover offered states, zero service requests, persisted cancellation, stale revision and changed context rejection, a shared command call path and a queued submission that never dispatches. Prompt and translate intents are not offered here. No desktop confirmation-dialog interaction, screenshot, Blender 5.0/5.2 run, remote cancellation change or live acceptance is claimed. Other document claims retain their separate evidence.",
    "sources": {
      "scenario/blender/runtime.py": "3f7a1467c516c11642bc81dfba323efa972fc5a6305e26f0d3f324dad3844981",
      "scenario/blender/job_recovery.py": "b5cfc9abef6ea4324616158292a84164e3211851463d8e58371e875dd0d7a796",
      "scenario/blender/model_jobs.py": "2c3e5ae36c87ef8be8194c2f5502c4f2ddb63f574a46c7823bf546292f551633",
      "scenario/blender/job_session.py": "3e25f86663d7024d22813e854aa26db84f64dc9a90f4b681c86961167f8a43d8",
      "scenario/core/jobs/coordinator.py": "a8b7efb39e74a1a34f350ff7274e2e714a06933383743744dd22e6e1b7d7096d",
      "scenario/core/jobs/workers.py": "716c07192e4fede52e5dcb696591d4183fd382bff34a72b695a51cddd41410a2",
      "scenario/mcp/tools_scenario.py": "5fa8768f9b8356fb9b5071cf7c889305b06e55905a72d4caf62114f9202b0f4d",
      "tests/blender/test_runtime_jobs.py": "51463a0b7bb672ea0fcc15189f4bf2de269eaaff8aac94f52fa59a4d82802a03",
      "tests/blender/test_model_generation.py": "05a97189a433b036e7cae5dc41ddbbe40374f4fa632eecec0e341819914e3a62",
      "tests/unit/test_job_workers.py": "f5210455f75ae2144c4e3dda971c1dca9dc8693691e10e5c067af5381250f7ad"
    }
  }
}
---

# Native prepared-job cancellation parity

Evidence for [the canonical document](../../BLENDER_JOB_CONTEXT.md).
