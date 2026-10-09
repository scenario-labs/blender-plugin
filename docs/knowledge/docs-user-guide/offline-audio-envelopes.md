---
{
  "type": "Evidence",
  "id": "docs-user-guide.offline-audio-envelopes",
  "title": "Generations waveform preview through the offline decoder",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "offline-audio-envelopes",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "fb699b8555f7cee62147794516cc7aaa224864f7",
    "limits": "Reviewed the prototype Generations preview after the PCM-only reader's retirement: worker-thread decoding through the offline child, before/after file stamps, envelope raster, the missing-executable refusal, Cancel terminating the decoder and the stated format and size limits. Installed-ZIP native tests for the waveform decoder, session previews and the prototype preview passed on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1; Windows and Linux rest on hosted CI, not on this review. Desktop drawing, UI scale and human listening were not reviewed; the inherited audio-preview topic keeps its older claims.",
    "sources": {
      "scenario/blender/audio_preview.py": "74c2781ed85dbd5b85cd9a79c43880eed7e53404a3f9c4514abe7d41c2d35e45",
      "tests/blender/test_audio_preview.py": "0453fd56a93036475d25b795c0d3a0dade754ef716a5f3e939b155f8a55ea083",
      "scenario/core/jobs/audio_decode.py": "4bc3c5a270ad36449e8927d580f9346075f737ad07da0a0b63967de4d81340ba",
      "scenario/blender/waveform_worker.py": "184e6aea667e31e84fa46f68c61448c12714e52d39dfdaef40f56db3091a4e4a",
      "scenario/core/audio_waveform.py": "888c1c6a1c3ab5dfeb0f174c807290e399c856cf067bd37e6011f5e184edf18c",
      "scenario/blender/runtime.py": "1c597c458a32872241b53724886fb7ba89efd9a6b5b2a3c7daeb2c94d1b5d401",
      "tests/blender/test_waveform_worker.py": "b1fbfb74b8c75ef5366283ce32c97b23350bb1e81766891a2a7fab046b537aa5"
    }
  }
}
---

# Generations waveform preview through the offline decoder

Evidence for [the canonical document](../../USER_GUIDE.md).
