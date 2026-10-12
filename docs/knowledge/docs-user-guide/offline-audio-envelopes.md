---
{
  "type": "Evidence",
  "id": "docs-user-guide.offline-audio-envelopes",
  "title": "Generations waveform preview through the offline decoder",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "offline-audio-envelopes",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "759f764dff9c9d9b1f50efecdd46835471f19189",
    "limits": "Reviewed the prototype Generations preview after the PCM-only reader's retirement: worker-thread decoding through the offline child, before/after file stamps, envelope raster, the missing-executable refusal, Cancel terminating the decoder and the stated format and size limits. Installed-ZIP native tests for the waveform decoder, session previews and the prototype preview passed on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1; Windows and Linux rest on hosted CI, not on this review. Desktop drawing, UI scale and human listening were not reviewed; the inherited audio-preview topic keeps its older claims. Re-checked the interface-responsiveness claim after the main-thread lock test changed: the test bounds the offline decode's longest main-thread pause at half that of the same decode run in process, with automatic garbage collection paused during both measurements. Other drifted sources were not re-reviewed. On 2026-10-12 the runtime.py fingerprint was refreshed after saved splat import passed point limit and axis options through prepare_model_application and prepare_asset_application and added revise_model_application; waveform_spec resolution, its fallback and retirement are unchanged, as are these statements and the review date. The refreshed fingerprint also covers main's prepare_first_frame_application and asset organization polling in runtime.py, which do not touch waveform_spec.",
    "sources": {
      "scenario/blender/audio_preview.py": "e77b8d21f7733322b9714a17ff8b982d24cd993e5702e6b0403d7b5b3ddfbb22",
      "tests/blender/test_audio_preview.py": "c024d3dff025d0c8600c0575fa2850dd16d29a4fc0babe79c5f82b35757b2f0e",
      "scenario/core/jobs/audio_decode.py": "45d1cc7aa8964ad0b7014bf28a23f3d3a46e336eee4770581e79a8aa293d0064",
      "scenario/blender/waveform_worker.py": "184e6aea667e31e84fa46f68c61448c12714e52d39dfdaef40f56db3091a4e4a",
      "scenario/core/audio_waveform.py": "888c1c6a1c3ab5dfeb0f174c807290e399c856cf067bd37e6011f5e184edf18c",
      "scenario/blender/runtime.py": "a62737e55602985dba9fde0199e6ffd65d73e174df0de664c49e0277661671e1",
      "tests/blender/test_waveform_worker.py": "5e03524a94fcedee799c9030c9b6a17ee872d9b8982349602c60bb369a62a230"
    }
  }
}
---

# Generations waveform preview through the offline decoder

Evidence for [the canonical document](../../USER_GUIDE.md).
