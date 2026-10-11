---
{
  "type": "Evidence",
  "id": "docs-job-coordinator.offline-audio-envelopes",
  "title": "Preview-lane audio envelope decode command",
  "evidence": {
    "path": "docs/JOB_COORDINATOR.md",
    "scope": "offline-audio-envelopes",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-11",
    "base_revision": "72723f02a97a7226b1c697c31d8124b77ac92c86",
    "limits": "Inspected decode_result_preview from the workers' preview lane through the coordinator and result commands: early cancellation discards the copy, ownership and scope are checked, the copy is always removed, failures cache nothing and the task's cancellation event reaches the child process. Unit tests use a stand-in decoder; native coverage is in the result preview evidence. No job transition, revision change, network read or Scenario service call.",
    "sources": {
      "scenario/core/jobs/coordinator.py": "8ce208dec2c738fa4f7aacec6dab8a6dbcf2edc9f1b521c5c31f39b1c00e0b22",
      "scenario/core/jobs/results.py": "1102124a4b24585e4108551860e283d7ef32523b97870368cad135476795d12b",
      "scenario/core/jobs/result_previews.py": "b08399a5f91362d9ccffa7ac615088f8dcd8c66984f86736245daca529dae741",
      "scenario/core/jobs/workers.py": "df2830bcfd58445dcf67845e605f49a0305a103275a0aa8bf3d52450ae9a3658",
      "scenario/core/jobs/audio_decode.py": "45d1cc7aa8964ad0b7014bf28a23f3d3a46e336eee4770581e79a8aa293d0064",
      "tests/unit/test_result_previews.py": "39bd9c984b9e8c93a078b677bbe398167ed72fa57803f7db7f73320cf2ff548d",
      "tests/unit/test_job_workers.py": "433229194bd6dc327f3f076f0f3c73ac919fb6df108a97bd6b99f9ff3346bca5"
    }
  }
}
---

# Preview-lane audio envelope decode command

Evidence for [the canonical guide](../../JOB_COORDINATOR.md).
