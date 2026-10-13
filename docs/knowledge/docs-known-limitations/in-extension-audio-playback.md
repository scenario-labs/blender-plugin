---
{
  "type": "Evidence",
  "id": "docs-known-limitations.in-extension-audio-playback",
  "title": "In-extension audio playback limits",
  "evidence": {
    "path": "docs/KNOWN_LIMITATIONS.md",
    "scope": "in-extension-audio-playback",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-13",
    "base_revision": "ca97ec56e28e58cdbe64a7000fa82aaa71e5d39a",
    "limits": "Reviewed the Play audio bullet and the Play audio additions to the saved media bullets against audio_player.py, audio_player_worker.py and result_media.py: one child per playback, playback from the start with no pause, seeking, volume or playhead, the Preferences output opened by name with the aud module's default 48 kHz stereo (read from a probe that opened CoreAudio by name and reported 48000 Hz and two channels), playback despite a parent started with -noaudio because the child opens its own output, and the crash path covered only by closing the pipe. A local probe on macOS arm64 played a digitally silent 8 kHz WAV through the unmodified worker on the CoreAudio output with standard input held open: it reported playback 0.61 to 0.83 s after the child started on Blender 5.0.1, 5.1.2 and 5.2.1, exited about 0.05 s after a 2 s file ended, and stopped within about 0.05 s of the lifeline closing. With standard input from /dev/null the lifeline stopped the worker before it opened the output, which is why the parent holds a pipe. Opening CoreAudio and OpenAL by name, but not SDL, PulseAudio or WASAPI, from a -noaudio background child, and the None output returning a handle whose status is not playing, were probed on 5.0.1 and 5.1.2 on macOS arm64 only. Nothing audible was played and no human listened. The installed-ZIP full native suite, including test_audio_player and the Play audio tests in test_result_media and test_result_actions, passed with 2019 tests and three Windows-only skips on each of macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1; its children used a recording output in place of a sound device or Blender's None output. Hosted Linux and Windows runs, desktop clicks and human listening had not happened at this review.",
    "sources": {
      "scenario/core/jobs/audio_player.py": "c3e63624468aae91aae0d72e0d8542f84e371d7d009de606a176b41293f9e375",
      "scenario/blender/audio_player_worker.py": "03398600e9eec3b00f4e6e56c2b943baed46b395f4378579f0a8695a30776c53",
      "scenario/blender/result_media.py": "e868fd88dbadccefc3718b7f37bee0c7e1c59d01916e6d913db29677aa537283",
      "tests/blender/test_audio_player.py": "a67d5c0c18a2b78f08f3457798afd2703104f173afc9a7755122017255038279",
      "tests/unit/test_audio_player.py": "7e82277bbafa89b8466a96cce15ae83e19b6fafc544ef618da337c3f2959b8ae"
    }
  }
}
---

# In-extension audio playback limits

Evidence for [the canonical guide](../../KNOWN_LIMITATIONS.md).
