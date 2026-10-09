---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.film-video-export",
  "title": "Owned offline Film video export",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "scope": "film-video-export",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Inspected the session-owned export thread and its independence from the shared workers and local media slot. Native/MCP export controls and the case-study bundle remain unimplemented. At this revision a local macOS arm64 run of the full installed suite passes on Blender 5.1.2, including a real child export verified by Blender's decode check and by an installed ffprobe; earlier revisions of this module also passed locally on 5.0.1 and 5.2.1. Linux and Windows evidence is the PR CI installed baseline on Blender 5.0.1, 5.1.2 and 5.2.1, which runs this module. No human playback, desktop interaction or native/MCP control is established. Destination policy is enforced by the session before the owned thread starts; the coordinator re-checks the portable shape.",
    "sources": {
      "scenario/blender/job_session.py": "070652fa2d92e43b01989823ef4bd20bc43bc6559a131a43297afc9b3ce8a498",
      "scenario/core/jobs/coordinator.py": "58481d249c456139b8d228e7a91b3da4a6d0b03cfe0000e6ff53a5a27fc265f9",
      "scenario/core/jobs/local_export.py": "3fe9dec68501ab40b6e292d41d4b62f54fd7049d4d47fdcde95feeb744c0e4a7",
      "scenario/core/jobs/workers.py": "fcfd589ac62e4a5c4eb97eda55c5a68ee0894cb16911c3b10ede65adf8820dc0"
    }
  }
}
---

Source evidence for [the canonical guide](../../architecture/runtime.md).
