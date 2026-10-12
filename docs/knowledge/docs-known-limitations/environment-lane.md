---
{
  "type": "Evidence",
  "id": "docs-known-limitations.environment-lane",
  "title": "Environment lane limits",
  "description": "What the native and MCP Environment lane does not yet establish.",
  "evidence": {
    "path": "docs/KNOWN_LIMITATIONS.md",
    "scope": "environment-lane",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "4bd0061d73f6d049a86adac37119cc7a2c37741c",
    "limits": "Reviewed that the Environment lane exists in the sidebar, Studio, the composer's Generate mode and local MCP, generates only through verified contracts and leaves results for explicit World approval; that output formats and sizes, the HDRI asset layout, seam and pole quality, measured HDR range and the remaining desktop evidence (the rebased composer tab row, a local panorama file upload and From image beyond its quote, after a physical pass on the pre-rebase stack) remain open under #98; and that MCP accepts only saved 360 results as panorama references while the native form also accepts a checked local file. The existing bullets on panoramic World application and accepted image formats were not re-reviewed. No paid or live generation, returned output format, size or asset layout, seam, pole or HDR range quality, or Blender 5.0 and 5.2 run is established by this review.",
    "sources": {
      "docs/KNOWN_LIMITATIONS.md": "d0c94b41d75ea50fa3f43933311dfb3a15ccdc028addd20bdb98d1a4efbd4e32",
      "scenario/core/scene/panorama_contract.py": "be4c2c949696ca82c18a1062c62ec252eec40d7d4e0e5d7fb2fe3064bab4e518",
      "scenario/blender/props.py": "b06289a5193a4345b0dcdfe66a26df8cb362ec856918360deaadedee42d1ff84",
      "scenario/blender/generation.py": "50ad17c4f7bff740bdc8095261835fb3a89ee10cd6c45f16affa3895f09327d2",
      "scenario/blender/panorama_lane.py": "d3808e8f060b47ae3610f6db1538915e563dced6ea772951a2df2dae55a02391",
      "scenario/blender/reference_form.py": "36cb61e5fb31c9efb01b6f7b36b0ff988c08e41bf9ea3985c9d0ef12e9c9cd50",
      "scenario/mcp/tools_scenario.py": "b4c064d45fda6d1ea734115574830ef887b6c09cfbc448973b14b275e7069a26",
      "tests/blender/test_panorama_lane.py": "08c113297e5b45faf9f00e9edc4029792123504312259dff7b5449651c942147",
      "tests/unit/test_panorama_contract.py": "2f1e9b0bf561912a586ba2e836ef3a1fffc90e1840c0d767b9050298e8196ed4"
    }
  }
}
---

Evidence for [the canonical document](../../../docs/KNOWN_LIMITATIONS.md#creation-and-scene-application).
