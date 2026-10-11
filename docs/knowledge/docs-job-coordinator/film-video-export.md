---
{
  "type": "Evidence",
  "id": "docs-job-coordinator.film-video-export",
  "title": "Owned offline Film video export",
  "evidence": {
    "path": "docs/JOB_COORDINATOR.md",
    "scope": "film-video-export",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-11",
    "base_revision": "72723f02a97a7226b1c697c31d8124b77ac92c86",
    "limits": "Inspected export_film and publish_film_export origin/active checks (a re-publish checks the active owner and the issuing coordinator, not the origins it carries), placeholder release on render failure and retirement, issued staged-export tracking and the LocalExportWorker admission, cancellation and join. Unit tests use the actual coordinator with an offline SDK transport and simulated renders. No Scenario request or job record is involved. The coordinator re-checks destination shape, refuses a reused snapshot before reserving, and runs the free-space preflight after reserving so a missing folder is reported as such; LocalExportWorker refuses relative destinations before starting its thread. publish checks free space for the exact staged size before copying and cancellation again before replacing the placeholder. Re-reviewed after the session-level inactive delivery guard; the coordinator contract is unchanged. Re-reviewed after the rebase onto 72723f02, whose merged changes to the session, coordinator, workers and native test registry add Film review controls, upload retirement on deactivation, a restart-upload command, inference-only cancellation and two native test modules; export admission, delivery, retirement, shutdown ordering and thread ownership are unchanged, and the native export module stays registered.",
    "sources": {
      "scenario/blender/job_session.py": "c49b46b2d62815199cd4a1a1e0920900d577d38cdac9e6cbdf0150d4b1f690eb",
      "scenario/core/jobs/coordinator.py": "0fbcc48fcd785e870d468782352ebca63778e76e184d9e4e197cfdc6d9c1663e",
      "scenario/core/jobs/local_export.py": "3fe9dec68501ab40b6e292d41d4b62f54fd7049d4d47fdcde95feeb744c0e4a7",
      "scenario/core/jobs/workers.py": "7089d332f856f0c69218df0af8e8f1842a631f0476899dd2bcbbef0c2e2c1910",
      "tests/unit/test_local_export.py": "884432f51c50a8c7956528fc90bfc5c55307a97661606fbc25e3b8188a27bbec"
    }
  }
}
---

Source evidence for [the canonical guide](../../JOB_COORDINATOR.md).
