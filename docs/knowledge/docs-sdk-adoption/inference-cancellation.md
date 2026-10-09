---
{
  "type": "Evidence",
  "id": "docs-sdk-adoption.inference-cancellation",
  "title": "Inference-only cancellation boundary",
  "description": "Pinned SDK and public reference limit for job cancellation.",
  "evidence": {
    "path": "docs/SDK_ADOPTION.md",
    "scope": "inference-cancellation",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the pinned scenario-sdk 2.2.0 jobs.trigger_action docstring and JobTriggerActionParams, which document 'Today only cancel on inference jobs is supported', and the Job retrieve model, whose jobType enum lists custom, inference and workflow as distinct values. The adapter call is unchanged (jobs.with_raw_response.trigger_action with action cancel, selected project and max_retries=0); no fallback, endpoint or SDK issue is added. The coordinator accepts only a fresh inference observation and the native and MCP controls offer cancel only after one. test_scenario_sdk_contract.py fails if the docstring, enum or CANCELLABLE_JOB_TYPES change; tests/unit/test_job_cancellation.py covers refusal before any claim. Only the public job action reference (https://docs.scenario.com/api/resources/jobs/methods/trigger_action) and the pinned SDK 2.2.0 jobs.trigger_action docstring, both reading 'Today only cancel on inference jobs is supported', establish eligibility; no live service cancellation, no live check of which lanes return inference jobs and no desktop interaction or screenshot is claimed. Other document claims retain their separate evidence.",
    "sources": {
      "scenario/core/jobs/coordinator.py": "90762a0037ef21524495fdfd6fbae77b40171f59b2533ed043d4f0674901cb7b",
      "scenario/core/api/sdk_adapter.py": "aa638824ce7af67c9b70d12b759f361ab88f41cb0bc7f39213f1ce1d3e8d39ff",
      "scenario/blender/model_jobs.py": "f87c0f601a18328379fb6049209fd9c0d84fb04892ae0c3f1d93ecece3b51fbe",
      "tests/unit/test_scenario_sdk_contract.py": "c84d19e267339150b63ec4eb4d802f9cf15a17a7742399e3492fd4b03b805d4d",
      "tests/unit/test_job_cancellation.py": "a2bc4d2af17a92f76351d48e60181a08a1ed7a165ccb70bb9658a4d09143cb44",
      "tests/fixtures/patina-copper-512/job.json": "6362ff219fc99e64d9d89edc31281c0efb68e3c3965ba5a53859698fa3189b73",
      "uv.lock": "a7b510cd1251679c6ff54186dffd8ca2a18da32a414dc1b427715da9f411a51d"
    }
  }
}
---

# Inference-only cancellation boundary

Evidence for [the canonical document](../../SDK_ADOPTION.md).
