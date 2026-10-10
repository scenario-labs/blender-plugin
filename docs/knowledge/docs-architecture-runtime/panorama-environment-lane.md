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
      "scenario/blender/generation.py": "265c53ce191b2b8d9f0eabecc1f0a726aa5758b0fae958ff1cae9b9aa0d620dd",
      "scenario/blender/panorama_lane.py": "84988f58d11e07b55f00285bcedae5d665324af4d195af9c50342193f4ff6e3b",
      "tests/unit/test_catalog_lanes.py": "a978ca89dd9198dd6bbf56b9b9f1d5c45fee7417f62c6ecbd13136225c1d2332",
      "tests/unit/test_panorama_contract.py": "03b45364309d8d1f2c5016966ed794f8f215088e6ed42047b0fdaf62cf53be70",
      "tests/blender/test_model_generation.py": "7a259312ca4bdbbcf45f14b34985cb71bcd722da2d8546439d4a206704a05049",
      "tests/blender/test_panorama_lane.py": "539c48697cad7224d20b2638e6f92d63a83352b52190394f8c6842c7825f5e86"
    }
  }
}
---

Evidence for [the canonical document](../../../docs/architecture/runtime.md).
