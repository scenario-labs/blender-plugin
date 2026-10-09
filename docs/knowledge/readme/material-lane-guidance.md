---
{
  "type": "Evidence",
  "id": "readme.material-lane-guidance",
  "title": "README.md: Materials feature summary",
  "description": "The Materials feature summary describes saved texture sets with explicit slot application.",
  "evidence": {
    "path": "README.md",
    "scope": "material-lane-guidance",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Reviewed only the Materials feature bullet. Shared Materials jobs stop at saved texture sets and do not texture the meshes selected at generation; assignment is the explicit native or MCP saved-material approval for one captured mesh material slot. The bullet links to the user guide, whose material-lane-guidance and material-result-application topics carry the detailed limits. Other feature bullets keep their inherited review. No live generation, provider output, desktop interaction or Materials/release acceptance is claimed.",
    "sources": {
      "scenario/blender/panels.py": "352f15b93daaf5129f587166b5be2f3ea9718c66a7930cc65aa7f73df06799c6",
      "scenario/blender/model_jobs.py": "bffb88d51557165fbdd5c22c89087c7a690ad15c17607a543b4a2cbc905ea00c",
      "scenario/blender/material_application.py": "bd8035e8cb12c7ee0b38f3027f02d2c4b654ca01d8d1939943e4bac5afe9ef03",
      "scenario/mcp/tools_scenario.py": "5fa8768f9b8356fb9b5071cf7c889305b06e55905a72d4caf62114f9202b0f4d",
      "tests/blender/test_material_lane.py": "f6d5deec65aa1aa96aced657a4fce6a18b95a6f0e1272a827a7a7c2e7a9e9fa0"
    }
  }
}
---

# README.md: Materials feature summary

Evidence for [the canonical document](../../../README.md).
