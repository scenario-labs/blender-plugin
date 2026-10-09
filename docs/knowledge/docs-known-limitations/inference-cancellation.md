---
{
  "type": "Evidence",
  "id": "docs-known-limitations.inference-cancellation",
  "title": "Inference-only remote cancellation",
  "description": "Remote cancellation limited to documented inference jobs.",
  "evidence": {
    "path": "docs/KNOWN_LIMITATIONS.md",
    "scope": "inference-cancellation",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the coordinator predicate (CANCELLABLE_JOB_TYPES is inference only) and the ModelJobs offer, and the sanitized captured model-generation fixture, which reports jobType custom. Such jobs are not canceled from Blender, keep polling and stay recoverable. Which generation lanes return inference jobs, and live cancellation acceptance, are not established and remain under #65. Only the public job action reference (https://docs.scenario.com/api/resources/jobs/methods/trigger_action) and the pinned SDK 2.2.0 jobs.trigger_action docstring, both reading 'Today only cancel on inference jobs is supported', establish eligibility; no live service cancellation, no live check of which lanes return inference jobs and no desktop interaction or screenshot is claimed. Other document claims retain their separate evidence.",
    "sources": {
      "scenario/core/jobs/coordinator.py": "90762a0037ef21524495fdfd6fbae77b40171f59b2533ed043d4f0674901cb7b",
      "scenario/blender/model_jobs.py": "f87c0f601a18328379fb6049209fd9c0d84fb04892ae0c3f1d93ecece3b51fbe",
      "tests/fixtures/patina-copper-512/job.json": "6362ff219fc99e64d9d89edc31281c0efb68e3c3965ba5a53859698fa3189b73",
      "tests/unit/test_job_cancellation.py": "a2bc4d2af17a92f76351d48e60181a08a1ed7a165ccb70bb9658a4d09143cb44"
    }
  }
}
---

# Inference-only remote cancellation

Evidence for [the canonical document](../../KNOWN_LIMITATIONS.md).
