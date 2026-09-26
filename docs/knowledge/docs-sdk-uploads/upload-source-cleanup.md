---
{
  "type": "Evidence",
  "id": "docs-sdk-uploads.upload-source-cleanup",
  "title": "docs/SDK_UPLOADS.md: finished upload source cleanup",
  "description": "Explicit verified cleanup of known terminal upload snapshots.",
  "evidence": {
    "path": "docs/SDK_UPLOADS.md",
    "scope": "upload-source-cleanup",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-26",
    "base_revision": "7db50f17a398178ae00f573d2e226b2f5c2325d7",
    "limits": "Reviewed scoped terminal-state admission, source hash and path checks, final owner/record guard, no recursive or original-file deletion, unchanged durable records and explicit retry after partial cleanup. Offline and installed fixtures cover context retirement, restart, malformed storage, interruptions and worker/main-thread boundaries. No protection against hostile replacement between filesystem calls, remote abort, automatic retention, unrecorded orphan deletion, active UI/MCP controls or live service acceptance is established. Other document claims retain their separate evidence.",
    "sources": {
      "scenario/core/jobs/upload_sources.py": "f5f6753769edd85c1a720408ed2eb174793a3336dfd96417196963994dbecdc3",
      "scenario/core/jobs/uploads.py": "fee6cebbb4cf6b8390b788a053fa9ba882f512182c40216f0656670c0319604d",
      "scenario/core/jobs/upload_store.py": "e53e44059fba806e5284f75327277fc7dcfceb7cd8a5f77e7a57696ce6372cf8",
      "scenario/core/jobs/coordinator.py": "b0d46de3342bc6e7afcb3acb4bde8fef8b07e6c5c502a4caa992a19b9560621c",
      "scenario/core/jobs/workers.py": "e270b7fc0a6064b110e85d1d67fcd182213d6924ed92193415344ca1b71f22cb",
      "scenario/blender/job_session.py": "e6a5b44eecac192219b50b5d41a5ede2e3bbf3c8f7b0a82ec0eb8b5b876b48f4",
      "tests/unit/test_upload_cleanup.py": "8fd481da53ff5b7fb404d26c65135bd950c3bffad81bc76164543b9334ec82c1",
      "tests/blender/test_session_uploads.py": "c51bc1488c072f02b6523f9ccc9f1efadfebca18c1ad94afae690dd4237f25f3"
    }
  }
}
---

# Finished upload source cleanup

Evidence for [the canonical document](../../SDK_UPLOADS.md).
