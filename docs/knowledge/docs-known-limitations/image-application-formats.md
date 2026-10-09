---
{
  "type": "Evidence",
  "id": "docs-known-limitations.image-application-formats",
  "title": "Image, World and material application formats",
  "description": "Automatic Image-lane import and saved image, World and material application accept PNG and scanline OpenEXR only.",
  "evidence": {
    "path": "docs/KNOWN_LIMITATIONS.md",
    "scope": "image-application-formats",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Reviewed the image-format entry against source and tests. Image import and material maps share a container preflight that accepts grayscale, RGB or RGBA PNG and single-part scanline OpenEXR, and checks the saved media type; material roles and the saved-image and World actions require PNG or EXR media types; World application uses the panorama preflight for the same two containers. An unsupported automatic Image-lane result pauses delivery while its saved download is preserved. Documentation-only review: no native, desktop, live provider or paid run, and no claim about which formats a given model returns.",
    "sources": {
      "scenario/core/scene/panorama.py": "35c61bed172fa3350a4edf663dd062fb689f58779a6229826897e638ac647e95",
      "scenario/blender/image_application.py": "aedd8fdad1f92ae4abfe2721a0061189fe94c6dc91f7ff85106ceecc56edb0cc",
      "scenario/blender/material_application.py": "bd8035e8cb12c7ee0b38f3027f02d2c4b654ca01d8d1939943e4bac5afe9ef03",
      "scenario/blender/world_application.py": "95a10cae5b1ec3fdc758a18dcb4e70a50ffe10961c1ab38e0c5bb9ea6dbe8934",
      "scenario/blender/model_jobs.py": "bffb88d51557165fbdd5c22c89087c7a690ad15c17607a543b4a2cbc905ea00c",
      "tests/unit/test_panorama.py": "4828ce5a0befd33b4e931d9b9ac75669d8c1a399a23c6ac1ccff948cdfc29654",
      "tests/blender/test_session_results.py": "abf066db37b5065da617ecfadb4c718dddba6aa4596382e764495f8185af68b6",
      "tests/blender/test_model_generation.py": "0ea4f5ef5c1211f922d453df93b0ef98d886c19c20faea2bf477ff6c2ce57b52"
    }
  }
}
---

# Image, World and material application formats

Evidence for [the canonical document](../../KNOWN_LIMITATIONS.md).
