---
{
  "type": "Evidence",
  "id": "docs-job-coordinator.remote-progress-projection",
  "title": "Active refresh progress stays in memory",
  "description": "Coordinator snapshots feed an unpersisted progress reading.",
  "evidence": {
    "path": "docs/JOB_COORDINATOR.md",
    "scope": "remote-progress-projection",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "4ca693cb8f0e02a5c27c12d39bedbbc166b4e725",
    "limits": "Reviewed that refresh_remote commits only terminal states and returns the existing RemoteSnapshot for an active status without a store write, and that progress.observe reads its status and progress without retaining the raw response. A unit test with the real SDK and a mock transport shows an active refresh keeps the saved record and revision and that no database file contains the fraction or status. The Blender projection is reviewed under BLENDER_JOB_CONTEXT; no live service response is claimed.",
    "sources": {
      "scenario/core/jobs/coordinator.py": "b8d5dc049f1f6284f6c74224da07b39e184ab28c2c1e1d5bd7957dd0b5ef8be3",
      "scenario/core/jobs/progress.py": "bf8bea9be0d1ba3c6ca7c2495fecf61eb67481ffb7499d1e30633cc154871af5",
      "tests/unit/test_job_coordinator.py": "4720568bbce431110195efdc59f342a5955b18f26c0c42fe1f245daf434683fd",
      "tests/unit/test_job_progress.py": "c6ab3586b2b9ae8f4abf957a36b066b20cb8f01259fda6d9db5c858b11204a17"
    }
  }
}
---

# Active refresh progress stays in memory

Evidence for [the canonical document](../../JOB_COORDINATOR.md).
