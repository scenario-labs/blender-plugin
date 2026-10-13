---
{
  "type": "Evidence",
  "id": "docs-privacy.in-extension-audio-playback",
  "title": "In-extension audio playback process and files",
  "evidence": {
    "path": "docs/PRIVACY.md",
    "scope": "in-extension-audio-playback",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-13",
    "base_revision": "ca97ec56e28e58cdbe64a7000fa82aaa71e5d39a",
    "limits": "Reviewed the Play audio paragraph and the clipboard sentence against audio_player.start, which starts the child with local_render's environment (no SCENARIO_, BLENDER_, PYTHON or proxy variables, a disposable profile and temporary directory), --offline-mode and --factory-startup, discards its output and writes a request holding only the copy and output paths, the device name and the limit; the worker, which imports only the standard library and aud and writes two small reports; release and the day-old sweep; and result_media's stopping paths. The unexpected-exit claim rests on the lifeline, tested by closing the pipe, not by crashing Blender. The installed-ZIP full native suite, including test_audio_player and the Play audio tests in test_result_media and test_result_actions, passed with 2019 tests and three Windows-only skips on each of macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1; its children used a recording output in place of a sound device or Blender's None output. Hosted Linux and Windows runs, desktop clicks and human listening had not happened at this review. Re-checked on 2026-10-13 after two review findings on #466, with no prose change: the directory is still removed when the process ends, now by the player's watcher thread, and a directory left by a crash is still removed once a day old when the next Play audio's watcher starts; a child that survives unregistering is kept and logged without a path. These fingerprints are the re-checked files': scenario/core/jobs/audio_player.py, scenario/blender/result_media.py, tests/unit/test_audio_player.py, tests/blender/test_audio_player.py.",
    "sources": {
      "scenario/core/jobs/audio_player.py": "d1f7851592e4a1b781a4ae2724dcb132af0d1ed86c697b80830e30d68583e7be",
      "scenario/blender/audio_player_worker.py": "03398600e9eec3b00f4e6e56c2b943baed46b395f4378579f0a8695a30776c53",
      "scenario/core/jobs/local_render.py": "24524eb2d2cbfb148b09bc427ae481d0945586fc9e41799a62a251e6a38bac70",
      "scenario/blender/result_media.py": "08aa532bb8b16a916c5c8c618e68e80b249654f543ad0569c7333b4b630d501c",
      "tests/blender/test_audio_player.py": "53d8646587b4ef577083ca8292b5d55ddb691b553622c52d8696becc7239b68d",
      "tests/unit/test_audio_player.py": "d292050db7db5cb78979d090330374e38cd9f1c0661c93dd485ffd6a1d99f22a"
    }
  }
}
---

# In-extension audio playback process and files

Evidence for [the canonical guide](../../PRIVACY.md).
