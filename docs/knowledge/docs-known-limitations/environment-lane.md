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
      "scenario/blender/props.py": "b85199b13c0f7fdac0108efc28b39d7e35b0d7fe0b4ac60a39c95020c8d28521",
      "scenario/blender/generation.py": "265c53ce191b2b8d9f0eabecc1f0a726aa5758b0fae958ff1cae9b9aa0d620dd",
      "scenario/blender/panorama_lane.py": "84988f58d11e07b55f00285bcedae5d665324af4d195af9c50342193f4ff6e3b",
      "scenario/blender/reference_form.py": "61fa30d6044619dc147c5b2297307944134174a0ea07edd936049051040c8954",
      "scenario/mcp/tools_scenario.py": "ddd3efd7b48378cec9c3bca01928ce1858cdabcf1d05bdbee086ed0b1d327b14",
      "tests/blender/test_panorama_lane.py": "539c48697cad7224d20b2638e6f92d63a83352b52190394f8c6842c7825f5e86",
      "tests/unit/test_panorama_contract.py": "03b45364309d8d1f2c5016966ed794f8f215088e6ed42047b0fdaf62cf53be70"
    }
  }
}
---

Evidence for [the canonical document](../../../docs/KNOWN_LIMITATIONS.md#creation-and-scene-application).
