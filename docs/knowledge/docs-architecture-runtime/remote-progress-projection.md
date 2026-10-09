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
    "base_revision": "fb699b8555f7cee62147794516cc7aaa224864f7",
    "limits": "Reviewed that context maintenance projects the validated remote reading and records the display-only scene lane binding in ModelJobs, that MCP job_status reads the same view projection, and that pump._jobs_changed compares drawn job rows (excluding transient offered actions) and online access and redraws only when they change, in addition to existing event redraws; pump.redraw tags the 3D viewport and Preferences regions. Restarted views stay generic and unbound. Installed tests cover one redraw per projected change and per online access change, and none on idle ticks or for a queued refresh. Installed native tests on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 cover these claims. No desktop interaction, screenshot, other operating system or live provider progress is claimed.",
    "sources": {
      "scenario/blender/model_jobs.py": "e49b0513dbaaa8c7805da01af007b0e0ff0598ac2c52f6d9afd583a9980b4163",
      "scenario/blender/pump.py": "dca1e1db201d017f99ce2d006292b1a990a81b224639fefbc5964ce3cdff61f1",
      "scenario/core/jobs/progress.py": "bf8bea9be0d1ba3c6ca7c2495fecf61eb67481ffb7499d1e30633cc154871af5",
      "scenario/mcp/tools_scenario.py": "364dc8cc70eb4761e698d9bc32c5d89fcfcb65a0e1e3bd8757030670528b20a9",
      "tests/blender/test_model_generation.py": "9defb9e875aa425a4130ef3208994b20bb3f2c2ab27057b79d48635a13db5be7"
    }
  }
}
---

# Shared job progress projection and redraw

Evidence for [the canonical document](../../architecture/runtime.md).
