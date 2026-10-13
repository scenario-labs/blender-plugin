---
{
  "type": "Evidence",
  "id": "docs-user-guide.in-extension-audio-playback",
  "title": "Playing saved audio inside Blender",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "in-extension-audio-playback",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-13",
    "base_revision": "ca97ec56e28e58cdbe64a7000fa82aaa71e5d39a",
    "limits": "Reviewed the Audio section's Play audio paragraph and the Audio row of the Generations actions table, as rewritten on main's shortened guide (#468), against result_media.py, audio_player.py, audio_player_worker.py and saved_job_actions.py: playback inside Blender through the output chosen in Preferences, the ten-minute check, Stop audio replacing the button while it plays, another result's Play audio stopping the first, Open in system player opening the private copy in the system player, and offline use, since nothing checks Online Access because nothing reaches the network. The guide leaves the process details, the None refusal and the start-up delay to the result previews guide and known limitations. The installed-ZIP full native suite, including test_audio_player and the Play audio tests in test_result_media and test_result_actions, passed with 2019 tests and three Windows-only skips on each of macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1; its children used a recording output in place of a sound device or Blender's None output. Hosted Linux and Windows runs, desktop clicks and human listening had not happened at this review.",
    "sources": {
      "scenario/blender/result_media.py": "e868fd88dbadccefc3718b7f37bee0c7e1c59d01916e6d913db29677aa537283",
      "scenario/core/jobs/audio_player.py": "a40e4cbf2a2596d248c0272fcf03d9d6132b9442098676202c55a5b576c4b90c",
      "scenario/blender/audio_player_worker.py": "03398600e9eec3b00f4e6e56c2b943baed46b395f4378579f0a8695a30776c53",
      "scenario/core/ui/saved_job_actions.py": "26d723e6b0a528b32081351e23010b0b397d072ba82eb5f5ab0751a0bd862fa9",
      "tests/blender/test_audio_player.py": "a67d5c0c18a2b78f08f3457798afd2703104f173afc9a7755122017255038279",
      "tests/blender/test_result_media.py": "3ac63e2eb21f6f79d552e177cb5613de5261defadbc63c0e78c2dd08c58b8cda"
    }
  }
}
---

# Playing saved audio inside Blender

Evidence for [the canonical guide](../../USER_GUIDE.md).
