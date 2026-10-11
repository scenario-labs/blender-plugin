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
    "limits": "Inspected export_film and publish_film_export origin/active checks (a re-publish checks the active owner and the issuing coordinator, not the origins it carries), placeholder release on render failure and retirement, issued staged-export tracking and the LocalExportWorker admission, cancellation and join. Unit tests use the actual coordinator with an offline SDK transport and simulated renders. No Scenario request or job record is involved. The coordinator re-checks destination shape, refuses a reused snapshot before reserving, and runs the free-space preflight after reserving so a missing folder is reported as such; LocalExportWorker refuses relative destinations before starting its thread. publish checks free space for the exact staged size before copying and cancellation again before replacing the placeholder. Re-reviewed after the session-level inactive delivery guard; the coordinator contract is unchanged. Re-reviewed after the rebase onto 72723f02, whose merged changes to the session, coordinator, workers and native test registry add Film review controls, upload retirement on deactivation, a restart-upload command, inference-only cancellation and two native test modules; export admission, delivery, retirement, shutdown ordering and thread ownership are unchanged, and the native export module stays registered. Re-reviewed after the bounded export shutdown: LocalExportWorker uses a daemon thread and its shutdown waits at most EXPORT_STOP_TIMEOUT (5 s) in total, logging a warning when a read blocked on file access keeps the thread alive; export_film registers a staged export only under the active check, so a render that finishes after deactivation registers none and never publishes. Unit tests simulate a blocked media read and a late render after retirement; both failed on the previous revision. The guide's shutdown wording was updated.",
    "sources": {
      "scenario/blender/job_session.py": "0ba497fdde65738c28b41c481aa8b95c93874a8a3d0d5a4a52fbdea3f69a9397",
      "scenario/core/jobs/coordinator.py": "bc513e99bc6fbf3d050edb2e340e8665570c69ab532d44eea939b158d742b2df",
      "scenario/core/jobs/local_export.py": "222a920e32cef1bc861fb3c0d2e641c67e61f40cbe1b03af591c1bff8e0b60e4",
      "scenario/core/jobs/workers.py": "b3486cf5c374172c56f438c9662ac77a67d7f796fc19274ea5b2a8fcba1fafdb",
      "tests/unit/test_local_export.py": "e9fc2544f802edf5d9ec472b5cf243a4dec9e3a5b52fe22256a1b90110d656d1"
    }
  }
}
---

Source evidence for [the canonical guide](../../JOB_COORDINATOR.md).
