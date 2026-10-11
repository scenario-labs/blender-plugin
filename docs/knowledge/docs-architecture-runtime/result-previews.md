---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.result-previews",
  "title": "Result preview runtime component",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "scope": "result-previews",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-11",
    "base_revision": "72723f02a97a7226b1c697c31d8124b77ac92c86",
    "limits": "Inspected the shared-runtime connection of the preview scheduler, preview lane and cache root, including retirement that waits for an idle preview lane before shutdown, a maintenance-only preview lane command that keeps the cache budget once previews settle, and a session that runs jobs without previews when the cache root cannot be created. No view schedules previews; UI, MCP and live acceptance remain open.",
    "sources": {
      "scenario/blender/job_session.py": "856baab7ec8aa2786f27ee482b0acc30a8f895fe547664e905b43304ad0ed08a",
      "scenario/blender/runtime.py": "56d4afe7ddb394b23d735c1f7b9e981c4a032963323ac50473f26b09ba9bd6ef",
      "scenario/core/jobs/workers.py": "dece4686af0b0889b99341a99d6d5143d48cdf63919fecef90299b834fbe9bc3",
      "scenario/core/jobs/preview_scheduler.py": "5ab4cf0b258aff1217223dcc8c4bbef4e09e664594c6e61cdf3156115b71a53c"
    }
  }
}
---

# Result preview runtime component

Evidence for [the runtime map](../../architecture/runtime.md).
