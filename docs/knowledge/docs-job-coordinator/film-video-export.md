---
{
  "type": "Evidence",
  "id": "docs-job-coordinator.film-video-export",
  "title": "Owned offline Film video export",
  "evidence": {
    "path": "docs/JOB_COORDINATOR.md",
    "scope": "film-video-export",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Inspected export_film and publish_film_export origin/active checks, placeholder release on render failure and retirement, issued staged-export tracking and the LocalExportWorker admission, cancellation and join. Unit tests use the actual coordinator with an offline SDK transport and simulated renders. No Scenario request or job record is involved. The coordinator re-checks destination shape, refuses a reused snapshot before reserving, and runs the free-space preflight after reserving so a missing folder is reported as such; LocalExportWorker refuses relative destinations before starting its thread.",
    "sources": {
      "scenario/blender/job_session.py": "6eadb9ccb81a2a5c570980160ba9d20e5072136cccd5de71c6538920645bf11c",
      "scenario/core/jobs/coordinator.py": "58481d249c456139b8d228e7a91b3da4a6d0b03cfe0000e6ff53a5a27fc265f9",
      "scenario/core/jobs/local_export.py": "244d39066b8da9af7fd365e04313b54de46732bafbb0167a82111b4d142d4f79",
      "scenario/core/jobs/workers.py": "fcfd589ac62e4a5c4eb97eda55c5a68ee0894cb16911c3b10ede65adf8820dc0",
      "tests/unit/test_local_export.py": "3f0453957fa751f6ab9344eb0cc2e8ce05b47a7c979a681ec498a511c25aba3e"
    }
  }
}
---

Source evidence for [the canonical guide](../../JOB_COORDINATOR.md).
