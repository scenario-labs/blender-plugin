---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.result-previews",
  "title": "Result preview runtime component",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "scope": "result-previews",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Inspected the shared-runtime connection of the preview scheduler, preview lane and cache root, including retirement that waits for an idle preview lane before shutdown and a session that runs jobs without previews when the cache root cannot be created. No view schedules previews; UI, MCP and live acceptance remain open.",
    "sources": {
      "scenario/blender/job_session.py": "a47e759441bddfd645e1dd17626600dc3c81d1e0938488619d31c69f11f804d2",
      "scenario/blender/runtime.py": "aa199b156270fbc86aa6dbc5edf30096dddac7e69de6cc1ea905d5619b2a51bb",
      "scenario/core/jobs/workers.py": "39e769705a7ae81582906460f01efe648390149f67aa99352ca77e2cb6f6e98f",
      "scenario/core/jobs/preview_scheduler.py": "cb75fc5ff870438352430c331ea7a2a4a5d9da307dfb44ad9a44bfbdb2c5e7dc"
    }
  }
}
---

# Result preview runtime component

Evidence for [the runtime map](../../architecture/runtime.md).
