---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.grayscale-images",
  "title": "Grayscale PNG result application",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "scope": "grayscale-images",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "6c70d2edb385f6bd9f4a5e53c1eee66c575ebd16",
    "limits": "General image preflight accepts 8- and 16-bit grayscale PNGs for receipt-bound image/material application. Panorama acceptance remains RGB/RGBA only. CRC, byte, pixel and chunk limits and native decode/packing remain enforced. Synthetic native regressions exercise grayscale scalar map decoding and packing alongside RGB material maps. Palette, grayscale-alpha and sub-byte grayscale formats remain unsupported. This source review does not establish desktop interaction, provider color fidelity or complete release acceptance.",
    "sources": {
      "scenario/core/scene/panorama.py": "35c61bed172fa3350a4edf663dd062fb689f58779a6229826897e638ac647e95",
      "scenario/blender/image_application.py": "aedd8fdad1f92ae4abfe2721a0061189fe94c6dc91f7ff85106ceecc56edb0cc",
      "scenario/blender/material_application.py": "bd8035e8cb12c7ee0b38f3027f02d2c4b654ca01d8d1939943e4bac5afe9ef03",
      "tests/unit/test_panorama.py": "4828ce5a0befd33b4e931d9b9ac75669d8c1a399a23c6ac1ccff948cdfc29654",
      "tests/blender/test_material_application.py": "6fae32e6104d1a54b9e1ee7f38f266915795e29e62365ff9e96ca180416522ba"
    }
  }
}
---

Evidence for the [canonical guide](../../architecture/runtime.md).
