---
{
  "type": "Evidence",
  "id": "docs-known-limitations.audio-preview",
  "title": "docs/KNOWN_LIMITATIONS.md: audio preview",
  "description": "Repository evidence for the named source family and canonical document.",
  "evidence": {
    "path": "docs/KNOWN_LIMITATIONS.md",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "limits": "Agent source inspection of the listed files; no live service calls or human verification in this review. Local PCM-WAV preview controller, worker-only bounded snapshot/metadata reads, record/context guards, native preview lifecycle and synthetic fixture tests inspected. This adds existing Generations UI preview only; no durable65 identity, compact/expanded66 integration, compressed-format preview, provider acceptance or human listening is claimed. Other claims retain their earlier review scope. Review follow-up inspected two tracked reader slots, timer-checked loading deadlines, late outcome rejection, sanitized thread-start failure, loading-only cancellation and slower terminal context invalidation. Cancellation cannot interrupt an OS filesystem call; occupied reader slots are retained until their threads exit. Selecting another preview restarts an existing native timer at the loading interval; the installed-operator regression uses Blender timers with the GUI branch selected in an isolated background fixture. That follow-up changed no layout or decoder bytes; its full native suite passed on Blender 5.0.1 macOS arm64. A later scoped review re-checked this document's audio preview claims: draw-time wrap columns and waveform icon scale now follow preferences.system.ui_scale (1 when background Blender reports 0), not pixel size times resolution scale; an installed synthetic-preferences test covers this on Blender 5.1.2. The preview was not physically checked at any resolution scale; physical UI evidence remains #66/#68. After this review, the unreleased prototype waveform preview was retired; its sources here were replaced by their successors, result_media.py and test_result_media.py, without re-reviewing this topic's other claims. The current saved media claims are evidenced by this document's saved-media-playback topic.",
    "sources": {
      "scenario/blender/apply_audio.py": "f9372110a8a3a868804241f6f48d0245488a5c53a1a9cf4cb37790a806c9441b",
      "scenario/blender/result_media.py": "3dedc599853505ebbb12be68bd2406e45cf5eaee16090de77237fd2b4dba1607",
      "scenario/core/audio_waveform.py": "5d59bbc6a1d465750984a3bb82b8305f348007f759f53d180e4008774bde8df7",
      "tests/blender/test_result_media.py": "250abc036f5b46890c384b17d25311ee8c59e57fb1cb84e45233e77cd49c8a2f",
      "tests/unit/test_audio_waveform.py": "70771c62f05fa33f2fd0354b482c208a226cd3641c51309ddf8bc6f7fcd875ec"
    },
    "scope": "audio-preview",
    "base_revision": "fb699b8555f7cee62147794516cc7aaa224864f7"
  }
}
---

# docs/KNOWN_LIMITATIONS.md: audio preview

Evidence for [the canonical document](../../KNOWN_LIMITATIONS.md).

Source families separate independent maintenance work. The review date, coverage,
source fingerprints and document-wide limitations were preserved during the split.
Grouping sources does not renew the review or attribute every inherited claim to
this subset. Review and narrow this topic's limits when its evidence changes.
