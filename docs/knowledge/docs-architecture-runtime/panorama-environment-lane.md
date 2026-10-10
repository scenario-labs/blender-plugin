---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.panorama-environment-lane",
  "title": "Environment lane catalog and contract preparation",
  "description": "Catalog lane panorama, its bpy-free contract registry and the native form.",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "scope": "panorama-environment-lane",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "4bd0061d73f6d049a86adac37119cc7a2c37741c",
    "limits": "Reviewed that the catalog appends lane panorama with image kind, curates the five contract models, adds the lane only for contract IDs and keeps those models in their capability lanes; that the bpy-free contract module applies locked, default, size and reference rules and fails closed on schema drift; that MCP lists every contract model while the native list follows the scene's mode; that the native sidebar, Studio Create and the composer's Generate mode build the same contract body through generation.build_request, with saved panorama references rechecked against storage and checked files bound to their bytes; and that ModelJobs admits only Image lane jobs to automatic application. Unit tests cover lane membership and order and the contract helpers. Installed native tests on macOS arm64 Blender 5.1.2 (exact dev ZIP, isolated profile) cover the MCP lane and the native form. Live output, seam or pole review and desktop evidence remain open under #98.",
    "sources": {
      "docs/architecture/runtime.md": "459cfc9d59ef8046fd5b806f6d902a12b46458ad085b7e20586e14469e28224c",
      "scenario/core/api/catalog.py": "474e4996d5bd2eda8109b452157d2179664814db0f6d6ac297d385aca974d1b1",
      "scenario/core/scene/panorama_contract.py": "be4c2c949696ca82c18a1062c62ec252eec40d7d4e0e5d7fb2fe3064bab4e518",
      "scenario/mcp/tools_scenario.py": "ddd3efd7b48378cec9c3bca01928ce1858cdabcf1d05bdbee086ed0b1d327b14",
      "scenario/blender/model_jobs.py": "b5174cdf8a73fea86b633fb660a7d942b0fd0f2516e81ec7477e1be6bb956b6b",
      "scenario/blender/generation.py": "7fd6bfde60cb2d5ffa758d85fe55ee2c0c582864991e88d2dd79e4d150c24c0b",
      "scenario/blender/panorama_lane.py": "d3808e8f060b47ae3610f6db1538915e563dced6ea772951a2df2dae55a02391",
      "tests/unit/test_catalog_lanes.py": "a978ca89dd9198dd6bbf56b9b9f1d5c45fee7417f62c6ecbd13136225c1d2332",
      "tests/unit/test_panorama_contract.py": "2f1e9b0bf561912a586ba2e836ef3a1fffc90e1840c0d767b9050298e8196ed4",
      "tests/blender/test_model_generation.py": "7a259312ca4bdbbcf45f14b34985cb71bcd722da2d8546439d4a206704a05049",
      "tests/blender/test_panorama_lane.py": "a556e269ab2ea9817ac51c92177d03e79b1cac826ee941cc88b4a61a99ce3172"
    }
  }
}
---

Evidence for [the canonical document](../../../docs/architecture/runtime.md).
