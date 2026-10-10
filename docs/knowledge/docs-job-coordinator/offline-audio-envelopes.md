---
{
  "type": "Evidence",
  "id": "docs-job-coordinator.offline-audio-envelopes",
  "title": "Preview-lane audio envelope decode command",
  "evidence": {
    "path": "docs/JOB_COORDINATOR.md",
    "scope": "offline-audio-envelopes",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "fb699b8555f7cee62147794516cc7aaa224864f7",
    "limits": "Inspected decode_result_preview from the workers' preview lane through the coordinator and result commands: early cancellation discards the copy, ownership and scope are checked, the copy is always removed, failures cache nothing and the task's cancellation event reaches the child process. Unit tests use a stand-in decoder; native coverage is in the result preview evidence. No job transition, revision change, network read or Scenario service call.",
    "sources": {
      "scenario/core/jobs/coordinator.py": "754bf1157082a887c30767c92e0f3a3604e2cfd4f1c5c6e15a118aee0e6b64ea",
      "scenario/core/jobs/results.py": "625d306accf972a65c20a01268be12c764d68eef48f2ae66d41b9fd1b8af17a1",
      "scenario/core/jobs/result_previews.py": "b08399a5f91362d9ccffa7ac615088f8dcd8c66984f86736245daca529dae741",
      "scenario/core/jobs/workers.py": "3389e06b6ec12eba09291ae7d66194c47ec2a86170bbd5079413c56cbf9651b3",
      "scenario/core/jobs/audio_decode.py": "45d1cc7aa8964ad0b7014bf28a23f3d3a46e336eee4770581e79a8aa293d0064",
      "tests/unit/test_result_previews.py": "1aaedd23563d63b78017e6bf72e33a825634a604abe105e8ab996fa4845b5929",
      "tests/unit/test_job_workers.py": "433229194bd6dc327f3f076f0f3c73ac919fb6df108a97bd6b99f9ff3346bca5"
    }
  }
}
---

# Preview-lane audio envelope decode command

Evidence for [the canonical guide](../../JOB_COORDINATOR.md).
