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
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the image-format entry against source and tests. Image import and material maps share a container preflight that accepts grayscale, RGB or RGBA PNG and single-part scanline OpenEXR, and checks the saved media type; material roles and the saved-image action require PNG or EXR media types. The World action accepts panorama.WORLD_MEDIA_TYPES (image/png, image/jpeg, image/exr, image/x-exr and image/aces), and World application uses the panorama preflight, which also accepts baseline or progressive JPEG and checks declared OpenEXR primaries (Rec.709, or ACES AP0 decoded as ACES2065-1). An unsupported automatic Image-lane result pauses delivery while its saved download is preserved. Documentation-only review: no native, desktop, live provider or paid run, and no claim about which formats a given model returns.",
    "sources": {
      "scenario/core/scene/panorama.py": "1d7d8fb6b0a06675baa2168a73c87a49fa4ecab6d4ad34843690d3c26edcf764",
      "scenario/blender/image_application.py": "aedd8fdad1f92ae4abfe2721a0061189fe94c6dc91f7ff85106ceecc56edb0cc",
      "scenario/blender/material_application.py": "bd8035e8cb12c7ee0b38f3027f02d2c4b654ca01d8d1939943e4bac5afe9ef03",
      "scenario/blender/world_application.py": "341b67665ec8be9201c3191559d47a31421aae5726bc2ea06b134f8245876895",
      "scenario/blender/model_jobs.py": "db89e83391d2d572e6c4b496cdd12aae7d1865d08e2ec4b66d406221716e5430",
      "tests/unit/test_panorama.py": "f8914ce8c3cbbe10812bed813b3e1fbe1551c71fc6e4f47f8517cb777e9f3fa7",
      "tests/blender/test_session_results.py": "e87afd949fda187702ddac63c0c52f2597fead62c171e2f2afcc9ab217defcf8",
      "tests/blender/test_model_generation.py": "7b07e69a73ff6828e803afbe0c3bc370b1f2d3d5bf7e0e06fe9dbd3b621c2fd2"
    }
  }
}
---

# Image, World and material application formats

Evidence for [the canonical document](../../KNOWN_LIMITATIONS.md).
