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
    "limits": "Reviewed that lane panorama lists only the five contract models with a JSON contract summary; estimate_cost and generate refuse other models and prepare parameters through the shared contract before the session quote; locked values are set and conflicting ones refused, the Flux numOutputs lane default applies only when unset, GPT sizes are limited to three 2:1 presets, panorama-kind references must be saved results of the selected scope with a receipt, projection equirectangular, source asset and a non-OpenEXR media type, the upscale factor is capped at 2 for references of unknown size, which fits a 2:1 reference up to 4096 pixels wide while larger unverified Flux or HY World outputs could still exceed the World limit, and refused for upscaled references, and a drifted schema fails closed. Panorama jobs are not admitted to automatic image application and the generate note points to explicit World approval. estimate_prompt advertises only the native lanes, so it does not offer the panorama lane, which has no native prompt field yet. Installed native tests on macOS arm64 Blender 5.1.2 cover listing, refusal of non-contract models, lane defaults in the dry-run and paid payloads, a single submission per quote, saved projection results without image import or World change, refusal of unknown and non-projection references, HDRI lock and upscale cap behavior with a fake SDK transport, and the lane enums of list_models, estimate_cost, generate and estimate_prompt; the generic lane tests include panorama for single-use quotes, lane binding and preserved uncertainty. The generated tool table renders first lines only and is unchanged. No paid or live generation, returned asset layout, output format or dimensions, other Blender version, native UI or desktop interaction is established; the Image and Render Image lanes still list the same models without the contract.",
    "sources": {
      "docs/MCP.md": "f7f0c7ad40d3b2c8d08d4d2ae8d1f2df54d684cdf3ba8636225480caaec3930a",
      "scenario/mcp/tools_scenario.py": "54dd2fc57b96ddcac1f8e44fa97df513487a7f3537266797a2f5ab024a760ca0",
      "scenario/core/scene/panorama_contract.py": "2110f885c49516bbc985c2948c9542350f74041448348ec34952e23d2fb8fa99",
      "scenario/core/api/catalog.py": "4a10bc8754fbb00df0e6944da1fb9d068bb3944da110ca4bb87370c255a4e50d",
      "scenario/blender/model_jobs.py": "88f17955538534d792b7408cf8e11e705bb2e6ee82d584173d51a365504c467d",
      "tests/blender/test_model_generation.py": "402e14442c01ec69eec18d401b3aebbc32ce7d080efc69e2ee32e9ea837a039c",
      "tests/unit/test_mcp_descriptions.py": "d48cbf8403c2e2b8367451c8a61a0fe7f16243eaa4006d4451b101b27204585f",
      "tests/unit/test_panorama_contract.py": "88786e64bb96a7cddaba5d48164b097c8cfccf9128a7e22248662e2c1a533e0b"
    }
  }
}
---

Evidence for [the canonical document](../../../docs/MCP.md#environment-lane-360-panoramas).
