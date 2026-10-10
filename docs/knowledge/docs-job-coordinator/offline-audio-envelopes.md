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
      "scenario/core/jobs/coordinator.py": "6c84cbc7bdac5c0b130d8afc859faa95a06b1bfe8390449f8e8ceab61263391b",
      "scenario/core/jobs/results.py": "58491953638b6401ec26771c8eb98ee5ff79019cd1708888398800ca32d1c813",
      "scenario/core/jobs/result_previews.py": "613ba1dcd0c807b0300fcad030739185bbe45a04a53de481f1c42652fd35ed73",
      "scenario/core/jobs/workers.py": "fb361cbf1291e9dc426502ba4eaf6a538bebd15a80da9f02dacac8c8fa466dc9",
      "scenario/core/jobs/audio_decode.py": "45d1cc7aa8964ad0b7014bf28a23f3d3a46e336eee4770581e79a8aa293d0064",
      "tests/unit/test_result_previews.py": "9d53eef20f77833a05dfb1779e84a3c81bebfeebb1d21c2a1172a4a50187c833",
      "tests/unit/test_job_workers.py": "433229194bd6dc327f3f076f0f3c73ac919fb6df108a97bd6b99f9ff3346bca5"
    }
  }
}
---

# Preview-lane audio envelope decode command

Evidence for [the canonical guide](../../JOB_COORDINATOR.md).
