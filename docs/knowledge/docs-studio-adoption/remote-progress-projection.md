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
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Reviewed that shared jobs project validated in-memory progress into SCENARIO_PT_jobs, which Studio Jobs reuses, and into MCP job_status. Studio previews.py and preview_worker.py adoption, automatic result previews, the compact composer surface and live or desktop acceptance are not implemented by this change.",
    "sources": {
      "scenario/blender/model_jobs.py": "ef10249154c8842a96da012d07395bf8c1554bc762542cdc27f1539ae1590e85",
      "scenario/blender/panels.py": "cf68b0ad25dffe11283878498975c8687d7c2ff8d95cd4afa47ea3a80147c419",
      "scenario/blender/studio.py": "ccdc50f2047cbab1792b1dd2a52a2b9e0c36ba9a85c315a7794d344e06b3e544",
      "scenario/mcp/tools_scenario.py": "a960c7495ea57658c9813fda4caa64178ead8f02a25530cd4bb5e93ed52cde64",
      "scenario/core/jobs/progress.py": "286563456f871fb3073ad32932cc3d9b750f12b9d263abef2fe931cbc5568f92"
    }
  }
}
---

# Studio progress retention status

Evidence for [the canonical document](../../STUDIO_ADOPTION.md).
