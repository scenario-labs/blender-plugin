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
    "reviewed_at": "2026-10-11",
    "base_revision": "7fb15252f747f52db24f7e659f8d5048241f803e",
    "limits": "Reviewed that context maintenance projects the validated remote reading and records the display-only scene lane binding in ModelJobs, that MCP job_status reads the same view projection, and that pump._jobs_changed compares drawn job rows (excluding transient offered actions) and online access and redraws only when they change, in addition to existing event redraws; pump.redraw tags the 3D viewport and Preferences regions. Restarted views stay generic and unbound. Installed tests cover one redraw per projected change and per online access change, and none on idle ticks or for a queued refresh. Installed native tests on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 cover these claims. No desktop interaction, screenshot, other operating system or live provider progress is claimed.",
    "sources": {
      "scenario/blender/model_jobs.py": "5a378d786f8c775bf097673c9962f449a868506e234ed9e829f0d221ad059d4f",
      "scenario/blender/pump.py": "d146e694610b8ec4ca23b4577da1d792d4ae2c0dbc8d7a8a88d690571a330acd",
      "scenario/core/jobs/progress.py": "bf8bea9be0d1ba3c6ca7c2495fecf61eb67481ffb7499d1e30633cc154871af5",
      "scenario/mcp/tools_scenario.py": "ca5374a5de59234a488a8bcf5119f343dfc1adefc1db11af814618d5f5a12bc5",
      "tests/blender/test_model_generation.py": "e3a6885f17b3e800ebf6e1d43c0328e2fc87f1eb3a7a903325b0f75aa4f701c4"
    }
  }
}
---

# Shared job progress projection and redraw

Evidence for [the canonical document](../../architecture/runtime.md).
