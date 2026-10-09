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
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed that context maintenance projects the validated remote reading and records the display-only scene lane binding in ModelJobs, that MCP job_status reads the same view projection, and that pump._jobs_changed compares drawn job rows (excluding transient offered actions) and online access and redraws only when they change, in addition to existing event redraws; pump.redraw tags the 3D viewport and Preferences regions. Restarted views stay generic and unbound. Installed tests cover one redraw per projected change and per online access change, and none on idle ticks or for a queued refresh. Installed native tests on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 cover these claims. No desktop interaction, screenshot, other operating system or live provider progress is claimed.",
    "sources": {
      "scenario/blender/model_jobs.py": "ff575c16838b19ef950d8825dc80d8d42c1b81f89a3763f5c50245da091fa33a",
      "scenario/blender/pump.py": "dca1e1db201d017f99ce2d006292b1a990a81b224639fefbc5964ce3cdff61f1",
      "scenario/core/jobs/progress.py": "bf8bea9be0d1ba3c6ca7c2495fecf61eb67481ffb7499d1e30633cc154871af5",
      "scenario/mcp/tools_scenario.py": "9c48234b23d9756877184ee0f0536253741320ee80239484e172bf351dec2b83",
      "tests/blender/test_model_generation.py": "3cca6011fa4ce6a1ea72922da75ff8846ae0c6ec0155b00143a6e3c724b8c02d"
    }
  }
}
---

# Shared job progress projection and redraw

Evidence for [the canonical document](../../architecture/runtime.md).
