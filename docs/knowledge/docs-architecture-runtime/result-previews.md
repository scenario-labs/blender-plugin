---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.result-previews",
  "title": "Result preview runtime component",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "scope": "result-previews",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Inspected the shared-runtime connection of the preview scheduler, preview lane and cache root, including retirement that waits for an idle preview lane before shutdown, a maintenance-only preview lane command that keeps the cache budget once previews settle, and a session that runs jobs without previews when the cache root cannot be created. No view schedules previews; UI, MCP and live acceptance remain open.",
    "sources": {
      "scenario/blender/job_session.py": "a47e759441bddfd645e1dd17626600dc3c81d1e0938488619d31c69f11f804d2",
      "scenario/blender/runtime.py": "aa199b156270fbc86aa6dbc5edf30096dddac7e69de6cc1ea905d5619b2a51bb",
      "scenario/core/jobs/workers.py": "08f9d8488e9df9892177a2f2570422d5d3e3a35dae89796f469640d4e2b97f35",
      "scenario/core/jobs/preview_scheduler.py": "bfe2b96bad5f175a28ca71b95d6cc0d478e40ee009e55c7929724fca88898a65"
    }
  }
}
---

# Result preview runtime component

Evidence for [the runtime map](../../architecture/runtime.md).
