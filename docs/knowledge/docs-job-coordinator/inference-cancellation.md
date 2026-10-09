---
{
  "type": "Evidence",
  "id": "docs-job-coordinator.inference-cancellation",
  "title": "Inference-only remote cancellation",
  "description": "Coordinator eligibility for durable remote cancellation claims.",
  "evidence": {
    "path": "docs/JOB_COORDINATOR.md",
    "scope": "inference-cancellation",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed JobCoordinator.cancel_remote: after the existing scope, revision, remote-state and model-operation checks and a fresh SDKAdapter.job retrieval, a terminal observation is still committed without an action, and an active job is claimed only when cancellable_job reports jobType inference (CANCELLABLE_JOB_TYPES). Every other value, including custom from the captured fixture, workflow, model-training, upload, None, a list and other spellings, raises CancellationUnsupported, a RecoveryError, before the CAS claim, so the record keeps its state and revision, no POST is sent, recovery_plan still suggests polling and refresh_remote can commit the eventual result. The durable claim, single action, uncertainty and restart semantics are unchanged and their tests now use inference responses. Unit tests reproduce the former behavior on the captured custom job (claimed and sent before this change) and cover the predicate; an SDK contract test pins the docstring, the distinct custom, inference and workflow enum values and the predicate. Installed native tests on macOS arm64 Blender 5.1.2 cover these claims through the packaged extension with a mock transport. Only the public job action reference (https://docs.scenario.com/api/resources/jobs/methods/trigger_action) and the pinned SDK 2.2.0 jobs.trigger_action docstring, both reading 'Today only cancel on inference jobs is supported', establish eligibility; no live service cancellation, no live check of which lanes return inference jobs and no desktop interaction or screenshot is claimed. Other document claims retain their separate evidence.",
    "sources": {
      "scenario/core/jobs/coordinator.py": "90762a0037ef21524495fdfd6fbae77b40171f59b2533ed043d4f0674901cb7b",
      "scenario/core/api/sdk_adapter.py": "aa638824ce7af67c9b70d12b759f361ab88f41cb0bc7f39213f1ce1d3e8d39ff",
      "tests/unit/test_job_cancellation.py": "a2bc4d2af17a92f76351d48e60181a08a1ed7a165ccb70bb9658a4d09143cb44",
      "tests/unit/test_scenario_sdk_contract.py": "c84d19e267339150b63ec4eb4d802f9cf15a17a7742399e3492fd4b03b805d4d",
      "tests/fixtures/patina-copper-512/job.json": "6362ff219fc99e64d9d89edc31281c0efb68e3c3965ba5a53859698fa3189b73",
      "tests/blender/test_job_session.py": "7ae4a36b3377ae74605f3cbd2826f64c43c4aa76eb74bc49fae7cfde69e9097f",
      "tests/blender/test_job_store.py": "087bef69c1cb54fef2cdb17bce62b0b0b1a688b2743f7a9716667225fe06b47c"
    }
  }
}
---

# Inference-only remote cancellation

Evidence for [the canonical document](../../JOB_COORDINATOR.md).
