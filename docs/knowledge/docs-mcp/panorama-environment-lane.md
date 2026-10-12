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
    "limits": "Reviewed that lane panorama lists every contract model with a JSON contract summary whatever mode the native form shows; estimate_cost and generate refuse other models and prepare parameters through the shared contract before the session quote; locked values are set and conflicting ones refused, the Flux numOutputs lane default applies only when unset, GPT sizes are limited to three 2:1 presets, panorama-kind references must be saved results of the selected scope with a receipt, projection equirectangular, source asset and a non-OpenEXR media type (the same saved_panorama_refs check the native form uses), the upscale factor is capped at 2 for references of unknown size and refused for upscaled references, and a drifted schema fails closed. Panorama jobs are not admitted to automatic image application and the generate note points to explicit World approval. estimate_prompt advertises the native lanes, which now include panorama because the native Environment form has its own prompt field; an uploaded file is still refused as a panorama reference because upload_reference performs no 2:1 preflight. Installed native tests on macOS arm64 Blender 5.1.2 (exact dev ZIP, isolated profile) cover the MCP lane, the advertised enums and native and MCP body parity for HDRI and GPT. The generated tool table is unchanged. No paid or live generation, returned output format, size or asset layout, seam, pole or HDR range quality, or Blender 5.0 and 5.2 run is established by this review. Re-checked 2026-10-12 after restacking on main 4bd0061d (with #380): the claims hold, and an installed test refuses a material map's asset ID as the HDRI panorama before any dry run.",
    "sources": {
      "docs/MCP.md": "c839924ec17ac321ca447fdaa9479e0fa1bc73a2cb58e17960cf5f9e3d538b91",
      "scenario/mcp/tools_scenario.py": "b4c064d45fda6d1ea734115574830ef887b6c09cfbc448973b14b275e7069a26",
      "scenario/core/scene/panorama_contract.py": "be4c2c949696ca82c18a1062c62ec252eec40d7d4e0e5d7fb2fe3064bab4e518",
      "scenario/core/api/catalog.py": "4a10bc8754fbb00df0e6944da1fb9d068bb3944da110ca4bb87370c255a4e50d",
      "scenario/blender/model_jobs.py": "4eeac905c9f752274d21fcd732d10fde0ffbba950d9c3ec90227ce5a39860f78",
      "scenario/blender/props.py": "b06289a5193a4345b0dcdfe66a26df8cb362ec856918360deaadedee42d1ff84",
      "scenario/blender/generation.py": "50ad17c4f7bff740bdc8095261835fb3a89ee10cd6c45f16affa3895f09327d2",
      "tests/blender/test_model_generation.py": "f56f96f6b0727ca9f24c4104d0ed0ed0ab69034007f0febaf88439b365bd71ba",
      "tests/blender/test_panorama_lane.py": "08c113297e5b45faf9f00e9edc4029792123504312259dff7b5449651c942147",
      "tests/unit/test_mcp_descriptions.py": "d48cbf8403c2e2b8367451c8a61a0fe7f16243eaa4006d4451b101b27204585f",
      "tests/unit/test_panorama_contract.py": "2f1e9b0bf561912a586ba2e836ef3a1fffc90e1840c0d767b9050298e8196ed4"
    }
  }
}
---

Evidence for [the canonical document](../../../docs/MCP.md#environment-lane-360-panoramas).
