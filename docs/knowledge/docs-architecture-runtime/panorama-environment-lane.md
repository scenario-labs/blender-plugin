---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.panorama-environment-lane",
  "title": "Environment lane catalog and contract preparation",
  "description": "Catalog lane panorama and its bpy-free contract registry.",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "scope": "panorama-environment-lane",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed that the catalog appends lane panorama with image kind, curates the five contract models, adds the lane only for contract IDs and keeps those models in their capability lanes, that the bpy-free contract module applies locked, default, size and reference rules and fails closed on schema drift, that MCP derives the lane list from loaded records because the native form has no panorama lane state, and that ModelJobs admits only Image lane jobs to automatic application. Unit tests cover lane membership and order, unchanged Image and Render Image membership and the payload-audit inventory; installed native tests on macOS arm64 Blender 5.1.2 cover the MCP lane. The native Environment tab, Studio and composer integration, live output and seam or pole review remain open under #98.",
    "sources": {
      "docs/architecture/runtime.md": "fc241b481782bf37805ccf8d9839588785a4c64a504dba41599605c70272bdfc",
      "scenario/core/api/catalog.py": "474e4996d5bd2eda8109b452157d2179664814db0f6d6ac297d385aca974d1b1",
      "scenario/core/scene/panorama_contract.py": "2110f885c49516bbc985c2948c9542350f74041448348ec34952e23d2fb8fa99",
      "scenario/mcp/tools_scenario.py": "250b62c0e6f90129bb9eb09336ac97ec823512a8440ab28e277e77ee14f013ab",
      "scenario/blender/model_jobs.py": "56e8699e97278dcd39bdf38404e9dc2407f22217053a98f663d11e8a4e6c284c",
      "scenario/blender/generation.py": "6f73c4ba35ceb97097d1356b2267c5b2b7a2a7105b6900d0376d2604f9e9de8f",
      "tests/unit/test_catalog_lanes.py": "a978ca89dd9198dd6bbf56b9b9f1d5c45fee7417f62c6ecbd13136225c1d2332",
      "tests/unit/test_panorama_contract.py": "88786e64bb96a7cddaba5d48164b097c8cfccf9128a7e22248662e2c1a533e0b",
      "tests/blender/test_model_generation.py": "bf3d274e457ff4377c0bd42ad8d639b557dfbeeccbcbd1311d5c0f814469d2ce"
    }
  }
}
---

Evidence for [the canonical document](../../../docs/architecture/runtime.md).
