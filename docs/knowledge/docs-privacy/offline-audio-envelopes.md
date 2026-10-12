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
    "limits": "Inspected where the decoder's request, disposable profile, temporary files, log and outputs are written and removed, the scrubbed child environment, offline mode, the cached envelope sidecar and the prototype preview's cache/audio-preview directories, including the sweep of abandoned decode directories older than a day. The prototype preview reads the downloaded file in place after a regular-file check. No network access, credential or signed URL reaches the child; this does not audit other cache users. On 2026-10-12 the runtime.py fingerprint was refreshed after saved splat import passed point limit and axis options through prepare_model_application and prepare_asset_application and added revise_model_application; waveform_spec resolution, its fallback and retirement are unchanged, as are these statements and the review date.",
    "sources": {
      "scenario/core/jobs/audio_decode.py": "45d1cc7aa8964ad0b7014bf28a23f3d3a46e336eee4770581e79a8aa293d0064",
      "scenario/blender/waveform_worker.py": "184e6aea667e31e84fa46f68c61448c12714e52d39dfdaef40f56db3091a4e4a",
      "scenario/core/audio_waveform.py": "888c1c6a1c3ab5dfeb0f174c807290e399c856cf067bd37e6011f5e184edf18c",
      "scenario/core/jobs/result_previews.py": "b08399a5f91362d9ccffa7ac615088f8dcd8c66984f86736245daca529dae741",
      "scenario/core/jobs/local_render.py": "259ec65d914e12b8a8dce009ea68a07f4ab3ca1007a232a63a2c43fb64e5daaf",
      "scenario/blender/audio_preview.py": "e77b8d21f7733322b9714a17ff8b982d24cd993e5702e6b0403d7b5b3ddfbb22",
      "scenario/blender/runtime.py": "46b212bd99c8473dea2ad9af66ace43ca6ba22e02b8711823a4e735cf9deb332"
    }
  }
}
---

# Local data used by offline audio envelopes

Evidence for [the canonical document](../../PRIVACY.md).
