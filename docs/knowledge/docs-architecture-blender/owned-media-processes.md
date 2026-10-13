---
{
  "type": "Evidence",
  "id": "docs-architecture-blender.owned-media-processes",
  "title": "Generated media decoded and played in owned processes",
  "evidence": {
    "path": "docs/architecture/blender.md",
    "scope": "owned-media-processes",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-13",
    "base_revision": "ca97ec56e28e58cdbe64a7000fa82aaa71e5d39a",
    "limits": "Reviewed the paragraph against audio_decode.py and audio_player.py, which start waveform_worker.py and audio_player_worker.py with the listed flags and no bpy, and against result_media.py, which never imports aud. Other modules that use aud in the session, such as the sequencer strip primitives, are application paths outside this rule's scope and were not re-reviewed.",
    "sources": {
      "scenario/core/jobs/audio_decode.py": "22a905adefc34dce78cacbf2068e9d7b48c6e2cda26ec5ca09473a5ee35d609b",
      "scenario/blender/waveform_worker.py": "184e6aea667e31e84fa46f68c61448c12714e52d39dfdaef40f56db3091a4e4a",
      "scenario/core/jobs/audio_player.py": "a40e4cbf2a2596d248c0272fcf03d9d6132b9442098676202c55a5b576c4b90c",
      "scenario/blender/audio_player_worker.py": "03398600e9eec3b00f4e6e56c2b943baed46b395f4378579f0a8695a30776c53",
      "scenario/blender/result_media.py": "e868fd88dbadccefc3718b7f37bee0c7e1c59d01916e6d913db29677aa537283"
    }
  }
}
---

# Generated media decoded and played in owned processes

Evidence for [the canonical guide](../../architecture/blender.md).
