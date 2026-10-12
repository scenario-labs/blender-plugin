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
    "limits": "Reviewed that the catalog appends lane panorama with image kind, curates the five contract models, adds the lane only for contract IDs and keeps those models in their capability lanes; that the bpy-free contract module applies locked, default, size and reference rules and fails closed on schema drift; that MCP lists every contract model while the native list follows the scene's mode; that the native sidebar, Studio Create and the composer's Generate mode build the same contract body through generation.build_request, with saved panorama references rechecked against storage and checked files bound to their bytes; and that ModelJobs admits only Image lane jobs to automatic application. Unit tests cover lane membership and order and the contract helpers. Installed native tests on macOS arm64 Blender 5.1.2 (exact dev ZIP, isolated profile) cover the MCP lane and the native form. Live output, seam or pole review and the remaining desktop evidence remain open under #98. Re-checked 2026-10-12 after restacking on main 4bd0061d (with #380).",
    "sources": {
      "docs/architecture/runtime.md": "9b8ffc7ba544b5c06f41a549ddeb357df4f8a736aade3ad835b901d2b5993cc1",
      "scenario/core/api/catalog.py": "4a10bc8754fbb00df0e6944da1fb9d068bb3944da110ca4bb87370c255a4e50d",
      "scenario/core/scene/panorama_contract.py": "be4c2c949696ca82c18a1062c62ec252eec40d7d4e0e5d7fb2fe3064bab4e518",
      "scenario/mcp/tools_scenario.py": "b4c064d45fda6d1ea734115574830ef887b6c09cfbc448973b14b275e7069a26",
      "scenario/blender/model_jobs.py": "4eeac905c9f752274d21fcd732d10fde0ffbba950d9c3ec90227ce5a39860f78",
      "scenario/blender/generation.py": "50ad17c4f7bff740bdc8095261835fb3a89ee10cd6c45f16affa3895f09327d2",
      "scenario/blender/panorama_lane.py": "d3808e8f060b47ae3610f6db1538915e563dced6ea772951a2df2dae55a02391",
      "tests/unit/test_catalog_lanes.py": "a978ca89dd9198dd6bbf56b9b9f1d5c45fee7417f62c6ecbd13136225c1d2332",
      "tests/unit/test_panorama_contract.py": "2f1e9b0bf561912a586ba2e836ef3a1fffc90e1840c0d767b9050298e8196ed4",
      "tests/blender/test_model_generation.py": "f56f96f6b0727ca9f24c4104d0ed0ed0ab69034007f0febaf88439b365bd71ba",
      "tests/blender/test_panorama_lane.py": "e1371f77d663b68ee782cf6e636ff8b66e32a80a19fb0bfad48931545203f8e8"
    }
  }
}
---

Evidence for [the canonical document](../../../docs/architecture/runtime.md).
