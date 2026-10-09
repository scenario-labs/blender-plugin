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
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Reviewed the committed first-party 32x16 progressive JPEG: SOF2 frame, 4:4:4 sampling, ten scans, four flat color blocks and no EXIF metadata. Its documented command with the locked Pillow 12.3.0 development dependency reproduced identical bytes on macOS arm64; other Pillow or libjpeg versions may encode differently. Native World tests decode it and build a scan flood from it; they never run the encoder. No recording, provider output or Scenario service call is involved, and the fixture establishes no real Scenario JPEG behavior.",
    "sources": {
      "tests/fixtures/synthetic/panorama-progressive.jpg": "38b9ad4e8d43fd7b0d2114fc4cdfef98ac6bbc5fac03cda5a3364a3d1d362d5c",
      "tests/blender/test_world_application.py": "dff1d3a7308e303a67f21225f29e7e403074015ef4d384e66e364a926bee7395",
      "tests/unit/test_panorama.py": "a5716070211c058ef1b7eff39b38da789de8a0a32782e478a8910d2df404f678",
      "scenario/core/scene/panorama.py": "a66306a9c8d82c14d2f299fa26a62468d4db7f852111b3bfcb47f434e5e2aa63",
      "pyproject.toml": "b60c17fedfd6a9ee2ceb6c3093247fa08f513ae32aa0e59a4a90173da61e4672"
    }
  }
}
---

Evidence for [the canonical document](../../../tests/fixtures/README.md).
