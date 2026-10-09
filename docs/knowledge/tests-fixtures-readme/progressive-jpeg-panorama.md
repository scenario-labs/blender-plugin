---
{
  "type": "Evidence",
  "id": "tests-fixtures-readme.progressive-jpeg-panorama",
  "title": "tests/fixtures/README.md: progressive JPEG panorama",
  "evidence": {
    "path": "tests/fixtures/README.md",
    "scope": "progressive-jpeg-panorama",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "fb699b8555f7cee62147794516cc7aaa224864f7",
    "limits": "Reviewed the committed first-party 32x16 progressive JPEG: SOF2 frame, 4:4:4 sampling, ten scans, four flat color blocks and no EXIF metadata. Its documented command with the locked Pillow 12.3.0 development dependency reproduced identical bytes on macOS arm64; other Pillow or libjpeg versions may encode differently. Unit tests check that the JPEG preflight accepts it and rejects comment floods inserted into it. Native World tests decode it, build scan and comment floods from it and decode it with comments up to the segment limit; they never run the encoder. No recording, provider output or Scenario service call is involved, and the fixture establishes no real Scenario JPEG behavior.",
    "sources": {
      "tests/fixtures/synthetic/panorama-progressive.jpg": "38b9ad4e8d43fd7b0d2114fc4cdfef98ac6bbc5fac03cda5a3364a3d1d362d5c",
      "tests/blender/test_world_application.py": "572c71ac8ea086606fe07c1a2ca3c839ba3b03bc840f6eeed8dc1c8714f9834c",
      "tests/unit/test_panorama.py": "f8914ce8c3cbbe10812bed813b3e1fbe1551c71fc6e4f47f8517cb777e9f3fa7",
      "scenario/core/scene/panorama.py": "1d7d8fb6b0a06675baa2168a73c87a49fa4ecab6d4ad34843690d3c26edcf764",
      "pyproject.toml": "b60c17fedfd6a9ee2ceb6c3093247fa08f513ae32aa0e59a4a90173da61e4672"
    }
  }
}
---

Evidence for [the canonical document](../../../tests/fixtures/README.md).
