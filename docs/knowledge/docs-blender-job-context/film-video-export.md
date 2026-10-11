---
{
  "type": "Evidence",
  "id": "docs-blender-job-context.film-video-export",
  "title": "Owned offline Film video export",
  "evidence": {
    "path": "docs/BLENDER_JOB_CONTEXT.md",
    "scope": "film-video-export",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-11",
    "base_revision": "1d86f53d3489b23f2447be69cb589140e2f3ba64",
    "limits": "Inspected JobSession export admission, drain flagging, delivery without scene resolution, cancellation, retirement and shutdown ordering. Installed tests cover owned-thread delivery, mid-render retirement and copy-only re-publish. Before the rebase onto 72723f02, a local macOS arm64 run of the full installed suite passed on Blender 5.1.2, including a real child export verified by Blender's decode check and by an installed ffprobe; earlier revisions of this module also passed locally on 5.0.1 and 5.2.1. Linux and Windows evidence is the PR CI installed baseline on Blender 5.0.1, 5.1.2 and 5.2.1, which runs this module. No human playback, desktop interaction or native/MCP control is established. export_film and publish_film_export validate destinations on the main thread against staging, extension and Blender user storage; export_film also refuses a reused snapshot or a child other than this Blender with the bundled worker, all before any thread, placeholder or media hash. Installed tests cover relative, private, existing and non-portable refusals, reuse and a foreign Blender or worker. deliver_local_export now refuses an inactive session, as the asset library, workflow catalog and cloud read deliveries do, even while a failed shutdown still holds issued outcomes; an installed test retires the session with an issued receipt, checks the refusal and that the published file is kept, and failed on the previous revision. Re-reviewed after the rebase onto 72723f02, whose merged changes to the session, coordinator, workers and native test registry add Film review controls, upload retirement on deactivation, a restart-upload command, inference-only cancellation and two native test modules; export admission, delivery, retirement, shutdown ordering and thread ownership are unchanged, and the native export module stays registered. Re-reviewed after the bounded export shutdown: LocalExportWorker uses a daemon thread and its shutdown waits at most EXPORT_STOP_TIMEOUT (5 s) in total, logging a warning when a read blocked on file access keeps the thread alive. JobSession.shutdown then keeps the session owned until _reap_inactive finds the task done and shuts it down again; an inactive session never delivers the late outcome. An installed test blocks the media hash, checks the bound, retained ownership, the reaper release and that nothing is published. The guide's shutdown wording was updated. Re-reviewed after the rebase onto 1d86f53d, whose merged session, coordinator, workers and native test registry changes add the saved-result preview scheduler with its dedicated ScenarioPreview lane in JobWorkers, trained-model route checks before quoting and three native test modules. The conflict resolution keeps both sides: deactivation closes the preview scheduler, cancels the export and then deactivates the workers, and shutdown releases preview copies with the rest of local ownership only once both the workers and the export thread have stopped, so a blocked export keeps them until the reaper shuts the session down again. Export admission, delivery, retirement and thread ownership are otherwise unchanged; the export thread stays separate from the job workers and the preview lane, and the native export module stays registered. A local macOS arm64 installed run of the full suite on Blender 5.1.2 at the rebased head ran 1386 tests with 3 skips and one failure, the known saved-job action label case in test_result_actions; 16 of the 17 export tests passed, including both real child exports, and the Windows-only deep-path test was skipped. The guide now says a blocked export also keeps the session's saved-result preview copies until then.",
    "sources": {
      "scenario/blender/job_session.py": "19e3964a7d15d913c4097f7802e765fc1b28b23c9f535716444535464cb062e8",
      "scenario/core/jobs/coordinator.py": "8a93052389141a9432378db73c944023c024bfafa64d8667b2a854b27253fe7c",
      "scenario/core/jobs/workers.py": "cbb6e04ddafe3cce7e30b2abd1cef9e7eba455c30ab929b654c484f8a1b23197",
      "tests/blender/test_film_export_primitive.py": "4f2603a3f7eeec9202263efa4ba7707ab9a0751cd4fa8c848ea954bbe828d33b",
      "tests/unit/test_local_export.py": "e9fc2544f802edf5d9ec472b5cf243a4dec9e3a5b52fe22256a1b90110d656d1"
    }
  }
}
---

Source evidence for [the canonical guide](../../BLENDER_JOB_CONTEXT.md).
