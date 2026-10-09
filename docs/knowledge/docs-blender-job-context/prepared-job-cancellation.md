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
    "base_revision": "fb699b8555f7cee62147794516cc7aaa224864f7",
    "limits": "Reviewed the cancel_prepared saved-job action for every prepared intent (model including Blockout, workflow, Film task, prompt and translate), including submissions queued in the current session. The native operator confirms through invoke_confirm with the title Cancel prepared job?, the confirm text Discard unsent job and, for an intent with a Film task binding, a note that the task stays reserved. It then calls runtime.cancel_prepared_job, the command used by MCP cancel_prepared_job, with the context token and observed revision; ModelJobs.control rejects it. The shared command updates an existing view. A queued model submission rejected by a canceled record is not reported as a failed submission, and the prompt field and the Blockout panel report a local cancellation instead of a stopped action. The store keeps a canceled Film task identity reserved. The MCP job_status description maps cancel_prepared to cancel_prepared_job. Installed native tests on macOS arm64 Blender 5.1.2 cover offered states including prompt and translate, the mocked confirmation call with its exact text leaving the record prepared at the same revision, zero service requests, persisted cancellation, stale revision and changed context rejection, a shared command call path, and queued model, translate and Blockout submissions that never dispatch. No desktop confirmation-dialog interaction, screenshot, Blender 5.0/5.2 run, remote cancellation change or live acceptance is claimed. Other document claims retain their separate evidence.",
    "sources": {
      "scenario/blender/runtime.py": "fb83ceaa622cbbfbea25210d2bb8d480231510d11712f58df34f45f41c13cf59",
      "scenario/blender/job_recovery.py": "4d4e1fc7bf4556f037a6abe9ca09ff3f76a0713950db334b63e8d376211e5370",
      "scenario/blender/model_jobs.py": "871f776b493890d35a74f4aaa67888b15ac6d33a1cdcaa0519eed0ce11140aab",
      "scenario/blender/prompt_jobs.py": "76cdeec9ee7c6db233634eff4825515a7d80961a32fe35f76a80386227ab55bf",
      "scenario/blender/job_session.py": "3e25f86663d7024d22813e854aa26db84f64dc9a90f4b681c86961167f8a43d8",
      "scenario/core/jobs/coordinator.py": "a8b7efb39e74a1a34f350ff7274e2e714a06933383743744dd22e6e1b7d7096d",
      "scenario/core/jobs/workers.py": "716c07192e4fede52e5dcb696591d4183fd382bff34a72b695a51cddd41410a2",
      "scenario/core/jobs/store.py": "b05eab9cb9a8a83df55889d94acdbd162521e70f71150c15c46e21b62abc554d",
      "scenario/mcp/tools_scenario.py": "69d5be07239f2f6c9503aa0b5ca86d4e0e1310f7d92b1de44cdbb409c88ab229",
      "tests/blender/test_runtime_jobs.py": "9cbc0a763541264ae1c3f291a7754c09755066f60dc11f03206ba1fe8f398cf3",
      "tests/blender/test_model_generation.py": "05a97189a433b036e7cae5dc41ddbbe40374f4fa632eecec0e341819914e3a62",
      "tests/blender/test_prompt_tools.py": "f66677160a495f6d9cc9ed21fcb4a21d7df21835c427d7e13a11e7edbf9bf861",
      "tests/unit/test_job_workers.py": "f5210455f75ae2144c4e3dda971c1dca9dc8693691e10e5c067af5381250f7ad",
      "scenario/blender/blockout_jobs.py": "56415f9205cd93f7cec15dc92520d379ea54ec8bb72f4d7c4920fff8cc287703",
      "tests/blender/test_blockout_jobs.py": "fd189d4cb712d98acb24e944857088378d327cb59455d858d4cdf64fce41e37e",
      "scenario/blender/blockout.py": "314a786af022272d8be5853613ff0f32d8a4d438b9472dadc3ac43c9116f70f8"
    }
  }
}
---

# Native prepared-job cancellation parity

Evidence for [the canonical document](../../BLENDER_JOB_CONTEXT.md).
