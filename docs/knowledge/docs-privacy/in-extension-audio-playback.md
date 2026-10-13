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
    "limits": "Reviewed the Play audio paragraph and the clipboard sentence against audio_player.start, which starts the child with local_render's environment (no SCENARIO_, BLENDER_, PYTHON or proxy variables, a disposable profile and temporary directory), --offline-mode and --factory-startup, discards its output and writes a request holding only the copy and output paths, the device name and the limit; the worker, which imports only the standard library and aud and writes two small reports; release and the day-old sweep; and result_media's stopping paths. The unexpected-exit claim rests on the lifeline, tested by closing the pipe, not by crashing Blender. The installed-ZIP full native suite, including test_audio_player and the Play audio tests in test_result_media and test_result_actions, passed with 2019 tests and three Windows-only skips on each of macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1; its children used a recording output in place of a sound device or Blender's None output. Hosted Linux and Windows runs, desktop clicks and human listening had not happened at this review.",
    "sources": {
      "scenario/core/jobs/audio_player.py": "c3e63624468aae91aae0d72e0d8542f84e371d7d009de606a176b41293f9e375",
      "scenario/blender/audio_player_worker.py": "03398600e9eec3b00f4e6e56c2b943baed46b395f4378579f0a8695a30776c53",
      "scenario/core/jobs/local_render.py": "24524eb2d2cbfb148b09bc427ae481d0945586fc9e41799a62a251e6a38bac70",
      "scenario/blender/result_media.py": "e868fd88dbadccefc3718b7f37bee0c7e1c59d01916e6d913db29677aa537283",
      "tests/blender/test_audio_player.py": "a67d5c0c18a2b78f08f3457798afd2703104f173afc9a7755122017255038279",
      "tests/unit/test_audio_player.py": "7e82277bbafa89b8466a96cce15ae83e19b6fafc544ef618da337c3f2959b8ae"
    }
  }
}
---

# In-extension audio playback process and files

Evidence for [the canonical guide](../../PRIVACY.md).
