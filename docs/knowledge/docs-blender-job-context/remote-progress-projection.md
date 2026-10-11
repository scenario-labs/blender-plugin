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
    "reviewed_at": "2026-10-11",
    "base_revision": "72723f02a97a7226b1c697c31d8124b77ac92c86",
    "limits": "Reviewed that ModelJobs._observe is the only display consumer of ModelJobs-owned refresh_remote and cancel_remote snapshots and calls progress.observe; _observe_cancellation, which decides the inference cancel offer, reads the same completion inside the delivery exception mapping without draining it again. progress.observe yields a reading only for a remote or cancel_requested record whose response jobId matches and whose status is one of the five active SDK statuses. PromptJobs and BlockoutJobs still issue and drain their own refresh_remote and project no progress, so the document's single display consumer statement holds for ModelJobs commands only. _observe runs after the next poll is scheduled and outside the delivery exception mapping; a failing projection drops the reading, logs only the exception type and never pauses delivery. Booleans, strings, missing, non-finite and out-of-range fractions become None; percent exists only for in-progress or finalizing above zero and floors round(fraction * 100, 6), so 0.29 shows 29. Each poll drops a reading when the state, remote ID or revision changes and marks it stale when Online Access is off, delivery is paused or the scheduled poll time plus STALE_GRACE has passed. Active refreshes keep the saved revision; nothing is persisted. ModelJobs._delivering is the one predicate for wait() and MCP delivery_active: _advancing counts prepared only while queued, ready only while an automatic import is pending and succeeded only when downloads_results holds, decided from the saved intent (workflow, or a model operation whose target is not the Blockout text model, which covers Film tasks submitted through ModelJobs and cloud jobs whose CloudJobIntent operation is model); _delivering further excludes remote, cancel_requested and succeeded while the Online Access value recorded by the last main-thread poll is off, and _offline reports exactly that hold for an advancing job as delivery_offline, so wait() reads no bpy on the HTTP worker. _display_status keeps succeeded for prompt, translate and Blockout records, and ModelJobs.poll starts download_results only when downloads_results holds; actions() offers no resume for them in succeeded. ModelJobs.submit records JobBinding(scene session_uid, lane) before dispatch for UI and MCP model lanes; workflow and Film submissions are unbound; bound_views reads only in-memory dictionaries; bindings retire with their owner. Unit tests cover validation, display words, percent snapping and the SDK status literal set. Installed tests cover UI and MCP binding, a 0.42 projection, an invalid fraction, terminal clearing, revision and remote ID mismatch drops, a failed projection that keeps delivery and polling, a cancel_remote completion for an inference job rebound to the cancel_requested revision, offline and overdue staleness, explicit refresh after restart, credential and file retirement, binding stability across real memfile undo and redo, an unbound workflow submission, wait parity, an offline wait that returns without polling, a prepared job that was never queued, finished Prompt Spark, Translate and Blockout jobs that stay terminal after Inspect saved jobs, and a restarted Blockout plan resumed to succeeded without a download command. Installed native tests on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 cover these claims. No desktop interaction, screenshot, other operating system or live provider progress is claimed. Film tasks and cloud jobs downloading, and Film submissions being unbound, are established by code review only. No compact composer surface uses the binding yet.",
    "sources": {
      "scenario/core/jobs/progress.py": "bf8bea9be0d1ba3c6ca7c2495fecf61eb67481ffb7499d1e30633cc154871af5",
      "scenario/blender/model_jobs.py": "8046852c9bb43eca3d5cb0b987c06df473b99e66cbc6cc5b66c245c38ea2f482",
      "scenario/core/jobs/coordinator.py": "86d723261acb1fda7ef9718248be03c46de52cf6086277f15b673a46487551f5",
      "tests/unit/test_job_progress.py": "c6ab3586b2b9ae8f4abf957a36b066b20cb8f01259fda6d9db5c858b11204a17",
      "tests/blender/test_model_generation.py": "26f6c6d95667096e50c4df2ba93d3fa37bf253cd64245ac6ca614dc3a47291f9",
      "tests/blender/test_workflow_commands.py": "74086c3122b3c83103e08072be6669e510ac1026a1da6cbb6f0eeaa1c0f49338",
      "tests/blender/helpers.py": "de6a4841486130ed22e5a67d006fe859b27d2f0af5246ca4d87b9229d2a298f5",
      "tests/blender/test_prompt_tools.py": "3337cbe8e763b7436c69394e3de5b056dd2f02156acc5da3de8307267c275dde",
      "tests/blender/test_blockout_jobs.py": "6151fbd3136147da03d6221962fb8492dd67f60fa2f0748687a44b1367e575b4"
    }
  }
}
---

# Remote progress readings and scene lane bindings

Evidence for [the canonical document](../../BLENDER_JOB_CONTEXT.md).
