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
    "limits": "Inspected export_film and publish_film_export origin/active checks (a re-publish checks the active owner and the issuing coordinator, not the origins it carries), placeholder release on render failure and retirement, issued staged-export tracking and the LocalExportWorker admission, cancellation and join. Unit tests use the actual coordinator with an offline SDK transport and simulated renders. No Scenario request or job record is involved. The coordinator re-checks destination shape, refuses a reused snapshot before reserving, and runs the free-space preflight after reserving so a missing folder is reported as such; LocalExportWorker refuses relative destinations before starting its thread. publish checks free space for the exact staged size before copying and cancellation again before replacing the placeholder.",
    "sources": {
      "scenario/blender/job_session.py": "070652fa2d92e43b01989823ef4bd20bc43bc6559a131a43297afc9b3ce8a498",
      "scenario/core/jobs/coordinator.py": "58481d249c456139b8d228e7a91b3da4a6d0b03cfe0000e6ff53a5a27fc265f9",
      "scenario/core/jobs/local_export.py": "3fe9dec68501ab40b6e292d41d4b62f54fd7049d4d47fdcde95feeb744c0e4a7",
      "scenario/core/jobs/workers.py": "fcfd589ac62e4a5c4eb97eda55c5a68ee0894cb16911c3b10ede65adf8820dc0",
      "tests/unit/test_local_export.py": "884432f51c50a8c7956528fc90bfc5c55307a97661606fbc25e3b8188a27bbec"
    }
  }
}
---

Source evidence for [the canonical guide](../../JOB_COORDINATOR.md).
