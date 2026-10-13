---
{
  "type": "Evidence",
  "id": "docs-result-previews.in-extension-audio-playback",
  "title": "In-extension audio playback in an owned offline process",
  "evidence": {
    "path": "docs/RESULT_PREVIEWS.md",
    "scope": "in-extension-audio-playback",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-13",
    "base_revision": "ca97ec56e28e58cdbe64a7000fa82aaa71e5d39a",
    "limits": "Reviewed the In-extension audio playback section, the Private player copies sentence and the Play audio sentences under Boundaries against audio_player.py (the start flags, local_render's scrubbed environment, a private listen-* directory below a canonical root created by playback_root, the request fields, standard input as a pipe and discarded output, the 60 s start timeout, the reported duration or 600 s plus 10 s end deadline, termination and a kill three seconds later, the fixed failure vocabulary, release only after exit and the day-old sweep), audio_player_worker.py (the output opened by name, the rate, channel and declared-length checks, the quarter-second head decode, the None output detected through the handle status, playing.json published by replace and the lifeline read with os.read), result_media.py (Play audio copies through prepare_playback, the playing audio stopped when a new Play audio is queued and again before a child starts, copies pinned while a child runs, late copies discarded by the existing context and key checks, retirement, file load and unregistering stopping it, unregistering waiting, the poll intervals and listening reading memory only) and runtime.audio_device and audio_player_spec. The comparison of the two designs restates the measured lock hold of envelope decoding and otherwise reasons about failure containment; it is not a new measurement of in-session playback. A local probe on macOS arm64 played a digitally silent 8 kHz WAV through the unmodified worker on the CoreAudio output with standard input held open: it reported playback 0.61 to 0.83 s after the child started on Blender 5.0.1, 5.1.2 and 5.2.1, exited about 0.05 s after a 2 s file ended, and stopped within about 0.05 s of the lifeline closing. With standard input from /dev/null the lifeline stopped the worker before it opened the output, which is why the parent holds a pipe. Opening CoreAudio and OpenAL by name, but not SDL, PulseAudio or WASAPI, from a -noaudio background child, and the None output returning a handle whose status is not playing, were probed on 5.0.1 and 5.1.2 on macOS arm64 only. Nothing audible was played and no human listened. Blender calling addon_utils.disable_all on exit was read from the 5.1.2 binary's strings, not observed. The installed-ZIP full native suite, including test_audio_player and the Play audio tests in test_result_media and test_result_actions, passed with 2019 tests and three Windows-only skips on each of macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1; its children used a recording output in place of a sound device or Blender's None output. Hosted Linux and Windows runs, desktop clicks and human listening had not happened at this review.",
    "sources": {
      "scenario/core/jobs/audio_player.py": "a40e4cbf2a2596d248c0272fcf03d9d6132b9442098676202c55a5b576c4b90c",
      "scenario/blender/audio_player_worker.py": "03398600e9eec3b00f4e6e56c2b943baed46b395f4378579f0a8695a30776c53",
      "scenario/blender/result_media.py": "e868fd88dbadccefc3718b7f37bee0c7e1c59d01916e6d913db29677aa537283",
      "scenario/blender/runtime.py": "1ba34f4c2a73dbb5fc492ae6b69566b640056642ba1ad056d0f5b3add9dfce41",
      "tests/blender/test_audio_player.py": "a67d5c0c18a2b78f08f3457798afd2703104f173afc9a7755122017255038279",
      "tests/blender/test_result_media.py": "3ac63e2eb21f6f79d552e177cb5613de5261defadbc63c0e78c2dd08c58b8cda",
      "tests/unit/test_audio_player.py": "7e82277bbafa89b8466a96cce15ae83e19b6fafc544ef618da337c3f2959b8ae"
    }
  }
}
---

# In-extension audio playback in an owned offline process

Evidence for [the canonical guide](../../RESULT_PREVIEWS.md).
