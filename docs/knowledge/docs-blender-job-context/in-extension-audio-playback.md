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
    "limits": "Reviewed the Play audio sentences of the saved media controller paragraph against result_media.py: the child started after the prepare_playback copy, the copy pinned until the child exits, timer polling, the stopping events, unregistering waiting through AudioPlayer.wait, and late copies that never start a child. The installed-ZIP full native suite, including test_audio_player and the Play audio tests in test_result_media and test_result_actions, passed with 2019 tests and three Windows-only skips on each of macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1; its children used a recording output in place of a sound device or Blender's None output. Hosted Linux and Windows runs, desktop clicks and human listening had not happened at this review.",
    "sources": {
      "scenario/blender/result_media.py": "e868fd88dbadccefc3718b7f37bee0c7e1c59d01916e6d913db29677aa537283",
      "scenario/core/jobs/audio_player.py": "a40e4cbf2a2596d248c0272fcf03d9d6132b9442098676202c55a5b576c4b90c",
      "scenario/blender/job_session.py": "b20ae0be8fbec16510d6750fa50757f7830ebf937f65649e186c16ee9068fb28",
      "tests/blender/test_result_media.py": "3ac63e2eb21f6f79d552e177cb5613de5261defadbc63c0e78c2dd08c58b8cda"
    }
  }
}
---

# Saved media controller: audio playback ownership

Evidence for [the canonical guide](../../BLENDER_JOB_CONTEXT.md).
