---
{
  "type": "Evidence",
  "id": "docs-mcp.result-source-projection",
  "title": "Result source and projection in job_status",
  "description": "Saved-job status exposes the delivered file source and declared projection.",
  "evidence": {
    "path": "docs/MCP.md",
    "scope": "result-source-projection",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed ModelJobs.status result entries and the job_status description: source and projection are copied from the saved manifest and are inspection only. The description keeps the actions mapping to cancel_prepared_job and recover_local_job and names the snapshot records mesh source records to avoid confusion with a result's source. Generated MCP reference unchanged by the description edit (checked with gen_mcp_docs --check). No new tool, approval or application path.",
    "sources": {
      "scenario/blender/model_jobs.py": "b41f0f4516bd80a255dc50bb2e353f799845be2a271ac37f40860781dec7a6ea",
      "scenario/mcp/tools_scenario.py": "119f9c524af56f6bac6ee8fba2ffdbdb8e30f576ea6953366a3c0e707b1bc3af",
      "scenario/core/jobs/store.py": "5e94feb941bd943939901be0b8e0e447e424da24635cf28b5f44f7f159c60ec6"
    }
  }
}
---

# Result source and projection in job_status

Evidence for [the canonical document](../../MCP.md).
