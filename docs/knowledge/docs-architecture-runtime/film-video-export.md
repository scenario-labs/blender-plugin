---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.film-video-export",
  "title": "Owned offline Film video export",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "scope": "film-video-export",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-11",
    "base_revision": "7fb15252f747f52db24f7e659f8d5048241f803e",
    "limits": "Inspected the session-owned export thread and its independence from the shared workers and local media slot. Native/MCP export controls and the case-study bundle remain unimplemented. Before the rebase onto 72723f02, a local macOS arm64 run of the full installed suite passed on Blender 5.1.2, including a real child export verified by Blender's decode check and by an installed ffprobe; earlier revisions of this module also passed locally on 5.0.1 and 5.2.1. Linux and Windows evidence is the PR CI installed baseline on Blender 5.0.1, 5.1.2 and 5.2.1, which runs this module. No human playback, desktop interaction or native/MCP control is established. Destination policy is enforced by the session before the owned thread starts; the coordinator re-checks the portable shape. Re-reviewed after the inactive-session delivery guard; thread ownership is unchanged. Re-reviewed after the rebase onto 72723f02, whose merged changes to the session, coordinator, workers and native test registry add Film review controls, upload retirement on deactivation, a restart-upload command, inference-only cancellation and two native test modules; export admission, delivery, retirement, shutdown ordering and thread ownership are unchanged, and the native export module stays registered. The guide's export wording was reconciled with the merged Film review controls: review scenes now have native/MCP controls, while export still has none. Re-reviewed after the even default size and bounded export shutdown (LocalExportWorker uses a daemon thread and its shutdown waits at most EXPORT_STOP_TIMEOUT (5 s) in total, logging a warning when a read blocked on file access keeps the thread alive); the runtime summary remains accurate. Re-reviewed after the rebase onto 7fb15252, whose merged session, coordinator, workers and native test registry changes add the saved-result preview scheduler with its dedicated ScenarioPreview lane in JobWorkers, trained-model route checks before quoting and three native test modules. The conflict resolution keeps both sides: deactivation closes the preview scheduler, cancels the export and then deactivates the workers, and shutdown releases preview copies with the rest of local ownership only once both the workers and the export thread have stopped, so a blocked export keeps them until the reaper shuts the session down again. Export admission, delivery, retirement and thread ownership are otherwise unchanged; the export thread stays separate from the job workers and the preview lane, and the native export module stays registered. A local macOS arm64 installed run of the full suite on Blender 5.1.2 at the rebased head ran 1386 tests with 3 skips and one failure, the known saved-job action label case in test_result_actions; 16 of the 17 export tests passed, including both real child exports, and the Windows-only deep-path test was skipped. The runtime summary remains accurate.",
    "sources": {
      "scenario/blender/job_session.py": "19e3964a7d15d913c4097f7802e765fc1b28b23c9f535716444535464cb062e8",
      "scenario/core/jobs/coordinator.py": "8a93052389141a9432378db73c944023c024bfafa64d8667b2a854b27253fe7c",
      "scenario/core/jobs/local_export.py": "222a920e32cef1bc861fb3c0d2e641c67e61f40cbe1b03af591c1bff8e0b60e4",
      "scenario/core/jobs/workers.py": "cbb6e04ddafe3cce7e30b2abd1cef9e7eba455c30ab929b654c484f8a1b23197"
    }
  }
}
---

Source evidence for [the canonical guide](../../architecture/runtime.md).
