---
{
  "type": "Evidence",
  "id": "docs-known-limitations.runtime-integration",
  "title": "docs/KNOWN_LIMITATIONS.md: runtime integration",
  "description": "Repository evidence for the named source family and canonical document.",
  "evidence": {
    "path": "docs/KNOWN_LIMITATIONS.md",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-25",
    "limits": "Agent source inspection of the listed files; no live service calls or human verification in this review. Local PCM-WAV preview controller, worker-only bounded snapshot/metadata reads, record/context guards, native preview lifecycle and synthetic fixture tests inspected. This adds existing Generations UI preview only; no durable65 identity, compact/expanded66 integration, compressed-format preview, provider acceptance or human listening is claimed. Other claims retain their earlier review scope. Review follow-up inspected two tracked reader slots, timer-checked loading deadlines, late outcome rejection, sanitized thread-start failure, loading-only cancellation and slower terminal context invalidation. Cancellation cannot interrupt an OS filesystem call; occupied reader slots are retained until their threads exit. Selecting another preview restarts an existing native timer at the loading interval; the installed-operator regression uses Blender timers with the GUI branch selected in an isolated background fixture. Full native suite passed on Blender 5.0.1 macOS arm64; no layout or decoder bytes changed.",
    "sources": {
      "scenario/blender/capture.py": "b8c2caae26103f45ea2bd619578360db3b464faf9f21a2938f033d630975016e",
      "scenario/blender/history.py": "c34d723e29b39fc88b3cd6ec88a188644dd2bb273a7ef2bad63d8f97e61d6df6",
      "scenario/blender/panels.py": "38583709a817e6269dd88459bf5a391ac1c3b2242d12e743ca0b2120b8a0075a",
      "scenario/blender/props.py": "0cac5c223860ed7e3709fda2a415ed1a7847c990d26d42ede0a0ce7def10ac21",
      "scenario/blender/registry.py": "8506ea846369c68cecb585830d336162c94b51ab00fd3043ad9950f789f2a4c0",
      "scenario/blender/runtime.py": "2afa6267f835569288ae6d1947af5410b05a0bbdcd3bbad985ff30a6dcb8a000"
    },
    "scope": "runtime-integration",
    "base_revision": "e013a26d7208f472b0d5d6fee1534763e2632f22"
  }
}
---

# docs/KNOWN_LIMITATIONS.md: runtime integration

Evidence for [the canonical document](../../KNOWN_LIMITATIONS.md).

Source families separate independent maintenance work. The review date, coverage,
source fingerprints and document-wide limitations were preserved during the split.
Grouping sources does not renew the review or attribute every inherited claim to
this subset. Review and narrow this topic's limits when its evidence changes.
