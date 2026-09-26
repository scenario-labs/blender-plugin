---
{
  "type": "Evidence",
  "id": "docs-user-guide.local-video-insertion",
  "title": "docs/USER_GUIDE.md: local video insertion",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "local-video-insertion",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-26",
    "base_revision": "03c5128eb05fc4bbae14e49a1941b98c3b6bf2f2",
    "limits": "Reviewed active native picture-only video insertion, current-frame placement, unused unlocked/unmuted channel selection, preserved scene settings and rollback after decoder errors. Synthetic first-party MP4 bytes exercise the bundled decoder. Exact packaged native suites pass on Blender 5.0.1, 5.1.2 and 5.2.1 on macOS arm64. Local import needs no external ffmpeg; encoding, embedded audio, automatic retiming, Film, other platforms and live service acceptance remain separate. Fixture rights statements apply only to the new synthetic clip, not historical provider media. Native GUI mouse insertion, viewport keyboard focus and Undo/Redo were verified on Blender 5.0.1 in a fresh offline profile. Empty workspace sequencer selection is initialized; an existing selection is preserved.",
    "sources": {
      "scenario/blender/apply_video.py": "decc84acdf125fe0d4f19c13e3e84b58a8c23e332daea92b5ac5ad6a5f1f8282",
      "scenario/blender/panels.py": "7a9f9eb3f1498699082cadf76dfcf198cc5af79bab8d9b5a812858a33518b2cf",
      "scenario/blender/registry.py": "75ad15dd91c8362d1a6487e2ee54f1be86f7a09e688dcb77d7672e6374d6ef58",
      "tests/blender/test_apply_video.py": "faab8fa465433dc8703541daa37b3c7a76e903e1fce92d0ba3ba4c476f6e8261",
      "tests/blender/run_all.py": "f25a426b87c99617a07450fbca480023fbd26bde5a22418c19bf90bba7ebe9c8",
      "tests/fixtures/synthetic/video-six-frames.mp4": "c2b435908a9adc6cd5903c0fda352cee6cd861a1eecfc7f31c0fa517460597e0"
    }
  }
}
---

Evidence for [the canonical document](../../USER_GUIDE.md).
