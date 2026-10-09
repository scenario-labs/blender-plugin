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
    "limits": "Inspected the shared-runtime connection of the preview scheduler, preview lane and cache root, including retirement that waits for an idle preview lane before shutdown. No view schedules previews; UI, MCP and live acceptance remain open.",
    "sources": {
      "scenario/blender/job_session.py": "f8ea693820df79a9e51d103873349f0e5d6512996841f0536dd091b15438757c",
      "scenario/blender/runtime.py": "7ba1a04feddcf53987879cd57406210f2aa9fe7aa7e2c3a1e9fcbd54714eef46",
      "scenario/core/jobs/workers.py": "39e769705a7ae81582906460f01efe648390149f67aa99352ca77e2cb6f6e98f",
      "scenario/core/jobs/preview_scheduler.py": "f9e20eaa003f7baafee3d8ddb78730b459741b2330bc8a21e9b6dff140efdc03"
    }
  }
}
---

# Result preview runtime component

Evidence for [the runtime map](../../architecture/runtime.md).
