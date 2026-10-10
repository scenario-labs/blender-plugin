---
{
  "type": "Evidence",
  "id": "docs-user-guide.offline-audio-envelopes",
  "title": "Generations waveform preview through the offline decoder",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "offline-audio-envelopes",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "fb699b8555f7cee62147794516cc7aaa224864f7",
    "limits": "Reviewed the prototype Generations preview after the PCM-only reader's retirement: worker-thread decoding through the offline child, before/after file stamps, envelope raster, the missing-executable refusal, Cancel terminating the decoder and the stated format and size limits. Installed-ZIP native tests for the waveform decoder, session previews and the prototype preview passed on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1; Windows and Linux rest on hosted CI, not on this review. Desktop drawing, UI scale and human listening were not reviewed; the inherited audio-preview topic keeps its older claims.",
    "sources": {
      "scenario/blender/audio_preview.py": "e77b8d21f7733322b9714a17ff8b982d24cd993e5702e6b0403d7b5b3ddfbb22",
      "tests/blender/test_audio_preview.py": "c024d3dff025d0c8600c0575fa2850dd16d29a4fc0babe79c5f82b35757b2f0e",
      "scenario/core/jobs/audio_decode.py": "45d1cc7aa8964ad0b7014bf28a23f3d3a46e336eee4770581e79a8aa293d0064",
      "scenario/blender/waveform_worker.py": "184e6aea667e31e84fa46f68c61448c12714e52d39dfdaef40f56db3091a4e4a",
      "scenario/core/audio_waveform.py": "888c1c6a1c3ab5dfeb0f174c807290e399c856cf067bd37e6011f5e184edf18c",
      "scenario/blender/runtime.py": "286974e2a90e4776de71d081651a88424c543573add3ed125b072ad47c524883",
      "tests/blender/test_waveform_worker.py": "b1fbfb74b8c75ef5366283ce32c97b23350bb1e81766891a2a7fab046b537aa5"
    }
  }
}
---

# Generations waveform preview through the offline decoder

Evidence for [the canonical document](../../USER_GUIDE.md).
