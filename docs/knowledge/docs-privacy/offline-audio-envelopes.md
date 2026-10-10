---
{
  "type": "Evidence",
  "id": "docs-privacy.offline-audio-envelopes",
  "title": "Local data used by offline audio envelopes",
  "evidence": {
    "path": "docs/PRIVACY.md",
    "scope": "offline-audio-envelopes",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "fb699b8555f7cee62147794516cc7aaa224864f7",
    "limits": "Inspected where the decoder's request, disposable profile, temporary files, log and outputs are written and removed, the scrubbed child environment, offline mode, the cached envelope sidecar and the prototype preview's cache/audio-preview directories, including the sweep of abandoned decode directories older than a day. The prototype preview reads the downloaded file in place after a regular-file check. No network access, credential or signed URL reaches the child; this does not audit other cache users.",
    "sources": {
      "scenario/core/jobs/audio_decode.py": "45d1cc7aa8964ad0b7014bf28a23f3d3a46e336eee4770581e79a8aa293d0064",
      "scenario/blender/waveform_worker.py": "184e6aea667e31e84fa46f68c61448c12714e52d39dfdaef40f56db3091a4e4a",
      "scenario/core/audio_waveform.py": "888c1c6a1c3ab5dfeb0f174c807290e399c856cf067bd37e6011f5e184edf18c",
      "scenario/core/jobs/result_previews.py": "613ba1dcd0c807b0300fcad030739185bbe45a04a53de481f1c42652fd35ed73",
      "scenario/core/jobs/local_render.py": "259ec65d914e12b8a8dce009ea68a07f4ab3ca1007a232a63a2c43fb64e5daaf",
      "scenario/blender/audio_preview.py": "e77b8d21f7733322b9714a17ff8b982d24cd993e5702e6b0403d7b5b3ddfbb22",
      "scenario/blender/runtime.py": "286974e2a90e4776de71d081651a88424c543573add3ed125b072ad47c524883"
    }
  }
}
---

# Local data used by offline audio envelopes

Evidence for [the canonical document](../../PRIVACY.md).
