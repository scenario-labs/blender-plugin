---
{
  "type": "Evidence",
  "id": "docs-privacy.offline-audio-envelopes",
  "title": "Local data used by offline audio envelopes",
  "evidence": {
    "path": "docs/PRIVACY.md",
    "scope": "offline-audio-envelopes",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "fb699b8555f7cee62147794516cc7aaa224864f7",
    "limits": "Inspected where the decoder's request, disposable profile, temporary files, log and outputs are written and removed, the scrubbed child environment, offline mode, the cached envelope sidecar and the prototype preview's cache/audio-preview directories, including the sweep of abandoned decode directories older than a day. The prototype preview reads the downloaded file in place after a regular-file check. No network access, credential or signed URL reaches the child; this does not audit other cache users.",
    "sources": {
      "scenario/core/jobs/audio_decode.py": "332645a336308d1a52690fa55b888073fffff5213f95cc59460a2314ca973720",
      "scenario/blender/waveform_worker.py": "184e6aea667e31e84fa46f68c61448c12714e52d39dfdaef40f56db3091a4e4a",
      "scenario/core/audio_waveform.py": "888c1c6a1c3ab5dfeb0f174c807290e399c856cf067bd37e6011f5e184edf18c",
      "scenario/core/jobs/result_previews.py": "1bc82a1318619cb3771377caa6db67d107d6180a85575fbcc2d5470c087e5467",
      "scenario/core/jobs/local_render.py": "37c57537f75172892b868c56c9e0bcb641617c271ec1dae5a037e96ecabaeaf8",
      "scenario/blender/audio_preview.py": "14b1f05e7ba0980e2c303d21d58945ae59286f38b0b14559b295dc5833fb749f",
      "scenario/blender/runtime.py": "1c597c458a32872241b53724886fb7ba89efd9a6b5b2a3c7daeb2c94d1b5d401"
    }
  }
}
---

# Local data used by offline audio envelopes

Evidence for [the canonical document](../../PRIVACY.md).
