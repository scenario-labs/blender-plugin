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
    "base_revision": "72723f02a97a7226b1c697c31d8124b77ac92c86",
    "limits": "Inspected the session-owned export thread and its independence from the shared workers and local media slot. Native/MCP export controls and the case-study bundle remain unimplemented. Before the rebase onto 72723f02, a local macOS arm64 run of the full installed suite passed on Blender 5.1.2, including a real child export verified by Blender's decode check and by an installed ffprobe; earlier revisions of this module also passed locally on 5.0.1 and 5.2.1. Linux and Windows evidence is the PR CI installed baseline on Blender 5.0.1, 5.1.2 and 5.2.1, which runs this module. No human playback, desktop interaction or native/MCP control is established. Destination policy is enforced by the session before the owned thread starts; the coordinator re-checks the portable shape. Re-reviewed after the inactive-session delivery guard; thread ownership is unchanged. Re-reviewed after the rebase onto 72723f02, whose merged changes to the session, coordinator, workers and native test registry add Film review controls, upload retirement on deactivation, a restart-upload command, inference-only cancellation and two native test modules; export admission, delivery, retirement, shutdown ordering and thread ownership are unchanged, and the native export module stays registered. The guide's export wording was reconciled with the merged Film review controls: review scenes now have native/MCP controls, while export still has none. Re-reviewed after the even default size and bounded export shutdown (LocalExportWorker uses a daemon thread and its shutdown waits at most EXPORT_STOP_TIMEOUT (5 s) in total, logging a warning when a read blocked on file access keeps the thread alive); the runtime summary remains accurate.",
    "sources": {
      "scenario/blender/job_session.py": "0ba497fdde65738c28b41c481aa8b95c93874a8a3d0d5a4a52fbdea3f69a9397",
      "scenario/core/jobs/coordinator.py": "bc513e99bc6fbf3d050edb2e340e8665570c69ab532d44eea939b158d742b2df",
      "scenario/core/jobs/local_export.py": "222a920e32cef1bc861fb3c0d2e641c67e61f40cbe1b03af591c1bff8e0b60e4",
      "scenario/core/jobs/workers.py": "b3486cf5c374172c56f438c9662ac77a67d7f796fc19274ea5b2a8fcba1fafdb"
    }
  }
}
---

Source evidence for [the canonical guide](../../architecture/runtime.md).
