---
{
  "type": "Evidence",
  "id": "docs-studio-adoption.environment-lane",
  "title": "HDRI and World row with the Environment lane",
  "description": "The HDRI and world capability row after native and MCP Environment generation.",
  "evidence": {
    "path": "docs/STUDIO_ADOPTION.md",
    "scope": "environment-lane",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed that the HDRI and world application row records Environment generation in the sidebar, Studio Create (which reuses the sidebar panel), the composer's Generate mode and local MCP through verified contracts, explicit World approval and the Make HDRI prefill, and that #98 and roadmap#674 G03 still own live acceptance and desktop evidence. The other capability rows were not re-reviewed. No paid or live generation, returned output format, size or asset layout, seam, pole or HDR range quality, or Blender 5.0 and 5.2 run is established by this review.",
    "sources": {
      "docs/STUDIO_ADOPTION.md": "6933aaee71a09db48683fb616d457fa89cc5f566690f25dd5df5e1163a831d30",
      "scenario/blender/panels.py": "fc31581e9276bce9d21dce3e93b4c9d7d2356b229a4145e3e0f55da959ef7251",
      "scenario/blender/studio.py": "d4ba0b268cdcc1a6d9477cb5f190ebb18233010de5b5963fecf941ba05995fb8",
      "scenario/core/scene/panorama_contract.py": "be4c2c949696ca82c18a1062c62ec252eec40d7d4e0e5d7fb2fe3064bab4e518",
      "scenario/blender/props.py": "d6c25753c641a863e99920e980ec4e14ead175b5f44c8d7725b7f454c51f3a52",
      "scenario/blender/generation.py": "7fd6bfde60cb2d5ffa758d85fe55ee2c0c582864991e88d2dd79e4d150c24c0b",
      "scenario/blender/panorama_lane.py": "d3808e8f060b47ae3610f6db1538915e563dced6ea772951a2df2dae55a02391",
      "tests/blender/test_panorama_lane.py": "a556e269ab2ea9817ac51c92177d03e79b1cac826ee941cc88b4a61a99ce3172",
      "tests/unit/test_panorama_contract.py": "2f1e9b0bf561912a586ba2e836ef3a1fffc90e1840c0d767b9050298e8196ed4"
    }
  }
}
---

Evidence for [the canonical document](../../../docs/STUDIO_ADOPTION.md#capability-decisions).
