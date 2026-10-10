---
{
  "type": "Evidence",
  "id": "docs-privacy.offline-audio-envelopes",
  "title": "Local data used by offline audio envelopes",
  "evidence": {
    "path": "docs/PRIVACY.md",
    "scope": "offline-audio-envelopes",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-11",
    "base_revision": "1d86f53d3489b23f2447be69cb589140e2f3ba64",
    "limits": "Inspected where the decoder's request, disposable profile, temporary files, log and outputs are written and removed, the scrubbed child environment, offline mode, the cached envelope sidecar and the prototype preview's cache/audio-preview directories, including the sweep of abandoned decode directories older than a day. The prototype preview reads the downloaded file in place after a regular-file check. No network access, credential or signed URL reaches the child; this does not audit other cache users. On 2026-10-12 the runtime.py fingerprint was refreshed after saved splat import passed point limit and axis options through prepare_model_application and prepare_asset_application and added revise_model_application; waveform_spec resolution, its fallback and retirement are unchanged, as are these statements and the review date. After this review, the unreleased prototype waveform preview was retired; its sources here were replaced by their successors, result_media.py and test_result_media.py, without re-reviewing this topic's other claims. The current saved media claims are evidenced by this document's saved-media-playback topic.",
    "sources": {
      "scenario/core/jobs/audio_decode.py": "22a905adefc34dce78cacbf2068e9d7b48c6e2cda26ec5ca09473a5ee35d609b",
      "scenario/blender/waveform_worker.py": "184e6aea667e31e84fa46f68c61448c12714e52d39dfdaef40f56db3091a4e4a",
      "scenario/core/audio_waveform.py": "888c1c6a1c3ab5dfeb0f174c807290e399c856cf067bd37e6011f5e184edf18c",
      "scenario/core/jobs/result_previews.py": "b08399a5f91362d9ccffa7ac615088f8dcd8c66984f86736245daca529dae741",
      "scenario/core/jobs/local_render.py": "fadde8df7fa89d69735f33c2d78682dafc9566c0ef401ab8b2deb6f08a1b912e",
      "scenario/blender/result_media.py": "276b32bbb8e7c1eafa904d4e2762ecfbfaf8e9cfb3c611ffac300f1bea080b69",
      "scenario/blender/runtime.py": "a14882a09ef239906b7d06f46b13bfee69be8ae15533406faa7408ae4ca07441"
    }
  }
}
---

# Local data used by offline audio envelopes

Evidence for [the canonical document](../../PRIVACY.md).
