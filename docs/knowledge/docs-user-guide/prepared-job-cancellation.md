---
{
  "type": "Evidence",
  "id": "docs-user-guide.prepared-job-cancellation",
  "title": "Cancel prepared job in the Jobs panel",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "prepared-job-cancellation",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "fb699b8555f7cee62147794516cc7aaa224864f7",
    "limits": "Reviewed the Cancel prepared job saved-job control for unsent prepared generation, workflow, Film task, Blockout, Prompt Spark and Translate requests, including queued or restarted ones. Prompt, translate, Blockout and restarted requests get a Jobs panel row after Inspect saved jobs. It asks for confirmation (Discard unsent job), then cancels locally through the same command as MCP cancel_prepared_job without a service request; claimed, stale or changed-context jobs are rejected. The dialog warns that a canceled Film task stays reserved, which the store enforces by task identity. Installed native tests on macOS arm64 Blender 5.1.2 cover these paths with mocked transports and a mocked confirmation call. No desktop dialog interaction, screenshot, other Blender version or OS, or live acceptance is claimed. The Jobs panel row now draws this control from the shared saved_job_actions descriptors through panels.draw_active_job; its label, confirmation and command are unchanged. Later descriptor review fixes (a shared World media type constant, a parameter rename and docstring wording) leave this action unchanged. Other guide topics retain their own evidence.",
    "sources": {
      "scenario/blender/job_recovery.py": "4d4e1fc7bf4556f037a6abe9ca09ff3f76a0713950db334b63e8d376211e5370",
      "scenario/blender/model_jobs.py": "e1b28274e6f113c8279c3e2bb94ee66172844b55dd10cf59b3b504143c0aec72",
      "scenario/blender/prompt_jobs.py": "76cdeec9ee7c6db233634eff4825515a7d80961a32fe35f76a80386227ab55bf",
      "scenario/blender/runtime.py": "fb83ceaa622cbbfbea25210d2bb8d480231510d11712f58df34f45f41c13cf59",
      "scenario/blender/panels.py": "bed7253191c6652514967c599590ec667aa67790a726880a5cfc1fd4ed46877e",
      "scenario/core/jobs/store.py": "b05eab9cb9a8a83df55889d94acdbd162521e70f71150c15c46e21b62abc554d",
      "tests/blender/test_runtime_jobs.py": "9cbc0a763541264ae1c3f291a7754c09755066f60dc11f03206ba1fe8f398cf3",
      "tests/blender/test_model_generation.py": "8e15c26842a6daf591731259e77df4f47f1c829ab1227fa3ba42ba50ee7b1017",
      "tests/blender/test_prompt_tools.py": "f66677160a495f6d9cc9ed21fcb4a21d7df21835c427d7e13a11e7edbf9bf861",
      "scenario/blender/blockout_jobs.py": "56415f9205cd93f7cec15dc92520d379ea54ec8bb72f4d7c4920fff8cc287703",
      "tests/blender/test_blockout_jobs.py": "fd189d4cb712d98acb24e944857088378d327cb59455d858d4cdf64fce41e37e",
      "scenario/blender/blockout.py": "314a786af022272d8be5853613ff0f32d8a4d438b9472dadc3ac43c9116f70f8",
      "scenario/core/ui/saved_job_actions.py": "90e86afc6b3c727abfb6834961da55676e11cdffeb31e19543398b40d5c25ec9"
    }
  }
}
---

# Cancel prepared job in the Jobs panel

Evidence for [the canonical guide](../../USER_GUIDE.md).
