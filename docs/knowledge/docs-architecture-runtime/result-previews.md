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
    "base_revision": "fb699b8555f7cee62147794516cc7aaa224864f7",
    "limits": "Inspected the shared-runtime connection of the preview scheduler, preview lane and cache root, including retirement that waits for an idle preview lane before shutdown and a session that runs jobs without previews when the cache root cannot be created. No view schedules previews; UI, MCP and live acceptance remain open.",
    "sources": {
      "scenario/blender/job_session.py": "f8ea693820df79a9e51d103873349f0e5d6512996841f0536dd091b15438757c",
      "scenario/blender/runtime.py": "e7d96070a984d22c589b33c035597fec6f3b2eb53ae28551c3e26b82f6b5ee34",
      "scenario/core/jobs/workers.py": "39e769705a7ae81582906460f01efe648390149f67aa99352ca77e2cb6f6e98f",
      "scenario/core/jobs/preview_scheduler.py": "cb75fc5ff870438352430c331ea7a2a4a5d9da307dfb44ad9a44bfbdb2c5e7dc"
    }
  }
}
---

# Result preview runtime component

Evidence for [the runtime map](../../architecture/runtime.md).
