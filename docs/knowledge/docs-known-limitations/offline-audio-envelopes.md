---
{
  "type": "Evidence",
  "id": "docs-known-limitations.offline-audio-envelopes",
  "title": "Waveform preview decoder limits",
  "evidence": {
    "path": "docs/KNOWN_LIMITATIONS.md",
    "scope": "offline-audio-envelopes",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "759f764dff9c9d9b1f50efecdd46835471f19189",
    "limits": "Reviewed the stated child start-up cost, missing-executable failure, two tracked readers, cancellation that terminates the decoder and the remaining filesystem-call limit. Also reviewed the deadline check against each reader's finish time, so an outcome finished before 30 s displays when Blender's timer runs late and a later one is discarded, and unregister's bounded wait of up to five seconds for readers to stop their decoders; the native shutdown test uses a stand-in for the child process that runs until canceled, and quitting Blender during a decode was not exercised. Start-up figures are local medians of five runs per version on macOS arm64, not test assertions. Installed-ZIP native tests for the waveform decoder, session previews and the prototype preview passed on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1; Windows and Linux rest on hosted CI, not on this review. Windows, Linux, antivirus and sandboxed packages are unmeasured. Re-checked after the main-thread lock test in test_waveform_worker.py changed to compare the offline decode's longest pause with an in-process control: the start-up, cancellation and missing-executable claims above do not depend on it. Other drifted sources were not re-reviewed. On 2026-10-12 the runtime.py fingerprint was refreshed after saved splat import passed point limit and axis options through prepare_model_application and prepare_asset_application and added revise_model_application; waveform_spec resolution, its fallback and retirement are unchanged, as are these statements and the review date. The refreshed fingerprint also covers main's prepare_first_frame_application and asset organization polling in runtime.py, which do not touch waveform_spec. After this review, the unreleased prototype waveform preview was retired; its sources here were replaced by their successors, result_media.py and test_result_media.py, without re-reviewing this topic's other claims. The current saved media claims are evidenced by this document's saved-media-playback topic.",
    "sources": {
      "scenario/blender/result_media.py": "3dedc599853505ebbb12be68bd2406e45cf5eaee16090de77237fd2b4dba1607",
      "tests/blender/test_result_media.py": "250abc036f5b46890c384b17d25311ee8c59e57fb1cb84e45233e77cd49c8a2f",
      "scenario/core/jobs/audio_decode.py": "22a905adefc34dce78cacbf2068e9d7b48c6e2cda26ec5ca09473a5ee35d609b",
      "scenario/blender/waveform_worker.py": "184e6aea667e31e84fa46f68c61448c12714e52d39dfdaef40f56db3091a4e4a",
      "scenario/core/audio_waveform.py": "888c1c6a1c3ab5dfeb0f174c807290e399c856cf067bd37e6011f5e184edf18c",
      "scenario/core/jobs/preview_scheduler.py": "969bd75231ed09bc81d32d27089405b47281cfe98391907d6769623d3350af8c",
      "scenario/blender/runtime.py": "a14882a09ef239906b7d06f46b13bfee69be8ae15533406faa7408ae4ca07441",
      "tests/blender/test_waveform_worker.py": "5e03524a94fcedee799c9030c9b6a17ee872d9b8982349602c60bb369a62a230"
    }
  }
}
---

# Waveform preview decoder limits

Evidence for [the canonical document](../../KNOWN_LIMITATIONS.md).
