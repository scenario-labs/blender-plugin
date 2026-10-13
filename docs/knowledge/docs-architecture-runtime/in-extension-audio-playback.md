---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.in-extension-audio-playback",
  "title": "Result previews row: in-extension audio",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "scope": "in-extension-audio-playback",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-13",
    "base_revision": "ca97ec56e28e58cdbe64a7000fa82aaa71e5d39a",
    "limits": "Reviewed the Result previews row's Play audio sentence and the #440 status against result_media.py and audio_player.py; the rest of the row keeps its existing evidence. The installed-ZIP full native suite, including test_audio_player and the Play audio tests in test_result_media and test_result_actions, passed with 2019 tests and three Windows-only skips on each of macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1; its children used a recording output in place of a sound device or Blender's None output. Hosted Linux and Windows runs, desktop clicks and human listening had not happened at this review.",
    "sources": {
      "scenario/blender/result_media.py": "e868fd88dbadccefc3718b7f37bee0c7e1c59d01916e6d913db29677aa537283",
      "scenario/core/jobs/audio_player.py": "a40e4cbf2a2596d248c0272fcf03d9d6132b9442098676202c55a5b576c4b90c",
      "tests/blender/test_result_media.py": "3ac63e2eb21f6f79d552e177cb5613de5261defadbc63c0e78c2dd08c58b8cda"
    }
  }
}
---

# Result previews row: in-extension audio

Evidence for [the canonical guide](../../architecture/runtime.md).
