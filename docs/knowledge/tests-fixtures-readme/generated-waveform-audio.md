---
{
  "type": "Evidence",
  "id": "tests-fixtures-readme.generated-waveform-audio",
  "title": "Generated audio for waveform tests",
  "evidence": {
    "path": "tests/fixtures/README.md",
    "scope": "generated-waveform-audio",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "759f764dff9c9d9b1f50efecdd46835471f19189",
    "limits": "Reviewed that waveform tests synthesize their PCM and compressed tones at runtime and otherwise read only the documented first-party synthetic silence and Film tone fixtures; no new media file is committed. Media rights for the existing fixtures keep their documented provenance. Re-checked after the main-thread lock test changed: it also decodes its runtime-generated five-minute MP3 tone in process as a control and commits no new media. When the unreleased prototype waveform preview was retired, its sources here were replaced by their successors, result_media.py and test_result_media.py, without re-reviewing this topic's other claims. The current saved media claims are evidenced by this document's saved-media-playback topic. On 2026-10-12 test_result_media.py was re-checked after it added a 1 s stereo 44.1 kHz tone: it still writes 16-bit PCM WAV tones at runtime and commits no media file; the other sources are unchanged. The Studio first-draw test added later that day reuses the same generated stereo tone and commits no media file. Re-checked on 2026-10-12, not a full re-review: test_result_media.py added only system player launcher tests, which use the stub MP4 header and commit no media file. These sources' fingerprints are the changed files'; the review date and base revision are unchanged. Also re-checked on 2026-10-12: the saved media timer now logs and survives a failed redraw instead of being unregistered, with a native test; this topic's claims do not describe that path. Re-checked on 2026-10-13 for in-extension audio playback (#435), not a full re-review: the paragraph now also lists the audio player tests, covered by the in-extension-audio-playback topic, and points listening acceptance to #440. The fingerprints of test_result_media.py stay as recorded: they already differed on main before this change, for changes this re-check did not review. The review date and base revision are unchanged.",
    "sources": {
      "tests/unit/test_audio_waveform.py": "8a165f722f77ca93f8ca5478ce913cea1b672677b6440f5f27e70d1d96201081",
      "tests/unit/test_audio_decode.py": "b9ec6010f524620c8597566d654eeebef5044bd4b317aecb313e59b8cf9da734",
      "tests/blender/test_result_media.py": "7c255c3e9a9a04806f5588e0d1d50fb69d7fa46028f43c0458c9327a6f9921e9",
      "tests/blender/test_result_previews.py": "fd31993233db037d73220f4c5e67355da6af5688c864fbe2f62848f228af4c80",
      "tests/blender/test_waveform_worker.py": "5e03524a94fcedee799c9030c9b6a17ee872d9b8982349602c60bb369a62a230"
    }
  }
}
---

# Generated audio for waveform tests

Evidence for [the canonical inventory](../../../tests/fixtures/README.md).
