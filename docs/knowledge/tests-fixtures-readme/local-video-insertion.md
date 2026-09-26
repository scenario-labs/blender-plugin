---
{
  "type": "Evidence",
  "id": "tests-fixtures-readme.local-video-insertion",
  "title": "tests/fixtures/README.md: local video insertion",
  "evidence": {
    "path": "tests/fixtures/README.md",
    "scope": "local-video-insertion",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-26",
    "base_revision": "03c5128eb05fc4bbae14e49a1941b98c3b6bf2f2",
    "limits": "Reviewed active native picture-only video insertion, current-frame placement, unused unlocked/unmuted channel selection, preserved scene settings and rollback after decoder errors. Synthetic first-party MP4 bytes exercise the bundled decoder. Exact packaged native suites pass on Blender 5.0.1, 5.1.2 and 5.2.1 on macOS arm64. Local import needs no external ffmpeg; encoding, embedded audio, automatic retiming, Film, other platforms and live service acceptance remain separate. Fixture rights statements apply only to the new synthetic clip, not historical provider media.",
    "sources": {
      "scenario/blender/apply_video.py": "7a9e831c52f40ed95b988179f73b27f69c63e1a3dc51e6fa50df7a9878b3fde6",
      "scenario/blender/panels.py": "7a9f9eb3f1498699082cadf76dfcf198cc5af79bab8d9b5a812858a33518b2cf",
      "scenario/blender/registry.py": "75ad15dd91c8362d1a6487e2ee54f1be86f7a09e688dcb77d7672e6374d6ef58",
      "tests/blender/test_apply_video.py": "1e2d724d0208debb2c8aa2930d865ad9e531ea77a3dcb9b77a927ee888604fe6",
      "tests/blender/run_all.py": "f25a426b87c99617a07450fbca480023fbd26bde5a22418c19bf90bba7ebe9c8",
      "tests/fixtures/synthetic/video-six-frames.mp4": "c2b435908a9adc6cd5903c0fda352cee6cd861a1eecfc7f31c0fa517460597e0"
    }
  }
}
---

Evidence for [the canonical document](../../../tests/fixtures/README.md).
