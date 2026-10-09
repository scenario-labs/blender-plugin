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
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Reviewed the Cancel prepared job saved-job control for unsent prepared generation, workflow, Film task, Prompt Spark and Translate requests, including queued or restarted ones. Prompt, translate and restarted requests get a Jobs panel row after Inspect saved jobs. It asks for confirmation (Discard unsent job), then cancels locally through the same command as MCP cancel_prepared_job without a service request; claimed, stale or changed-context jobs are rejected. The dialog warns that a canceled Film task stays reserved, which the store enforces by task identity. Installed native tests on macOS arm64 Blender 5.1.2 cover these paths with mocked transports and a mocked confirmation call. No desktop dialog interaction, screenshot, other Blender version or OS, or live acceptance is claimed. Other guide topics retain their own evidence.",
    "sources": {
      "scenario/blender/job_recovery.py": "4d4e1fc7bf4556f037a6abe9ca09ff3f76a0713950db334b63e8d376211e5370",
      "scenario/blender/model_jobs.py": "871f776b493890d35a74f4aaa67888b15ac6d33a1cdcaa0519eed0ce11140aab",
      "scenario/blender/prompt_jobs.py": "76cdeec9ee7c6db233634eff4825515a7d80961a32fe35f76a80386227ab55bf",
      "scenario/blender/runtime.py": "3f7a1467c516c11642bc81dfba323efa972fc5a6305e26f0d3f324dad3844981",
      "scenario/blender/panels.py": "0ea312ede072b4e25c8177120214d404b449ea60db10c02edd12ad5eb985d989",
      "scenario/core/jobs/store.py": "b05eab9cb9a8a83df55889d94acdbd162521e70f71150c15c46e21b62abc554d",
      "tests/blender/test_runtime_jobs.py": "9cbc0a763541264ae1c3f291a7754c09755066f60dc11f03206ba1fe8f398cf3",
      "tests/blender/test_model_generation.py": "05a97189a433b036e7cae5dc41ddbbe40374f4fa632eecec0e341819914e3a62",
      "tests/blender/test_prompt_tools.py": "f66677160a495f6d9cc9ed21fcb4a21d7df21835c427d7e13a11e7edbf9bf861"
    }
  }
}
---

# Cancel prepared job in the Jobs panel

Evidence for [the canonical guide](../../USER_GUIDE.md).
