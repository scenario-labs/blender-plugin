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
    "reviewed_at": "2026-10-09",
    "base_revision": "fb699b8555f7cee62147794516cc7aaa224864f7",
    "limits": "Reviewed that shared jobs project validated in-memory progress into SCENARIO_PT_jobs, which Studio Jobs reuses, and into MCP job_status. Studio previews.py and preview_worker.py adoption, automatic result previews, the compact composer surface and live or desktop acceptance are not implemented by this change.",
    "sources": {
      "scenario/blender/model_jobs.py": "e49b0513dbaaa8c7805da01af007b0e0ff0598ac2c52f6d9afd583a9980b4163",
      "scenario/blender/panels.py": "18b655d47e620589b822b643248d81135d7dd37aa1c23350ccfd020b797b2fdf",
      "scenario/blender/studio.py": "ccdc50f2047cbab1792b1dd2a52a2b9e0c36ba9a85c315a7794d344e06b3e544",
      "scenario/mcp/tools_scenario.py": "364dc8cc70eb4761e698d9bc32c5d89fcfcb65a0e1e3bd8757030670528b20a9",
      "scenario/core/jobs/progress.py": "bf8bea9be0d1ba3c6ca7c2495fecf61eb67481ffb7499d1e30633cc154871af5"
    }
  }
}
---

# Studio progress retention status

Evidence for [the canonical document](../../STUDIO_ADOPTION.md).
