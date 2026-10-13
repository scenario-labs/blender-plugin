---
{
  "type": "Evidence",
  "id": "docs-user-guide.prepared-job-cancellation",
  "title": "Cancel prepared job in the Jobs panel",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "prepared-job-cancellation",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-13",
    "base_revision": "3221af5a67583d5a992e9f25f9c41d00abed8924",
    "limits": "Reviewed the Cancel prepared job saved-job control for unsent prepared generation, workflow, Film task, Blockout, Prompt Spark and Translate requests, including queued or restarted ones. Prompt, translate, Blockout and restarted requests get a Jobs panel row after Inspect saved jobs. It asks for confirmation (Discard unsent job), then cancels locally through the same command as MCP cancel_prepared_job without a service request; claimed, stale or changed-context jobs are rejected. The dialog warns that a canceled Film task stays reserved, which the store enforces by task identity. Installed native tests on macOS arm64 Blender 5.1.2 cover these paths with mocked transports and a mocked confirmation call. No desktop dialog interaction, screenshot, other Blender version or OS, or live acceptance is claimed. Other guide topics retain their own evidence. Scoped 2026-10-10 check of the Render Video first-frame handoff, not a full re-review: runtime adds the prepare_first_frame_application facade with the same context-token check; other facades are unchanged. The claims above still hold; the review date and base revision are unchanged. On 2026-10-10 the runtime.py fingerprint was refreshed after saved splat import added option-aware model application wrappers; the prepared-job cancellation claims are unchanged, and the review date is unchanged. Jobs bullet on unconfirmed requests re-reviewed on 2026-10-13 against the coordinator guard, the native Mark reviewed action and its session-only mark.",
    "sources": {
      "scenario/blender/job_recovery.py": "8c5067cc8d07970bd7f644ae9f4e3bcd2f1a4240aa1e563fe0e9a67f471a3811",
      "scenario/blender/model_jobs.py": "e8a81c2f386fc5edb944da8e13e02a5d9769450d16fe8e34c215380a2535bcfc",
      "scenario/blender/prompt_jobs.py": "76cdeec9ee7c6db233634eff4825515a7d80961a32fe35f76a80386227ab55bf",
      "scenario/blender/runtime.py": "0a371030d406343469b9decdb549a0085429e251b46f2211e4cc2f4841f62e1f",
      "scenario/blender/panels.py": "bed7253191c6652514967c599590ec667aa67790a726880a5cfc1fd4ed46877e",
      "scenario/core/jobs/store.py": "4a6c2d23df588ba24882b6e727d3a5b77f87fee9b55eb49088ca19c02be7e445",
      "tests/blender/test_runtime_jobs.py": "9cbc0a763541264ae1c3f291a7754c09755066f60dc11f03206ba1fe8f398cf3",
      "tests/blender/test_model_generation.py": "b5ae7d892591ea6cca6d34e926f59bb87d004aee7807623a68470ccdb035a562",
      "tests/blender/test_prompt_tools.py": "939e959296a1eecefb5a87d3aa7f1ea0d7187e77427700f49ecf3fd4f796099b",
      "scenario/blender/blockout_jobs.py": "c388284557a0418ba5a036ecc0a184ad6d6c72f82d1fcff8191fe9d5ed3068f8",
      "tests/blender/test_blockout_jobs.py": "9e129f555919ddc76c2bfab279d6a55a9e27ed79ae9fcd73a95eed333b146eac",
      "scenario/blender/blockout.py": "314a786af022272d8be5853613ff0f32d8a4d438b9472dadc3ac43c9116f70f8",
      "scenario/core/jobs/coordinator.py": "c6c0f45e3ede225313e6524e3bba512b702e180ae91d6f8766c988037d442e81",
      "scenario/core/ui/saved_job_actions.py": "c511896cc54a046231f6a84b6b3a0fe5a4f3ac9ff92f46fe4d3610453eb69def"
    }
  }
}
---

# Cancel prepared job in the Jobs panel

Evidence for [the canonical guide](../../USER_GUIDE.md).
