---
{
  "type": "Evidence",
  "id": "docs-ui-style.in-extension-audio-playback",
  "title": "Play audio, Stop audio and system player rows",
  "evidence": {
    "path": "docs/UI_STYLE.md",
    "scope": "in-extension-audio-playback",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-13",
    "base_revision": "ca97ec56e28e58cdbe64a7000fa82aaa71e5d39a",
    "limits": "Reviewed the saved media playback rows against saved_job_actions.describe (a video row of Play video and Play in Blender; an audio row of Play audio or Stop audio and Waveform, then Open in system player on a row of its own; Stop only for the asset that listening names, without the saved revision; numbering over every saved asset; none of these names in the MCP action vocabulary), job_recovery.result_actions passing result_media.controller.listening, which reads only the pending LISTEN request and active players in memory for the current context, and the two new operators, unavailable to Play audio in background Blender. The claim that a third aligned button would clip the system player's label is reasoning from the 561 px sidebar measured for the waveform text, not a screenshot. No desktop pass has drawn these rows. The installed-ZIP full native suite, including test_audio_player and the Play audio tests in test_result_media and test_result_actions, passed with 2019 tests and three Windows-only skips on each of macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1; its children used a recording output in place of a sound device or Blender's None output. Hosted Linux and Windows runs, desktop clicks and human listening had not happened at this review.",
    "sources": {
      "scenario/core/ui/saved_job_actions.py": "26d723e6b0a528b32081351e23010b0b397d072ba82eb5f5ab0751a0bd862fa9",
      "scenario/blender/job_recovery.py": "39e0a1c00ee3e64e0055cdb6ce4516c7799dcb47735b3d46318a76f5e0449205",
      "scenario/blender/result_media.py": "e868fd88dbadccefc3718b7f37bee0c7e1c59d01916e6d913db29677aa537283",
      "tests/unit/test_saved_job_actions.py": "74839da272dcee1d6c81b7bf2f07f1d5c4f0e9e85d437c407dce605d2883a7e5",
      "tests/blender/test_result_media.py": "3ac63e2eb21f6f79d552e177cb5613de5261defadbc63c0e78c2dd08c58b8cda",
      "tests/blender/test_result_actions.py": "9f56619737843d597247eb80dac4860832cc43e9b210c1622c31f2cd0b2abb74"
    }
  }
}
---

# Play audio, Stop audio and system player rows

Evidence for [the canonical guide](../../UI_STYLE.md).
