---
{
  "type": "Evidence",
  "id": "docs-known-limitations.audio-preview",
  "title": "docs/KNOWN_LIMITATIONS.md: audio preview",
  "description": "Repository evidence for the named source family and canonical document.",
  "evidence": {
    "path": "docs/KNOWN_LIMITATIONS.md",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-25",
    "limits": "Agent source inspection of the listed files; no live service calls or human verification in this review. Local PCM-WAV preview controller, worker-only bounded snapshot/metadata reads, record/context guards, native preview lifecycle and synthetic fixture tests inspected. This adds existing Generations UI preview only; no durable65 identity, compact/expanded66 integration, compressed-format preview, provider acceptance or human listening is claimed. Other claims retain their earlier review scope. Review follow-up inspected two tracked reader slots, timer-checked loading deadlines, late outcome rejection, sanitized thread-start failure, loading-only cancellation and slower terminal context invalidation. Cancellation cannot interrupt an OS filesystem call; occupied reader slots are retained until their threads exit. Selecting another preview restarts an existing native timer at the loading interval; the installed-operator regression uses Blender timers with the GUI branch selected in an isolated background fixture. Full native suite passed on Blender 5.0.1 macOS arm64; no layout or decoder bytes changed.",
    "sources": {
      "scenario/blender/apply_audio.py": "f9372110a8a3a868804241f6f48d0245488a5c53a1a9cf4cb37790a806c9441b",
      "scenario/blender/audio_preview.py": "9d6673aeb3ca183c08e8197f67274ac499b1aaf473813447ccf74977c53d4ba3",
      "scenario/core/audio_waveform.py": "5d59bbc6a1d465750984a3bb82b8305f348007f759f53d180e4008774bde8df7",
      "tests/blender/test_audio_preview.py": "955951607f3506665a262b336c7f0c74edff29fabf7196956b65ade2e731bd7a",
      "tests/unit/test_audio_waveform.py": "70771c62f05fa33f2fd0354b482c208a226cd3641c51309ddf8bc6f7fcd875ec"
    },
    "scope": "audio-preview",
    "base_revision": "e013a26d7208f472b0d5d6fee1534763e2632f22"
  }
}
---

# docs/KNOWN_LIMITATIONS.md: audio preview

Evidence for [the canonical document](../../KNOWN_LIMITATIONS.md).

Source families separate independent maintenance work. The review date, coverage,
source fingerprints and document-wide limitations were preserved during the split.
Grouping sources does not renew the review or attribute every inherited claim to
this subset. Review and narrow this topic's limits when its evidence changes.
