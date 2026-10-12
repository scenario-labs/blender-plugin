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
    "reviewed_at": "2026-10-12",
    "base_revision": "4ca693cb8f0e02a5c27c12d39bedbbc166b4e725",
    "limits": "Reviewed that shared jobs project validated in-memory progress into SCENARIO_PT_jobs, which Studio Jobs reuses, and into MCP job_status. Studio previews.py and preview_worker.py adoption, automatic result previews, the compact composer surface and live or desktop acceptance are not implemented by this change.",
    "sources": {
      "scenario/blender/model_jobs.py": "d297562e1684d2d7576bc4af5378c0059a783f5744070672168bc5b5ed84738b",
      "scenario/blender/panels.py": "6865424bb96bd545a60a72ae5fad6531eccc97016fdd8eac21857d29eecf5415",
      "scenario/blender/studio.py": "7a4a6b694ba4becb7a51dac11f95838a35d9f2a3dc752d85a50e1b1cd0f1f071",
      "scenario/mcp/tools_scenario.py": "918b40da89720c9afba73f013e56dc7943e2eaebe0c15422b687377609d89c29",
      "scenario/core/jobs/progress.py": "bf8bea9be0d1ba3c6ca7c2495fecf61eb67481ffb7499d1e30633cc154871af5"
    }
  }
}
---

# Studio progress retention status

Evidence for [the canonical document](../../STUDIO_ADOPTION.md).
