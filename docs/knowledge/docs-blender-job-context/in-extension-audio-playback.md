---
{
  "type": "Evidence",
  "id": "docs-blender-job-context.in-extension-audio-playback",
  "title": "Saved media controller: audio playback ownership",
  "evidence": {
    "path": "docs/BLENDER_JOB_CONTEXT.md",
    "scope": "in-extension-audio-playback",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-13",
    "base_revision": "ca97ec56e28e58cdbe64a7000fa82aaa71e5d39a",
    "limits": "Reviewed the Play audio sentences of the saved media controller paragraph against result_media.py: the child started after the prepare_playback copy, the copy pinned until the child exits, timer polling, the stopping events, unregistering waiting through AudioPlayer.wait, and late copies that never start a child. The installed-ZIP full native suite, including test_audio_player and the Play audio tests in test_result_media and test_result_actions, passed with 2019 tests and three Windows-only skips on each of macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1; its children used a recording output in place of a sound device or Blender's None output. Hosted Linux and Windows runs, desktop clicks and human listening had not happened at this review. Re-checked on 2026-10-13 after a Windows CI fix, not a full re-review: test_result_media's Play audio test now compares the copy's playback root by file identity, because on Windows the copy keeps Python's extended \\\\?\\ namespace; the claims above still hold, and this fingerprint is the changed file's. Re-checked on 2026-10-13 after two review findings on #466: the controller now reads each process's phase from memory, its watcher thread reads the reports, kills and removes the directory, and unregistering keeps a process that survives the kill with a warning while the watcher keeps reaping it; the paragraph now says so. Unit tests drive the watcher's step on a fake process, check that the owner's poll, phase, active and released read only memory, that removal and the sweep run on the ScenarioAudioPlayer thread, and that wait returns False for a child that survives the kill while the watcher still removes its directory once it exits. Installed tests record that no listen-* removal ran on Blender's main thread across a file load, a connection change and unregistering, that unregistering returns with the directory gone, and that a stand-in survivor stays listed with one warning naming no path. The full installed suite passed on macOS arm64 Blender 5.1.2 with 2020 tests and three Windows-only skips; 5.0.1 and 5.2.1 were not rerun for this change. These fingerprints are the re-checked files': scenario/blender/result_media.py, scenario/core/jobs/audio_player.py, tests/blender/test_result_media.py.",
    "sources": {
      "scenario/blender/result_media.py": "08aa532bb8b16a916c5c8c618e68e80b249654f543ad0569c7333b4b630d501c",
      "scenario/core/jobs/audio_player.py": "d1f7851592e4a1b781a4ae2724dcb132af0d1ed86c697b80830e30d68583e7be",
      "scenario/blender/job_session.py": "b20ae0be8fbec16510d6750fa50757f7830ebf937f65649e186c16ee9068fb28",
      "tests/blender/test_result_media.py": "60f41e2209c8b05d1ac52bb956d9d22e28e776f9fe8478156d5255c109dd11ce"
    }
  }
}
---

# Saved media controller: audio playback ownership

Evidence for [the canonical guide](../../BLENDER_JOB_CONTEXT.md).
