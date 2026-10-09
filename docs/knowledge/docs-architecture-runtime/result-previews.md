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
    "limits": "Inspected the shared-runtime connection of the preview scheduler, preview lane and cache root. No view schedules previews; UI, MCP and live acceptance remain open.",
    "sources": {
      "scenario/blender/job_session.py": "a4a5a108a4b500ce09448f027243973a6116f8e615bcc7444902a561741a772d",
      "scenario/blender/runtime.py": "5c7d192dcdc8cbfc0b3e3d13d4e786d8bbaee67b855d6deaad80eaf0b08d746d",
      "scenario/core/jobs/workers.py": "ff77957be1e66ca7f24abc04b9378a39ca9f3db7959e00abc326f5fb6b0b2f66",
      "scenario/core/jobs/preview_scheduler.py": "4a8d4924e4e959be28ab314ddce976f5e7290cf461ae8e784475e185da0d28f7"
    }
  }
}
---

# Result preview runtime component

Evidence for [the runtime map](../../architecture/runtime.md).
