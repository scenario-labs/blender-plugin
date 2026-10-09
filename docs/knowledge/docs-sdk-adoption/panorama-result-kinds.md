---
{
  "type": "Evidence",
  "id": "docs-sdk-adoption.panorama-result-kinds",
  "title": "SDK adoption: panorama and HDRI model check kinds",
  "description": "Panorama result kinds reuse saved asset metadata and add no SDK call.",
  "evidence": {
    "path": "docs/SDK_ADOPTION.md",
    "scope": "panorama-result-kinds",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Inspected the panorama and hdri result kinds in tools/smoke_image.py: every saved result must be an image, only results whose saved projection is equirectangular are inspected, each such verified file must pass the bounded 2:1 PNG/OpenEXR panorama preflight shared with World application, and hdri additionally needs a source: original result labelled image/x-exr or image/aces whose container is OpenEXR. The suite plan accepts both kinds through RESULT_KINDS. Offline tests use the real SDK adapter, coordinator, store and result commands with mocked service responses and synthetic PNG/OpenEXR headers: accepted projections with image companions, missing or skybox-3d projections, square files, JPEG bytes, a video companion, preview-only, Radiance and LDR originals, plus a seven-kind aggregate suite. No live skybox output, JPEG panorama support, pixel decoding, dynamic range, seam review or paid run is claimed; #98 acceptance remains open.",
    "sources": {
      "tools/smoke_image.py": "a9cdb0211ba9ad6f2a1f8eec22a235023ffb9316f06415d57b89226327aba018",
      "tools/smoke_suite.py": "7595c08b8c5bae299908f12c9124ab3f2376da0237203f0ecc937aaaf3c38a36",
      "scenario/core/scene/panorama.py": "35c61bed172fa3350a4edf663dd062fb689f58779a6229826897e638ac647e95",
      "scenario/core/jobs/result_metadata.py": "00904085422404c9d6d6a81805ed9c86a224b73f4c59c8516bf0c2de894c8e0f",
      "scenario/core/jobs/results.py": "e06c043bbff65e56b4b910de0e1e763da39a49c05b0ef0397b888f00b93a72f5",
      "tests/unit/test_smoke_image.py": "b3dc147d5863daf66ce60db36e67a3723f1b7fa3d758af6322dd4de685f825b0",
      "tests/unit/test_smoke_suite.py": "ee39b9c1b324ccf001a7491affea19f4194d30c2f81e0ba5e41a8cc62c51cd29",
      "tests/unit/test_panorama.py": "4828ce5a0befd33b4e931d9b9ac75669d8c1a399a23c6ac1ccff948cdfc29654"
    }
  }
}
---

# SDK adoption: panorama and HDRI model check kinds

Evidence for [model acceptance commands](../../SDK_ADOPTION.md#model-acceptance-commands).
