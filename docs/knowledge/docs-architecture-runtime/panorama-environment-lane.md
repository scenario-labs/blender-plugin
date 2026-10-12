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
    "reviewed_at": "2026-10-12",
    "base_revision": "4bd0061d73f6d049a86adac37119cc7a2c37741c",
    "limits": "Reviewed that the catalog appends lane panorama with image kind, curates the five contract models, adds the lane only for contract IDs and keeps those models in their capability lanes, that the bpy-free contract module applies locked, default, size and reference rules and fails closed on schema drift, that MCP derives the lane list from loaded records because the native form has no panorama lane state, and that ModelJobs admits only Image lane jobs to automatic application. Unit tests cover lane membership and order, unchanged Image and Render Image membership and the payload-audit inventory; installed native tests on macOS arm64 Blender 5.1.2 cover the MCP lane. The native Environment tab, Studio and composer integration, live output and seam or pole review remain open under #98.",
    "sources": {
      "docs/architecture/runtime.md": "568407045ee7761e96498fb5c6e230d0214e5fae71c4a56c4d9752f5e1234450",
      "scenario/core/api/catalog.py": "4a10bc8754fbb00df0e6944da1fb9d068bb3944da110ca4bb87370c255a4e50d",
      "scenario/core/scene/panorama_contract.py": "2110f885c49516bbc985c2948c9542350f74041448348ec34952e23d2fb8fa99",
      "scenario/mcp/tools_scenario.py": "54dd2fc57b96ddcac1f8e44fa97df513487a7f3537266797a2f5ab024a760ca0",
      "scenario/blender/model_jobs.py": "88f17955538534d792b7408cf8e11e705bb2e6ee82d584173d51a365504c467d",
      "scenario/blender/generation.py": "9ea7d7a562a5178fe0264bb125855bcbea64257d0e4a3c21fd77e006854bc73d",
      "tests/unit/test_catalog_lanes.py": "a978ca89dd9198dd6bbf56b9b9f1d5c45fee7417f62c6ecbd13136225c1d2332",
      "tests/unit/test_panorama_contract.py": "88786e64bb96a7cddaba5d48164b097c8cfccf9128a7e22248662e2c1a533e0b",
      "tests/blender/test_model_generation.py": "402e14442c01ec69eec18d401b3aebbc32ce7d080efc69e2ee32e9ea837a039c"
    }
  }
}
---

Evidence for [the canonical document](../../../docs/architecture/runtime.md).
