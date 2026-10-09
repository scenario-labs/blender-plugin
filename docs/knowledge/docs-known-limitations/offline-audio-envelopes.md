---
{
  "type": "Evidence",
  "id": "docs-known-limitations.offline-audio-envelopes",
  "title": "Waveform preview decoder limits",
  "evidence": {
    "path": "docs/KNOWN_LIMITATIONS.md",
    "scope": "offline-audio-envelopes",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "fb699b8555f7cee62147794516cc7aaa224864f7",
    "limits": "Reviewed the stated child start-up cost, missing-executable failure, two tracked readers, cancellation that terminates the decoder and the remaining filesystem-call limit. Start-up figures are local medians of five runs per version on macOS arm64, not test assertions. Installed-ZIP native tests for the waveform decoder, session previews and the prototype preview passed on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1; Windows and Linux rest on hosted CI, not on this review. Windows, Linux, antivirus and sandboxed packages are unmeasured.",
    "sources": {
      "scenario/blender/audio_preview.py": "14b1f05e7ba0980e2c303d21d58945ae59286f38b0b14559b295dc5833fb749f",
      "tests/blender/test_audio_preview.py": "0453fd56a93036475d25b795c0d3a0dade754ef716a5f3e939b155f8a55ea083",
      "scenario/core/jobs/audio_decode.py": "332645a336308d1a52690fa55b888073fffff5213f95cc59460a2314ca973720",
      "scenario/blender/waveform_worker.py": "184e6aea667e31e84fa46f68c61448c12714e52d39dfdaef40f56db3091a4e4a",
      "scenario/core/audio_waveform.py": "888c1c6a1c3ab5dfeb0f174c807290e399c856cf067bd37e6011f5e184edf18c",
      "scenario/core/jobs/preview_scheduler.py": "259ba661bb90b15d33723bfd7bafc0eb70b4443b5c8a56e70d45b9ffa99ac466",
      "scenario/blender/runtime.py": "1c597c458a32872241b53724886fb7ba89efd9a6b5b2a3c7daeb2c94d1b5d401",
      "tests/blender/test_waveform_worker.py": "b1fbfb74b8c75ef5366283ce32c97b23350bb1e81766891a2a7fab046b537aa5"
    }
  }
}
---

# Waveform preview decoder limits

Evidence for [the canonical document](../../KNOWN_LIMITATIONS.md).
