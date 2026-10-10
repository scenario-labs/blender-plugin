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
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed that lane panorama lists only the five contract models with a JSON contract summary; estimate_cost and generate refuse other models and prepare parameters through the shared contract before the session quote; locked values are set and conflicting ones refused, the Flux numOutputs lane default applies only when unset, GPT sizes are limited to three 2:1 presets, panorama-kind references must be saved results of the selected scope with a receipt, projection equirectangular, source asset and a non-OpenEXR media type, the upscale factor is capped at 2 for references of unknown size, which fits a 2:1 reference up to 4096 pixels wide while larger unverified Flux or HY World outputs could still exceed the World limit, and refused for upscaled references, and a drifted schema fails closed. Panorama jobs are not admitted to automatic image application and the generate note points to explicit World approval. estimate_prompt advertises only the native lanes, so it does not offer the panorama lane, which has no native prompt field yet. Installed native tests on macOS arm64 Blender 5.1.2 cover listing, refusal of non-contract models, lane defaults in the dry-run and paid payloads, a single submission per quote, saved projection results without image import or World change, refusal of unknown and non-projection references, HDRI lock and upscale cap behavior with a fake SDK transport, and the lane enums of list_models, estimate_cost, generate and estimate_prompt; the generic lane tests include panorama for single-use quotes, lane binding and preserved uncertainty. The generated tool table renders first lines only and is unchanged. No paid or live generation, returned asset layout, output format or dimensions, other Blender version, native UI or desktop interaction is established; the Image and Render Image lanes still list the same models without the contract.",
    "sources": {
      "docs/MCP.md": "40724c1b62ddcdc2d8c24d0ec2b526552a30bf656a73928e28740716160e9254",
      "scenario/mcp/tools_scenario.py": "250b62c0e6f90129bb9eb09336ac97ec823512a8440ab28e277e77ee14f013ab",
      "scenario/core/scene/panorama_contract.py": "2110f885c49516bbc985c2948c9542350f74041448348ec34952e23d2fb8fa99",
      "scenario/core/api/catalog.py": "474e4996d5bd2eda8109b452157d2179664814db0f6d6ac297d385aca974d1b1",
      "scenario/blender/model_jobs.py": "56e8699e97278dcd39bdf38404e9dc2407f22217053a98f663d11e8a4e6c284c",
      "tests/blender/test_model_generation.py": "bf3d274e457ff4377c0bd42ad8d639b557dfbeeccbcbd1311d5c0f814469d2ce",
      "tests/unit/test_mcp_descriptions.py": "cc5e67d469ddde6696d76e494ee05fde77e290820c6a2264bfabf8fb33067ee8",
      "tests/unit/test_panorama_contract.py": "88786e64bb96a7cddaba5d48164b097c8cfccf9128a7e22248662e2c1a533e0b"
    }
  }
}
---

Evidence for [the canonical document](../../../docs/MCP.md#environment-lane-360-panoramas).
