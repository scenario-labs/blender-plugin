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
    "base_revision": "1d86f53d3489b23f2447be69cb589140e2f3ba64",
    "limits": "Inspected export_film and publish_film_export origin/active checks (a re-publish checks the active owner and the issuing coordinator, not the origins it carries), placeholder release on render failure and retirement, issued staged-export tracking and the LocalExportWorker admission, cancellation and join. Unit tests use the actual coordinator with an offline SDK transport and simulated renders. No Scenario request or job record is involved. The coordinator re-checks destination shape, refuses a reused snapshot before reserving, and runs the free-space preflight after reserving so a missing folder is reported as such; LocalExportWorker refuses relative destinations before starting its thread. publish checks free space for the exact staged size before copying and cancellation again before replacing the placeholder. Re-reviewed after the session-level inactive delivery guard; the coordinator contract is unchanged. Re-reviewed after the rebase onto 72723f02, whose merged changes to the session, coordinator, workers and native test registry add Film review controls, upload retirement on deactivation, a restart-upload command, inference-only cancellation and two native test modules; export admission, delivery, retirement, shutdown ordering and thread ownership are unchanged, and the native export module stays registered. Re-reviewed after the bounded export shutdown: LocalExportWorker uses a daemon thread and its shutdown waits at most EXPORT_STOP_TIMEOUT (5 s) in total, logging a warning when a read blocked on file access keeps the thread alive; export_film registers a staged export only under the active check, so a render that finishes after deactivation registers none and never publishes. Unit tests simulate a blocked media read and a late render after retirement; both failed on the previous revision. The guide's shutdown wording was updated. Re-reviewed after the rebase onto 1d86f53d, whose merged session, coordinator, workers and native test registry changes add the saved-result preview scheduler with its dedicated ScenarioPreview lane in JobWorkers, trained-model route checks before quoting and three native test modules. The conflict resolution keeps both sides: deactivation closes the preview scheduler, cancels the export and then deactivates the workers, and shutdown releases preview copies with the rest of local ownership only once both the workers and the export thread have stopped, so a blocked export keeps them until the reaper shuts the session down again. Export admission, delivery, retirement and thread ownership are otherwise unchanged; the export thread stays separate from the job workers and the preview lane, and the native export module stays registered. The coordinator contract is unchanged; its merged trained-route and preview-lane commands do not touch export. Rechecked on 2026-10-13 after the shared installed-tool lookup: ffmpeg and ffprobe are now found by scenario/core/jobs/installed_tools.py (PATH first, then fixed macOS and Linux install folders; Windows uses PATH only) in media_probe.probe_tool, local_render.media_tools, local_export verification and film_export.verifier, and tests fake that lookup instead of shutil.which. This topic's claims are unchanged. Only the test_local_export.py fingerprint was refreshed; the review date and base revision are unchanged.",
    "sources": {
      "scenario/blender/job_session.py": "19e3964a7d15d913c4097f7802e765fc1b28b23c9f535716444535464cb062e8",
      "scenario/core/jobs/coordinator.py": "8a93052389141a9432378db73c944023c024bfafa64d8667b2a854b27253fe7c",
      "scenario/core/jobs/local_export.py": "222a920e32cef1bc861fb3c0d2e641c67e61f40cbe1b03af591c1bff8e0b60e4",
      "scenario/core/jobs/workers.py": "cbb6e04ddafe3cce7e30b2abd1cef9e7eba455c30ab929b654c484f8a1b23197",
      "tests/unit/test_local_export.py": "741bc8623f1d26a7b19a5639500d0fb3649889de7a066101d39f4b46f8f332c8"
    }
  }
}
---

Source evidence for [the canonical guide](../../JOB_COORDINATOR.md).
