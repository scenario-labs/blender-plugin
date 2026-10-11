---
{
  "type": "Evidence",
  "id": "docs-studio-adoption.remote-progress-projection",
  "title": "Studio progress retention status",
  "description": "Status of the automatic previews and progress adoption row.",
  "evidence": {
    "path": "docs/STUDIO_ADOPTION.md",
    "scope": "remote-progress-projection",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-11",
    "base_revision": "1d86f53d3489b23f2447be69cb589140e2f3ba64",
    "limits": "Reviewed that shared jobs project validated in-memory progress into SCENARIO_PT_jobs, which Studio Jobs reuses, and into MCP job_status. Studio previews.py and preview_worker.py adoption, automatic result previews, the compact composer surface and live or desktop acceptance are not implemented by this change.",
    "sources": {
      "scenario/blender/model_jobs.py": "5a378d786f8c775bf097673c9962f449a868506e234ed9e829f0d221ad059d4f",
      "scenario/blender/panels.py": "8c9ed56c0d83b4c0cfd4578e7158c05f1df895f7c2765319c0894c1ca0491e83",
      "scenario/blender/studio.py": "7a4a6b694ba4becb7a51dac11f95838a35d9f2a3dc752d85a50e1b1cd0f1f071",
      "scenario/mcp/tools_scenario.py": "ca5374a5de59234a488a8bcf5119f343dfc1adefc1db11af814618d5f5a12bc5",
      "scenario/core/jobs/progress.py": "bf8bea9be0d1ba3c6ca7c2495fecf61eb67481ffb7499d1e30633cc154871af5"
    }
  }
}
---

# Studio progress retention status

Evidence for [the canonical document](../../STUDIO_ADOPTION.md).
