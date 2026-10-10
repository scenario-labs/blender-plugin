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
    "limits": "Reviewed that waveform tests synthesize their PCM and compressed tones at runtime and otherwise read only the documented first-party synthetic silence and Film tone fixtures; no new media file is committed. Media rights for the existing fixtures keep their documented provenance. Re-checked after the main-thread lock test changed: it also decodes its runtime-generated five-minute MP3 tone in process as a control and commits no new media. After this review, the unreleased prototype waveform preview was retired; its sources here were replaced by their successors, result_media.py and test_result_media.py, without re-reviewing this topic's other claims. The current saved media claims are evidenced by this document's saved-media-playback topic.",
    "sources": {
      "tests/unit/test_audio_waveform.py": "8a165f722f77ca93f8ca5478ce913cea1b672677b6440f5f27e70d1d96201081",
      "tests/unit/test_audio_decode.py": "3191b66bb5ed1cb995165ebe5f9736d06a84fb9effca42cd75a23dca41c31196",
      "tests/blender/test_result_media.py": "250abc036f5b46890c384b17d25311ee8c59e57fb1cb84e45233e77cd49c8a2f",
      "tests/blender/test_result_previews.py": "fd31993233db037d73220f4c5e67355da6af5688c864fbe2f62848f228af4c80",
      "tests/blender/test_waveform_worker.py": "5e03524a94fcedee799c9030c9b6a17ee872d9b8982349602c60bb369a62a230"
    }
  }
}
---

# Generated audio for waveform tests

Evidence for [the canonical inventory](../../../tests/fixtures/README.md).
