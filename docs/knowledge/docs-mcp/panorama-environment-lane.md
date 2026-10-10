---
{
  "type": "Evidence",
  "id": "docs-mcp.panorama-environment-lane",
  "title": "MCP Environment lane for 360 panoramas",
  "description": "Contract-only panorama lane in list_models, estimate_cost and generate.",
  "evidence": {
    "path": "docs/MCP.md",
    "scope": "panorama-environment-lane",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "4bd0061d73f6d049a86adac37119cc7a2c37741c",
    "limits": "Reviewed that lane panorama lists every contract model with a JSON contract summary whatever mode the native form shows; estimate_cost and generate refuse other models and prepare parameters through the shared contract before the session quote; locked values are set and conflicting ones refused, the Flux numOutputs lane default applies only when unset, GPT sizes are limited to three 2:1 presets, panorama-kind references must be saved results of the selected scope with a receipt, projection equirectangular, source asset and a non-OpenEXR media type (the same saved_panorama_refs check the native form uses), the upscale factor is capped at 2 for references of unknown size and refused for upscaled references, and a drifted schema fails closed. Panorama jobs are not admitted to automatic image application and the generate note points to explicit World approval. estimate_prompt advertises the native lanes, which now include panorama because the native Environment form has its own prompt field; an uploaded file is still refused as a panorama reference because upload_reference performs no 2:1 preflight. Installed native tests on macOS arm64 Blender 5.1.2 (exact dev ZIP, isolated profile) cover the MCP lane, the advertised enums and native and MCP body parity for HDRI and GPT. The generated tool table is unchanged. No paid or live generation, returned output format, size or asset layout, seam, pole or HDR range quality, or Blender 5.0 and 5.2 run is established by this review.",
    "sources": {
      "docs/MCP.md": "185a6e046f1c2c2bb0086e119b20d213a04c77393e5129a95f77e820af56bab3",
      "scenario/mcp/tools_scenario.py": "ddd3efd7b48378cec9c3bca01928ce1858cdabcf1d05bdbee086ed0b1d327b14",
      "scenario/core/scene/panorama_contract.py": "be4c2c949696ca82c18a1062c62ec252eec40d7d4e0e5d7fb2fe3064bab4e518",
      "scenario/core/api/catalog.py": "474e4996d5bd2eda8109b452157d2179664814db0f6d6ac297d385aca974d1b1",
      "scenario/blender/model_jobs.py": "b5174cdf8a73fea86b633fb660a7d942b0fd0f2516e81ec7477e1be6bb956b6b",
      "scenario/blender/props.py": "b85199b13c0f7fdac0108efc28b39d7e35b0d7fe0b4ac60a39c95020c8d28521",
      "scenario/blender/generation.py": "265c53ce191b2b8d9f0eabecc1f0a726aa5758b0fae958ff1cae9b9aa0d620dd",
      "tests/blender/test_model_generation.py": "7a259312ca4bdbbcf45f14b34985cb71bcd722da2d8546439d4a206704a05049",
      "tests/blender/test_panorama_lane.py": "539c48697cad7224d20b2638e6f92d63a83352b52190394f8c6842c7825f5e86",
      "tests/unit/test_mcp_descriptions.py": "cc5e67d469ddde6696d76e494ee05fde77e290820c6a2264bfabf8fb33067ee8",
      "tests/unit/test_panorama_contract.py": "03b45364309d8d1f2c5016966ed794f8f215088e6ed42047b0fdaf62cf53be70"
    }
  }
}
---

Evidence for [the canonical document](../../../docs/MCP.md#environment-lane-360-panoramas).
