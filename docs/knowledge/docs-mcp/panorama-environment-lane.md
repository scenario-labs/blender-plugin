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
    "limits": "Reviewed that lane panorama lists only the five contract models with a JSON contract summary; estimate_cost and generate refuse other models and prepare parameters through the shared contract before the session quote; locked values are set and conflicting ones refused, the Flux numOutputs lane default applies only when unset, GPT sizes are limited to three 2:1 presets, panorama-kind references must be saved results of the selected scope with a receipt, projection equirectangular, source asset and a non-OpenEXR media type, the upscale factor is capped at 2 for references of unknown size and refused for upscaled references, and a drifted schema fails closed. Panorama jobs are not admitted to automatic image application and the generate note points to explicit World approval. Installed native tests on macOS arm64 Blender 5.1.2 cover listing, refusal of non-contract models, lane defaults in the dry-run and paid payloads, a single submission per quote, saved projection results without image import or World change, refusal of unknown and non-projection references and HDRI lock and upscale cap behavior with a fake SDK transport; the generic lane tests include panorama for single-use quotes, lane binding and preserved uncertainty. The generated tool table renders first lines only and is unchanged. No paid or live generation, returned asset layout, output format or dimensions, other Blender version, native UI or desktop interaction is established; the Image and Render Image lanes still list the same models without the contract.",
    "sources": {
      "docs/MCP.md": "8f0e0ba9bf0912ef9d24f6b2cb1d11b66a5d30aea6d8248db62c19e7b7345cde",
      "scenario/mcp/tools_scenario.py": "77dbdf62a8929019548650c80682cb41c1436a466591244b412ff03c0405ba34",
      "scenario/core/scene/panorama_contract.py": "2110f885c49516bbc985c2948c9542350f74041448348ec34952e23d2fb8fa99",
      "scenario/core/api/catalog.py": "474e4996d5bd2eda8109b452157d2179664814db0f6d6ac297d385aca974d1b1",
      "scenario/blender/model_jobs.py": "56e8699e97278dcd39bdf38404e9dc2407f22217053a98f663d11e8a4e6c284c",
      "tests/blender/test_model_generation.py": "a4d32c045b2764d55af10ca7128ceb0dbca48c23a88eeab5cc234b0c8b310d75",
      "tests/unit/test_mcp_descriptions.py": "cbf07bb4c0cf4dc9794a7783f618cf126a5339f8cc5391ebaf8c7ab380173e9d",
      "tests/unit/test_panorama_contract.py": "88786e64bb96a7cddaba5d48164b097c8cfccf9128a7e22248662e2c1a533e0b"
    }
  }
}
---

Evidence for [the canonical document](../../../docs/MCP.md#environment-lane-360-panoramas).
