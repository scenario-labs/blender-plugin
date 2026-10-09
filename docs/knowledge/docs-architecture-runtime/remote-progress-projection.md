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
    "limits": "Reviewed that context maintenance projects the validated remote reading and records the display-only scene lane binding in ModelJobs, that MCP job_status reads the same view projection, and that pump._jobs_changed compares drawn job rows (excluding transient offered actions) and redraws only when they change, in addition to existing event redraws. Restarted views stay generic and unbound. Installed tests cover one redraw per projected change and none on idle ticks or for a queued refresh. Installed native tests on macOS arm64 Blender 5.1.2 cover these claims. No desktop interaction, screenshot, Blender 5.0/5.2 run, other operating system or live provider progress is claimed.",
    "sources": {
      "scenario/blender/model_jobs.py": "ef10249154c8842a96da012d07395bf8c1554bc762542cdc27f1539ae1590e85",
      "scenario/blender/pump.py": "370e0c393cf3655a258ac705857d40756467a530265e6022e86c9c79ba89e7d4",
      "scenario/core/jobs/progress.py": "286563456f871fb3073ad32932cc3d9b750f12b9d263abef2fe931cbc5568f92",
      "scenario/mcp/tools_scenario.py": "a960c7495ea57658c9813fda4caa64178ead8f02a25530cd4bb5e93ed52cde64",
      "tests/blender/test_model_generation.py": "a7994ea7cf89c4c26b29701682b9cf9e39971e6fef54a031f4394b9ed57e2f66"
    }
  }
}
---

# Shared job progress projection and redraw

Evidence for [the canonical document](../../architecture/runtime.md).
