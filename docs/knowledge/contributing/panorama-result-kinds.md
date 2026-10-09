---
{
  "type": "Evidence",
  "id": "contributing.panorama-result-kinds",
  "title": "CONTRIBUTING.md: panorama and HDRI result kinds",
  "description": "The generic model check accepts the panorama and hdri result kinds.",
  "evidence": {
    "path": "CONTRIBUTING.md",
    "scope": "panorama-result-kinds",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Inspected the panorama and hdri result kinds in tools/smoke_image.py: every saved result must be an image, only results whose saved projection is equirectangular are inspected, each such verified file must pass the bounded 2:1 PNG, JPEG or OpenEXR panorama preflight (inspect_panorama) shared with World application, and hdri additionally needs a source: original result labelled image/x-exr or image/aces whose container is OpenEXR. The suite plan accepts both kinds through RESULT_KINDS. Offline tests use the real SDK adapter, coordinator, store and result commands with mocked service responses and synthetic PNG, JPEG and OpenEXR headers: accepted projections with image companions, an accepted 2:1 JPEG panorama, missing or skybox-3d projections, square files, malformed JPEG bytes, a video companion, preview-only, Radiance, PNG and JPEG originals, plus a seven-kind aggregate suite. No live skybox output, pixel decoding, dynamic range, seam review or paid run is claimed; #98 acceptance remains open.",
    "sources": {
      "tools/smoke_image.py": "a60c05f4da35f9a740b8289261b56acfde8142bd7770a4123ea12cd545d65e64",
      "tools/smoke_suite.py": "7595c08b8c5bae299908f12c9124ab3f2376da0237203f0ecc937aaaf3c38a36",
      "scenario/core/scene/panorama.py": "1d7d8fb6b0a06675baa2168a73c87a49fa4ecab6d4ad34843690d3c26edcf764",
      "scenario/core/jobs/result_metadata.py": "775986522c43e4b837f3deb333f964ca721eb6b8c74bd0282f40824a19c4af17",
      "scenario/core/jobs/results.py": "e06c043bbff65e56b4b910de0e1e763da39a49c05b0ef0397b888f00b93a72f5",
      "tests/unit/test_smoke_image.py": "0c907d6d03f4dda0ea0bb197e5bdfe629b95000a43b41306351d54788e476940",
      "tests/unit/test_smoke_suite.py": "ee39b9c1b324ccf001a7491affea19f4194d30c2f81e0ba5e41a8cc62c51cd29",
      "tests/unit/test_panorama.py": "f8914ce8c3cbbe10812bed813b3e1fbe1551c71fc6e4f47f8517cb777e9f3fa7"
    }
  }
}
---

# CONTRIBUTING.md: panorama and HDRI result kinds

Evidence for [the contributor guide](../../../CONTRIBUTING.md#live-commands) and
[model command reference](../../../tests/smoke/README.md#result-kinds-and-entry-points).
