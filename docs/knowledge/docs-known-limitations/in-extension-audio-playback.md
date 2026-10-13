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
    "limits": "Reviewed the Play audio bullet and the Play audio additions to the saved media bullets against audio_player.py, audio_player_worker.py and result_media.py: one child per playback, playback from the start with no pause, seeking, volume or playhead, the Preferences output opened by name with the aud module's default 48 kHz stereo (read from a probe that opened CoreAudio by name and reported 48000 Hz and two channels), playback despite a parent started with -noaudio because the child opens its own output, and the crash path covered only by closing the pipe. A local probe on macOS arm64 played a digitally silent 8 kHz WAV through the unmodified worker on the CoreAudio output with standard input held open: it reported playback 0.61 to 0.83 s after the child started on Blender 5.0.1, 5.1.2 and 5.2.1, exited about 0.05 s after a 2 s file ended, and stopped within about 0.05 s of the lifeline closing. With standard input from /dev/null the lifeline stopped the worker before it opened the output, which is why the parent holds a pipe. Opening CoreAudio and OpenAL by name, but not SDL, PulseAudio or WASAPI, from a -noaudio background child, and the None output returning a handle whose status is not playing, were probed on 5.0.1 and 5.1.2 on macOS arm64 only. Nothing audible was played and no human listened. The installed-ZIP full native suite, including test_audio_player and the Play audio tests in test_result_media and test_result_actions, passed with 2019 tests and three Windows-only skips on each of macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1; its children used a recording output in place of a sound device or Blender's None output. Hosted Linux and Windows runs, desktop clicks and human listening had not happened at this review. Re-checked on 2026-10-13 after two review findings on #466: the new sentences on disabling the extension follow AudioPlayer.wait, which joins the watcher for three seconds, kills the child and joins three seconds more, and MediaController.shutdown, which keeps and logs a child whose wait returns False. Unit tests drive the watcher's step on a fake process, check that the owner's poll, phase, active and released read only memory, that removal and the sweep run on the ScenarioAudioPlayer thread, and that wait returns False for a child that survives the kill while the watcher still removes its directory once it exits. Installed tests record that no listen-* removal ran on Blender's main thread across a file load, a connection change and unregistering, that unregistering returns with the directory gone, and that a stand-in survivor stays listed with one warning naming no path. The full installed suite passed on macOS arm64 Blender 5.1.2 with 2020 tests and three Windows-only skips; 5.0.1 and 5.2.1 were not rerun for this change. These fingerprints are the re-checked files': scenario/core/jobs/audio_player.py, scenario/blender/result_media.py, tests/unit/test_audio_player.py, tests/blender/test_audio_player.py.",
    "sources": {
      "scenario/core/jobs/audio_player.py": "d1f7851592e4a1b781a4ae2724dcb132af0d1ed86c697b80830e30d68583e7be",
      "scenario/blender/audio_player_worker.py": "03398600e9eec3b00f4e6e56c2b943baed46b395f4378579f0a8695a30776c53",
      "scenario/blender/result_media.py": "08aa532bb8b16a916c5c8c618e68e80b249654f543ad0569c7333b4b630d501c",
      "tests/blender/test_audio_player.py": "53d8646587b4ef577083ca8292b5d55ddb691b553622c52d8696becc7239b68d",
      "tests/unit/test_audio_player.py": "d292050db7db5cb78979d090330374e38cd9f1c0661c93dd485ffd6a1d99f22a"
    }
  }
}
---

# In-extension audio playback limits

Evidence for [the canonical guide](../../KNOWN_LIMITATIONS.md).
