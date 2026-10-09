---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.remote-progress-projection",
  "title": "Shared job progress projection and redraw",
  "description": "Runtime map entry for the progress projection, binding and pump redraw.",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "scope": "remote-progress-projection",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Reviewed that context maintenance projects the validated remote reading and records the display-only scene lane binding in ModelJobs, that MCP job_status reads the same view projection, and that pump._jobs_changed compares drawn job rows (excluding transient offered actions) and online access and redraws only when they change, in addition to existing event redraws. Restarted views stay generic and unbound. Installed tests cover one redraw per projected change and per online access change, and none on idle ticks or for a queued refresh. Installed native tests on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 cover these claims. No desktop interaction, screenshot, other operating system or live provider progress is claimed.",
    "sources": {
      "scenario/blender/model_jobs.py": "7278524fcd4cac373ce186782e741cc58b5a18e0a8ddca17d4c6cd1045fc52a6",
      "scenario/blender/pump.py": "dca1e1db201d017f99ce2d006292b1a990a81b224639fefbc5964ce3cdff61f1",
      "scenario/core/jobs/progress.py": "bf8bea9be0d1ba3c6ca7c2495fecf61eb67481ffb7499d1e30633cc154871af5",
      "scenario/mcp/tools_scenario.py": "3b75c077ed05ddddf882e251c46064c6d61bb61611c516e8dc7491fb11988e13",
      "tests/blender/test_model_generation.py": "e0f1b143a429bee22f5715ce420ff0d364916efc11bc94b630e8ad067a466f10"
    }
  }
}
---

# Shared job progress projection and redraw

Evidence for [the canonical document](../../architecture/runtime.md).
