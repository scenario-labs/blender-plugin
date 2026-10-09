---
{
  "type": "Evidence",
  "id": "docs-job-coordinator.offline-audio-envelopes",
  "title": "Preview-lane audio envelope decode command",
  "evidence": {
    "path": "docs/JOB_COORDINATOR.md",
    "scope": "offline-audio-envelopes",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "fb699b8555f7cee62147794516cc7aaa224864f7",
    "limits": "Inspected decode_result_preview from the workers' preview lane through the coordinator and result commands: early cancellation discards the copy, ownership and scope are checked, the copy is always removed, failures cache nothing and the task's cancellation event reaches the child process. Unit tests use a stand-in decoder; native coverage is in the result preview evidence. No job transition, revision change, network read or Scenario service call.",
    "sources": {
      "scenario/core/jobs/coordinator.py": "6c84cbc7bdac5c0b130d8afc859faa95a06b1bfe8390449f8e8ceab61263391b",
      "scenario/core/jobs/results.py": "58491953638b6401ec26771c8eb98ee5ff79019cd1708888398800ca32d1c813",
      "scenario/core/jobs/result_previews.py": "1bc82a1318619cb3771377caa6db67d107d6180a85575fbcc2d5470c087e5467",
      "scenario/core/jobs/workers.py": "fb361cbf1291e9dc426502ba4eaf6a538bebd15a80da9f02dacac8c8fa466dc9",
      "scenario/core/jobs/audio_decode.py": "4bc3c5a270ad36449e8927d580f9346075f737ad07da0a0b63967de4d81340ba",
      "tests/unit/test_result_previews.py": "d571f7848c51872570a9207a42a393e9b40e01b3e7ed8f0b9d7a2b545572addb",
      "tests/unit/test_job_workers.py": "433229194bd6dc327f3f076f0f3c73ac919fb6df108a97bd6b99f9ff3346bca5"
    }
  }
}
---

# Preview-lane audio envelope decode command

Evidence for [the canonical guide](../../JOB_COORDINATOR.md).
