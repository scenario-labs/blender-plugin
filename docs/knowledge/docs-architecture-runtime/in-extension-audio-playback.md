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
    "limits": "Reviewed the Result previews row's Play audio sentence and the #440 status against result_media.py and audio_player.py; the rest of the row keeps its existing evidence. The installed-ZIP full native suite, including test_audio_player and the Play audio tests in test_result_media and test_result_actions, passed with 2019 tests and three Windows-only skips on each of macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1; its children used a recording output in place of a sound device or Blender's None output. Hosted Linux and Windows runs, desktop clicks and human listening had not happened at this review. Re-checked on 2026-10-13 after a Windows CI fix, not a full re-review: test_result_media's Play audio test now compares the copy's playback root by file identity, because on Windows the copy keeps Python's extended \\\\?\\ namespace; the claims above still hold, and this fingerprint is the changed file's. Re-checked on 2026-10-13 after two review findings on #466, with no prose change: the row's stopping events and one-at-a-time claim still hold with the watcher thread that now owns each child's files. These fingerprints are the re-checked files': scenario/blender/result_media.py, scenario/core/jobs/audio_player.py, tests/blender/test_result_media.py.",
    "sources": {
      "scenario/blender/result_media.py": "08aa532bb8b16a916c5c8c618e68e80b249654f543ad0569c7333b4b630d501c",
      "scenario/core/jobs/audio_player.py": "d1f7851592e4a1b781a4ae2724dcb132af0d1ed86c697b80830e30d68583e7be",
      "tests/blender/test_result_media.py": "60f41e2209c8b05d1ac52bb956d9d22e28e776f9fe8478156d5255c109dd11ce"
    }
  }
}
---

# Result previews row: in-extension audio

Evidence for [the canonical guide](../../architecture/runtime.md).
