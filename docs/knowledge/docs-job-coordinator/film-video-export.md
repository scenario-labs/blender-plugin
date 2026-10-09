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
    "base_revision": "fb699b8555f7cee62147794516cc7aaa224864f7",
    "limits": "Inspected export_film and publish_film_export origin/active checks (a re-publish checks the active owner and the issuing coordinator, not the origins it carries), placeholder release on render failure and retirement, issued staged-export tracking and the LocalExportWorker admission, cancellation and join. Unit tests use the actual coordinator with an offline SDK transport and simulated renders. No Scenario request or job record is involved. The coordinator re-checks destination shape, refuses a reused snapshot before reserving, and runs the free-space preflight after reserving so a missing folder is reported as such; LocalExportWorker refuses relative destinations before starting its thread. publish checks free space for the exact staged size before copying and cancellation again before replacing the placeholder. Re-reviewed after the session-level inactive delivery guard; the coordinator contract is unchanged.",
    "sources": {
      "scenario/blender/job_session.py": "35f3181e2c6f9be8f0d4ca1c18b6cf46d2d0e04bc0d2c6790c8d86ea206c5942",
      "scenario/core/jobs/coordinator.py": "58481d249c456139b8d228e7a91b3da4a6d0b03cfe0000e6ff53a5a27fc265f9",
      "scenario/core/jobs/local_export.py": "3fe9dec68501ab40b6e292d41d4b62f54fd7049d4d47fdcde95feeb744c0e4a7",
      "scenario/core/jobs/workers.py": "fcfd589ac62e4a5c4eb97eda55c5a68ee0894cb16911c3b10ede65adf8820dc0",
      "tests/unit/test_local_export.py": "884432f51c50a8c7956528fc90bfc5c55307a97661606fbc25e3b8188a27bbec"
    }
  }
}
---

Source evidence for [the canonical guide](../../JOB_COORDINATOR.md).
