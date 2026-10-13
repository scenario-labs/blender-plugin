---
{
  "type": "Evidence",
  "id": "tests-fixtures-readme.audio-player-media",
  "title": "Generated audio for the audio player tests",
  "evidence": {
    "path": "tests/fixtures/README.md",
    "scope": "audio-player-media",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-13",
    "base_revision": "ca97ec56e28e58cdbe64a7000fa82aaa71e5d39a",
    "limits": "Reviewed that the audio player tests synthesize WAV tones with the wave module and MP3, Ogg Vorbis, FLAC and ADTS AAC tones with Blender's audio module at runtime, copy the documented first-party film-four-seconds-audio.mp4 as an M4A, write an undecodable MP3 header, and commit no new media; their children play to a recording stand-in that replaces aud.Device or to Blender's None output, so no test sound reaches a speaker. Re-checked on 2026-10-13 after a Windows CI fix, not a full re-review: test_result_media's Play audio test now compares the copy's playback root by file identity, because on Windows the copy keeps Python's extended \\\\?\\ namespace; the claims above still hold, and this fingerprint is the changed file's.",
    "sources": {
      "tests/blender/test_audio_player.py": "a67d5c0c18a2b78f08f3457798afd2703104f173afc9a7755122017255038279",
      "tests/blender/test_result_media.py": "66c0a220b98878570bd8f99c8a330ec677247b7d18f745a19c53244fe07e38d7",
      "tests/unit/test_audio_player.py": "7e82277bbafa89b8466a96cce15ae83e19b6fafc544ef618da337c3f2959b8ae"
    }
  }
}
---

# Generated audio for the audio player tests

Evidence for [the canonical inventory](../../../tests/fixtures/README.md).
