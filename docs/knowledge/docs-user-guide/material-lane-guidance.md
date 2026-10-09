---
{
  "type": "Evidence",
  "id": "docs-user-guide.material-lane-guidance",
  "title": "Materials lane result guidance",
  "description": "Materials generation saves texture sets; assignment needs explicit saved-material approval.",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "material-lane-guidance",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Shared ModelJobs submission marks only Image-lane jobs for automatic application; Materials jobs stop at saved ready results. Unbound job_done events cannot invoke the prototype material callback, which is the only reader of the target_objects metadata still recorded at submission. Ready saved jobs are non-terminal views drawn in the Jobs panel, where Apply saved material targets the active mesh's active slot after confirmation; the shared MCP material approval captures the same active-mesh slot target. The overview, lane list and Materials section describe saved texture sets applied explicitly to a chosen mesh material slot. The Materials lane draws two short static hint lines in one column without reading selection. The Generations Tiling action is drawn only for a material named by the prototype callback, never by saved application, so the guide no longer lists it. An installed native regression asserts the hint lines with and without a selected mesh on Blender 5.1.2 macOS arm64 only; the 36-character bound is a width heuristic, not a measured sidebar or DPI check. The Materials screenshot predates this hint, still shows the former selection wording and is captioned as an earlier layout; regenerating it remains a follow-up. This review does not cover physical focus/DPI review, other Blender versions or live provider output, and does not establish full Materials or release acceptance.",
    "sources": {
      "scenario/blender/panels.py": "352f15b93daaf5129f587166b5be2f3ea9718c66a7930cc65aa7f73df06799c6",
      "scenario/blender/model_jobs.py": "bffb88d51557165fbdd5c22c89087c7a690ad15c17607a543b4a2cbc905ea00c",
      "scenario/blender/job_recovery.py": "e39883dfa3dd4604d7b045e109ac6037fa822ef325b25fbb3ae98c86459009eb",
      "scenario/blender/generation.py": "d09d69727d3eadc999615ff8e969f982ccc454b20accf4490c2e66093bb0abe4",
      "scenario/blender/apply_material.py": "b8de96e6f25e62b1372e129af31f762d11cb5ce2c3388b77647ee747f4d5566c",
      "scenario/blender/handlers.py": "699dba07a70d4b796f29e2e52799abb62d2ae7d0595b484c1f984f156cae1834",
      "scenario/blender/material_application.py": "bd8035e8cb12c7ee0b38f3027f02d2c4b654ca01d8d1939943e4bac5afe9ef03",
      "scenario/mcp/tools_scenario.py": "5fa8768f9b8356fb9b5071cf7c889305b06e55905a72d4caf62114f9202b0f4d",
      "tests/blender/test_material_lane.py": "f6d5deec65aa1aa96aced657a4fce6a18b95a6f0e1272a827a7a7c2e7a9e9fa0",
      "tests/blender/test_generation.py": "893b2601f6b694417878ad9d66a703fa6631f133090173b1a28687f135ae961a",
      "docs/images/panel-materials.png": "63899b0eee76b2ff384c48bfcd98457813ceaf0f3b8fe54eea6bc40757ed58bc"
    }
  }
}
---

# Materials lane result guidance

Evidence for [the canonical document](../../USER_GUIDE.md).
