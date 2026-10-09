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
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Reviewed ModelJobs.status result entries and the job_status description: source and projection are copied from the saved manifest and are inspection only. Generated MCP reference unchanged by the description edit (checked with gen_mcp_docs --check). No new tool, approval or application path.",
    "sources": {
      "scenario/blender/model_jobs.py": "f09de87f40cbe1e4fe95c1869a63d7d84e52d967eb95421ebc4c9c6a47d699f6",
      "scenario/mcp/tools_scenario.py": "8fd2f8673317e0d2c3bd767850330014ab37f0b1d3f2c56fd16eb47c01925b74",
      "scenario/core/jobs/store.py": "af6a1aca80668fb15001ca1ac75dabecef5d7118c045a2223caee9b404c844e1"
    }
  }
}
---

# Result source and projection in job_status

Evidence for [the canonical document](../../MCP.md).
