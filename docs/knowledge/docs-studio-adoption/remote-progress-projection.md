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
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed that shared jobs project validated in-memory progress into SCENARIO_PT_jobs, which Studio Jobs reuses, and into MCP job_status. Studio previews.py and preview_worker.py adoption, automatic result previews, the compact composer surface and live or desktop acceptance are not implemented by this change.",
    "sources": {
      "scenario/blender/model_jobs.py": "ff575c16838b19ef950d8825dc80d8d42c1b81f89a3763f5c50245da091fa33a",
      "scenario/blender/panels.py": "683cbe1ba4486ce2e59cc203bbac153d9ea6c31e3f0bc7710cf01bb028019d54",
      "scenario/blender/studio.py": "d4ba0b268cdcc1a6d9477cb5f190ebb18233010de5b5963fecf941ba05995fb8",
      "scenario/mcp/tools_scenario.py": "9c48234b23d9756877184ee0f0536253741320ee80239484e172bf351dec2b83",
      "scenario/core/jobs/progress.py": "bf8bea9be0d1ba3c6ca7c2495fecf61eb67481ffb7499d1e30633cc154871af5"
    }
  }
}
---

# Studio progress retention status

Evidence for [the canonical document](../../STUDIO_ADOPTION.md).
