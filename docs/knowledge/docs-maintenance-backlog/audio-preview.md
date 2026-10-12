---
{
  "type": "Evidence",
  "id": "docs-maintenance-backlog.audio-preview",
  "title": "docs/maintenance/backlog.md: audio preview",
  "description": "Repository evidence for the named source family and canonical document.",
  "evidence": {
    "path": "docs/maintenance/backlog.md",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-24",
    "limits": "Agent source inspection of the listed files; no live service calls, native runtime rerun or human verification in this review. Re-checked on 2026-10-12, not a full re-review: apply_audio.py lost only its unused system opener, which no control called, and was formatted; this topic's claims do not describe it. These sources' fingerprints are the changed files'; the review date and base revision are unchanged.",
    "sources": {
      "scenario/blender/apply_audio.py": "9cc2291528ad82aeffa2cc424a33846e52666e71d0b1cff43a8d8bf1abde8989"
    },
    "scope": "audio-preview",
    "base_revision": "cdc8775a4a074a4997eca84cec2699e0dbb16e8c"
  }
}
---

# docs/maintenance/backlog.md: audio preview

Evidence for [the canonical document](../../maintenance/backlog.md).

Source families separate independent maintenance work. The review date, coverage,
source fingerprints and document-wide limitations were preserved during the split.
Grouping sources does not renew the review or attribute every inherited claim to
this subset. Review and narrow this topic's limits when its evidence changes.
