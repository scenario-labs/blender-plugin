---
{
  "type": "Evidence",
  "id": "docs-known-limitations.offline-audio-envelopes",
  "title": "Waveform preview decoder limits",
  "evidence": {
    "path": "docs/KNOWN_LIMITATIONS.md",
    "scope": "offline-audio-envelopes",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "fb699b8555f7cee62147794516cc7aaa224864f7",
    "limits": "Reviewed the stated child start-up cost, missing-executable failure, two tracked readers, cancellation that terminates the decoder and the remaining filesystem-call limit. Also reviewed the deadline check against each reader's finish time, so an outcome finished before 30 s displays when Blender's timer runs late and a later one is discarded, and unregister's bounded wait of up to five seconds for readers to stop their decoders; the native shutdown test uses a stand-in for the child process that runs until canceled, and quitting Blender during a decode was not exercised. Start-up figures are local medians of five runs per version on macOS arm64, not test assertions. Installed-ZIP native tests for the waveform decoder, session previews and the prototype preview passed on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1; Windows and Linux rest on hosted CI, not on this review. Windows, Linux, antivirus and sandboxed packages are unmeasured.",
    "sources": {
      "scenario/blender/audio_preview.py": "e77b8d21f7733322b9714a17ff8b982d24cd993e5702e6b0403d7b5b3ddfbb22",
      "tests/blender/test_audio_preview.py": "c024d3dff025d0c8600c0575fa2850dd16d29a4fc0babe79c5f82b35757b2f0e",
      "scenario/core/jobs/audio_decode.py": "45d1cc7aa8964ad0b7014bf28a23f3d3a46e336eee4770581e79a8aa293d0064",
      "scenario/blender/waveform_worker.py": "184e6aea667e31e84fa46f68c61448c12714e52d39dfdaef40f56db3091a4e4a",
      "scenario/core/audio_waveform.py": "888c1c6a1c3ab5dfeb0f174c807290e399c856cf067bd37e6011f5e184edf18c",
      "scenario/core/jobs/preview_scheduler.py": "259ba661bb90b15d33723bfd7bafc0eb70b4443b5c8a56e70d45b9ffa99ac466",
      "scenario/blender/runtime.py": "286974e2a90e4776de71d081651a88424c543573add3ed125b072ad47c524883",
      "tests/blender/test_waveform_worker.py": "b1fbfb74b8c75ef5366283ce32c97b23350bb1e81766891a2a7fab046b537aa5"
    }
  }
}
---

# Waveform preview decoder limits

Evidence for [the canonical document](../../KNOWN_LIMITATIONS.md).
