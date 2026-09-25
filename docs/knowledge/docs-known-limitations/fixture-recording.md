---
{
  "type": "Evidence",
  "id": "docs-known-limitations.fixture-recording",
  "title": "docs/KNOWN_LIMITATIONS.md: fixture recording",
  "description": "Repository evidence for the named source family and canonical document.",
  "evidence": {
    "path": "docs/KNOWN_LIMITATIONS.md",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-25",
    "limits": "Agent source inspection of the listed files; no live service calls or human verification in this review. Local PCM-WAV preview controller, worker-only bounded snapshot/metadata reads, record/context guards, native preview lifecycle and synthetic fixture tests inspected. This adds existing Generations UI preview only; no durable65 identity, compact/expanded66 integration, compressed-format preview, provider acceptance or human listening is claimed. Other claims retain their earlier review scope. Review follow-up inspected two tracked reader slots, timer-checked loading deadlines, late outcome rejection, sanitized thread-start failure, loading-only cancellation and slower terminal context invalidation. Cancellation cannot interrupt an OS filesystem call; occupied reader slots are retained until their threads exit. Selecting another preview restarts an existing native timer at the loading interval; the installed-operator regression uses Blender timers with the GUI branch selected in an isolated background fixture. Full native suite passed on Blender 5.0.1 macOS arm64; no layout or decoder bytes changed.",
    "sources": {
      "tests/fixtures/README.md": "041796a3008fc6724f3475510a6602c2ce6f9ffcedab3cc0b9865e4ea521e963"
    },
    "scope": "fixture-recording",
    "base_revision": "e013a26d7208f472b0d5d6fee1534763e2632f22"
  }
}
---

# docs/KNOWN_LIMITATIONS.md: fixture recording

Evidence for [the canonical document](../../KNOWN_LIMITATIONS.md).

Source families separate independent maintenance work. The review date, coverage,
source fingerprints and document-wide limitations were preserved during the split.
Grouping sources does not renew the review or attribute every inherited claim to
this subset. Review and narrow this topic's limits when its evidence changes.
