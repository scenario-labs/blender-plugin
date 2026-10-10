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
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed that the Environment lane exists in the sidebar, Studio, the composer's Generate mode and local MCP, generates only through verified contracts and leaves results for explicit World approval; that output formats and sizes, the HDRI asset layout, seam and pole quality, measured HDR range and desktop evidence remain open under #98; and that MCP accepts only saved 360 results as panorama references while the native form also accepts a checked local file. The existing bullets on panoramic World application and accepted image formats were not re-reviewed. No paid or live generation, returned output format, size or asset layout, seam, pole or HDR range quality, or Blender 5.0 and 5.2 run is established by this review.",
    "sources": {
      "docs/KNOWN_LIMITATIONS.md": "f1138754ec3161488f7e3cba2f30497074919d30e65ab9bfecbc47ed17d4cb2f",
      "scenario/core/scene/panorama_contract.py": "be4c2c949696ca82c18a1062c62ec252eec40d7d4e0e5d7fb2fe3064bab4e518",
      "scenario/blender/props.py": "d6c25753c641a863e99920e980ec4e14ead175b5f44c8d7725b7f454c51f3a52",
      "scenario/blender/generation.py": "7fd6bfde60cb2d5ffa758d85fe55ee2c0c582864991e88d2dd79e4d150c24c0b",
      "scenario/blender/panorama_lane.py": "d3808e8f060b47ae3610f6db1538915e563dced6ea772951a2df2dae55a02391",
      "scenario/blender/reference_form.py": "61fa30d6044619dc147c5b2297307944134174a0ea07edd936049051040c8954",
      "scenario/mcp/tools_scenario.py": "ddd3efd7b48378cec9c3bca01928ce1858cdabcf1d05bdbee086ed0b1d327b14",
      "tests/blender/test_panorama_lane.py": "a556e269ab2ea9817ac51c92177d03e79b1cac826ee941cc88b4a61a99ce3172",
      "tests/unit/test_panorama_contract.py": "2f1e9b0bf561912a586ba2e836ef3a1fffc90e1840c0d767b9050298e8196ed4"
    }
  }
}
---

Evidence for [the canonical document](../../../docs/KNOWN_LIMITATIONS.md#creation-and-scene-application).
