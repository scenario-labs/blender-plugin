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
    "reviewed_at": "2026-10-12",
    "base_revision": "4bd0061d73f6d049a86adac37119cc7a2c37741c",
    "limits": "Reviewed that the HDRI and world application row records Environment generation in the sidebar, Studio Create (which reuses the sidebar panel), the composer's Generate mode and local MCP through verified contracts, explicit World approval and the Make HDRI prefill, and that #98 and roadmap#674 G03 still own live acceptance and desktop evidence. The other capability rows were not re-reviewed. Re-checked 2026-10-12 after restacking on main 4bd0061d (with #380); the row's claims are unchanged, and a physical pass on the pre-rebase stack covered Studio Create on the Environment tab without closing the remaining desktop evidence. No paid or live generation, returned output format, size or asset layout, seam, pole or HDR range quality, or Blender 5.0 and 5.2 run is established by this review.",
    "sources": {
      "docs/STUDIO_ADOPTION.md": "965e6d7c010d311fc1d6573f2c108d4c63a302ac25a4f2711cfc7942113a7941",
      "scenario/blender/panels.py": "c0cdbf46e8db8e7d400fb4ba6898e497e5da60b082b9e7897619bfd204aa184e",
      "scenario/blender/studio.py": "7a4a6b694ba4becb7a51dac11f95838a35d9f2a3dc752d85a50e1b1cd0f1f071",
      "scenario/core/scene/panorama_contract.py": "be4c2c949696ca82c18a1062c62ec252eec40d7d4e0e5d7fb2fe3064bab4e518",
      "scenario/blender/props.py": "b06289a5193a4345b0dcdfe66a26df8cb362ec856918360deaadedee42d1ff84",
      "scenario/blender/generation.py": "50ad17c4f7bff740bdc8095261835fb3a89ee10cd6c45f16affa3895f09327d2",
      "scenario/blender/panorama_lane.py": "d3808e8f060b47ae3610f6db1538915e563dced6ea772951a2df2dae55a02391",
      "tests/blender/test_panorama_lane.py": "e1371f77d663b68ee782cf6e636ff8b66e32a80a19fb0bfad48931545203f8e8",
      "tests/unit/test_panorama_contract.py": "2f1e9b0bf561912a586ba2e836ef3a1fffc90e1840c0d767b9050298e8196ed4"
    }
  }
}
---

Evidence for [the canonical document](../../../docs/STUDIO_ADOPTION.md#capability-decisions).
